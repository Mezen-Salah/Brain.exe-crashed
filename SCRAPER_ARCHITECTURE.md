# Mytek.tn Web Scraper - Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                              │
│                                                                     │
│  CLI Commands:                                                      │
│  • python scripts/scrape_mytek.py [options]                        │
│  • python scripts/load_mytek_data.py                               │
│  • ./scripts/run_mytek_pipeline.sh                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                    SCRAPING LAYER                                   │
│                  (scrape_mytek.py)                                  │
│                                                                     │
│  ┌─────────────┐           ┌─────────────┐                        │
│  │  Selenium   │    OR     │  Requests   │                        │
│  │   Mode      │           │    Only     │                        │
│  │ (JavaScript)│           │   (Fast)    │                        │
│  └──────┬──────┘           └──────┬──────┘                        │
│         │                         │                                │
│         └────────────┬────────────┘                                │
│                      │                                             │
│         ┌────────────▼────────────┐                                │
│         │   HTML Parser (BS4)     │                                │
│         │  • BeautifulSoup + lxml │                                │
│         │  • CSS selectors        │                                │
│         │  • Regex patterns       │                                │
│         └────────────┬────────────┘                                │
└──────────────────────┼─────────────────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────────────┐
│                   PARSING LAYER                                     │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │  Product Information Extractors:                          │    │
│  │  • parse_product_card()    - Quick listing data          │    │
│  │  • parse_product_detail()  - Detailed page data          │    │
│  │  • discover_categories()   - Navigation discovery        │    │
│  │  • extract_price()         - TND price normalization     │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                     │
│  Extracted Data:                                                   │
│  • Name, Brand, Model                                              │
│  • Prices (TND), Discounts                                         │
│  • Images, Specifications                                          │
│  • Categories, Ratings, SKU                                        │
└────────────────────────┬───────────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────────┐
│                  ENRICHMENT LAYER                                   │
│                                                                     │
│  enrich_products():                                                │
│  • Generate unique IDs (mytek_00001, ...)                         │
│  • Add timestamps (created_at, updated_at)                        │
│  • Calculate discounts (percentage)                               │
│  • Set default values (condition, availability, seller)           │
│  • Extract model numbers from names                               │
└────────────────────────┬───────────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────────┐
│                   OUTPUT LAYER                                      │
│                                                                     │
│  JSON Files:                                                       │
│  • mytek_products.json         - Full product array              │
│  • mytek_products_summary.json - Statistics & metadata           │
│                                                                     │
│  Format: Compatible with PriceSense data structure                │
└────────────────────────┬───────────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────────┐
│              INTEGRATION LAYER (Optional)                           │
│                 (load_mytek_data.py)                               │
│                                                                     │
│  ┌─────────────────────────────────────────────────┐              │
│  │  Data Processing:                               │              │
│  │  • TND → USD conversion (0.32 rate)            │              │
│  │  • Build searchable text for embeddings        │              │
│  │  • Normalize to system schema                  │              │
│  └────────────────────┬────────────────────────────┘              │
│                       │                                            │
│  ┌────────────────────▼────────────────────────────┐              │
│  │  CLIP Embeddings:                               │              │
│  │  • Generate 512-dim vectors                     │              │
│  │  • Text encoding via CLIPEmbedder               │              │
│  └────────────────────┬────────────────────────────┘              │
│                       │                                            │
│  ┌────────────────────▼────────────────────────────┐              │
│  │  Qdrant Upload:                                 │              │
│  │  • Batch processing (50 products/batch)        │              │
│  │  • Vector + payload storage                    │              │
│  │  • Progress tracking & error handling          │              │
│  └─────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────┘

```

## Data Flow

```
Website (mytek.tn)
    │
    │ HTTP/HTTPS Request
    ▼
HTML Content
    │
    │ BeautifulSoup Parsing
    ▼
Raw Product Data
    │
    │ Normalization & Enrichment
    ▼
JSON File (TND prices)
    │
    │ Optional: load_mytek_data.py
    ▼
