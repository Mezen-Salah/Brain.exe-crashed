# 🛍️ PriceSense

**AI-Powered E-Commerce with Financial Intelligence**

A sophisticated multi-agent recommendation system that combines product discovery with financial analysis, ensuring users find products they can actually afford.

---

## ⚠️ **IMPORTANT: Setup Required**

**This project does NOT work immediately after cloning.**

Before you can run this application, you must:
1. ✅ Install Docker Desktop (for Qdrant + Redis)
2. ✅ Create `.env` file with Google API key
3. ✅ Load data into Qdrant vector database
4. ✅ Install Python dependencies

**📖 See [SETUP.md](SETUP.md) for complete step-by-step instructions.**

**⏱️ Estimated setup time: 30-45 minutes**

---

## 🌟 Key Features

- **Multi-Agent AI System**: 5 specialized agents working together
- **Financial Analysis**: Real-time affordability checking with RAG
- **Smart Routing**: 3-tier execution (Fast/Smart/Deep paths)
- **Reinforcement Learning**: Thompson Sampling for continuous improvement
- **Multimodal Search**: Text + image understanding via CLIP
- **LLM Explanations**: Verified explanations with zero hallucinations
- **Creative Solutions**: Budget pathfinding for unaffordable items

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│              (Streamlit UI + Query Processing)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              INTELLIGENT ROUTING LAYER                       │
│         (Complexity Estimator + 3-Path Router)               │
│    Fast Path (50ms) | Smart Path (600ms) | Deep Path (2.5s) │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   AI AGENTS LAYER                            │
│  Agent 1: Product Discovery (CLIP + Qdrant)                  │
│  Agent 2: Financial Analyzer (RAG + Rules)                   │
│  Agent 2.5: Budget Pathfinder (K-Means + Creative Solutions) │
│  Agent 3: Smart Recommender (Thompson Sampling + ColabFilter)│
│  Agent 4: Explainer (Gemini LLM + Verification)              │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              KNOWLEDGE & MEMORY LAYER                        │
│  Qdrant (4 collections: products, users, financial_kb,       │
│          transactions) + Redis (cache + Thompson state)      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│           LEARNING & ADAPTATION LAYER                        │
│  Thompson Sampling Updates + User Profile Evolution          │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              TRUST & SAFETY LAYER                            │
│  Verification Agent + RAGAS Metrics + Trust Scoring          │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- Google Gemini API Key ([Get it here](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone and setup**:
```bash
cd c:\Users\mezen\fincommerce-engine
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

2. **Start services**:
```bash
docker-compose up -d
```

3. **Initialize database** (first time only):
```bash
docker-compose exec backend python scripts/init_db.py
docker-compose exec backend python scripts/seed_data.py
```

4. **Access the app**:
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Qdrant UI: http://localhost:6333/dashboard

## 📊 Technology Stack

### Core Infrastructure
- **Docker Compose**: Service orchestration
- **FastAPI**: High-performance backend API
- **Streamlit**: Interactive web interface

### Databases
- **Qdrant v1.7.4**: Vector database (512-dim embeddings)
- **Redis 7.2**: Cache + RL state management

### AI & ML
- **CLIP ViT-B/32**: Multimodal embeddings (text + image)
- **Google Gemini 1.5 Flash**: LLM for explanations
- **LangGraph**: Multi-agent orchestration
- **Thompson Sampling**: Bayesian reinforcement learning
- **K-Means**: Product clustering (scikit-learn)
- **RAGAS**: RAG quality evaluation

### Data Processing
- **Chonkie**: Smart text chunking
- **Regex**: Pattern matching & verification
- **Pydantic**: Data validation

## 📁 Project Structure

```
fincommerce-engine/
├── backend/
│   ├── agents/
│   │   ├── agent1_discovery.py       # Product search with CLIP
│   │   ├── agent2_financial.py       # Affordability analysis
│   │   ├── agent2_5_pathfinder.py    # Creative financing
│   │   ├── agent3_recommender.py     # Thompson Sampling ranking
│   │   └── agent4_explainer.py       # LLM explanations
│   ├── core/
│   │   ├── config.py                 # Configuration
│   │   ├── embeddings.py             # CLIP integration
│   │   ├── qdrant_client.py          # Vector DB
│   │   └── redis_client.py           # Cache & RL
│   ├── models/
│   │   ├── schemas.py                # Pydantic models
│   │   └── state.py                  # LangGraph state
│   ├── routers/
│   │   ├── search.py                 # Search endpoints
│   │   └── feedback.py               # User actions
│   ├── services/
│   │   ├── routing.py                # Complexity routing
│   │   ├── rag.py                    # RAG retrieval
│   │   ├── thompson.py               # RL logic
│   │   └── verification.py           # Fact-checking
│   ├── utils/
│   │   ├── financial.py              # Calculators
│   │   └── ragas_eval.py             # Quality metrics
│   ├── scripts/
│   │   ├── init_db.py                # Setup Qdrant
│   │   └── seed_data.py              # Load sample data
│   ├── main.py                       # FastAPI app
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app.py                        # Streamlit UI
│   ├── components/
│   │   ├── search_bar.py
│   │   ├── profile_form.py
│   │   └── results_display.py
│   ├── Dockerfile
│   └── requirements.txt
├── data/
│   ├── products.json                 # Sample products
│   ├── financial_rules.txt           # Knowledge base
│   └── users.json                    # Sample users
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🔧 API Endpoints

### Search
- `POST /api/search` - Main search endpoint
- `GET /api/search/cached/{query_hash}` - Check cache

### Feedback
- `POST /api/feedback/action` - Log user action
- `POST /api/feedback/rating` - Submit rating

### Monitoring
- `GET /api/metrics` - System metrics
- `GET /api/health` - Health check

## 🎯 Performance Targets

- **P50 Latency**: <2.0 seconds
- **P95 Latency**: <3.3 seconds
- **Cache Hit Rate**: ~35%
- **RAGAS Faithfulness**: >0.90
- **Answer Relevancy**: >0.85

## 🕷️ Web Scraping

The project includes a web scraper for [Mytek.tn](https://www.mytek.tn/), a Tunisian electronics e-commerce website.

### Quick Start

```bash
# Scrape products (basic)
python backend/scripts/scrape_mytek.py --no-selenium --max-products 100

# Scrape with detailed product pages
python backend/scripts/scrape_mytek.py --detail --max-products 50

# Load scraped products into Qdrant
python backend/scripts/load_mytek_data.py
```

See [SCRAPER_README.md](backend/scripts/SCRAPER_README.md) for detailed documentation.

## 📈 Future Enhancements

- [ ] Voice search integration
- [ ] Mobile app
- [ ] Real-time price tracking
- [ ] AR/VR product preview
- [ ] Group buying features
- [ ] Sustainability scoring
- [ ] Trade-in valuation
- [ ] Loan pre-approval

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

## 📧 Contact

For questions or support, open an issue on GitHub.
