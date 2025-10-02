#!/bin/bash
# Installation script for git-stack CLI

set -e

echo "Installing git-stack CLI..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Get installation directory
INSTALL_DIR="${HOME}/.local/bin"
mkdir -p "${INSTALL_DIR}"

# Copy the script
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/stack.py"
cp "${SCRIPT_PATH}" "${INSTALL_DIR}/git-stack"
chmod +x "${INSTALL_DIR}/git-stack"

# Check if directory is in PATH
if [[ ":$PATH:" != *":${INSTALL_DIR}:"* ]]; then
    echo ""
    echo "⚠️  Warning: ${INSTALL_DIR} is not in your PATH"
    echo "Add this line to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo "✓ git-stack CLI installed to ${INSTALL_DIR}/git-stack"
echo ""
echo "Run 'git-stack' or 'git stack' to get started!"
echo "Tip: Create an alias: alias sk='git-stack'"
