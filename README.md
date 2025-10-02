# Stack CLI - Stacked Branch Workflow for Git

A lightweight, single-file CLI tool for managing stacked Git branches. Stack helps you work with dependent branches without requiring cloud services or complex setups - just Python 3 and Git.

## What are Stacked Branches?

Stacked branches (also called "stacked diffs" or "stacked PRs") is a development workflow where you create a chain of dependent feature branches, each building on top of the previous one. This allows you to:

- **Break large features into smaller, reviewable chunks**
- **Get faster code reviews** (smaller PRs = quicker reviews)
- **Continue working while waiting for reviews**
- **Maintain a clean commit history**

### Traditional Workflow vs Stacked Workflow

**Traditional:**
```
main → feature-branch (big PR with 20 files changed)
```

**Stacked:**
```
main → auth-foundation → auth-ui → auth-testing
       (3 files)         (5 files)  (2 files)
```

## Installation

```bash
# Clone or download stack.py
curl -o stack.py https://raw.githubusercontent.com/your-repo/stack-cli/main/stack.py

# Run the installer
chmod +x install.sh
./install.sh

# Or install manually
mkdir -p ~/.local/bin
cp stack.py ~/.local/bin/stack
chmod +x ~/.local/bin/stack

# Make sure ~/.local/bin is in your PATH
export PATH="$HOME/.local/bin:$PATH"
```

Verify installation:
```bash
stack --help
```

## Quick Start

### Basic Workflow

```bash
# Start from main
git checkout main

# Create your first branch
echo "Authentication module" > auth.py
git add auth.py
stack create auth-foundation -m "Add auth foundation"

# Stack another branch on top
echo "Login UI component" > login.py
git add login.py
stack create auth-ui -m "Add login UI"

# Stack a third branch
echo "Auth tests" > auth_test.py
git add auth_test.py
stack create auth-tests -m "Add auth tests"

# View your stack
stack tree
```

Output:
```
📊 Stack tree (base: main)

● main
  ├─ auth-foundation
    ├─ auth-ui
      ├─ auth-tests (current)
```

## Core Commands

### Creating Branches

```bash
# Create a new branch with a commit (requires staged files)
git add <files>
stack create <branch-name> -m "Commit message"

# Create a branch without committing (keeps changes staged)
git add <files>
stack create <branch-name> --no-commit

# Note: You must stage files before creating a branch
# stack create will fail if no files are staged
```

### Navigation

```bash
# Move to parent branch
stack up

# Move to child branch (interactive if multiple children)
stack down

# Jump to the top of the stack
stack top

# Jump to the bottom of the stack (first branch above main)
stack bottom

# Interactive branch checkout
stack checkout
```

### Viewing Your Stack

```bash
# Show the branch tree
stack tree

# Show current branch info
stack status
```

### Modifying Branches

```bash
# Amend the current commit and restack children
git add <modified-files>
stack modify

# The modify command automatically rebases all child branches
```

### Syncing with Main

```bash
# Pull latest main and restack all branches
stack sync

# Force reset main to origin/main (with safety checks)
stack sync --force
```

### Restacking

```bash
# Restack current branch and its children
stack restack

# Restack a specific branch
stack restack <branch-name>
```

### Submitting Pull Requests

```bash
# Push branches and create/update PRs for the entire stack
stack submit

# Submit a specific branch and its ancestors
stack submit <branch-name>

# Requires GitHub CLI (gh) to be installed and authenticated
# Install: https://cli.github.com/
```

## Real-World Scenarios

### Scenario 1: Building a New Feature in Layers

You're building a user profile feature with backend, frontend, and tests.

```bash
# Start from main
git checkout main

# Layer 1: Database models
git add models/user_profile.py
stack create profile-models -m "Add user profile database models"

# Layer 2: API endpoints (builds on models)
git add api/profile_endpoints.py
stack create profile-api -m "Add profile API endpoints"

# Layer 3: Frontend components (builds on API)
git add components/ProfilePage.tsx
stack create profile-ui -m "Add profile UI components"

# Layer 4: Tests (builds on everything)
git add tests/test_profile.py
stack create profile-tests -m "Add comprehensive profile tests"

# View your stack
stack tree
```

Output:
```
📊 Stack tree (base: main)

● main
  ├─ profile-models
    ├─ profile-api
      ├─ profile-ui
        ├─ profile-tests (current)
```

**Creating Pull Requests:**
```bash
# Automated approach (requires GitHub CLI)
stack submit

# Output:
# 📤 Submitting stack (4 branch(es)):
#   profile-models → main
#   profile-api → profile-models
#   profile-ui → profile-api
#   profile-tests → profile-ui
#
# [1/4] Processing profile-models...
#   Pushing profile-models to origin...
#   Creating PR: profile-models → main
#   ✓ Created PR
#   🔗 https://github.com/user/repo/pull/123
# ...

# Manual approach
git push -u origin profile-models
git push -u origin profile-api
git push -u origin profile-ui
git push -u origin profile-tests

# Create PRs in GitHub
# PR 1: profile-models -> main
# PR 2: profile-api -> profile-models
# PR 3: profile-ui -> profile-api
# PR 4: profile-tests -> profile-ui
```

