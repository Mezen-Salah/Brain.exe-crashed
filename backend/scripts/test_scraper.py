"""
Test script for Mytek.tn scraper
Tests parsing functions with mock HTML data
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from bs4 import BeautifulSoup
from scripts.scrape_mytek import MytekScraper

def test_price_extraction():
    """Test price extraction from various formats"""
    print("Testing price extraction...")
    scraper = MytekScraper(use_selenium=False)
    
    test_cases = [
        ("1200 TND", 1200.0),
        ("1,500.50 DT", 1500.50),
        ("Price: 999 TND", 999.0),
        ("2500", 2500.0),
        ("", None),
    ]
    
    for text, expected in test_cases:
        result = scraper.extract_price(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{text}' -> {result} (expected: {expected})")

def test_product_card_parsing():
    """Test parsing of product card HTML"""
    print("\nTesting product card parsing...")
    scraper = MytekScraper(use_selenium=False)
    
    # Mock product card HTML
    mock_html = """
    <div class="product-card">
        <a href="/product/laptop-123" class="product-link">
            <img src="/images/laptop.jpg" alt="Laptop"/>
            <h3 class="product-title">HP Pavilion Laptop 15</h3>
        </a>
        <div class="brand">HP</div>
        <div class="price-current">2500 TND</div>
        <div class="price-old">3000 TND</div>
        <div class="stock">In Stock</div>
    </div>
    """
    
    soup = BeautifulSoup(mock_html, 'lxml')
    card = soup.find('div', class_='product-card')
    
    product = scraper.parse_product_card(card)
    
    if product:
        print(f"  ✓ Parsed product successfully:")
        print(f"    Name: {product.get('name')}")
        print(f"    Price: {product.get('price_TND')} TND")
        print(f"    Original Price: {product.get('original_price_TND')} TND")
        print(f"    Brand: {product.get('brand')}")
        print(f"    Availability: {product.get('availability')}")
        print(f"    URL: {product.get('url')}")
    else:
        print("  ✗ Failed to parse product card")

def test_metadata_enrichment():
    """Test product metadata enrichment"""
    print("\nTesting metadata enrichment...")
    scraper = MytekScraper(use_selenium=False)
    
    # Mock products
    scraper.products = [
        {
            'name': 'Samsung Galaxy S21',
            'price_TND': 2000,
            'original_price_TND': 2500,
        },
        {
            'name': 'iPhone 13 Pro',
            'price_TND': 3500,
            'original_price_TND': 3500,
        }
    ]
    
    scraper.enrich_products()
    
    print(f"  ✓ Enriched {len(scraper.products)} products")
    for i, product in enumerate(scraper.products):
        print(f"\n  Product {i+1}:")
        print(f"    ID: {product.get('id')}")
        print(f"    Name: {product.get('name')}")
        print(f"    Discount: {product.get('discount_percentage')}%")
        print(f"    Condition: {product.get('condition')}")
        print(f"    Seller: {product.get('seller')}")
        print(f"    Created: {product.get('created_at')}")

def test_category_discovery():
    """Test category URL discovery"""
    print("\nTesting category discovery...")
    scraper = MytekScraper(use_selenium=False)
    
    mock_html = """
    <nav class="main-menu">
        <ul>
            <li><a href="/category/laptops">Laptops</a></li>
            <li><a href="/category/phones">Smartphones</a></li>
            <li><a href="/category/tablets">Tablets</a></li>
            <li><a href="/about">About</a></li>
            <li><a href="/contact">Contact</a></li>
        </ul>
    </nav>
    """
    
    categories = scraper.discover_categories(mock_html)
    print(f"  ✓ Found {len(categories)} category URLs:")
    for url in categories:
        print(f"    - {url}")

def main():
    """Run all tests"""
    print("=" * 60)
    print("MYTEK.TN SCRAPER - UNIT TESTS")
    print("=" * 60)
    
    try:
        test_price_extraction()
        test_product_card_parsing()
        test_metadata_enrichment()
        test_category_discovery()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
