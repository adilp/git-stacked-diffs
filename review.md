# Code Review: Stack CLI

## Critical Issues

### 1. **No Metadata Cleanup for Deleted Branches** ✅ FIXED
~~When branches are deleted outside of Stack (e.g., `git branch -D feature`), the metadata still references them. The parent's children list is never cleaned up, leading to:~~
- ~~Orphaned references accumulating over time~~
- ~~Potential errors when operations traverse these ghost branches~~
- ~~The tool detects missing branches but doesn't remove them from metadata~~

**Fix implemented:** Added `_cleanup_deleted_branches()` method (stack.py:39-74) that:
- Detects branches in metadata that no longer exist in Git
- Removes them from parent's children list
- Reassigns their children to their parent (maintaining the stack structure)
- Automatically runs during `tree`, `sync`, and `status` commands
- Provides user feedback when branches are cleaned up

### 2. **Race Condition in `continue_rebase`** ✅ FIXED
~~After `git rebase --continue` succeeds, the code calls `_restack_all_from(current_branch)` assuming we're still on the same branch. However:~~
- ~~The rebase might have been the last commit, leaving us in detached HEAD or different state~~
- ~~No verification that we're actually on the expected branch before continuing~~
- ~~Could restack wrong branch's children~~

**Fix implemented:** Added persistent rebase state tracking (stack.py:83-100, 271-307) that:
- Saves which branch is being rebased to `.git/stack-rebase-state.json` before each rebase operation
- Loads the saved state in `continue_rebase` to know which branch to restack
- Verifies current branch matches expected branch after rebase completes
- Warns user if branch state is unexpected but attempts to continue safely
- Clears state file after successful completion to prevent stale state
- Prevents confusion if user runs `stack continue` without an active stack rebase

### 3. **Unsafe `modify` Command** ✅ FIXED
~~- Always does `git add -A` without asking, staging *everything* including potentially unwanted files~~
~~- No confirmation before amending~~
~~- Could accidentally include unrelated changes in the amendment~~

**Fix implemented:** Removed automatic staging from `modify` command (stack.py:310-336) that:
- No longer runs `git add -A` automatically
- Checks if there are staged changes before attempting to amend
- Returns with helpful error message if no staged changes exist
- Puts control back in user's hands to stage exactly what they want
- User must explicitly `git add` files before running `stack modify`

### 4. **`create` Auto-Stages Everything** ✅ FIXED
~~- `git add -A` adds ALL files including untracked ones without warning~~
~~- No way to selectively stage files~~
~~- Could commit sensitive files (.env, credentials, etc.)~~

**Fix implemented:** Removed automatic staging from `create` command (stack.py:125-142) that:
- No longer runs `git add -A` automatically
- Checks if there are staged changes before creating commit
- Warns user if no staged changes and creates branch without commit
- User must explicitly `git add` files before running `stack create`
- Prevents accidentally committing sensitive or unrelated files

### 5. **Main Branch Not in Metadata** ✅ FIXED
~~The main branch itself is never added to `metadata["stacks"]`, yet code checks `if base_branch not in self.metadata["stacks"]`. This means:~~
- ~~Can't restack from main properly~~
- ~~`tree()` command special-cases main branch~~
- ~~Inconsistent data model~~

**Fix implemented:** Main branch now included in metadata (stack.py:33-49, 51-61, 433-451) that:
- `_load_metadata()` ensures main branch is always in stacks with `parent: None`
- Main branch has no parent (represented as `None`)
- All code updated to handle `None` parent correctly
- `up()` command checks for `None` parent and displays appropriate message
- `bottom()` command stops at branches with `None` or main as parent
- `_cleanup_deleted_branches()` never removes the main branch
- Consistent data model throughout the application

## Major Issues

### 6. **No Atomic Metadata Updates** ✅ FIXED
~~If a git operation succeeds but the process crashes before `_save_metadata()`, the metadata becomes out of sync with actual Git state. No recovery mechanism exists.~~

**Fix implemented:** Added atomic metadata updates with backup/restore (stack.py:97-115, 159-203, 233-280, 371-411) that:
- Creates backup of metadata file before any git operations
- Wraps critical operations (`create`, `sync`, `modify`) in try-catch blocks
- Automatically restores metadata from backup if operation fails
- Clears backup file after successful completion
- Backup stored at `.git/stack-metadata.backup.json`
- Ensures metadata stays consistent with Git state even if process crashes
- Provides clear error messages when restoration occurs

### 7. **Dangerous `sync --force`** ✅ FIXED
~~- Does `git reset --hard origin/main` with no confirmation or warning about losing local commits~~
~~- No backup or stash of local changes~~
~~- Could destroy uncommitted work on main branch~~

**Fix implemented:** Added safety measures to `sync --force` (stack.py:233-295) that:
- Checks for local commits that will be lost (using `git rev-list`)
- Checks for uncommitted changes on main branch
- Shows user exactly what will be destroyed (commit log + file changes)
- Automatically creates timestamped backup branch (e.g., `main-backup-1234567890`)
- Requires explicit 'yes' confirmation to proceed
- Allows user to cancel without any changes
- Provides instructions to restore from backup branch if needed