### Scenario 2: Addressing Review Feedback

Your reviewer asks for changes in the middle of your stack.

```bash
# You're on profile-tests, reviewer comments on profile-api
stack checkout profile-api

# Make the requested changes
git add api/profile_endpoints.py

# Amend the commit and automatically restack all children
stack modify

# All child branches (profile-ui, profile-tests) are automatically rebased!
```

**What happens:**
1. `profile-api` commit is amended with your changes
2. `profile-ui` is automatically rebased onto the updated `profile-api`
3. `profile-tests` is automatically rebased onto the updated `profile-ui`

### Scenario 3: Main Branch Gets Updated

Someone merged a PR to main while you're working on your stack.

```bash
# Sync your stack with the latest main
stack sync

# This will:
# 1. Pull latest main from origin
# 2. Rebase profile-models onto main
# 3. Rebase profile-api onto profile-models
# 4. Rebase profile-ui onto profile-api
# 5. Rebase profile-tests onto profile-ui
```

### Scenario 4: Handling Merge Conflicts

```bash
# Sync encounters a conflict
stack sync

# Output:
# ⚠️  Conflict detected while restacking profile-api
# Please resolve conflicts, then run: stack continue

# Resolve conflicts manually
git add <resolved-files>

# Continue the restack process
stack continue

# Stack automatically restacks remaining children
```

### Scenario 5: Working on Multiple Independent Stacks

```bash
# Stack 1: Authentication feature
git checkout main
git add auth.py
stack create auth-base -m "Add auth base"
git add login.py
stack create auth-login -m "Add login"

# Stack 2: Separate feature - User settings
git checkout main
git add settings.py
stack create settings-base -m "Add settings base"
git add preferences.py
stack create settings-prefs -m "Add preferences"

# View both stacks
stack tree
```

Output:
```
📊 Stack tree (base: main)

● main
  ├─ auth-base
  │  ├─ auth-login
  ├─ settings-base
     ├─ settings-prefs (current)
```

### Scenario 6: Interactive Navigation

```bash
# You're deep in a stack and want to go back to the beginning
stack bottom  # Jump to first branch in stack

# Navigate up the tree
stack up      # Go to parent branch

# Check where you are
stack status

# Current branch: auth-login
# Parent: auth-base
# Children: auth-tests, auth-docs

# If multiple children exist, stack prompts you to choose
stack down

# Multiple children available:
#   1. auth-tests
#   2. auth-docs
# Select branch number (or 'q' to quit): 1
```

### Scenario 7: Creating Branches Without Committing

Useful when you want to create a branch structure first, then commit later.

```bash
# Stage some changes
git add feature.py

# Create branch without committing
stack create my-feature --no-commit

# Changes remain staged
git status
# On branch my-feature
# Changes to be committed:
#   new file:   feature.py

# Commit when ready
git commit -m "Add feature"
```

### Scenario 8: Recovering from Mistakes

```bash
# Stack maintains automatic backups
stack status

# Output:
# Current branch: feature-branch
# Parent: main
# Children: none
#
# 💾 Backup available (created 5 minutes ago)
#    Restore with: stack restore-backup

# If something goes wrong
stack restore-backup

# Type 'yes' to restore from backup, or anything else to cancel: yes
# ✓ Metadata restored from backup
```

## Advanced Workflows

### Splitting a Large PR into a Stack

You have a large feature branch with 50+ file changes. Split it into reviewable chunks:

```bash
# On your large feature branch
git checkout my-large-feature

# Create a clean stack from main
git checkout main

# Cherry-pick related commits into separate branches
git checkout main
git checkout -b feature-part1
git cherry-pick <commit-hash-1> <commit-hash-2>
# Now track it with stack (from main)
git checkout main
git add .  # Add any uncommitted changes
stack create feature-part1 -m "Part 1: Core functionality"

# Continue with next part
git cherry-pick <commit-hash-3> <commit-hash-4>
stack create feature-part2 -m "Part 2: UI components"

# And so on...
```

### Maintaining Multiple PR Chains

```bash
# Check all your stacks
stack tree

# Regularly sync to stay updated
stack sync

# Push all branches for PR review
git push --all origin
```

## Best Practices

### 1. Keep Branches Focused
Each branch should represent one logical change:
```bash
✅ Good: stack create add-user-validation -m "Add email validation"
❌ Bad:  stack create misc-changes -m "Fix stuff"
```

### 2. Use Descriptive Branch Names
```bash
✅ Good: auth-oauth-integration
✅ Good: ui-dark-mode-toggle
❌ Bad:  feature-1
❌ Bad:  fix
```

