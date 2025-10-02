# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Stack is a lightweight CLI tool for managing stacked Git branches, written in Python. It's a single-file application (`stack.py`) that provides a simplified alternative to Graphite CLI for managing dependent branches without requiring cloud services or external dependencies beyond Python 3 and Git.

## Core Architecture

### Single-File Design
The entire application is contained in `stack.py` (~920 lines). This intentional design choice makes the tool easy to install, understand, and modify.

### Metadata System
Stack maintains branch relationships in `.git/stack-metadata.json` with the structure:
```json
{
  "main_branch": "main",
  "stacks": {
    "main": {
      "parent": null,
      "children": ["feature1", "feature2"]
    },
    "feature1": {
      "parent": "main",
      "children": ["feature1-child"]
    }
  }
}
```

This metadata is the source of truth for:
- Parent-child relationships between branches
- Which branches belong to which stacks
- The base branch (default: "main")

**Important:** The main branch itself is always included in `stacks` with `parent: null`. This ensures consistent data model and eliminates special-case handling throughout the codebase.

### StackManager Class
The `StackManager` class is the core component that handles:
- **Metadata management**: Loading/saving `.git/stack-metadata.json` and backup
- **Git operations**: All Git commands go through `_run_git()` method
- **Branch tracking**: Maintains parent-child relationships
- **Recursive restacking**: When a branch changes, all descendants are automatically rebased
- **Cycle detection**: Prevents infinite recursion on corrupted metadata
- **Input validation**: Validates branch names and commit messages

### Key Operations

**Creating branches** (`create` method):
- Validates branch name according to Git rules
- Blocks creation in detached HEAD state with helpful error
- Creates branch from current branch
- **User must stage changes manually** with `git add` before running
- Only commits if there are staged changes and a message is provided
- Validates commit message (non-empty)
- Updates metadata to track parent-child relationship

**Restacking** (`_restack_all_from` method):
- Recursively rebases child branches onto their parents
- **Includes cycle detection** to prevent infinite recursion
- Handles conflicts by exiting and prompting user to resolve
- Critical for maintaining stack integrity after modifications

**Syncing** (`sync` method):
- Checks for remote existence (gracefully handles local-only repos)
- Pulls latest main branch (only if remote/upstream exists)
- Recursively restacks all branches from main
- Can force reset with `--force` flag
- Force mode includes safety checks:
  - Detects local commits and uncommitted changes
  - Shows what will be lost
  - Creates timestamped backup branch automatically (using Python time, not shell)
  - Requires explicit 'yes' confirmation

**Modifying branches** (`modify` method):
- Amends the last commit with staged changes
- **User must stage changes manually** with `git add` before running
- Returns with error if no staged changes exist
- Automatically restacks all child branches after amendment

**Navigation** (`up`/`down`/`top`/`bottom`):
- `up`/`down`: Move between parent/child branches
- `top`/`bottom`: Jump to stack endpoints
- Uses metadata to traverse relationships
- **Includes cycle detection** to prevent infinite loops on corrupted metadata
- Validates parent existence before checkout
- Interactive selection when multiple children exist
- Retry loops for invalid input with option to quit

**Tree visualization** (`tree` method):
- Displays branch hierarchy starting from main
- **Includes cycle detection** with visual warnings
- Shows current branch indicator
- Identifies orphaned branches (not connected to main)
- Auto-cleans deleted branches before display

**Rebase state tracking**:
- Saves which branch is being rebased to `.git/stack-rebase-state.json`
- Allows `continue` command to resume after conflict resolution
- Verifies branch state after rebase completes
- Prevents race conditions during multi-branch rebasing

**Atomic metadata updates**:
- Backs up metadata before critical operations (`create`, `sync`, `modify`)
- Automatically restores from backup if operation fails
- Backup persists at `.git/stack-metadata.backup.json`
- Manual restore via `stack restore-backup` command
- Ensures metadata consistency even if process crashes

**Submitting PRs** (`submit` method):
- Pushes all branches in the stack to origin with upstream tracking
- Creates PRs with correct base branches (each branch targets its parent)
- Updates existing PRs if base branch changes
- Requires GitHub CLI (`gh`) installed and authenticated
- Shows PR URLs for easy access
- Automatically generates PR body with stack context and commit messages

## Important Workflow Changes

### Staged Files Required for Branch Creation
The tool **requires staged files before creating branches**. Users cannot create branches without staged changes:

```bash
# Creating a new branch with changes
git add file1.py file2.py
stack create feature-branch -m "Add new feature"

# Modifying an existing branch
git add updated-file.py
stack modify
```

This design ensures:
- Every branch has a meaningful commit (no empty branches)
- Explicit staging prevents accidentally committing sensitive files (.env, credentials)
- No unrelated changes sneak into commits
- Clear intent: users must stage before branching

### Metadata Cleanup
The tool automatically cleans up deleted branches when running:
- `stack tree`
- `stack sync`
- `stack status`

Deleted branches are removed from metadata and their children are reassigned to their parent.

### Force Sync Safety
When using `stack sync --force`:
- Tool detects if local work will be lost
- Shows exactly what commits/changes will be destroyed
- Automatically creates backup branch (e.g., `main-backup-1234567890`)
- Requires explicit 'yes' confirmation before proceeding
- User can restore from backup branch if needed

