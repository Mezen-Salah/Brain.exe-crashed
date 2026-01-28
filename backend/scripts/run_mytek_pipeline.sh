#!/bin/bash
# Quick start script for scraping and loading Mytek.tn products

echo "=================================="
echo "Mytek.tn Product Scraper Pipeline"
echo "=================================="
echo ""

# Check if we're in the right directory
if [ ! -f "scripts/scrape_mytek.py" ]; then
    echo "❌ Error: Please run this from the backend directory"
    echo "   cd /home/runner/work/Brain.exe-crashed/Brain.exe-crashed/backend"
    exit 1
fi

# Step 1: Scrape products
echo "Step 1: Scraping products from Mytek.tn..."
echo ""

# Run scraper with no-selenium flag for compatibility
python3 scripts/scrape_mytek.py --no-selenium --max-products 100

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Scraping failed!"
    exit 1
fi

echo ""
echo "✅ Scraping complete!"
echo ""

# Check if products file was created
if [ ! -f "../data/mytek_products.json" ]; then
    echo "❌ Error: Products file not found!"
    exit 1
fi

# Step 2: Load products into Qdrant (optional)
echo ""
echo "Step 2: Load products into Qdrant? (y/n)"
read -r answer

if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
    echo ""
    echo "Loading products into Qdrant..."
    python3 scripts/load_mytek_data.py
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ Loading failed!"
        echo "   Make sure Qdrant is running: docker-compose up -d"
        exit 1
    fi
    
    echo ""
    echo "✅ Products loaded successfully!"
fi

echo ""
echo "=================================="
echo "✅ Pipeline Complete!"
echo "=================================="
echo ""
echo "Products saved to: ../data/mytek_products.json"
echo ""
echo "Next steps:"
echo "  - Review the scraped data in data/mytek_products.json"
echo "  - Check the summary in data/mytek_products_summary.json"
echo "  - Use the products in your application"
echo ""
