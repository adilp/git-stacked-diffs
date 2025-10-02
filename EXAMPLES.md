# Stack CLI - Examples & Best Practices

## Real-World Examples

### Example 1: Full-Stack Feature

Building a user authentication feature across the stack:

```bash
# Start from main
git checkout main

# 1. Database migration
stack create auth-db-migration -m "Add users and sessions tables"
# Edit migration files
vim migrations/001_add_auth_tables.sql
git add migrations/
# Changes are auto-committed

# 2. API models and endpoints  
stack create auth-api-models -m "Add User and Session models"
vim models/user.py
vim models/session.py
git add models/

stack create auth-api-endpoints -m "Add /login and /register endpoints"
vim api/auth.py
git add api/

# 3. Frontend components
stack create auth-ui-components -m "Add Login and Register components"
vim components/Login.tsx
vim components/Register.tsx
git add components/

# 4. Integration
stack create auth-integration -m "Wire up auth flow"
vim app/auth.ts
git add app/

# View your beautiful stack
stack tree
```

Output:
```
📊 Stack tree (base: main)

● main
  ├─ auth-db-migration
    ├─ auth-api-models
      ├─ auth-api-endpoints
        ├─ auth-ui-components
          ├─ auth-integration (current)
```

### Example 2: Addressing Code Review

You get review feedback on the API endpoints:

```bash
# Go to the API endpoints branch
stack checkout auth-api-endpoints

# Make the requested changes
vim api/auth.py

# Modify and auto-restack everything above
stack modify

# Everything dependent on auth-api-endpoints is now rebased:
# - auth-ui-components (uses the API)
# - auth-integration (wires it all up)
```

### Example 3: Parallel Development

Working on two features at once:

```bash
# Feature A: User profiles
git checkout main
stack create profile-db -m "Add profile fields"
stack create profile-api -m "Add profile API"
stack create profile-ui -m "Add profile page"

# Feature B: Admin dashboard (start fresh from main)
git checkout main  
stack create admin-db -m "Add admin tables"
stack create admin-api -m "Add admin API"
stack create admin-ui -m "Add admin dashboard"

# See both stacks
stack tree
```

Output:
```
📊 Stack tree (base: main)

● main
  ├─ profile-db
    ├─ profile-api
      ├─ profile-ui
  ├─ admin-db
    ├─ admin-api
      ├─ admin-ui (current)
```

### Example 4: Daily Workflow

Monday morning:

```bash
# Sync with team's changes from Friday
stack sync

# If conflicts occur:
# - Fix them in your editor
# - git add resolved files  
# - stack continue

# Now you're up to date!
```

Working on your feature:

```bash
# Navigate to your working branch
stack checkout my-feature

# Make changes
vim my-file.py

# Quick test
npm test

# Amend commit with changes
stack modify

# Continue to next branch
stack down
```

End of day:

```bash
# View what you worked on
stack tree
stack log  # If using enhanced version

# Push your work (if using enhanced version)
stack push-stack
```

## Best Practices

### 1. Small, Focused Branches

**Good:**
```bash
stack create add-user-model -m "Add User model"
stack create add-user-validation -m "Add User validation"
stack create add-user-tests -m "Add User tests"
```

**Bad:**
```bash
stack create big-feature -m "Add everything"
# One massive commit with DB + API + UI + tests
```

**Why:** Small branches are easier to review, easier to rebase, and easier to merge independently.

### 2. Logical Dependencies

**Good:** Each branch builds on the previous
```
main
 ├─ add-api-endpoint      # Adds new endpoint
   ├─ add-endpoint-tests  # Tests the endpoint (needs the endpoint)
     ├─ add-ui-for-api    # UI using the endpoint (needs the endpoint)
```

**Bad:** Branches with no logical connection
```
main
 ├─ add-random-feature-a
   ├─ fix-unrelated-bug-b
     ├─ refactor-something-c
```

### 3. Sync Frequently

```bash
# First thing in the morning
stack sync

# After lunch (if your team is active)
stack sync

# Before starting new work
stack sync
```

**Why:** Small, frequent rebases are easier than large, infrequent ones. You'll catch conflicts early when they're fresh in your mind.

