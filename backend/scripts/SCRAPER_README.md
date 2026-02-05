# Mytek.tn Web Scraper

## Overview

This scraper extracts product information from [Mytek.tn](https://www.mytek.tn/), a Tunisian electronics e-commerce website, and saves the data in a JSON format compatible with the existing PriceSense system.

## Features

- **Dual Mode**: Supports both Selenium (for JavaScript-heavy pages) and requests-only mode
- **Comprehensive Scraping**: Extracts product names, prices, images, specifications, and more
- **Automatic Category Discovery**: Finds and scrapes all product categories
- **Detail Page Scraping**: Optionally fetches detailed product information
- **Retry Logic**: Handles network failures gracefully with configurable retries
- **Rate Limiting**: Respectful delays between requests
- **Metadata Enrichment**: Adds timestamps, IDs, and calculates discounts
- **JSON Output**: Saves products in a structured format with summary statistics

## Installation

### Prerequisites

1. Python 3.10+
2. Chrome/Chromium browser (for Selenium mode)
3. ChromeDriver (automatically managed by Selenium)

### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

The scraper requires these additional packages (already added to requirements.txt):
- beautifulsoup4==4.12.2
- requests==2.31.0
- selenium==4.16.0
- lxml==5.1.0

## Usage

### Basic Usage

Scrape products using default settings:

```bash
cd backend
python scripts/scrape_mytek.py
```

This will:
- Use Selenium for dynamic content
- Scrape product listings (without detail pages)
- Save output to `data/mytek_products.json`

### Advanced Options

#### Scrape with Detailed Product Pages

Get comprehensive product information by visiting each product's detail page:

```bash
python scripts/scrape_mytek.py --detail
```

**Note**: This is slower but provides more complete data (descriptions, specifications, reviews, etc.)

#### Limit Number of Products

Scrape only a specific number of products (useful for testing):

```bash
python scripts/scrape_mytek.py --max-products 50
```

#### Use Requests-Only Mode

Disable Selenium and use faster requests-only mode (may miss JavaScript-loaded content):

```bash
python scripts/scrape_mytek.py --no-selenium
```

#### Custom Output Location

Specify a custom output file:

```bash
python scripts/scrape_mytek.py --output /path/to/output.json
```

#### Combined Example

Scrape 100 products with details, no Selenium:

```bash
python scripts/scrape_mytek.py --detail --max-products 100 --no-selenium --output data/mytek_sample.json
```

## Output Format

The scraper produces two JSON files:

### 1. Main Products File (`mytek_products.json`)

Array of product objects with the following structure:

```json
[
  {
    "id": "mytek_00001",
    "name": "Product Name",
    "price_TND": 1200.0,
    "original_price_TND": 1500.0,
    "discount_percentage": 20.0,
    "brand": "Samsung",
    "model": "ABC123",
    "category": "Electronics",
    "subcategory": "Smartphones",
    "description": "Product description...",
    "main_image": "https://www.mytek.tn/image.jpg",
    "images": ["url1", "url2", "url3"],
    "specifications": {
      "processor": "Snapdragon 888",
      "ram": "8GB",
      "storage": "256GB"
    },
    "rating": 4.5,
    "number_of_reviews": 120,
    "availability": "in_stock",
    "condition": "new",
    "seller": "Mytek",
    "sku": "SKU123",
    "features": [],
    "colors_available": [],
    "url": "https://www.mytek.tn/product/...",
    "created_at": "2026-01-28T17:56:00",
    "updated_at": "2026-01-28T17:56:00"
  }
]
```

### 2. Summary File (`mytek_products_summary.json`)

Summary statistics:

```json
{
  "total_products": 500,
  "scrape_date": "2026-01-28T17:56:00",
  "source": "https://www.mytek.tn",
  "categories": ["Electronics", "Computers", "Smartphones"],
  "brands": ["Samsung", "Apple", "HP", "Dell"]
}
```

## Loading Scraped Data into PriceSense

After scraping, you can load the products into the PriceSense system:

### Option 1: Use Existing Load Script

Modify `backend/scripts/load_products_data.py` to point to the scraped file:

```python
PRODUCTS_FILE = Path(__file__).parent.parent.parent / "data/mytek_products.json"
```

Then run:

```bash
python backend/scripts/load_products_data.py
```

### Option 2: Direct Load

```python
from pathlib import Path
import json
from core.qdrant_client import QdrantManager
from core.embeddings import CLIPEmbedder

# Load scraped products
with open('data/mytek_products.json', 'r') as f:
    products = json.load(f)

# Initialize services
qdrant = QdrantManager()
embedder = CLIPEmbedder()

# Process and upload (use logic from load_products_data.py)
```

## Configuration

Edit the scraper configuration in `backend/scripts/scrape_mytek.py`:

```python
BASE_URL = "https://www.mytek.tn"
MAX_RETRIES = 3              # Number of retry attempts
RETRY_DELAY = 2              # Delay between retries (seconds)
REQUEST_TIMEOUT = 30         # HTTP request timeout (seconds)
PAGE_LOAD_TIMEOUT = 30       # Selenium page load timeout (seconds)
```

## Troubleshooting

### Selenium Issues

If you get errors about ChromeDriver:

```bash
# Install chromium and driver
sudo apt-get update
sudo apt-get install -y chromium-browser chromium-chromedriver
```

Or use requests-only mode: `--no-selenium`

### Network Timeouts

Increase timeouts in the script:

```python
REQUEST_TIMEOUT = 60
PAGE_LOAD_TIMEOUT = 60
```

### Empty Results

The scraper uses CSS selectors that may need adjustment based on the actual HTML structure of Mytek.tn. Inspect the website and update the selectors in:
- `parse_product_card()`
- `parse_product_detail()`
- `discover_categories()`

### Memory Issues

When scraping many products, use `--max-products` to limit the number:

```bash
python scripts/scrape_mytek.py --max-products 1000
```

## Limitations

1. **HTML Structure Dependency**: The scraper uses heuristic CSS selectors that may need updates if the website changes its HTML structure
2. **Rate Limiting**: Built-in delays prevent overwhelming the server, but scraping is slower
3. **JavaScript Content**: Requires Selenium for JavaScript-rendered content (slower but more complete)
4. **Dynamic Content**: Some content loaded via AJAX may not be captured

## Future Enhancements

- [ ] Add support for pagination to scrape all products
- [ ] Implement parallel scraping for faster execution
- [ ] Add proxy support for avoiding rate limits
- [ ] Create monitoring/scheduling for regular updates
- [ ] Add incremental updates (only scrape new/changed products)
- [ ] Support for product variants and options
- [ ] Extract customer reviews and Q&A

## License

MIT License - See project LICENSE file for details

## Support

For issues or questions, please open an issue on GitHub.