Processed Data (USD prices)
    │
    │ CLIP Embedding Generation
    ▼
Qdrant Vector Database
    │
    │ Integration with PriceSense
    ▼
AI-Powered Search & Recommendations
```

## Component Interaction

```
┌──────────────────┐
│  CLI Interface   │
└────────┬─────────┘
         │
         │ executes
         ▼
┌──────────────────┐     ┌──────────────────┐
│ MytekScraper     │────▶│  requests/       │
│                  │     │  selenium        │
│ • fetch_page()   │◀────│                  │
│ • parse_*()      │     └──────────────────┘
│ • enrich_*()     │
│ • save_to_json() │     ┌──────────────────┐
└────────┬─────────┘────▶│  BeautifulSoup   │
         │               │  (HTML Parser)   │
         │               └──────────────────┘
         │
         │ saves
         ▼
┌──────────────────┐
│  JSON Files      │
│  (data/)         │
└────────┬─────────┘
         │
         │ reads
         ▼
┌──────────────────┐     ┌──────────────────┐
│ load_mytek_data  │────▶│  CLIPEmbedder    │
│                  │     │  (Embeddings)    │
│ • process_*()    │     └──────────────────┘
│ • upload_*()     │
└────────┬─────────┘     ┌──────────────────┐
         │               │  QdrantManager   │
         └──────────────▶│  (Vector DB)     │
                         └──────────────────┘
```

## Error Handling Flow

```
┌─────────────────┐
│ Start Request   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Try Fetch       │◀─────────────┐
└────────┬────────┘              │
         │                       │
    Success? ──No──▶ Retry? ─Yes─┘
         │              │
        Yes            No
         │              │
         ▼              ▼
┌─────────────────┐  ┌─────────────────┐
│ Parse HTML      │  │ Log Error &     │
└────────┬────────┘  │ Continue        │
         │           └─────────────────┘
         ▼
┌─────────────────┐
│ Extract Data    │
└────────┬────────┘
         │
    Valid? ──No──▶ Skip Product
         │
        Yes
         │
         ▼
┌─────────────────┐
│ Add to Results  │
└─────────────────┘
```

## Testing Architecture

```
┌──────────────────────────────────────────┐
│         test_scraper.py                  │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ test_price_extraction()            │ │
│  │ • Various TND formats              │ │
│  │ • Edge cases                       │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ test_product_card_parsing()        │ │
│  │ • Mock HTML structures             │ │
│  │ • Field extraction                 │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ test_metadata_enrichment()         │ │
│  │ • ID generation                    │ │
│  │ • Discount calculation             │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ test_category_discovery()          │ │
│  │ • URL extraction                   │ │
│  │ • Navigation parsing               │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

## Configuration & Customization Points

```
scrape_mytek.py
├── BASE_URL          = "https://www.mytek.tn"
├── MAX_RETRIES       = 3
├── RETRY_DELAY       = 2 seconds
├── REQUEST_TIMEOUT   = 30 seconds
├── PAGE_LOAD_TIMEOUT = 30 seconds
└── OUTPUT_DIR        = "../data/"

load_mytek_data.py
├── TND_TO_USD_RATE   = 0.32
├── BATCH_SIZE        = 50 products
└── PRODUCTS_FILE     = "../data/mytek_products.json"
```

## Key Features by Layer

### Scraping Layer
✓ Dual mode (Selenium/Requests)
✓ User-Agent spoofing
✓ Retry with exponential backoff
✓ Rate limiting

### Parsing Layer
✓ Heuristic CSS selectors
✓ Regex pattern matching
✓ Price normalization (TND)
✓ Image URL resolution

### Enrichment Layer
✓ Unique ID generation
✓ Timestamp addition
✓ Discount calculation
✓ Default value filling

### Integration Layer
✓ Currency conversion
✓ CLIP embedding generation
✓ Batch processing
✓ Vector database upload

---
*Architecture designed for robustness, maintainability, and extensibility*