### 4. One Commit Per Branch

Graphite-style workflow uses one commit per branch:

```bash
# Make changes
vim file.py

# Amend the commit
stack modify
```

If you want multiple commits, just create multiple branches:

```bash
stack create fix-bug-part-1 -m "Fix validation"
stack create fix-bug-part-2 -m "Fix error handling"
```

### 5. Naming Conventions

Use consistent branch names:

```bash
# Feature branches
stack create feat-user-auth
stack create feat-payment-api

# Bug fixes  
stack create fix-login-crash
stack create fix-memory-leak

# Refactoring
stack create refactor-api-layer
stack create refactor-db-queries

# With ticket numbers
stack create PROJ-123-add-feature
stack create PROJ-124-fix-bug
```

### 6. Navigate Efficiently

Learn the navigation commands:

```bash
# Quick jumps
stack top      # Go to top of stack
stack bottom   # Go to bottom

# Step by step
stack down     # Move to child
stack up       # Move to parent

# Interactive
stack checkout # Select from list
```

### 7. Clean Up Merged Branches

After merging:

```bash
# Sync will detect merged branches
stack sync

# It will offer to delete them
# Or manually:
git branch -D merged-branch

# Clean up metadata if needed
# (stack will handle this automatically)
```

## Common Patterns

### Pattern 1: Feature + Tests

```bash
stack create add-feature -m "Add feature X"
# ... implement feature ...

stack create test-feature -m "Add tests for feature X"
# ... write tests ...

# If tests fail, go back and fix
stack up
# ... fix ...
stack modify  # Rebases tests automatically
```

### Pattern 2: Backend + Frontend

```bash
stack create api-endpoint -m "Add /users endpoint"
# ... implement API ...

stack create ui-users -m "Add users page"
# ... implement UI that calls API ...

# API needs changes after testing UI
stack up
# ... update API ...
stack modify  # UI gets updated API automatically
```

### Pattern 3: Database + Code

```bash
stack create db-migration -m "Add new table"
# ... create migration ...

stack create use-new-table -m "Use new table in code"
# ... write code using table ...

# Need to modify migration after testing
stack up
# ... fix migration ...
stack modify  # Code gets updated migration
```

### Pattern 4: Incremental Refactoring

```bash
stack create refactor-step-1 -m "Extract helper functions"
stack create refactor-step-2 -m "Update callers"
stack create refactor-step-3 -m "Remove old code"
stack create refactor-step-4 -m "Add documentation"
```

Each step is reviewable and can be merged independently!

## Conflict Resolution Strategies

### Strategy 1: Resolve at the Bottom

When you get conflicts during `stack sync`:

```bash
$ stack sync
⚠️  Conflict detected while restacking auth-api-endpoints
```

The conflict is in `auth-api-endpoints`. This is the bottom-most conflicting branch.

**Why it's at the bottom:** Your team changed main, and those changes conflict with your branch.

**Resolution:**
```bash
# You're already on auth-api-endpoints
# Fix the conflict
vim api/auth.py

# Stage the fix
git add api/auth.py

# Continue - stack will handle all children
stack continue
```

### Strategy 2: Prevention via Frequent Syncs

```bash
# Daily syncs mean smaller conflicts
stack sync  # Morning
# ... work ...
stack sync  # Afternoon
```

### Strategy 3: Understand the Conflict

Before resolving, understand what changed:

```bash
# See what changed on main
git log main --oneline -10

# See your changes
git log HEAD --oneline -10

# See the conflicting file
git diff main...HEAD -- path/to/file
```

## Advanced Workflows

### Workflow 1: Landing Stack Incrementally

Instead of merging the whole stack at once, merge from bottom to top:

```bash
# Merge bottom branch
stack bottom
# Create PR, get approved, merge

# Sync to update stack
stack sync

# Bottom branch is gone, next one is now at bottom
stack bottom
# Create PR, get approved, merge

# Repeat until stack is empty
```

### Workflow 2: Split Branch Mid-Development

Realized your branch is too big?

