# Stack CLI - Quick Reference

## What You Get

A simple Python CLI tool for managing stacked Git branches, with:

- ✅ **Automatic restacking** - When you modify a branch, all dependent branches rebase automatically
- ✅ **Easy sync** - Pull main and rebase entire stack in one command
- ✅ **Navigation** - Move up/down your stack easily
- ✅ **Conflict handling** - Clear workflow for resolving rebase conflicts
- ✅ **Visual tree** - See your entire stack structure
- ✅ **No dependencies** - Just Python 3 and Git

## Files Included

```
stack.py              # Main CLI tool (single file, ~600 lines)
install.sh            # Installation script
test-stack.sh         # Demo/test script
README.md             # Full documentation
EXAMPLES.md           # Real-world examples and best practices
stack-enhanced.py     # Enhanced version with push/PR features
```

## Installation

```bash
./install.sh
```

Or manually:
```bash
cp stack.py ~/.local/bin/stack
chmod +x ~/.local/bin/stack
export PATH="$HOME/.local/bin:$PATH"
```

## Quick Start

```bash
# Create your first stack
git checkout main
stack create api -m "Add API endpoint"
stack create tests -m "Add tests"
stack create docs -m "Add documentation"

# See the stack
stack tree

# Navigate
stack up      # Go to parent
stack down    # Go to child
stack bottom  # Jump to bottom
stack top     # Jump to top

# Sync with main
stack sync

# Modify a branch
stack checkout api
# ... make changes ...
stack modify  # Auto-restacks tests and docs!
```

## Core Commands

| Command | Description |
|---------|-------------|
| `stack create <name> -m "msg"` | Create new branch |
| `stack checkout [name]` | Switch branches (interactive if no name) |
| `stack sync` | Pull main and rebase all branches |
| `stack restack` | Rebase current branch and children |
| `stack modify` | Amend commit and restack children |
| `stack continue` | Continue after resolving conflicts |
| `stack tree` | Show visual tree |
| `stack up/down` | Navigate parent/child |
| `stack top/bottom` | Jump to top/bottom of stack |

## How It Works

Stack maintains metadata in `.git/stack-metadata.json` that tracks parent/child relationships between branches. When you run commands like `modify` or `sync`, it automatically rebases dependent branches in the correct order.

## Typical Workflow

```bash
# Monday morning
stack sync

# Start new feature
stack create feat-step-1 -m "First step"
# ... code ...

stack create feat-step-2 -m "Second step"  
# ... code ...

# Review feedback on step 1
stack checkout feat-step-1
# ... make changes ...
stack modify  # feat-step-2 rebases automatically

# End of day
stack tree  # See what you did
```

## When to Use

**Perfect for:**
- Large features split into small PRs
- Features with clear dependencies (DB → API → UI)
- Teams that want fast code reviews
- Developers who hate waiting for reviews

**Not needed for:**
- Single, simple changes
- Completely independent features
- Teams that prefer large PRs

## vs Graphite

Stack is a simplified, self-contained version of Graphite:

| Feature | Stack | Graphite |
|---------|-------|----------|
| Stacked branches | ✅ | ✅ |
| Auto-restack | ✅ | ✅ |
| Sync with main | ✅ | ✅ |
| Navigation | ✅ | ✅ |
| GitHub integration | ❌ | ✅ |
| Web UI | ❌ | ✅ |
| Cloud sync | ❌ | ✅ |
| Team features | ❌ | ✅ |
| Installation | One file | Package |
| Cost | Free | Paid for teams |

Use Stack if you want the core workflow without complexity. Use Graphite if you need GitHub integration and team features.

## Key Benefits

1. **Stay in flow** - Don't wait for reviews to continue coding
2. **Easier reviews** - Small PRs are faster to review
3. **Better history** - Each change is separate and clear
4. **Parallel work** - Work on multiple related features
5. **Easy iteration** - Modify any branch, dependents update automatically

## Common Questions

**Q: What happens if I use regular Git commands?**  
A: That's fine! Stack is just a wrapper. Use `git` whenever you want. Just run `stack restack` after to update dependents.

**Q: What if I get conflicts?**  
A: Resolve them normally (`git add` + `stack continue`), Stack handles the rest.

**Q: Can I have multiple stacks?**  
A: Yes! Just create branches from main. Each forms its own stack.

**Q: How do I merge my stack?**  
A: Merge PRs bottom-to-top, run `stack sync` between merges.

**Q: What if I mess up the metadata?**  
A: Delete `.git/stack-metadata.json` and recreate your branches with `stack create`.

## Next Steps

1. Try the demo: `./test-stack.sh`
2. Read examples: `EXAMPLES.md`
3. Integrate with your workflow
4. Consider enhanced features: `stack-enhanced.py`

## Customization Ideas

Want to extend it? Easy since it's just Python:

- Add `stack submit` to create GitHub PRs
- Add `stack push` to push branches  
- Integrate with your CI/CD
- Add branch naming conventions
- Auto-format commit messages
- Integrate with Jira/Linear

Check `stack-enhanced.py` for examples!

## Getting Help

- Run `stack` with no args for help
- Check `README.md` for full docs
- Read `EXAMPLES.md` for real-world patterns
- Open issues/PRs if you find bugs

---

**Made with ❤️ for developers who love clean Git history**

Start stacking! 🥞
