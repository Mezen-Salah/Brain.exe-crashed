# 🚀 Setup Guide - FinCommerce Engine

## ⚠️ IMPORTANT: This Project REQUIRES Setup Before Running

**No, the site will NOT work immediately after cloning from GitHub.**

You need to complete these setup steps:

---

## 📋 What You Need to Install

### 1. External Services (REQUIRED)
- ✅ **Qdrant** (Vector Database) - localhost:6333
- ✅ **Redis** (Cache Server) - localhost:6379

### 2. Environment Configuration (REQUIRED)
- ✅ **`.env` file** with Google API key (NOT in GitHub for security)
- ✅ **Python dependencies** from requirements.txt

### 3. Data Loading (REQUIRED)
- ✅ **Load 992 products** into Qdrant with CLIP embeddings
- ✅ **Load 50,200 users** for collaborative filtering
- ✅ **Load 10 financial rules** for RAG retrieval
- ✅ **Load 3,509 transactions** for behavior analysis

---

## 🔧 Step-by-Step Installation

### Prerequisites

**Before you start, install:**
1. Python 3.10+ ([Download](https://www.python.org/downloads/))
2. Docker Desktop ([Download](https://www.docker.com/products/docker-desktop))
3. Git ([Download](https://git-scm.com/downloads))

**System Requirements:**
- RAM: 8GB minimum (16GB recommended)
- Storage: ~5GB for models and data
- OS: Windows 10+, macOS 11+, or Linux

---

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/fincommerce-engine.git
cd fincommerce-engine
```

---

### Step 2: Install Python Dependencies

**Create virtual environment:**

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Install packages:**
```bash
cd backend
pip install -r requirements.txt
```

⏱️ **This takes 5-10 minutes** (PyTorch is large)

---

### Step 3: Start External Services

**Using Docker (Recommended):**

```bash
# Start Qdrant and Redis
docker-compose up -d

# Verify they're running
docker ps
# Should show: fincommerce-qdrant and fincommerce-redis
```

**Verify connections:**
```bash
# Test Qdrant
curl http://localhost:6333/collections

# Test Redis (requires redis-cli)
redis-cli ping
# Returns: PONG
```

**Manual Installation Alternative:**

If you don't want Docker:
- **Qdrant**: Download from https://qdrant.tech/documentation/quick-start/
- **Redis**: Download from https://redis.io/download

---

### Step 4: Configure Environment

**Create `.env` file in `backend/` folder:**

```bash
cd backend
cp ../.env.example .env
```

**Edit `.env` and add your Google API key:**

```bash
# Get API key from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=AIzaSy...your_actual_key_here

# These should work as-is
QDRANT_HOST=localhost
QDRANT_PORT=6333
REDIS_HOST=localhost
REDIS_PORT=6379
LLM_MODEL=gemini-2.0-flash
```

**🔑 Getting Google API Key:**
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Paste into `.env` file

---

### Step 5: Load Data into Qdrant

**⚠️ CRITICAL: You must have your data files first!**

Place your data in `data 2.0/` folder:
```
data 2.0/
├── products.json       (Your product catalog)
├── users.json          (User profiles)
├── transactions.json   (Purchase history)
└── financial_kb.json   (Financial rules)
```

**Create Qdrant collections:**
```bash
cd backend
python scripts/recreate_collections.py
```

Expected output:
```
✅ Deleted existing collections
✅ Created collection: products (512-dim)
✅ Created collection: users (512-dim)
✅ Created collection: financial_kb (512-dim)
✅ Created collection: transactions (512-dim)
```

**Load your data:**
```bash
# Load products, users, and transactions
python scripts/load_data_2_0.py

# Load financial knowledge base
python scripts/load_financial_kb.py
```

⏱️ **This takes 10-30 minutes** (CLIP generates embeddings for each item)

Expected output:
```
✅ Loaded 992 products
✅ Loaded 50,200 users
✅ Loaded 10 financial rules
✅ Loaded 3,509 transactions
```

---

### Step 6: Start the Application

**Terminal 1 - Backend API:**
```bash
cd backend
python -m uvicorn main:app --port 8000 --reload
```

Expected:
```
================================================================================
🚀 PriceSense API Starting Up
================================================================================
✅ Qdrant connected: 4 collections
✅ Redis connected
🔧 MCP Tools: 12 registered
📡 API running at: http://localhost:8000
📚 Docs available at: http://localhost:8000/api/docs
================================================================================
```

**Terminal 2 - Frontend (Optional):**
```bash
cd frontend
streamlit run app.py --server.port 8501
```

Opens at: http://localhost:8501

---

## ✅ Verify Installation

### Test 1: API Health
```bash
curl http://localhost:8000/api/health
```

Should return:
```json
{
  "status": "healthy",
  "qdrant": {"connected": true, "collections": 4},
  "redis": {"connected": true},
  "mcp_tools": 12
}
```

### Test 2: Simple Search
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "laptop"}'
```

Should return products with scores.

### Test 3: Run Test Suite
```bash
cd backend

# Test Qdrant
python test_qdrant_quick.py

# Test Redis
python test_redis_quick.py

# Test MCP tools
python test_mcp_tools.py
```

All tests should show `✅ SUCCESS`.

---

## 🐛 Common Issues & Solutions

### Issue 1: "Connection refused" to Qdrant/Redis

**Cause**: Services not running

**Fix:**
```bash
# Check Docker
docker ps

# Restart services
docker-compose restart

# Check logs
docker-compose logs qdrant
docker-compose logs redis
```

---

### Issue 2: "No module named 'langchain'"

**Cause**: Dependencies not installed

**Fix:**
```bash
# Make sure venv is activated
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

cd backend
pip install -r requirements.txt
```

---

### Issue 3: "429 RESOURCE_EXHAUSTED" Google API

**Cause**: API quota exhausted or invalid key

**Fix:**
1. Get NEW API key from https://aistudio.google.com/app/apikey
2. Update `.env` file
3. Restart backend server

**Alternative**: Switch to OpenAI GPT-4
```bash
# In .env
OPENAI_API_KEY=sk-...your_openai_key
LLM_MODEL=gpt-4
```

---

### Issue 4: "expected dim: 512, got 384"

**Cause**: Collections created with wrong vector size

**Fix:**
```bash
# Delete and recreate collections
python scripts/recreate_collections.py

# Reload data
python scripts/load_data_2_0.py
```

---

### Issue 5: No Products in Search Results

**Cause**: Data not loaded or cache issue

**Fix:**
```bash
# Clear Redis cache
python -c "import redis; r = redis.Redis(port=6379); r.flushall()"

# Check Qdrant has data
curl http://localhost:6333/collections/products
# Should show points_count > 0
```

---

## 📦 What Gets Committed to GitHub

**✅ Included in repo:**
- Source code (`.py` files)
- Requirements (`requirements.txt`)
- Documentation (`README.md`, `SETUP.md`, etc.)
- Example config (`.env.example`)
- Docker Compose (`docker-compose.yml`)
- `.gitignore`

**❌ NOT in repo (must setup locally):**
- `.env` file (sensitive API keys)
- `venv/` folder (virtual environment)
- `data 2.0/` folder (large data files)
- `qdrant_storage/` (database files)
- `__pycache__/` (Python cache)

---

## 🚀 Quick Start Summary

For someone cloning your repo:

```bash
# 1. Clone
git clone https://github.com/yourusername/fincommerce-engine.git
cd fincommerce-engine

# 2. Install Python packages
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
cd backend
pip install -r requirements.txt

# 3. Start services
cd ..
docker-compose up -d

# 4. Setup .env
cp .env.example backend/.env
# Edit backend/.env - add your GOOGLE_API_KEY

# 5. Prepare data (YOU MUST PROVIDE data 2.0/ folder)
# Copy your data files to data 2.0/

# 6. Load data
cd backend
python scripts/recreate_collections.py
python scripts/load_data_2_0.py
python scripts/load_financial_kb.py

# 7. Start backend
python -m uvicorn main:app --port 8000

# 8. Test
curl http://localhost:8000/api/health
```

---

## 📖 Additional Resources

- **[README.md](README.md)** - Project overview and features
- **[ARCHITECTURE_CHECKLIST.md](ARCHITECTURE_CHECKLIST.md)** - Implementation status
- **[MCP_INTEGRATION.md](MCP_INTEGRATION.md)** - MCP tools documentation
- **[API Docs](http://localhost:8000/api/docs)** - Interactive Swagger UI

---

## 💡 Pro Tips

1. **Use Docker**: It's the easiest way to run Qdrant and Redis
2. **Cache Your Data**: After loading once, Qdrant persists data (don't reload every time)
3. **Monitor Resources**: CLIP model uses ~2GB RAM
4. **Use `.env.example`**: Share this in repo so others know what to configure
5. **Document Your Data Format**: Add example JSON structures to help others

---

## 🤝 Sharing Your Project

**What to tell people:**

> "This project requires setup before running. Please follow SETUP.md for:
> 1. Installing Docker (for Qdrant + Redis)
> 2. Creating .env file with Google API key
> 3. Loading your data into Qdrant
> 
> Estimated setup time: 30-45 minutes"

**Consider adding to README.md:**
```markdown
## ⚠️ Setup Required

This project does NOT work out of the box. See [SETUP.md](SETUP.md) for complete installation instructions.

Required before running:
- Docker Desktop
- Google API Key
- Python 3.10+
- 30-45 minutes for setup
```

---

**Need help? Check troubleshooting section above or open an issue on GitHub.**