```bash
# You're on big-feature branch
# Create a new branch from main
git checkout main
stack create part-1 -m "First part of feature"

# Cherry-pick specific commits
git cherry-pick <commit-hash>

# Continue building
stack create part-2 -m "Second part of feature"
# ... more work ...
```

### Workflow 3: Reparent a Branch

Move a branch to depend on a different parent:

```bash
# Manual reparenting
stack checkout branch-to-move
git rebase new-parent

# Update metadata
# Edit .git/stack-metadata.json to update parent

# Or recreate the branch
git branch -m branch-to-move branch-to-move-old
stack create branch-to-move -m "..."
# ... cherry-pick or reapply changes ...
```

## Troubleshooting

### Problem: Lost track of branches

**Solution:**
```bash
# See all branches
git branch -a

# See stack tree
stack tree

# If branch isn't tracked, recreate it:
git checkout orphaned-branch
git checkout -b orphaned-branch-new
stack create orphaned-branch-new -m "Recovered branch"
```

### Problem: Metadata got corrupted

**Solution:**
```bash
# Backup current metadata
cp .git/stack-metadata.json .git/stack-metadata.json.bak

# Start fresh
rm .git/stack-metadata.json

# Recreate your stack
git checkout main
stack create branch-1 -m "Branch 1"
stack create branch-2 -m "Branch 2"
# etc.
```

### Problem: Accidentally modified wrong branch

**Solution:**
```bash
# Undo last commit
git reset HEAD~1

# Move to correct branch
stack checkout correct-branch

# Recommit
git add -A
git commit -m "My changes"
```

### Problem: Can't resolve conflict

**Solution:**
```bash
# Abort the rebase
git rebase --abort

# Start over with fresh main
stack sync --force

# Or skip this branch for now
git checkout main
```

## Integration with Other Tools

### With GitHub CLI

```bash
# Create PRs for your stack
for branch in $(git branch --list | grep feat-); do
  git checkout $branch
  parent=$(git show-branch | grep '*' | grep -v "$(git branch --show-current)" | head -n1 | sed 's/.*\[\(.*\)\].*/\1/')
  gh pr create --base $parent --head $branch
done
```

### With Git Hooks

```bash
# .git/hooks/post-checkout
#!/bin/bash
# Auto-sync when switching to main
if [ "$3" == "1" ] && [ "$1" != "$2" ]; then
  new_branch=$(git branch --show-current)
  if [ "$new_branch" == "main" ]; then
    stack sync
  fi
fi
```

### With VS Code

Add to `.vscode/tasks.json`:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Stack Sync",
      "type": "shell",
      "command": "stack sync",
      "presentation": {"reveal": "always"}
    },
    {
      "label": "Stack Tree",
      "type": "shell",
      "command": "stack tree",
      "presentation": {"reveal": "always"}
    }
  ]
}
```

## Migration Guide

### From Git Flow

```bash
# Old way
git checkout develop
git checkout -b feature/my-feature
# ... work ...
git checkout develop
git merge feature/my-feature

# New way with stack
git checkout main
stack create my-feature -m "Add feature"
# ... work ...
# Small PRs along the way!
```

### From GitHub Flow

```bash
# Old way
git checkout -b my-huge-feature
# ... weeks of work ...
git push
# Create one massive PR

# New way with stack
stack create part-1 -m "Part 1"
# ... small amount of work ...
stack create part-2 -m "Part 2"
# ... small amount of work ...
# Multiple small PRs!
```

## Tips for Teams

### 1. Document Your Stack Strategy

Add to your team's `CONTRIBUTING.md`:

```markdown
## Stacked PRs Workflow

We use stacked PRs for large features:

1. Break features into small, logical chunks
2. Each chunk is a separate branch/PR
3. Use `stack` CLI to manage dependencies
4. Review and merge incrementally from bottom to top
```

### 2. Code Review Guidelines

- Review from bottom to top of the stack
- Each PR should be independently understandable
- Approve bottom PRs first
- Top PRs can be conditionally approved ("LGTM once bottom is merged")

### 3. Merge Strategy

- Use "Squash and Merge" for each PR
- Merge bottom to top
- Run `stack sync` after each merge
- CI should run on each branch

Happy stacking! 🥞
