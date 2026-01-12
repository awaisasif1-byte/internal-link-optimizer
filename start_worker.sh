#!/bin/bash

# Quick Start Script for Python Crawler Worker
# Usage: ./start_worker.sh

echo "🚀 Internal Link Optimizer - Worker Setup"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Check if dependencies are installed
if ! python3 -c "import httpx" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

# Check environment variables
if [ -z "$SUPABASE_URL" ]; then
    echo "⚠️  SUPABASE_URL not set"
    read -p "Enter your Supabase URL: " SUPABASE_URL
    export SUPABASE_URL
fi

if [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "⚠️  SUPABASE_SERVICE_ROLE_KEY not set"
    read -p "Enter your Supabase Service Role Key: " SUPABASE_SERVICE_ROLE_KEY
    export SUPABASE_SERVICE_ROLE_KEY
fi

if [ -z "$SESSION_ID" ]; then
    echo "⚠️  SESSION_ID not set"
    read -p "Enter your Session ID (from dashboard): " SESSION_ID
    export SESSION_ID
fi

echo ""
echo "✅ Configuration complete!"
echo "📋 Session ID: $SESSION_ID"
echo "🌐 Supabase: $SUPABASE_URL"
echo ""
echo "Starting crawler worker..."
echo "Press Ctrl+C to stop (progress will be saved)"
echo ""

# Run the worker
python3 worker.py
