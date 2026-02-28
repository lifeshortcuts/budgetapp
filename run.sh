#!/bin/bash
# Launch the app on Mac
cd "$(dirname "$0")"
source .venv/bin/activate
streamlit run app.py