### 8. **Parent Validation Missing** ✅ FIXED
~~`up()` blindly checks out the parent without verifying:~~
- ~~Parent branch actually exists~~
- ~~Parent hasn't been deleted~~
- ~~Results in cryptic Git errors if parent is gone~~

**Fix implemented:** Added parent validation to `up()` command (stack.py:540-558) that:
- Checks if parent is `None` (at root branch)
- Verifies parent branch exists using `_branch_exists()`
- Shows clear error message if parent is missing
- Prevents cryptic Git errors
- Also fixed in issue #5 when implementing main branch in metadata

### 9. **Infinite Loop Potential in `find_bottom`** ✅ FIXED
~~If metadata has circular references (parent → child → parent), `find_bottom()` will infinitely recurse. No cycle detection.~~

**Fix implemented:** Added cycle detection to `top()` and `bottom()` methods (stack.py:498-547) that:
- Uses visited set to track branches already traversed
- Detects cycles immediately when a branch is visited twice
- Shows clear error message indicating corrupted metadata
- Returns current branch as safe fallback instead of crashing
- Prevents infinite recursion
- Applied to both `top()` (traversing children) and `bottom()` (traversing parents)

### 10. **Command-Line Parsing is Fragile** ✅ FIXED
~~Manual argv parsing means:~~
- ~~`-m` flag must be exactly at position 3~~
- ~~Can't handle `-m "message"` with quotes as single arg~~
- ~~No support for `--message` or other flag formats~~
- ~~Breaks if user adds other flags~~

**Fix implemented:** Replaced manual argv parsing with argparse (stack.py:625-730) that:
- Uses Python's built-in `argparse` module for robust argument parsing
- Supports both `-m` and `--message` flag formats
- Handles quoted strings properly (e.g., `-m "commit message"`)
- Provides automatic `--help` for each command
- Validates arguments and shows clear error messages
- Supports flexible flag ordering (flags can appear anywhere)
- Auto-generated help text for all commands
- Example: `stack create --help` shows detailed usage

## Security/Safety Issues

### 11. **No Input Validation on Branch Names** ✅ FIXED
~~Branch names aren't validated before passing to Git. Could allow:~~
- ~~Shell injection via branch names with special chars~~
- ~~Though subprocess with list args mitigates this somewhat~~

**Fix implemented:** Added comprehensive branch name validation (stack.py:160-193, 197-199) that:
- Validates branch names according to Git's official rules
- Rejects names starting with '.'
- Blocks invalid characters (~^:\[]?* and spaces)
- Prevents control characters (ASCII < 32 or 127)
- Checks for dangerous patterns (.., @{, .lock)
- Enforces reasonable length limit (255 chars)
- Shows clear error messages for each validation failure
- Exits before attempting git operations if invalid

### 12. **Empty Commit Messages Allowed** ✅ FIXED
~~If `-m` is provided but message is empty, creates commit with empty message (Git's default behavior kicks in, but unexpected).~~

**Fix implemented:** Added commit message validation (stack.py:212-215) that:
- Checks if message is empty or only whitespace
- Shows clear error message if empty
- Creates branch without commit if message invalid
- Prevents confusing Git behavior with empty commits

## Usability Issues

### 13. **No Undo/History** ✅ FIXED
~~Once metadata is overwritten, there's no way to recover previous state. No `.git/stack-metadata.json.backup` or versioning.~~

**Fix implemented:** Added backup and restore functionality (stack.py:98-117, 678-700) that:
- Automatically creates backup before all critical operations (from issue #6)
- Backup file persists at `.git/stack-metadata.backup.json` (not deleted)
- New `stack restore-backup` command for manual recovery
- `stack status` shows if recent backup is available
- Requires confirmation before restoring from backup
- Shows backup age and restore instructions
- Provides rollback capability if operations go wrong

### 14. **Silent Failures in Interactive Mode** ✅ FIXED
~~Invalid input in interactive selections just prints error but doesn't retry or exit with error code.~~

**Fix implemented:** Improved interactive selection in `checkout` and `down` commands (stack.py:263-284, 647-666) that:
- Uses retry loop instead of single attempt
- Prompts continuously until valid input or quit
- Added 'q' option to cancel/quit at any time
- Shows clear error messages with valid range
- Strips whitespace from input
- Returns cleanly on cancel (no error code needed for user cancellation)
- Better user experience with helpful prompts

### 15. **`top()` Only Follows First Child** ✅ FIXED
~~If a branch has multiple children, `top()` arbitrarily picks `children[0]`. User has no control over which branch to traverse.~~

**Fix implemented:** Made `top()` interactive when multiple children exist (stack.py:551-601) that:
- Detects when branch has multiple children
- Shows interactive menu to choose which path to follow
- Allows user to select which child branch to traverse
- Option to quit/stay at current branch ('q')
- Recursively prompts at each branch with multiple children
- Automatic traversal when only single child exists
- Full user control over navigation path

## Recommendations Priority

### Fix Immediately
1. Add metadata cleanup for deleted branches (#1)
2. Validate parent exists before checkout (#8)
3. Add confirmation for destructive operations (#3, #7)
4. Fix `create` auto-staging to be more selective (#4)

### Fix Soon
5. Add cycle detection (#9)
6. Include main branch in metadata properly (#5)
7. Better command-line parsing (use argparse) (#10)
8. Verify branch state before continuing rebase (#2)