### Metadata Backup and Recovery
The tool maintains automatic backups for recovery:
- Backup created before all critical operations
- Stored at `.git/stack-metadata.backup.json` (persisted)
- `stack status` shows if recent backup available
- `stack restore-backup` command for manual recovery
- Requires confirmation before restoring
- Provides rollback if operations fail or metadata gets corrupted

### GitHub PR Integration
The `submit` command automates PR creation for stacked branches:
- Each branch creates a PR targeting its parent (not main)
- Automatically pushes branches with upstream tracking
- Updates existing PRs if base changes
- Generates PR body with stack visualization and commit list
- Requires GitHub CLI (`gh`) for automation
- Falls back to manual instructions if `gh` not available

## Development Commands

### Running the CLI
```bash
# Direct execution (development)
python3 stack.py <command>

# Installed version
stack <command>
```

### Installation
```bash
./install.sh
```
Copies `stack.py` to `~/.local/bin/stack` and makes it executable.

### Testing
```bash
./test-stack.sh
```
Creates a temporary Git repository at `/tmp/stack-test-*` and runs through all major commands to verify functionality. The test repo is preserved for manual inspection.

## Important Implementation Details

### Conflict Handling
When a rebase fails, the tool:
1. Saves rebase state to `.git/stack-rebase-state.json`
2. Exits with status code 1
3. Prompts user to run `stack continue`
4. Does NOT call `git rebase --continue` directly - users must use `stack continue` to ensure children are also restacked
5. Verifies branch state matches expected state when continuing

### Branch Existence Checks
Before operating on branches, the code checks if they exist using `_branch_exists()`. This prevents errors when branches are deleted outside of Stack.

### Interactive Mode
Several commands (`checkout`, `down`, `top`) support interactive selection when multiple options exist:
- Numbered menus for selection
- Retry loops for invalid input
- Option to quit with 'q'
- Clear error messages with valid ranges

### Cycle Detection
The tool detects cycles in branch hierarchies:
- `tree()` shows visual warnings but continues
- `_restack_all_from()` exits immediately (unsafe to continue)
- Uses visited set to track traversed branches
- Provides clear error messages pointing to corrupted metadata

### Detached HEAD Handling
The tool prevents operations in detached HEAD state:
- `create` command blocks with helpful error message
- `status` command shows warning
- Maintains invariant: metadata parent matches Git history

### Local-Only Repository Support
The tool works without remotes:
- `sync` detects missing remote/upstream
- Provides "local-only sync" message
- Gracefully skips pull operations
- Still performs restacking of local branches

### Git Root Detection
The tool finds the Git repository root using `git rev-parse --show-toplevel` to ensure metadata is stored in the correct `.git` directory regardless of current working directory.

### Command-Line Parsing
The tool uses Python's `argparse` module for robust argument parsing:
- Supports both short (`-m`) and long (`--message`) flags
- Auto-generates help text for all commands
- Handles quoted strings properly
- Flexible flag ordering
- Built-in validation and error messages
- Each command has its own help (e.g., `stack create --help`)

## Key Design Principles

1. **Simplicity over features**: Minimal GitHub integration (optional PR creation). No cloud sync or web UI. Just core stacking workflow.

2. **Git as foundation**: Stack is a thin wrapper around Git. Users can always fall back to regular Git commands.

3. **Stateless operations**: Each command loads metadata fresh, performs operation, saves metadata. No daemon or background process.

4. **Recursive algorithms**: Most operations (restacking, tree display, navigation) use recursion to traverse parent-child relationships.

5. **Fail-fast on conflicts**: When rebase conflicts occur, stop immediately and let user resolve rather than trying to auto-resolve.

6. **Atomic operations**: Critical operations use backup/restore pattern to ensure metadata stays consistent with Git state even if process crashes or fails.

## Modifying the Code

### Adding a New Command
1. Add method to `StackManager` class
2. Add subparser in `main()` function using `argparse`
3. Add command handler in the main try-catch block
4. Help text is auto-generated by argparse

**Example:**
```python
# In main()
subparsers.add_parser('mycommand', help='Description of my command')

# In command dispatch
elif args.command == "mycommand":
    manager.mycommand()
```

### Changing Metadata Format
The metadata is loaded in `_load_metadata()` and saved in `_save_metadata()`. Any schema changes should maintain backward compatibility or include migration logic.

**Important:** Main branch must always be in stacks with `parent: null`.

### Handling Git Operations
Always use `_run_git()` method rather than calling subprocess directly. It handles:
- Command construction
- Output capture
- Error checking
- Consistent subprocess interface

### Input Validation
Use existing validation helpers:
- `_validate_branch_name()` - Validates branch names per Git rules
- `_is_detached_head()` - Checks for detached HEAD state
- `_has_remote()` - Checks if remote exists
- `_has_upstream_branch()` - Checks if branch has upstream
- `_branch_exists()` - Checks if local branch exists

## Testing Approach

The `test-stack.sh` script covers:
1. Branch creation and stacking
2. Tree visualization
3. Navigation (up/down/top/bottom)
4. Modify and restack workflow
5. Sync with main after updates

When adding new features, extend this test script to cover new commands.
