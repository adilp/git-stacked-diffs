#!/bin/bash
# Comprehensive test script for stack CLI functionality
#
# This script creates an isolated test repository and validates:
# - Branch creation and stacking
# - Tree visualization and structure
# - Navigation commands (up/down/top/bottom)
# - Modify and restack workflow
# - Sync with main branch updates
# - Conflict resolution with stack continue
# - --no-commit flag behavior
# - Metadata integrity and JSON validity
#
# Each test includes assertions to validate:
# - Current branch after operations
# - Branch existence
# - Commit messages
# - File contents
# - Staged changes preservation
# - Metadata tracking

set -e

# Helper function to assert current branch
assert_branch() {
    local expected="$1"
    local actual=$(git branch --show-current)
    if [ "$actual" != "$expected" ]; then
        echo "❌ FAIL: Expected to be on branch '$expected', but on '$actual'"
        exit 1
    fi
    echo "✓ On branch: $expected"
}

# Helper function to assert branch exists
assert_branch_exists() {
    local branch="$1"
    if ! git show-ref --verify --quiet "refs/heads/$branch"; then
        echo "❌ FAIL: Expected branch '$branch' to exist, but it doesn't"
        exit 1
    fi
    echo "✓ Branch exists: $branch"
}

# Helper function to assert commit message
assert_commit_message() {
    local expected="$1"
    local actual=$(git log -1 --pretty=%B | head -1)
    if [ "$actual" != "$expected" ]; then
        echo "❌ FAIL: Expected commit message '$expected', but got '$actual'"
        exit 1
    fi
    echo "✓ Commit message: $expected"
}

# Helper function to assert file exists and has content
assert_file_content() {
    local file="$1"
    local expected="$2"
    if [ ! -f "$file" ]; then
        echo "❌ FAIL: Expected file '$file' to exist, but it doesn't"
        exit 1
    fi
    local actual=$(cat "$file")
    if [ "$actual" != "$expected" ]; then
        echo "❌ FAIL: Expected file '$file' to contain '$expected', but got '$actual'"
        exit 1
    fi
    echo "✓ File content correct: $file"
}

# Helper function to verify metadata exists and is valid JSON
assert_metadata_valid() {
    local metadata_file=".git/stack-metadata.json"
    if [ ! -f "$metadata_file" ]; then
        echo "❌ FAIL: Metadata file not found at $metadata_file"
        exit 1
    fi
    if ! python3 -c "import json; json.load(open('$metadata_file'))" 2>/dev/null; then
        echo "❌ FAIL: Metadata file is not valid JSON"
        exit 1
    fi
    echo "✓ Metadata file is valid JSON"
}

# Helper function to assert branch is in metadata
assert_in_metadata() {
    local branch="$1"
    local metadata_file=".git/stack-metadata.json"
    if ! python3 -c "import json; data = json.load(open('$metadata_file')); exit(0 if '$branch' in data.get('stacks', {}) else 1)" 2>/dev/null; then
        echo "❌ FAIL: Branch '$branch' not found in metadata"
        exit 1
    fi
    echo "✓ Branch in metadata: $branch"
}

echo "🧪 Stack CLI Demo"
echo "================="
echo ""

# Get the path to stack CLI BEFORE changing directory
STACK_CLI="$HOME/.local/bin/stack"
if [ ! -f "$STACK_CLI" ]; then
    # Get absolute path to the script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    STACK_CLI="$SCRIPT_DIR/stack.py"
fi

echo "📦 Using stack CLI at: $STACK_CLI"
echo ""

# Setup test repo
TEST_DIR="/tmp/stack-test-$(date +%s)"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "📁 Creating test repository at $TEST_DIR"
git init
git config user.email "test@example.com"
git config user.name "Test User"

# Create initial commit on main
echo "main content" > README.md
git add README.md
git commit -m "Initial commit"
assert_branch "main"
assert_commit_message "Initial commit"
assert_file_content "README.md" "main content"
echo "✓ Created main branch with initial commit"
echo ""

# Test 1: Create first branch
echo "Test 1: Creating first branch in stack"
echo "---------------------------------------"
echo "file1 content" > file1.txt
git add file1.txt
python3 "$STACK_CLI" create feature-1 -m "Add feature 1"
assert_branch "feature-1"
assert_branch_exists "feature-1"
assert_commit_message "Add feature 1"
assert_file_content "file1.txt" "file1 content"
echo ""

# Test 2: Create second branch on top
echo "Test 2: Stacking second branch"
echo "-------------------------------"
echo "file2 content" > file2.txt
git add file2.txt
python3 "$STACK_CLI" create feature-2 -m "Add feature 2"
assert_branch "feature-2"
assert_branch_exists "feature-2"
assert_commit_message "Add feature 2"
assert_file_content "file2.txt" "file2 content"
echo "✓ feature-2 stacked on feature-1"
echo ""