### 3. Commit Often, Stack Strategically
```bash
# Make small commits within a branch
git commit -m "Add basic structure"
git commit -m "Add error handling"
git commit -m "Add tests"

# Stack when you have a complete, reviewable unit
stack create auth-middleware -m "Add authentication middleware"
```

### 4. Sync Regularly
```bash
# Sync at least once a day
stack sync

# Before starting new work
git checkout main
git pull
stack sync
```

### 5. Handle Conflicts Promptly
```bash
# When conflicts occur during sync
stack sync
# ⚠️  Conflict detected...

# Don't ignore it - resolve immediately
vim conflicted-file.py
git add conflicted-file.py
stack continue
```

### 6. Use --no-commit for Experimentation
```bash
# Try out changes without committing
git add experimental-feature.py
stack create experiment --no-commit

# Decide later whether to commit or discard
git commit -m "Keep this change"
# or
git reset HEAD experimental-feature.py
```

## Comparison with Other Tools

### Stack vs Graphite CLI

**Stack (this tool):**
- ✅ Zero dependencies (just Python + Git)
- ✅ Single file, easy to audit
- ✅ No cloud service required
- ✅ Works offline
- ✅ Local metadata only
- ✅ Optional GitHub integration (via GitHub CLI)
- ✅ Automated PR creation/updating with `stack submit`
- ❌ No web UI

**Graphite:**
- ✅ GitHub PR management
- ✅ Web dashboard
- ✅ Team collaboration features
- ✅ Advanced PR workflows
- ❌ Requires cloud service
- ❌ More complex setup
- ❌ Paid tiers for teams

**When to use Stack:**
- You want a simple, local-first tool
- You're comfortable with Git and GitHub CLI
- You value simplicity and control
- You want optional PR automation without cloud dependencies

**When to use Graphite:**
- You need advanced team collaboration features
- You want a web UI for visualization
- You need enterprise features

## Troubleshooting

### "Branch not tracked in stack"
```bash
# You created a branch outside of stack
git checkout -b manual-branch

# You'll need to recreate it using stack to track it
git checkout main
git cherry-pick <commits-from-manual-branch>
stack create manual-branch -m "Track existing branch"
```

### "Cycle detected in branch hierarchy"
```bash
# Metadata is corrupted
# Check .git/stack-metadata.json

# Restore from backup
stack restore-backup
```

### "Rebase in progress" after a failed operation
```bash
# Check if you're in a rebase
git status

# If in a rebase
git add <resolved-files>
stack continue

# Or abort if needed
git rebase --abort
```

### Branches out of sync with metadata
```bash
# Stack auto-cleans deleted branches
stack tree
# 🧹 Cleaned up 2 deleted branch(es): old-branch-1, old-branch-2
```

## Command Reference

| Command | Description |
|---------|-------------|
| `stack create <name> -m "msg"` | Create a new branch on top of current |
| `stack create <name> --no-commit` | Create branch without committing |
| `stack checkout [name]` | Checkout a branch (interactive if no name) |
| `stack tree` | Display the branch tree |
| `stack status` | Show current branch status |
| `stack up` | Move to parent branch |
| `stack down` | Move to child branch |
| `stack top` | Jump to top of current stack |
| `stack bottom` | Jump to bottom of current stack |
| `stack modify` | Amend current commit and restack children |
| `stack sync` | Pull main and restack all branches |
| `stack sync --force` | Force reset main to origin/main |
| `stack restack [name]` | Restack branch and its children |
| `stack continue` | Continue after resolving conflicts |
| `stack restore-backup` | Restore metadata from backup |
| `stack submit [branch]` | Push branches and create/update PRs for the stack |

## Tips & Tricks

### Create a shorter command alias
```bash
# Add to ~/.bashrc or ~/.zshrc
alias st='stack'

# Now you can use:
st tree
st create my-branch -m "message"
st co  # Interactive checkout
st sync
```

### Create aliases for common operations
```bash
# Add to ~/.bashrc or ~/.zshrc
alias stree='stack tree'
alias sstatus='stack status'
alias sup='stack up'
alias sdown='stack down'
alias ssync='stack sync'
```

### Use with GitHub CLI for PR management
```bash
# Automated approach - use stack submit
stack submit

# Or create PRs manually for specific branches
gh pr create --base parent-branch --head feature-branch --fill
```

### Visualize your stack before pushing
```bash
# Always check before pushing
stack tree

# Push all branches
git push --all origin
```

### Keep a clean main branch
```bash
# Never work directly on main
git checkout main
# Always create a branch first
stack create <feature-name> -m "Start feature"
```

## Contributing

Stack is a single-file tool designed to be simple and auditable. Contributions are welcome!

- **Bug reports:** Open an issue with reproduction steps
- **Feature requests:** Describe your use case
- **Pull requests:** Keep changes focused and tested

Run the test suite:
```bash
./test-stack.sh
```

## License

MIT License - See LICENSE file for details

## Credits

Inspired by Graphite CLI, designed for simplicity and local-first development.
