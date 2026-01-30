#!/bin/bash
# Quick Setup Script for FinCommerce Engine (macOS/Linux)
# Run this after cloning the repository

echo "========================================"
echo "FinCommerce Engine - Quick Setup"
echo "========================================"
echo ""

# Check Python
echo "[1/7] Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ Python found: $PYTHON_VERSION"
else
    echo "❌ Python 3.10+ required. Install from https://www.python.org/"
    exit 1
fi

# Check Docker
echo ""
echo "[2/7] Checking Docker installation..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "✅ Docker found: $DOCKER_VERSION"
else
    echo "❌ Docker required. Install from https://www.docker.com/"
    exit 1
fi

# Create virtual environment
echo ""
echo "[3/7] Creating Python virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists"
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate and install dependencies
echo ""
echo "[4/7] Installing Python dependencies..."
echo "⏱️  This may take 5-10 minutes..."

source venv/bin/activate
cd backend
pip install -r requirements.txt --quiet
if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi
cd ..

# Start Docker services
echo ""
echo "[5/7] Starting Qdrant and Redis..."
docker-compose up -d
sleep 5

QDRANT_RUNNING=$(docker ps --filter "name=fincommerce-qdrant" --format "{{.Names}}")
REDIS_RUNNING=$(docker ps --filter "name=fincommerce-redis" --format "{{.Names}}")

if [ ! -z "$QDRANT_RUNNING" ] && [ ! -z "$REDIS_RUNNING" ]; then
    echo "✅ Qdrant running on port 6333"
    echo "✅ Redis running on port 6379"
else
    echo "❌ Failed to start Docker services"
    exit 1
fi

# Check .env file
echo ""
echo "[6/7] Checking .env configuration..."
if [ -f "backend/.env" ]; then
    echo "✅ .env file exists"
    
    # Check if API key is set
    if grep -q "GOOGLE_API_KEY=AIza" backend/.env; then
        echo "✅ Google API key configured"
    else
        echo "⚠️  Please add your Google API key to backend/.env"
        echo "   Get key from: https://aistudio.google.com/app/apikey"
    fi
else
    echo "⚠️  Creating .env from template..."
    cp .env.example backend/.env
    echo "⚠️  Please edit backend/.env and add your Google API key"
    echo "   Get key from: https://aistudio.google.com/app/apikey"
fi

# Check data folder
echo ""
echo "[7/7] Checking data files..."
if [ -d "data 2.0" ]; then
    DATA_COUNT=$(ls "data 2.0"/*.json 2>/dev/null | wc -l)
    if [ $DATA_COUNT -ge 4 ]; then
        echo "✅ Data files found: $DATA_COUNT files"
        echo ""
        echo "📊 Ready to load data into Qdrant:"
        echo "   cd backend"
        echo "   python scripts/recreate_collections.py"
        echo "   python scripts/load_data_2_0.py"
        echo "   python scripts/load_financial_kb.py"
    else
        echo "⚠️  Some data files missing in 'data 2.0' folder"
    fi
else
    echo "⚠️  'data 2.0' folder not found"
    echo "   Create folder and add your JSON data files"
fi

# Summary
echo ""
echo "========================================"
echo "Setup Complete! 🎉"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Add Google API key to backend/.env (if not done)"
echo "2. Load data into Qdrant (see commands above)"
echo "3. Start backend: cd backend && python -m uvicorn main:app --port 8000"
echo "4. Open browser: http://localhost:8000/api/docs"
echo ""
echo "See SETUP.md for detailed instructions"
echo ""