# Test 3: Create third branch (modify different file to avoid conflicts)
echo "Test 3: Stacking third branch"
echo "------------------------------"
echo "file3 content" > file3.txt
git add file3.txt
python3 "$STACK_CLI" create feature-3 -m "Add feature 3"
assert_branch "feature-3"
assert_branch_exists "feature-3"
assert_commit_message "Add feature 3"
assert_file_content "file3.txt" "file3 content"
echo "✓ feature-3 stacked on feature-2"
echo ""

# Test 4: Show tree
echo "Test 4: Displaying stack tree"
echo "------------------------------"
TREE_OUTPUT=$(python3 "$STACK_CLI" tree)
echo "$TREE_OUTPUT"
# Verify all branches appear in tree output
if ! echo "$TREE_OUTPUT" | grep -q "feature-1"; then
    echo "❌ FAIL: feature-1 not found in tree output"
    exit 1
fi
if ! echo "$TREE_OUTPUT" | grep -q "feature-2"; then
    echo "❌ FAIL: feature-2 not found in tree output"
    exit 1
fi
if ! echo "$TREE_OUTPUT" | grep -q "feature-3"; then
    echo "❌ FAIL: feature-3 not found in tree output"
    exit 1
fi
echo "✓ All branches present in tree"
echo ""

# Test 5: Navigate down
echo "Test 5: Navigating down the stack"
echo "----------------------------------"
python3 "$STACK_CLI" bottom
assert_branch "feature-1"
echo "✓ Navigated to bottom of stack"
echo ""

# Test 6: Navigate up
echo "Test 6: Navigating up the stack"
echo "--------------------------------"
python3 "$STACK_CLI" up
assert_branch "main"
echo "✓ Navigated up to parent (main)"
python3 "$STACK_CLI" status
echo ""

# Test 7: Test modify on leaf branch (no children to restack)
echo "Test 7: Testing modify command on leaf branch"
echo "----------------------------------------------"
git checkout feature-3
assert_branch "feature-3"
# Modify the leaf branch (no conflicts possible since no children)
echo "additional content" >> file3.txt
git add file3.txt
BEFORE_HASH=$(git rev-parse HEAD)
ORIGINAL_MESSAGE=$(git log -1 --pretty=%B | head -1)
python3 "$STACK_CLI" modify
AFTER_HASH=$(git rev-parse HEAD)
if [ "$BEFORE_HASH" = "$AFTER_HASH" ]; then
    echo "❌ FAIL: Commit was not amended"
    exit 1
fi
# Message should stay the same (modify amends without changing message)
assert_commit_message "$ORIGINAL_MESSAGE"
echo "✓ Modified leaf branch successfully"
echo ""

# Test 8: Simulate main branch update
echo "Test 8: Syncing with updated main"
echo "----------------------------------"
# Remember current branch before switching
BRANCH_BEFORE_SYNC=$(git branch --show-current)
git checkout main
assert_branch "main"
BEFORE_HASH=$(git rev-parse HEAD)
echo "main updated content" >> README.md
git add README.md
git commit -m "Update main"
AFTER_HASH=$(git rev-parse HEAD)
if [ "$BEFORE_HASH" = "$AFTER_HASH" ]; then
    echo "❌ FAIL: Main branch commit failed"
    exit 1
fi
echo "✓ Updated main branch"
echo ""
echo "Now syncing stack..."
python3 "$STACK_CLI" sync
# After sync, should return to the branch we were on before (unless it was main)
if [ "$BRANCH_BEFORE_SYNC" = "main" ]; then
    assert_branch "main"
else
    assert_branch "$BRANCH_BEFORE_SYNC"
fi
echo "✓ Sync completed successfully"
echo ""

# Test 9: Show final tree
echo "Test 9: Final stack tree"
echo "------------------------"
TREE_OUTPUT=$(python3 "$STACK_CLI" tree)
echo "$TREE_OUTPUT"
# Verify stack still intact after sync
if ! echo "$TREE_OUTPUT" | grep -q "feature-1"; then
    echo "❌ FAIL: feature-1 missing after sync"
    exit 1
fi
if ! echo "$TREE_OUTPUT" | grep -q "feature-2"; then
    echo "❌ FAIL: feature-2 missing after sync"
    exit 1
fi
if ! echo "$TREE_OUTPUT" | grep -q "feature-3"; then
    echo "❌ FAIL: feature-3 missing after sync"
    exit 1
fi
echo "✓ Stack intact after sync"
echo ""

