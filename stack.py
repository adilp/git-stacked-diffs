#!/usr/bin/env python3
"""
Stack - A simple stacked branches CLI for Git
Inspired by Graphite CLI but simplified
"""

import argparse
import json
import os
import subprocess
import sys
import termios
import tty
from pathlib import Path
from typing import Dict, List, Optional

class StackManager:
    """Manages stacked branch metadata and operations"""
    
    def __init__(self):
        self.git_root = self._get_git_root()
        self.metadata_file = Path(self.git_root) / ".git" / "stack-metadata.json"
        self.metadata_backup_file = Path(self.git_root) / ".git" / "stack-metadata.backup.json"
        self.rebase_state_file = Path(self.git_root) / ".git" / "stack-rebase-state.json"
        self.metadata = self._load_metadata()
    
    def _get_git_root(self) -> str:
        """Get the root directory of the git repository"""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    
    def _detect_main_branch(self) -> str:
        """Auto-detect the main branch name"""
        # Try to get default branch from any remote's HEAD
        # Get list of all remotes
        remotes_result = self._run_git("remote", check=False)
        if remotes_result.returncode == 0 and remotes_result.stdout.strip():
            remotes = remotes_result.stdout.strip().split('\n')
            # Try each remote (prioritize 'origin' if it exists)
            if 'origin' in remotes:
                remotes = ['origin'] + [r for r in remotes if r != 'origin']

            for remote in remotes:
                result = self._run_git("symbolic-ref", f"refs/remotes/{remote}/HEAD", check=False)
                if result.returncode == 0:
                    # Output is like "refs/remotes/origin/main"
                    ref = result.stdout.strip()
                    remote_prefix = f"refs/remotes/{remote}/"
                    if ref.startswith(remote_prefix):
                        return ref.replace(remote_prefix, "")

        # Fallback: check which common branch exists
        for candidate in ["main", "master", "develop", "trunk"]:
            if self._branch_exists(candidate):
                return candidate

        # Ultimate fallback
        return "main"

    def _load_metadata(self) -> Dict:
        """Load stack metadata from file"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            # Auto-detect main branch for new repos
            detected_main = self._detect_main_branch()
            metadata = {"stacks": {}, "main_branch": detected_main}

        # Ensure main branch is always in the stacks with no parent
        main_branch = metadata.get("main_branch", "main")
        if main_branch not in metadata["stacks"]:
            metadata["stacks"][main_branch] = {
                "parent": None,
                "children": []
            }

        return metadata

    def _cleanup_deleted_branches(self):
        """Remove references to branches that no longer exist in Git"""
        branches_to_remove = []
        main_branch = self.metadata["main_branch"]

        # Find branches in metadata that don't exist in Git
        # (skip the main branch itself)
        for branch_name in self.metadata["stacks"].keys():
            if branch_name != main_branch and not self._branch_exists(branch_name):
                branches_to_remove.append(branch_name)

        # Remove deleted branches from metadata
        for branch_name in branches_to_remove:
            branch_info = self.metadata["stacks"][branch_name]
            parent = branch_info["parent"]

            # Remove this branch from its parent's children list (if parent exists)
            if parent and parent in self.metadata["stacks"]:
                if branch_name in self.metadata["stacks"][parent]["children"]:
                    self.metadata["stacks"][parent]["children"].remove(branch_name)

            # Reassign this branch's children to its parent
            for child in branch_info["children"]:
                if child in self.metadata["stacks"]:
                    self.metadata["stacks"][child]["parent"] = parent
                    # Add children to parent's children list if parent exists
                    if parent and parent in self.metadata["stacks"]:
                        if child not in self.metadata["stacks"][parent]["children"]:
                            self.metadata["stacks"][parent]["children"].append(child)

            # Remove the branch from metadata
            del self.metadata["stacks"][branch_name]

        # Save if we made changes
        if branches_to_remove:
            self._save_metadata()
            return branches_to_remove
        return []

    def _save_metadata(self):
        """Save stack metadata to file"""
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)

    def _backup_metadata(self):
        """Create a backup of the current metadata file"""
        if self.metadata_file.exists():
            import shutil
            shutil.copy2(self.metadata_file, self.metadata_backup_file)

    def _restore_metadata_from_backup(self):
        """Restore metadata from backup file"""
        if self.metadata_backup_file.exists():
            import shutil
            shutil.copy2(self.metadata_backup_file, self.metadata_file)
            self.metadata = self._load_metadata()
            return True
        return False

    def _clear_metadata_backup(self):
        """Remove the backup file after successful operation"""
        # Keep the backup file for recovery - don't delete it
        # This allows users to manually restore if needed
        pass

    def _save_rebase_state(self, branch: str):
        """Save the branch being rebased for continue command"""
        state = {"branch": branch}
        with open(self.rebase_state_file, 'w') as f:
            json.dump(state, f)

    def _load_rebase_state(self) -> Optional[str]:
        """Load the branch that was being rebased"""
        if self.rebase_state_file.exists():
            with open(self.rebase_state_file, 'r') as f:
                state = json.load(f)
                return state.get("branch")
        return None

    def _clear_rebase_state(self):
        """Clear the rebase state file"""
        if self.rebase_state_file.exists():
            self.rebase_state_file.unlink()
    
    def _run_git(self, *args, check=True, capture=True) -> subprocess.CompletedProcess:
        """Run a git command"""
        cmd = ["git"] + list(args)
        if capture:
            return subprocess.run(cmd, capture_output=True, text=True, check=check)
        else:
            return subprocess.run(cmd, check=check)
    
    def _get_current_branch(self) -> str:
        """Get the current branch name"""
        result = self._run_git("branch", "--show-current")
        return result.stdout.strip()

    def _is_detached_head(self) -> bool:
        """Check if currently in detached HEAD state"""
        current = self._get_current_branch()
        return current == ""

    def _branch_exists(self, branch: str) -> bool:
        """Check if a branch exists"""
        result = self._run_git("show-ref", "--verify", f"refs/heads/{branch}", check=False)
        return result.returncode == 0

    def _has_remote(self, remote_name: str = "origin") -> bool:
        """Check if a remote exists"""
        result = self._run_git("remote", "get-url", remote_name, check=False)
        return result.returncode == 0

    def _has_upstream_branch(self, branch: str, remote: str = "origin") -> bool:
        """Check if a branch has an upstream on the remote"""
        result = self._run_git("rev-parse", "--verify", f"{remote}/{branch}", check=False)
        return result.returncode == 0

    def _validate_branch_name(self, branch_name: str) -> bool:
        """Validate branch name according to Git rules"""
        import re

        if not branch_name:
            print("⚠️  Branch name cannot be empty")
            return False

        # Git branch name rules
        invalid_patterns = [
            (r'^\.', "Branch name cannot start with '.'"),
            (r'\.\.|\.lock$|/$|^/', "Invalid pattern in branch name"),
            (r'[~^:\\\s\[\]?*]', "Branch name contains invalid characters (~^:\\[]?* or spaces)"),
            (r'\.\.', "Branch name cannot contain '..'"),
            (r'@\{', "Branch name cannot contain '@{'"),
            (r'^\.|\/\.|\.\/|\.\.$', "Branch name has invalid '.' placement"),
        ]

        for pattern, message in invalid_patterns:
            if re.search(pattern, branch_name):
                print(f"⚠️  Invalid branch name: {message}")
                return False

        # Check for control characters
        if any(ord(c) < 32 or ord(c) == 127 for c in branch_name):
            print("⚠️  Branch name cannot contain control characters")
            return False

        # Additional safety check: branch name should be reasonable length
        if len(branch_name) > 255:
            print("⚠️  Branch name too long (max 255 characters)")
            return False

        return True

    def create(self, branch_name: str, message: Optional[str] = None, no_commit: bool = False):
        """Create a new branch in the stack"""
        # Validate branch name
        if not self._validate_branch_name(branch_name):
            sys.exit(1)

        # Check for detached HEAD state
        if self._is_detached_head():
            print("⚠️  You are in detached HEAD state")
            print("Cannot create a stacked branch from detached HEAD because the parent is ambiguous.")
            print("\nOptions:")
            print("  1. Create branch from main:  git checkout main && stack create <name>")
            print("  2. Create branch from a specific branch first, then use stack")
            print(f"  3. Create untracked branch: git checkout -b {branch_name}")
            sys.exit(1)

        current_branch = self._get_current_branch()

        # Backup metadata before making changes
        self._backup_metadata()

        try:
            # Check if there are staged changes before creating the branch
            staged = self._run_git("diff", "--cached", "--quiet", check=False)
            has_staged_changes = staged.returncode != 0

            # Require staged changes before creating branch
            if not has_staged_changes:
                print("⚠️  No staged changes found.")
                print("You must stage files before creating a branch:")
                print(f"  git add <files>")
                print(f"  stack create {branch_name} -m \"Your message\"")
                return

            # If staged changes exist but no commit message, require a message or --no-commit flag
            if not no_commit and not message:
                print("⚠️  You have staged changes but no commit message provided.")
                print("Either:")
                print(f"  1. Provide a message: stack create {branch_name} -m \"Your message\"")
                print(f"  2. Create branch without committing (changes stay staged): stack create {branch_name} --no-commit")
                return

            # If message is provided but empty/whitespace, reject it
            if message and not message.strip():
                print("⚠️  Commit message cannot be empty or whitespace only")
                return

            # Create the new branch
            self._run_git("checkout", "-b", branch_name)

            # Commit if we have a message and it's not no_commit mode
            if message and not no_commit:
                # Commit the staged changes
                self._run_git("commit", "-m", message)
                print(f"✓ Committed staged changes")
            elif no_commit:
                print(f"ℹ️  Branch created with staged changes (not committed)")
                print(f"   Use 'git commit' or 'stack create <child-branch> -m \"message\"' to commit later")

            # Track this branch in the stack
            parent = current_branch if current_branch else self.metadata["main_branch"]
            self.metadata["stacks"][branch_name] = {
                "parent": parent,
                "children": []
            }

            # Update parent's children
            if parent in self.metadata["stacks"]:
                if branch_name not in self.metadata["stacks"][parent]["children"]:
                    self.metadata["stacks"][parent]["children"].append(branch_name)

            self._save_metadata()
            # Clear backup after successful operation
            self._clear_metadata_backup()
            print(f"✓ Created branch '{branch_name}' on top of '{parent}'")

        except Exception as e:
            # Restore metadata from backup on failure
            print(f"⚠️  Error during branch creation: {e}")
            if self._restore_metadata_from_backup():
                print("Metadata restored from backup")
            raise
    
    def _get_key(self):
        """Read a single keypress from stdin"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            # Handle arrow keys (escape sequences)
            if ch == '\x1b':
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A':
                        return 'up'
                    elif ch3 == 'B':
                        return 'down'
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _interactive_select(self, options: List[str], title: str, current_branch: Optional[str] = None) -> Optional[str]:
        """Interactive selection with arrow keys"""
        if not options:
            return None

        selected_idx = 0
        # Start at current branch if specified
        if current_branch and current_branch in options:
            selected_idx = options.index(current_branch)

        # Print title once
        print(f"? {title} (arrow keys to move, enter to select, q to quit)\n")

        first_draw = True
        while True:
            if not first_draw:
                # Move cursor up to redraw menu
                print(f'\033[{len(options)}A', end='')
            first_draw = False

            # Draw options
            for i, option in enumerate(options):
                # Clear line
                print('\033[K', end='')
                if i == selected_idx:
                    marker = "❯"
                    print(f"\033[36m{marker}   {option}\033[0m")  # Cyan for selected
                else:
                    marker = " "
                    print(f"{marker}   {option}")

            key = self._get_key()

            if key == 'up' and selected_idx > 0:
                selected_idx -= 1
            elif key == 'down' and selected_idx < len(options) - 1:
                selected_idx += 1
            elif key == '\r' or key == '\n':  # Enter
                print()  # Add newline after selection
                return options[selected_idx]
            elif key == 'q' or key == '\x03':  # q or Ctrl-C
                print()  # Add newline
                return None

    def checkout(self, branch_name: Optional[str] = None):
        """Checkout a branch (interactive if no name provided)"""
        if branch_name:
            # Validate that the branch exists before checkout
            if not self._branch_exists(branch_name):
                print(f"⚠️  Branch '{branch_name}' does not exist")
                print(f"Available branches: {', '.join(self.metadata['stacks'].keys())}")
                sys.exit(1)
            self._run_git("checkout", branch_name)
            print(f"✓ Checked out '{branch_name}'")
        else:
            # Interactive branch selection with arrow keys
            cleaned = self._cleanup_deleted_branches()
            if cleaned:
                print(f"🧹 Cleaned up {len(cleaned)} deleted branch(es): {', '.join(cleaned)}\n")

            branches = list(self.metadata["stacks"].keys())
            if not branches:
                print("No branches in stack")
                return

            # Filter to only branches that actually exist in Git
            existing_branches = [b for b in branches if self._branch_exists(b)]
            if not existing_branches:
                print("No existing branches found in Git")
                return

            current_branch = self._get_current_branch()
            selected_branch = self._interactive_select(existing_branches, "Checkout a branch", current_branch)

            if selected_branch:
                if not self._branch_exists(selected_branch):
                    print(f"⚠️  Branch '{selected_branch}' no longer exists")
                    return

                # Try to checkout, handle errors gracefully
                result = self._run_git("checkout", selected_branch, check=False)
                if result.returncode == 0:
                    print(f"✓ Checked out '{selected_branch}'")
                else:
                    print(f"⚠️  Failed to checkout '{selected_branch}'")
                    print(result.stderr)
                    if "would be overwritten" in result.stderr or "uncommitted changes" in result.stderr:
                        print("\nYou have uncommitted changes. Either:")
                        print("  1. Commit them: git add . && git commit -m 'message'")
                        print("  2. Stash them: git stash")
                        print("  3. Create a branch: stack create <branch-name> -m 'message'")
            else:
                print("Cancelled")
    
    def sync(self, force: bool = False):
        """Sync with remote and restack all branches"""
        main_branch = self.metadata["main_branch"]
        current_branch = self._get_current_branch()

        # Backup metadata before making changes
        self._backup_metadata()

        try:
            # Check for uncommitted changes before checkout
            status_result = self._run_git("status", "--porcelain", check=False)
            if status_result.stdout.strip():
                print("⚠️  You have uncommitted changes:")
                for line in status_result.stdout.strip().split('\n')[:5]:
                    print(f"  {line}")
                if len(status_result.stdout.strip().split('\n')) > 5:
                    print("  ...")
                print("\nCommit or stash your changes before syncing:")
                print("  1. Commit: git add . && git commit -m 'message'")
                print("  2. Stash: git stash")
                print("  3. Create branch: stack create <branch-name> -m 'message'")
                sys.exit(1)

            self._run_git("checkout", main_branch)

            # Check if remote exists
            if not self._has_remote("origin"):
                print(f"ℹ️  No remote 'origin' configured - performing local-only sync")
                print(f"✓ {main_branch} is local-only (no remote to pull from)")
            else:
                # Check if upstream branch exists
                if not self._has_upstream_branch(main_branch, "origin"):
                    print(f"ℹ️  No upstream branch 'origin/{main_branch}' - performing local-only sync")
                    print(f"✓ {main_branch} has no remote tracking branch")
                else:
                    print(f"🌲 Pulling {main_branch} from remote...")

                    # Pull latest changes
                    if force:
                        self._run_git("fetch", "origin", main_branch)

                        # Check if there are local commits that will be lost
                        local_commits = self._run_git("rev-list", f"origin/{main_branch}..{main_branch}", check=False)
                        has_local_commits = bool(local_commits.stdout.strip())

                        # Check if there are uncommitted changes
                        uncommitted = self._run_git("status", "--porcelain")
                        has_uncommitted = bool(uncommitted.stdout.strip())

                        if has_local_commits or has_uncommitted:
                            print(f"\n⚠️  WARNING: This will destroy local changes on '{main_branch}'!")

                            if has_local_commits:
                                # Show what commits will be lost
                                commit_log = self._run_git("log", "--oneline", f"origin/{main_branch}..{main_branch}")
                                print(f"\nLocal commits that will be LOST:")
                                for line in commit_log.stdout.strip().split('\n'):
                                    if line:
                                        print(f"  - {line}")

                            if has_uncommitted:
                                print(f"\nUncommitted changes that will be LOST:")
                                for line in uncommitted.stdout.strip().split('\n')[:5]:  # Show first 5 changes
                                    if line:
                                        print(f"  {line}")
                                if len(uncommitted.stdout.strip().split('\n')) > 5:
                                    print(f"  ... and more")

                            # Create backup branch using Python time instead of shell date
                            import time
                            backup_branch = f"{main_branch}-backup-{int(time.time())}"
                            print(f"\n💾 Creating backup branch: {backup_branch}")
                            self._run_git("branch", backup_branch)
                            print(f"✓ Backup created (you can restore with: git checkout {backup_branch})")

                            # Ask for confirmation
                            print(f"\nType 'yes' to continue with force reset, or anything else to cancel: ", end='')
                            confirmation = input().strip().lower()

                            if confirmation != 'yes':
                                print("❌ Sync cancelled")
                                self._clear_metadata_backup()
                                return

                        self._run_git("reset", "--hard", f"origin/{main_branch}")
                    else:
                        result = self._run_git("pull", "--rebase", check=False)
                        if result.returncode != 0:
                            print(f"⚠️  Failed to pull {main_branch}")
                            print(result.stderr)
                            print("\nYou may have uncommitted changes. Either:")
                            print("  1. Commit your changes: git add . && git commit -m 'message'")
                            print("  2. Stash your changes: git stash")
                            print("  3. Use force sync: stack sync --force")
                            sys.exit(1)

                    print(f"✓ {main_branch} is up to date")

            # Clean up any deleted branches before restacking
            cleaned = self._cleanup_deleted_branches()
            if cleaned:
                print(f"\n🧹 Cleaned up {len(cleaned)} deleted branch(es): {', '.join(cleaned)}")

            # Delete merged branches
            merged_result = self._run_git("branch", "--merged", main_branch, check=False)
            if merged_result.returncode == 0:
                merged_branches = []
                current_branch_merged = False
                for line in merged_result.stdout.strip().split('\n'):
                    branch = line.strip().strip('* ').strip()
                    # Skip main branch
                    if branch and branch != main_branch:
                        if branch == current_branch:
                            current_branch_merged = True
                        else:
                            merged_branches.append(branch)

                if merged_branches or current_branch_merged:
                    # If current branch is merged, checkout main first
                    if current_branch_merged:
                        print(f"\n⚠️  Current branch '{current_branch}' has been merged.")
                        print(f"Switching to {main_branch}...")
                        self._run_git("checkout", main_branch)
                        # Now add it to the list
                        merged_branches.insert(0, current_branch)

                if merged_branches:
                    print(f"\n🧹 Found {len(merged_branches)} merged branch(es):")
                    deleted_any = False
                    for branch in merged_branches:
                        print(f"\nDelete '{branch}'? (y/n): ", end='')
                        confirmation = input().strip().lower()

                        if confirmation == 'y' or confirmation == 'yes':
                            result = self._run_git("branch", "-d", branch, check=False)
                            if result.returncode == 0:
                                print(f"  ✓ Deleted {branch}")
                                deleted_any = True
                            else:
                                # Try force delete
                                print(f"  ⚠️  Failed to delete {branch} (may have unmerged commits)")
                                print(f"      Force delete? (y/n): ", end='')
                                force_confirm = input().strip().lower()
                                if force_confirm == 'y' or force_confirm == 'yes':
                                    force_result = self._run_git("branch", "-D", branch, check=False)
                                    if force_result.returncode == 0:
                                        print(f"      ✓ Force deleted {branch}")
                                        deleted_any = True
                                    else:
                                        print(f"      ⚠️  Failed to force delete {branch}")
                                else:
                                    print(f"      Skipped {branch}")
                        else:
                            print(f"  Skipped {branch}")

                    # Clean up metadata after deleting branches
                    if deleted_any:
                        self._cleanup_deleted_branches()

            # If force mode, check for uncommitted changes on all child branches
            if force:
                branches_with_changes = []

                def check_branch_for_changes(branch):
                    """Recursively check branch and its children for uncommitted changes"""
                    if branch not in self.metadata["stacks"]:
                        return

                    # Check if branch exists in Git
                    if not self._branch_exists(branch):
                        return

                    # Check for uncommitted changes on this branch
                    self._run_git("checkout", branch, check=False)
                    uncommitted = self._run_git("status", "--porcelain")
                    if uncommitted.stdout.strip():
                        branches_with_changes.append((branch, uncommitted.stdout.strip()))

                    # Check all children
                    for child in self.metadata["stacks"][branch]["children"]:
                        check_branch_for_changes(child)

                # Check all branches in the stack
                check_branch_for_changes(main_branch)

                # If any branches have uncommitted changes, warn the user
                if branches_with_changes:
                    print(f"\n⚠️  WARNING: Uncommitted changes detected on child branches!")
                    print(f"These changes may be LOST during rebase if conflicts occur:\n")

                    for branch, changes in branches_with_changes:
                        print(f"  Branch '{branch}':")
                        for line in changes.split('\n')[:3]:  # Show first 3 changes
                            if line:
                                print(f"    {line}")
                        if len(changes.split('\n')) > 3:
                            print(f"    ... and more")
                        print()

                    print("Recommendation: Commit or stash these changes before force sync.")
                    print(f"\nType 'yes' to continue anyway, or anything else to cancel: ", end='')
                    confirmation = input().strip().lower()

                    if confirmation != 'yes':
                        print("❌ Sync cancelled")
                        self._clear_metadata_backup()
                        # Return to original branch
                        if current_branch != main_branch and self._branch_exists(current_branch):
                            self._run_git("checkout", current_branch)
                        return

                # Go back to main before restacking
                self._run_git("checkout", main_branch)

            # Restack all branches
            print("\n♻️  Restacking branches...")
            self._restack_all_from(main_branch)

            # Clear rebase state after successful sync
            self._clear_rebase_state()

            # Clear backup after successful operation
            self._clear_metadata_backup()

            # Return to original branch if it still exists, otherwise go to main
            if current_branch != main_branch and self._branch_exists(current_branch):
                self._run_git("checkout", current_branch)
            elif not self._branch_exists(current_branch):
                # Original branch was deleted, return to main
                self._run_git("checkout", main_branch)

            print("\n✓ Sync complete")

        except Exception as e:
            # Restore metadata from backup on failure
            print(f"⚠️  Error during sync: {e}")
            if self._restore_metadata_from_backup():
                print("Metadata restored from backup")
            raise
    
    def _restack_all_from(self, base_branch: str, visited: Optional[set] = None):
        """Recursively restack all children of a branch"""
        if visited is None:
            visited = set()

        # Cycle detection
        if base_branch in visited:
            print(f"\n⚠️  ERROR: Cycle detected in branch hierarchy at '{base_branch}'")
            print(f"This indicates corrupted metadata. Please check .git/stack-metadata.json")
            print(f"You may need to manually fix the parent-child relationships.")
            sys.exit(1)

        visited.add(base_branch)

        if base_branch not in self.metadata["stacks"]:
            return

        children = self.metadata["stacks"][base_branch]["children"]
        for child in children:
            if not self._branch_exists(child):
                print(f"⚠️  Branch '{child}' no longer exists, skipping")
                continue

            print(f"  Restacking {child} onto {base_branch}...")
            self._run_git("checkout", child)

            # Save state before rebase in case of conflicts
            self._save_rebase_state(child)

            result = self._run_git("rebase", base_branch, check=False)
            if result.returncode != 0:
                print(f"\n⚠️  Conflict detected while restacking {child}")
                print(f"Please resolve conflicts, then run: stack continue")
                sys.exit(1)

            # Recursively restack children with cycle detection
            self._restack_all_from(child, visited)
    
    def restack(self, branch: Optional[str] = None):
        """Restack a branch and all its children"""
        # Clean up deleted branches first
        cleaned = self._cleanup_deleted_branches()
        if cleaned:
            print(f"🧹 Cleaned up {len(cleaned)} deleted branch(es): {', '.join(cleaned)}\n")

        if branch is None:
            branch = self._get_current_branch()

        if branch not in self.metadata["stacks"]:
            print(f"Branch '{branch}' is not tracked in the stack")
            return

        parent = self.metadata["stacks"][branch]["parent"]
        print(f"♻️  Restacking {branch} onto {parent}...")

        self._run_git("checkout", branch)

        # Save state before rebase in case of conflicts
        self._save_rebase_state(branch)

        result = self._run_git("rebase", parent, check=False)

        if result.returncode != 0:
            print(f"\n⚠️  Conflict detected")
            print(f"Resolve conflicts, then run: stack continue")
            sys.exit(1)

        # Restack all children
        self._restack_all_from(branch)

        # Clear rebase state after successful completion
        self._clear_rebase_state()
        print("✓ Restack complete")
    
    def continue_rebase(self):
        """Continue after resolving rebase conflicts"""
        # Load the branch that was being rebased
        expected_branch = self._load_rebase_state()
        if not expected_branch:
            print("⚠️  No rebase state found. Are you sure you're in the middle of a stack rebase?")
            print("If you started a rebase manually, use 'git rebase --continue' instead.")
            sys.exit(1)

        print(f"Continuing rebase for branch '{expected_branch}'...")
        result = self._run_git("rebase", "--continue", check=False, capture=False)

        if result.returncode == 0:
            # Verify we're on the expected branch
            current_branch = self._get_current_branch()
            if current_branch != expected_branch:
                print(f"⚠️  Warning: Expected to be on '{expected_branch}' but on '{current_branch}'")
                print(f"This might indicate a rebase issue. Attempting to continue with '{current_branch}'...")
                branch_to_restack = current_branch
            else:
                branch_to_restack = expected_branch

            # Clear the state before restacking children (in case of nested conflicts)
            self._clear_rebase_state()

            # Continue restacking children
            self._restack_all_from(branch_to_restack)
            print("✓ Restack complete")
        else:
            print("⚠️  Still have conflicts to resolve")
            print("After resolving, run: stack continue")
    
    def modify(self, amend: bool = True):
        """Modify the current branch and restack children"""
        # Clean up deleted branches first
        cleaned = self._cleanup_deleted_branches()
        if cleaned:
            print(f"🧹 Cleaned up {len(cleaned)} deleted branch(es): {', '.join(cleaned)}\n")

        current_branch = self._get_current_branch()

        if current_branch not in self.metadata["stacks"]:
            print(f"Branch '{current_branch}' is not tracked")
            return

        # Backup metadata before making changes
        self._backup_metadata()

        try:
            if amend:
                # Check if there are any staged changes
                staged = self._run_git("diff", "--cached", "--quiet", check=False)
                has_staged = staged.returncode != 0

                if not has_staged:
                    print("⚠️  No staged changes to amend.")
                    print("Stage your changes with 'git add' first, or run 'git commit --amend' manually.")
                    return

                print("Amending last commit with staged changes...")
                self._run_git("commit", "--amend", "--no-edit")

            # Restack children
            self._restack_all_from(current_branch)

            # Clear rebase state after successful modification
            self._clear_rebase_state()

            # Clear backup after successful operation
            self._clear_metadata_backup()
            print("✓ Modified and restacked")

        except Exception as e:
            # Restore metadata from backup on failure
            print(f"⚠️  Error during modify: {e}")
            if self._restore_metadata_from_backup():
                print("Metadata restored from backup")
            raise
    
    def tree(self):
        """Display the branch tree"""
        # Clean up deleted branches first
        cleaned = self._cleanup_deleted_branches()
        if cleaned:
            print(f"🧹 Cleaned up {len(cleaned)} deleted branch(es): {', '.join(cleaned)}\n")

        main_branch = self.metadata["main_branch"]
        print(f"📊 Stack tree (base: {main_branch})\n")

        # Cache current branch to avoid repeated git calls
        current_branch = self._get_current_branch()

        # Track visited branches for cycle detection
        visited = set()
        cycle_detected = False

        def print_branch(branch: str, level: int = 0):
            nonlocal cycle_detected

            # Cycle detection - if we've seen this branch before, it's a cycle
            if branch in visited:
                indent = "  " * level
                print(f"{indent}⚠️  CYCLE DETECTED at '{branch}'!")
                cycle_detected = True
                return

            visited.add(branch)

            indent = "  " * level
            marker = "├─" if level > 0 else "●"
            current = " (current)" if branch == current_branch else ""
            print(f"{indent}{marker} {branch}{current}")

            if branch in self.metadata["stacks"]:
                children = self.metadata["stacks"][branch]["children"]
                for child in children:
                    print_branch(child, level + 1)

        # Start from main branch
        print_branch(main_branch)

        if cycle_detected:
            print(f"\n⚠️  WARNING: Cycles detected in branch hierarchy!")
            print(f"Please check .git/stack-metadata.json and fix parent-child relationships.")
        
        # Show any orphaned branches
        all_branches = set(self.metadata["stacks"].keys())
        connected = set()
        
        def mark_connected(branch):
            connected.add(branch)
            if branch in self.metadata["stacks"]:
                for child in self.metadata["stacks"][branch]["children"]:
                    mark_connected(child)
        
        mark_connected(main_branch)
        orphaned = all_branches - connected
        
        if orphaned:
            print("\n⚠️  Orphaned branches (not connected to main):")
            for branch in orphaned:
                print(f"  ● {branch}")
    
    def top(self):
        """Checkout the top branch in the current stack"""
        # Clean up deleted branches first
        cleaned = self._cleanup_deleted_branches()
        if cleaned:
            print(f"🧹 Cleaned up {len(cleaned)} deleted branch(es): {', '.join(cleaned)}\n")

        current = self._get_current_branch()

        # Find the top-most branch in this stack
        visited = set()
        def find_top(branch, interactive=False):
            if branch in visited:
                # Cycle detected!
                print(f"⚠️  Cycle detected in branch hierarchy at '{branch}'")
                print(f"This indicates corrupted metadata. Please check .git/stack-metadata.json")
                return current  # Return current as fallback

            visited.add(branch)

            if branch not in self.metadata["stacks"]:
                return branch
            children = self.metadata["stacks"][branch]["children"]
            if not children:
                return branch

            # If multiple children, let user choose
            if len(children) > 1:
                print(f"\nBranch '{branch}' has multiple children:")
                for i, child in enumerate(children, 1):
                    print(f"  {i}. {child}")

                while True:
                    choice = input("\nSelect which path to follow to top (or 'q' to stay here): ").strip()

                    if choice.lower() == 'q':
                        return branch

                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(children):
                            return find_top(children[idx], interactive=True)
                        else:
                            print(f"⚠️  Invalid selection. Please enter a number between 1 and {len(children)}")
                    except ValueError:
                        print("⚠️  Invalid input. Please enter a number or 'q' to quit")
            else:
                # Single child, follow it
                return find_top(children[0], interactive)

        top_branch = find_top(current)
        if top_branch != current:
            self._run_git("checkout", top_branch)
            print(f"✓ Checked out top branch: {top_branch}")
        else:
            print(f"Already at top: {current}")
    
    def bottom(self):
        """Checkout the bottom branch in the current stack"""
        # Clean up deleted branches first
        cleaned = self._cleanup_deleted_branches()
        if cleaned:
            print(f"🧹 Cleaned up {len(cleaned)} deleted branch(es): {', '.join(cleaned)}\n")

        current = self._get_current_branch()
        main_branch = self.metadata["main_branch"]

        # If we're already on main, we're at the bottom
        if current == main_branch:
            print(f"Already at bottom: {current}")
            return

        # Walk up the parents until we hit main or a branch with no parent
        visited = set()
        def find_bottom(branch):
            if branch in visited:
                # Cycle detected!
                print(f"⚠️  Cycle detected in branch hierarchy at '{branch}'")
                print(f"This indicates corrupted metadata. Please check .git/stack-metadata.json")
                return current  # Return current as fallback

            visited.add(branch)

            # If this is the main branch, it's the bottom
            if branch == main_branch:
                return branch

            if branch not in self.metadata["stacks"]:
                return branch

            parent = self.metadata["stacks"][branch]["parent"]
            # If parent is None, this branch is the bottom
            if parent is None:
                return branch
            # If parent is the main branch, current branch is the bottom of the stack
            if parent == main_branch:
                return branch
            return find_bottom(parent)

        bottom_branch = find_bottom(current)
        if bottom_branch != current:
            self._run_git("checkout", bottom_branch)
            print(f"✓ Checked out bottom branch: {bottom_branch}")
        else:
            print(f"Already at bottom: {current}")
    
    def up(self):
        """Move up to parent branch"""
        # Clean up deleted branches first
        cleaned = self._cleanup_deleted_branches()
        if cleaned:
            print(f"🧹 Cleaned up {len(cleaned)} deleted branch(es): {', '.join(cleaned)}\n")

        current = self._get_current_branch()
        if current not in self.metadata["stacks"]:
            print(f"Branch '{current}' is not tracked")
            return

        parent = self.metadata["stacks"][current]["parent"]
        if parent is None:
            print(f"Already at the root branch (no parent)")
            return

        # Verify parent branch exists
        if not self._branch_exists(parent):
            print(f"⚠️  Parent branch '{parent}' no longer exists")
            return

        self._run_git("checkout", parent)
        print(f"✓ Moved up to: {parent}")
    
    def down(self):
        """Move down to first child branch"""
        # Clean up deleted branches first
        cleaned = self._cleanup_deleted_branches()
        if cleaned:
            print(f"🧹 Cleaned up {len(cleaned)} deleted branch(es): {', '.join(cleaned)}\n")

        current = self._get_current_branch()
        if current not in self.metadata["stacks"]:
            print(f"Branch '{current}' is not tracked")
            return

        children = self.metadata["stacks"][current]["children"]
        if not children:
            print("No child branches")
            return
        
        if len(children) == 1:
            self._run_git("checkout", children[0])
            print(f"✓ Moved down to: {children[0]}")
        else:
            while True:
                print(f"\nMultiple children available:")
                for i, child in enumerate(children, 1):
                    print(f"  {i}. {child}")
                choice = input("\nSelect branch number (or 'q' to quit): ").strip()

                if choice.lower() == 'q':
                    print("Cancelled")
                    return

                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(children):
                        self._run_git("checkout", children[idx])
                        print(f"✓ Moved down to: {children[idx]}")
                        return
                    else:
                        print(f"⚠️  Invalid selection. Please enter a number between 1 and {len(children)}")
                except ValueError:
                    print("⚠️  Invalid input. Please enter a number or 'q' to quit")
    
    def status(self):
        """Show stack status"""
        # Clean up deleted branches first
        cleaned = self._cleanup_deleted_branches()
        if cleaned:
            print(f"\n🧹 Cleaned up {len(cleaned)} deleted branch(es): {', '.join(cleaned)}")

        # Check for detached HEAD
        if self._is_detached_head():
            print("\n⚠️  Detached HEAD state")
            print("You are not currently on any branch.")
            print("Stack commands may not work as expected.")
            return

        current = self._get_current_branch()
        print(f"\nCurrent branch: {current}")

        if current in self.metadata["stacks"]:
            info = self.metadata["stacks"][current]
            print(f"Parent: {info['parent']}")
            print(f"Children: {', '.join(info['children']) if info['children'] else 'none'}")
        else:
            print("(not tracked in stack)")

        # Show if backup exists
        if self.metadata_backup_file.exists():
            import time
            backup_time = os.path.getmtime(self.metadata_backup_file)
            backup_age = time.time() - backup_time

            # Format age nicely
            if backup_age < 60:
                age_str = f"{int(backup_age)} seconds ago"
            elif backup_age < 3600:
                age_str = f"{int(backup_age/60)} minutes ago"
            elif backup_age < 86400:
                age_str = f"{int(backup_age/3600)} hours ago"
            else:
                age_str = f"{int(backup_age/86400)} days ago"

            print(f"\n💾 Backup available (created {age_str})")
            print(f"   Restore with: stack restore-backup")

    def restore_backup(self):
        """Restore metadata from backup file"""
        if not self.metadata_backup_file.exists():
            print("⚠️  No backup file found")
            print(f"Backup location: {self.metadata_backup_file}")
            return

        print("💾 Found metadata backup")
        print(f"Current metadata: {self.metadata_file}")
        print(f"Backup file: {self.metadata_backup_file}")
        print("\n⚠️  This will replace your current metadata with the backup.")
        print("Type 'yes' to restore from backup, or anything else to cancel: ", end='')
        confirmation = input().strip().lower()

        if confirmation != 'yes':
            print("❌ Restore cancelled")
            return

        if self._restore_metadata_from_backup():
            print("✓ Metadata restored from backup")
            print("Run 'stack tree' to see the restored state")
        else:
            print("⚠️  Failed to restore from backup")

    def clean_merged(self):
        """Delete local branches that have been merged into main"""
        main_branch = self.metadata["main_branch"]
        current_branch = self._get_current_branch()

        # Get list of merged branches
        merged_result = self._run_git("branch", "--merged", main_branch, check=False)
        if merged_result.returncode != 0:
            print("⚠️  Failed to check merged branches")
            return

        merged_branches = []
        for line in merged_result.stdout.strip().split('\n'):
            branch = line.strip().strip('* ').strip()
            # Skip main branch and current branch
            if branch and branch != main_branch and branch != current_branch:
                merged_branches.append(branch)

        if not merged_branches:
            print("No merged branches to clean up")
            return

        print(f"Found {len(merged_branches)} merged branch(es):\n")
        for branch in merged_branches:
            print(f"  • {branch}")

        print(f"\nDelete these branches? Type 'yes' to confirm: ", end='')
        confirmation = input().strip().lower()

        if confirmation != 'yes':
            print("❌ Cancelled")
            return

        # Delete each branch
        deleted = []
        for branch in merged_branches:
            result = self._run_git("branch", "-d", branch, check=False)
            if result.returncode == 0:
                deleted.append(branch)
                print(f"✓ Deleted {branch}")
            else:
                print(f"⚠️  Failed to delete {branch}")

        if deleted:
            # Clean up metadata
            self._cleanup_deleted_branches()
            print(f"\n✓ Cleaned up {len(deleted)} branch(es)")

    def submit(self, branch: Optional[str] = None):
        """Push branches and create/update PRs for the stack"""
        # Clean up deleted branches first
        cleaned = self._cleanup_deleted_branches()
        if cleaned:
            print(f"🧹 Cleaned up {len(cleaned)} deleted branch(es): {', '.join(cleaned)}\n")

        # Check if gh CLI is installed
        gh_check = self._run_git("--version", check=False)
        result = subprocess.run(["gh", "--version"], capture_output=True, check=False)
        if result.returncode != 0:
            print("⚠️  GitHub CLI (gh) is not installed")
            print("Install it from: https://cli.github.com/")
            print("\nAlternatively, create PRs manually:")
            print("  1. Push branches: git push -u origin <branch>")
            print("  2. Create PR with correct base for each branch")
            sys.exit(1)

        # Check if remote exists
        if not self._has_remote("origin"):
            print("⚠️  No remote 'origin' configured")
            print("Add a remote first: git remote add origin <url>")
            sys.exit(1)

        # Determine which branch to start from
        if branch is None:
            branch = self._get_current_branch()

        if branch not in self.metadata["stacks"]:
            print(f"⚠️  Branch '{branch}' is not tracked in the stack")
            sys.exit(1)

        main_branch = self.metadata["main_branch"]

        # Find all branches from main to current branch
        branches_to_submit = []
        current = branch

        # Walk up to main, building the list
        visited = set()
        while current and current != main_branch:
            if current in visited:
                print(f"⚠️  Cycle detected in branch hierarchy at '{current}'")
                sys.exit(1)
            visited.add(current)

            if current not in self.metadata["stacks"]:
                break

            branches_to_submit.insert(0, current)  # Insert at beginning to get bottom-up order
            current = self.metadata["stacks"][current]["parent"]

        if not branches_to_submit:
            print(f"⚠️  No branches to submit (already on {main_branch})")
            return

        print(f"📤 Submitting stack ({len(branches_to_submit)} branch(es)):\n")
        for b in branches_to_submit:
            parent = self.metadata["stacks"][b]["parent"]
            print(f"  {b} → {parent}")
        print()

        # Push and create/update PRs for each branch
        for i, branch_name in enumerate(branches_to_submit):
            parent_branch = self.metadata["stacks"][branch_name]["parent"]

            print(f"[{i+1}/{len(branches_to_submit)}] Processing {branch_name}...")

            # Push the branch
            print(f"  Pushing {branch_name} to origin...")
            push_result = self._run_git("push", "-u", "origin", branch_name, check=False)

            # If push fails due to non-fast-forward, try force push with lease
            if push_result.returncode != 0:
                if "rejected" in push_result.stderr and "non-fast-forward" in push_result.stderr:
                    print(f"  Branch history changed, force pushing with --force-with-lease...")
                    push_result = self._run_git("push", "--force-with-lease", "-u", "origin", branch_name, check=False)

                if push_result.returncode != 0:
                    print(f"⚠️  Failed to push {branch_name}")
                    print(push_result.stderr)
                    sys.exit(1)

            # Check if PR already exists
            pr_check = subprocess.run(
                ["gh", "pr", "list", "--head", branch_name, "--json", "number,baseRefName"],
                capture_output=True,
                text=True,
                check=False
            )

            if pr_check.returncode == 0 and pr_check.stdout.strip() != "[]":
                # PR exists, update base if needed
                import json
                pr_data = json.loads(pr_check.stdout)
                if pr_data:
                    pr_number = pr_data[0]["number"]
                    current_base = pr_data[0]["baseRefName"]

                    if current_base != parent_branch:
                        print(f"  Updating PR #{pr_number} base: {current_base} → {parent_branch}")
                        subprocess.run(
                            ["gh", "pr", "edit", str(pr_number), "--base", parent_branch],
                            check=True
                        )
                    else:
                        print(f"  PR #{pr_number} already exists (base: {parent_branch})")

                    # View the PR URL
                    pr_url_result = subprocess.run(
                        ["gh", "pr", "view", str(pr_number), "--json", "url", "-q", ".url"],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if pr_url_result.returncode == 0:
                        print(f"  🔗 {pr_url_result.stdout.strip()}")
            else:
                # Create new PR
                print(f"  Creating PR: {branch_name} → {parent_branch}")

                # Get commit messages for PR body
                commit_log = self._run_git(
                    "log", "--format=%s", f"{parent_branch}..{branch_name}",
                    check=False
                )

                pr_body = f"Stack: {' → '.join(branches_to_submit[:i+1])}\n\n"
                if commit_log.stdout.strip():
                    pr_body += "## Changes\n"
                    for line in commit_log.stdout.strip().split('\n'):
                        pr_body += f"- {line}\n"

                pr_result = subprocess.run(
                    ["gh", "pr", "create",
                     "--base", parent_branch,
                     "--head", branch_name,
                     "--title", f"[Stack] {branch_name}",
                     "--body", pr_body],
                    capture_output=True,
                    text=True,
                    check=False
                )

                if pr_result.returncode == 0:
                    print(f"  ✓ Created PR")
                    # Extract URL from output
                    pr_url = pr_result.stdout.strip()
                    print(f"  🔗 {pr_url}")
                else:
                    print(f"⚠️  Failed to create PR for {branch_name}")
                    print(pr_result.stderr)

            print()

        print(f"✓ Stack submitted successfully!")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog='stack',
        description='Stack - Stacked Branches CLI for Git'
    )

    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # create command
    create_parser = subparsers.add_parser('create', help='Create a new branch on top of current')
    create_parser.add_argument('branch_name', help='Name of the branch to create')
    create_parser.add_argument('-m', '--message', help='Commit message')
    create_parser.add_argument('--no-commit', action='store_true', help='Create branch without committing staged changes')

    # checkout command
    checkout_parser = subparsers.add_parser('checkout', help='Checkout a branch (interactive if no name)')
    checkout_parser.add_argument('branch', nargs='?', help='Branch name to checkout')

    # co (alias for checkout)
    co_parser = subparsers.add_parser('co', help='Alias for checkout')
    co_parser.add_argument('branch', nargs='?', help='Branch name to checkout')

    # sync command
    sync_parser = subparsers.add_parser('sync', help='Pull main and restack all branches')
    sync_parser.add_argument('--force', action='store_true', help='Force reset to origin/main')

    # restack command
    restack_parser = subparsers.add_parser('restack', help='Restack current/specified branch and children')
    restack_parser.add_argument('branch', nargs='?', help='Branch to restack')

    # continue command
    subparsers.add_parser('continue', help='Continue after resolving conflicts')

    # modify command
    subparsers.add_parser('modify', help='Amend current commit and restack children')

    # tree command
    subparsers.add_parser('tree', help='Show branch tree')

    # status command
    subparsers.add_parser('status', help='Show current branch status')

    # restore-backup command
    subparsers.add_parser('restore-backup', help='Restore metadata from backup file')

    # submit command
    submit_parser = subparsers.add_parser('submit', help='Push branches and create/update PRs for the stack')
    submit_parser.add_argument('branch', nargs='?', help='Branch to submit (default: current)')

    # clean-merged command
    subparsers.add_parser('clean-merged', help='Delete local branches that have been merged into main')

    # Navigation commands
    subparsers.add_parser('top', help='Go to top of stack')
    subparsers.add_parser('bottom', help='Go to bottom of stack')
    subparsers.add_parser('up', help='Go to parent branch')
    subparsers.add_parser('down', help='Go to child branch')

    # Parse arguments
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        manager = StackManager()

        if args.command == "create":
            manager.create(args.branch_name, args.message, args.no_commit)

        elif args.command in ("checkout", "co"):
            manager.checkout(args.branch)

        elif args.command == "sync":
            manager.sync(args.force)

        elif args.command == "restack":
            manager.restack(args.branch)

        elif args.command == "continue":
            manager.continue_rebase()

        elif args.command == "modify":
            manager.modify()

        elif args.command == "tree":
            manager.tree()

        elif args.command == "top":
            manager.top()

        elif args.command == "bottom":
            manager.bottom()

        elif args.command == "up":
            manager.up()

        elif args.command == "down":
            manager.down()

        elif args.command == "status":
            manager.status()

        elif args.command == "restore-backup":
            manager.restore_backup()

        elif args.command == "submit":
            manager.submit(args.branch)

        elif args.command == "clean-merged":
            manager.clean_merged()

    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
