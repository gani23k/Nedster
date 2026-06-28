#!/bin/bash
# Install script to make Nedster accessible globally for users.

set -e

echo "========================================="
echo "   Installing Nedster Global Wrapper"
echo "========================================="

# 1. Detect where the script is being run from (the repo directory)
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[1/4] Repository found at: $REPO_DIR"

# 2. Setup the virtual environment and install dependencies
echo "[2/4] Setting up Python virtual environment..."
cd "$REPO_DIR"

# Check if python3-venv is available or if we should just use uv/pip
if command -v uv &> /dev/null; then
    echo "Using 'uv' for fast dependency resolution..."
    uv venv .venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
else
    echo "Using standard pip..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
fi
echo "Dependencies installed."

# 3. Create the global executable wrapper
echo "[3/4] Creating global 'nedster' command..."
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

WRAPPER_PATH="$BIN_DIR/nedster"

cat << EOF > "$WRAPPER_PATH"
#!/bin/bash
# Global wrapper to run Nedster from anywhere

# Change to the Nedster repository directory
cd "$REPO_DIR" || exit 1

# Activate the virtual environment
source .venv/bin/activate

# Execute Nedster with passed arguments
exec python3 nedster.py "\$@"
EOF

chmod +x "$WRAPPER_PATH"
echo "Created wrapper at: $WRAPPER_PATH"

# 4. Ensure ~/.local/bin is in the user's PATH
echo "[4/4] Verifying PATH..."
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "\nWARNING: $BIN_DIR is not in your PATH."
    echo "To use the 'nedster' command globally, add this line to your ~/.bashrc or ~/.zshrc:"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "Then run: source ~/.bashrc"
else
    echo "PATH is correctly configured."
fi

echo "========================================="
echo "   Installation Complete!"
echo "   You can now run 'nedster' from anywhere."
echo "========================================="