# Test 10: Test navigation commands
echo "Test 10: Testing navigation commands"
echo "-------------------------------------"
python3 "$STACK_CLI" bottom
assert_branch "feature-1"
echo "✓ At bottom"
echo "Moving up to parent..."
python3 "$STACK_CLI" up
assert_branch "main"
echo "✓ Moved up to parent (main)"
echo "Going back to bottom and then to top..."
python3 "$STACK_CLI" bottom
python3 "$STACK_CLI" top
assert_branch "feature-3"
echo "✓ At top of stack"
echo ""

echo "Test 11: Testing conflict resolution with stack continue"
echo "---------------------------------------------------------"
echo "Setting up a conflict scenario..."

# Start from main and create a branch
git checkout main
assert_branch "main"
echo "line 1" > shared-file.txt
git add shared-file.txt
python3 "$STACK_CLI" create conflict-branch-a -m "Add shared file with line 1"
assert_branch "conflict-branch-a"
assert_commit_message "Add shared file with line 1"

# Add a child branch
echo "line 2 from branch a" >> shared-file.txt
git add shared-file.txt
python3 "$STACK_CLI" create conflict-child-a -m "Add line 2"
assert_branch "conflict-child-a"
assert_commit_message "Add line 2"
echo "✓ Created parent and child branches"
echo ""

# Now go back to main and add conflicting content
git checkout main
echo "line 1" > shared-file.txt
echo "conflicting line 2 from main" >> shared-file.txt
git add shared-file.txt
git commit -m "Add conflicting change to main"
echo "✓ Created conflicting change on main"
echo ""

# Now try to sync - this should cause a conflict
echo "Attempting to sync conflict-branch-a (this will cause a conflict)..."
git checkout conflict-branch-a
set +e  # Allow command to fail
OUTPUT=$(python3 "$STACK_CLI" sync 2>&1)
SYNC_EXIT=$?
set -e
echo "$OUTPUT" | tail -5

if [ $SYNC_EXIT -eq 0 ]; then
    echo "❌ FAIL: Expected sync to fail with conflict, but it succeeded"
    git rebase --abort 2>/dev/null || true
    exit 1
else
    echo "✓ Sync failed as expected due to conflict"
    echo ""
    echo "Checking rebase state..."
    if git status | grep -q "rebase in progress\|needs merge"; then
        echo "✓ Git is in rebase/conflict state"
        echo ""
        echo "Resolving conflict by accepting theirs (newer version)..."
        git checkout --theirs shared-file.txt 2>/dev/null || true
        git add shared-file.txt
        echo ""
        echo "Running 'stack continue' to complete the rebase..."
        python3 "$STACK_CLI" continue
        # After continue, we end up on the last restacked branch (child)
        # Verify both branches still exist
        assert_branch_exists "conflict-branch-a"
        assert_branch_exists "conflict-child-a"
        echo "✓ Conflict resolution completed successfully"
        echo "✓ Both parent and child branches exist after conflict resolution"
    else
        echo "❌ FAIL: Git is not in rebase state after conflict"
        exit 1
    fi
fi
echo ""

echo "Test 12: Testing --no-commit flag"
echo "----------------------------------"
git checkout main
assert_branch "main"
echo "test file for no-commit" > no-commit-test.txt
git add no-commit-test.txt
python3 "$STACK_CLI" create no-commit-branch --no-commit
assert_branch "no-commit-branch"
assert_branch_exists "no-commit-branch"
echo "✓ Branch created without committing staged changes"
# Verify the file is still staged
if git diff --cached --quiet; then
    echo "❌ FAIL: Expected staged changes but found none"
    exit 1
else
    echo "✓ Staged changes preserved"
fi
# Verify the staged file is the one we created
if ! git diff --cached --name-only | grep -q "no-commit-test.txt"; then
    echo "❌ FAIL: Expected no-commit-test.txt to be staged"
    exit 1
fi
echo "✓ Correct file is staged"
echo ""

echo "Test 13: Validating metadata integrity"
echo "---------------------------------------"
assert_metadata_valid
assert_in_metadata "main"
assert_in_metadata "feature-1"
assert_in_metadata "feature-2"
assert_in_metadata "feature-3"
assert_in_metadata "conflict-branch-a"
assert_in_metadata "conflict-child-a"
assert_in_metadata "no-commit-branch"
echo "✓ All branches properly tracked in metadata"
echo ""

echo "✅ All tests passed!"
echo ""
echo "Test repository created at: $TEST_DIR"
echo "You can explore it with: cd $TEST_DIR && python3 $STACK_CLI tree"
echo ""
echo "To cleanup: rm -rf $TEST_DIR"
