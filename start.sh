#!/bin/bash
# Startup script for Monolith Standalone with AI features

cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org openai anthropic
else
    # Activate virtual environment
    source venv/bin/activate
fi

echo "Starting Monolith Editor with AI features..."
echo "Server will be available at: http://localhost:8000"
echo ""

# Start the server
python MonolithStandalone.py
