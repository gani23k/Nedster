#!/bin/bash
# Global wrapper to run Nedster from anywhere

# Change to the Nedster repository directory
cd "/home/mnm/AI_Lab/Workspace/Nedster" || exit 1

# Activate the virtual environment
source .venv/bin/activate

# Execute Nedster with passed arguments
exec python3 nedster.py "$@"
