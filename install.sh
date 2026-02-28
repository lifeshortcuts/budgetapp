#!/bin/bash
# One-time setup for Mac
cd "$(dirname "$0")"
echo "Setting up Budget Tracker..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt
echo ""
echo "Done! Run ./run.sh to start the app."
