#!/usr/bin/env python3
"""
Stack Enhanced - Extended version with push and PR support
Not included yet
anotherone
stack2
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Import base functionality from original stack.py
# (In practice, you'd either extend the class or merge features)

class EnhancedStackManager:
    """Extended stack manager with push and PR features"""
    
    def __init__(self):
        self.git_root = self._get_git_root()
        self.metadata_file = Path(self.git_root) / ".git" / "stack-metadata.json"
        self.metadata = self._load_metadata()
    
    def _get_git_root(self) -> str:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    
    def _load_metadata(self) -> Dict:
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {"stacks": {}, "main_branch": "main"}
    
    def _save_metadata(self):
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def _run_git(self, *args, check=True, capture=True) -> subprocess.CompletedProcess:
        cmd = ["git"] + list(args)
        if capture:
            return subprocess.run(cmd, capture_output=True, text=True, check=check)
        else:
            return subprocess.run(cmd, check=check)
    
    def _get_current_branch(self) -> str:
        result = self._run_git("branch", "--show-current")
        return result.stdout.strip()
    
    def _branch_exists(self, branch: str) -> bool:
        result = self._run_git("show-ref", "--verify", f"refs/heads/{branch}", check=False)
        return result.returncode == 0
    
    def push_branch(self, branch: Optional[str] = None, force: bool = False):
        """Push a branch to remote"""
        if branch is None:
            branch = self._get_current_branch()
        
        print(f"📤 Pushing {branch} to remote...")
        
        cmd_args = ["push", "-u", "origin", branch]
        if force:
            cmd_args.insert(1, "--force-with-lease")
        
        self._run_git(*cmd_args, capture=False)
        print(f"✓ Pushed {branch}")
    
    def push_stack(self, force: bool = False):
        """Push all branches in the current stack"""
        current = self._get_current_branch()
        
        # Find all branches in the stack
        def collect_stack(branch, branches=None):
            if branches is None:
                branches = []
            branches.append(branch)
            if branch in self.metadata["stacks"]:
                for child in self.metadata["stacks"][branch]["children"]:
                    collect_stack(child, branches)
            return branches
        
        # Find the root of current stack
        def find_root(branch):
            if branch not in self.metadata["stacks"]:
                return branch
            parent = self.metadata["stacks"][branch]["parent"]
            if parent == self.metadata["main_branch"] or parent not in self.metadata["stacks"]:
                return branch
            return find_root(parent)
        
        root = find_root(current)
        branches = collect_stack(root)
        
        print(f"📤 Pushing stack ({len(branches)} branches)...")
        for branch in branches:
            self.push_branch(branch, force)
        
        print("✓ Stack pushed")
    
    def submit(self, stack: bool = False, draft: bool = False):
        """
        Submit branch(es) as PR(s)
        This is a placeholder - in practice you'd integrate with GitHub CLI
        """
        current = self._get_current_branch()
        
        if not self._has_remote():
            print("⚠️  No remote repository configured")
            return
        
        # Check if gh CLI is available
        gh_available = subprocess.run(
            ["which", "gh"],
            capture_output=True,
            check=False
        ).returncode == 0
        
        if not gh_available:
            print("⚠️  GitHub CLI (gh) not found")
            print("Install it to create PRs automatically: https://cli.github.com/")
            print("")
            print("Alternative: Push your branches and create PRs manually:")
            if stack:
                print(f"  stack push-stack")
            else:
                print(f"  git push -u origin {current}")
            return
        
        # Push first
        if stack:
            self.push_stack()
        else:
            self.push_branch(current)
        
        # Create PR(s)
        branches_to_submit = []
        if stack:
            # Find all branches in stack that don't have PRs
            def collect_stack(branch, branches=None):
                if branches is None:
                    branches = []
                if branch != self.metadata["main_branch"]:
                    branches.append(branch)
                if branch in self.metadata["stacks"]:
                    for child in self.metadata["stacks"][branch]["children"]:
                        collect_stack(child, branches)
                return branches
            
            branches_to_submit = collect_stack(current)
        else:
            branches_to_submit = [current]
        
        print(f"\n📝 Creating PR(s)...")
        for branch in branches_to_submit:
            if branch not in self.metadata["stacks"]:
                continue
            
            parent = self.metadata["stacks"][branch]["parent"]
            
            # Get commit message as PR title
            result = self._run_git("log", "-1", "--pretty=%s", branch)
            title = result.stdout.strip()
            
            cmd = ["gh", "pr", "create", "--head", branch, "--base", parent, "--title", title]
            if draft:
                cmd.append("--draft")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                print(f"✓ Created PR for {branch}")
                # Parse URL from output
                for line in result.stdout.split('\n'):
                    if 'https://' in line:
                        print(f"  {line.strip()}")
            else:
                if "already exists" in result.stderr:
                    print(f"  PR for {branch} already exists")
                else:
                    print(f"⚠️  Failed to create PR for {branch}: {result.stderr}")
    
    def _has_remote(self) -> bool:
        """Check if repository has a remote"""
        result = self._run_git("remote", "-v", check=False)
        return result.returncode == 0 and result.stdout.strip() != ""
    
    def pr_view(self):
        """Open PR in browser"""
        current = self._get_current_branch()
        
        # Try using gh CLI
        result = subprocess.run(
            ["gh", "pr", "view", "--web"],
            capture_output=True,
            check=False
        )
        
        if result.returncode != 0:
            print("⚠️  Could not open PR. Make sure GitHub CLI is installed and PR exists.")
    
    def log_stack(self):
        """Show git log for the entire stack"""
        current = self._get_current_branch()
        
        # Find stack boundaries
        def find_root(branch):
            if branch not in self.metadata["stacks"]:
                return self.metadata["main_branch"]
            parent = self.metadata["stacks"][branch]["parent"]
            if parent == self.metadata["main_branch"]:
                return branch
            return find_root(parent)
        
        def find_top(branch):
            if branch not in self.metadata["stacks"]:
                return branch
            children = self.metadata["stacks"][branch]["children"]
            if not children:
                return branch
            return find_top(children[0])
        
        bottom = find_root(current)
        top = find_top(current)
        base = self.metadata["stacks"][bottom]["parent"] if bottom in self.metadata["stacks"] else self.metadata["main_branch"]
        
        print(f"\n📜 Stack log ({base}..{top})\n")
        self._run_git("log", "--oneline", "--graph", "--decorate", f"{base}..{top}", capture=False)


def print_enhanced_help():
    help_text = """
Stack Enhanced - Extended Commands

Additional commands beyond base stack:

Push Commands:
  push [branch]             Push branch to remote
  push-stack [--force]      Push all branches in current stack
  
PR Commands:
  submit [--stack] [--draft]  Create PR (--stack for all branches)
  pr                          Open current branch's PR in browser
  
Info Commands:
  log                         Show git log for current stack

Examples:
  stack push-stack              # Push all branches in your stack
  stack submit --stack          # Create PRs for all branches
  stack submit --stack --draft  # Create draft PRs
  stack pr                      # Open PR in browser
  stack log                     # View commits in your stack
"""
    print(help_text)


# This would be integrated into the main CLI
if __name__ == "__main__":
    print("This is an enhanced version showing additional features.")
    print("Integrate these methods into the main StackManager class.")
    print_enhanced_help()
