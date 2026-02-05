"""
Mytek.tn Web Scraper
Scrapes products from https://www.mytek.tn/ and saves them in JSON format
Compatible with the existing product data structure
"""
import sys
import json
import logging
import time
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Selenium imports (optional)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available. Install with: pip install selenium")

# Configuration
BASE_URL = "https://www.mytek.tn"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "mytek_products.json"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 30  # seconds
PAGE_LOAD_TIMEOUT = 30  # seconds


class MytekScraper:
    """Scraper for Mytek.tn e-commerce website"""
    
    def __init__(self, use_selenium: bool = True):
        """
        Initialize the scraper
        
        Args:
            use_selenium: If True, use Selenium for JavaScript-heavy pages
        """
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        if use_selenium and not SELENIUM_AVAILABLE:
            logger.warning("Selenium requested but not available. Falling back to requests-only mode.")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.driver = None
        self.products = []
        
    def setup_selenium(self):
        """Setup Selenium WebDriver with Chrome"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            logger.info("✅ Selenium WebDriver initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Selenium: {e}")
            logger.info("Falling back to requests-only mode")
            self.use_selenium = False
    
    def close_selenium(self):
        """Close Selenium WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("Selenium WebDriver closed")
    
    def fetch_page(self, url: str, retries: int = MAX_RETRIES) -> Optional[str]:
        """
        Fetch a page with retry logic
        
        Args:
            url: URL to fetch
            retries: Number of retry attempts
            
        Returns:
            HTML content or None if failed
        """
        for attempt in range(retries):
            try:
                if self.use_selenium and self.driver:
                    logger.info(f"Fetching with Selenium: {url}")
                    self.driver.get(url)
                    # Wait for page to load
                    time.sleep(2)
                    html = self.driver.page_source
                else:
                    logger.info(f"Fetching with requests: {url}")
                    response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                    response.raise_for_status()
                    html = response.text
                
                return html
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Failed to fetch {url} after {retries} attempts")
                    return None
    
    def extract_price(self, text: str) -> Optional[float]:
        """
        Extract price from text (handles TND currency)
        
        Args:
            text: Text containing price
            
        Returns:
            Price as float or None
        """
        if not text:
            return None
        
        # Remove currency symbols and text
        text = text.replace('TND', '').replace('DT', '').replace(',', '')
        
        # Extract numeric value
        match = re.search(r'(\d+(?:\.\d+)?)', text.strip())
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
    
    def parse_product_card(self, element: BeautifulSoup) -> Optional[Dict]:
        """
        Parse a product card element
        
        Args:
            element: BeautifulSoup element containing product info
            
        Returns:
            Product dictionary or None
        """
        try:
            # This is a template - actual selectors need to be adjusted based on real HTML structure
            product = {}
            
            # Product name
            name_elem = element.find(['h2', 'h3', 'h4'], class_=re.compile(r'product.*title|name', re.I))
            if not name_elem:
                name_elem = element.find('a', class_=re.compile(r'product.*link', re.I))
            product['name'] = name_elem.get_text(strip=True) if name_elem else None
            
            # Product link
            link_elem = element.find('a', href=True)
            product['url'] = urljoin(BASE_URL, link_elem['href']) if link_elem else None
            
            # Price
            price_elem = element.find(class_=re.compile(r'price.*current|product.*price', re.I))
            if price_elem:
                product['price_TND'] = self.extract_price(price_elem.get_text())
            
            # Original price (if on sale)
            original_price_elem = element.find(class_=re.compile(r'price.*old|price.*regular', re.I))
            if original_price_elem:
                product['original_price_TND'] = self.extract_price(original_price_elem.get_text())
            else:
                product['original_price_TND'] = product.get('price_TND')
            
            # Image
            img_elem = element.find('img')
            if img_elem:
                product['main_image'] = img_elem.get('src') or img_elem.get('data-src')
                if product['main_image']:
                    product['main_image'] = urljoin(BASE_URL, product['main_image'])
            
            # Brand (if available)
            brand_elem = element.find(class_=re.compile(r'brand|manufacturer', re.I))
            product['brand'] = brand_elem.get_text(strip=True) if brand_elem else None
            
            # Availability
            availability_elem = element.find(class_=re.compile(r'stock|availability', re.I))
            if availability_elem:
                stock_text = availability_elem.get_text(strip=True).lower()
                product['availability'] = 'in_stock' if 'stock' in stock_text or 'available' in stock_text else 'out_of_stock'
            else:
                product['availability'] = 'in_stock'  # Default
            
            # Only return if we have minimum required fields
            if product.get('name') and product.get('price_TND'):
                return product
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing product card: {e}")
            return None
    
    def parse_product_detail(self, html: str, product_url: str) -> Dict:
        """
        Parse detailed product page
        
        Args:
            html: HTML content of product page
            product_url: URL of the product
            
        Returns:
            Detailed product dictionary
        """
        soup = BeautifulSoup(html, 'lxml')
        product = {}
        
        try:
            # Product name
            name_elem = soup.find(['h1', 'h2'], class_=re.compile(r'product.*title|product.*name', re.I))
            product['name'] = name_elem.get_text(strip=True) if name_elem else None
            
            # Description
            desc_elem = soup.find(class_=re.compile(r'description|product.*content', re.I))
            product['description'] = desc_elem.get_text(strip=True) if desc_elem else None
            
            # Price
            price_elem = soup.find(class_=re.compile(r'price.*current|product.*price', re.I))
            if price_elem:
                product['price_TND'] = self.extract_price(price_elem.get_text())
            
            # Original price
            original_price_elem = soup.find(class_=re.compile(r'price.*old|price.*regular', re.I))
            if original_price_elem:
                product['original_price_TND'] = self.extract_price(original_price_elem.get_text())
            else:
                product['original_price_TND'] = product.get('price_TND')
            
            # Images
            images = []
            for img in soup.find_all('img', src=re.compile(r'product|image', re.I)):
                img_url = img.get('src') or img.get('data-src')
                if img_url is not None and img_url:
                    images.append(urljoin(BASE_URL, img_url))
            product['images'] = images[:10]  # Limit to 10 images
            product['main_image'] = images[0] if images else None
            
            # Specifications
            specs = {}
            spec_table = soup.find('table', class_=re.compile(r'spec|attribute|feature', re.I))
            if spec_table:
                for row in spec_table.find_all('tr'):
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        specs[key.lower().replace(' ', '_')] = value
            product['specifications'] = specs
            
            # Brand
            brand_elem = soup.find(class_=re.compile(r'brand|manufacturer', re.I))
            product['brand'] = brand_elem.get_text(strip=True) if brand_elem else None
            
            # Category
            breadcrumb = soup.find(class_=re.compile(r'breadcrumb|category', re.I))
            if breadcrumb:
                categories = [a.get_text(strip=True) for a in breadcrumb.find_all('a')]
                if len(categories) > 0:
                    product['category'] = categories[-1]
                if len(categories) > 1:
                    product['subcategory'] = categories[-2]
            
            # Rating
            rating_elem = soup.find(class_=re.compile(r'rating|star', re.I))
            if rating_elem:
                rating_text = rating_elem.get_text()
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    product['rating'] = float(rating_match.group(1))
            
            # Reviews count
            reviews_elem = soup.find(class_=re.compile(r'review.*count|reviews', re.I))
            if reviews_elem:
                reviews_text = reviews_elem.get_text()
                reviews_match = re.search(r'(\d+)', reviews_text)
                if reviews_match:
                    product['number_of_reviews'] = int(reviews_match.group(1))
            
            # SKU
            sku_elem = soup.find(class_=re.compile(r'sku|product.*code', re.I))
            product['sku'] = sku_elem.get_text(strip=True) if sku_elem else None
            
            # Availability
            availability_elem = soup.find(class_=re.compile(r'stock|availability', re.I))
            if availability_elem:
                stock_text = availability_elem.get_text(strip=True).lower()
                product['availability'] = 'in_stock' if 'stock' in stock_text or 'available' in stock_text else 'out_of_stock'
            
            product['url'] = product_url
            
            return product
            
        except Exception as e:
            logger.error(f"Error parsing product detail: {e}")
            return product
    
    def discover_categories(self, html: str) -> List[str]:
        """
        Discover product category URLs from the main page
        
        Args:
            html: HTML content of main page
            
        Returns:
            List of category URLs
        """
        soup = BeautifulSoup(html, 'lxml')
        category_urls = []
        
        # Look for navigation menus, category links
        nav = soup.find(['nav', 'ul'], class_=re.compile(r'menu|nav|categor', re.I))
        if nav:
            for link in nav.find_all('a', href=True):
                href = link['href']
                # Skip non-category links
                if any(x in href.lower() for x in ['contact', 'about', 'cart', 'account', 'login']):
                    continue
                category_urls.append(urljoin(BASE_URL, href))
        
        # Also look for category cards/blocks
        for link in soup.find_all('a', class_=re.compile(r'categor', re.I), href=True):
            href = link['href']
            if href not in category_urls:
                category_urls.append(urljoin(BASE_URL, href))
        
        logger.info(f"Discovered {len(category_urls)} category URLs")
        return category_urls
    
    def scrape_category_page(self, url: str) -> List[str]:
        """
        Scrape product URLs from a category page
        
        Args:
            url: Category page URL
            
        Returns:
            List of product URLs
        """
        html = self.fetch_page(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        product_urls = []
        
        # Find product cards/links
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Common patterns for product URLs
            if any(x in href.lower() for x in ['/product/', '/p/', '/item/', '-p-', '_p_']):
                product_url = urljoin(BASE_URL, href)
                if product_url not in product_urls:
                    product_urls.append(product_url)
        
        logger.info(f"Found {len(product_urls)} products in {url}")
        return product_urls
    
    def scrape_products_from_listing(self, url: str, max_products: Optional[int] = None) -> List[Dict]:
        """
        Scrape products from a listing page
        
        Args:
            url: Listing page URL
            max_products: Maximum number of products to scrape (None for all)
            
        Returns:
            List of product dictionaries
        """
        html = self.fetch_page(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        products = []
        
        # Find product cards
        product_cards = soup.find_all(class_=re.compile(r'product.*card|product.*item|product.*box', re.I))
        
        # If no cards found with class, try finding by structure
        if not product_cards:
            product_cards = soup.find_all(['div', 'li'], class_=re.compile(r'product', re.I))
        
        logger.info(f"Found {len(product_cards)} product cards on page")
        
        for i, card in enumerate(product_cards):
            if max_products and i >= max_products:
                break
            
            product = self.parse_product_card(card)
            if product:
                products.append(product)
        
        return products
    
    def scrape_all_products(self, detail_pages: bool = False, max_products: Optional[int] = None) -> List[Dict]:
        """
        Scrape all products from Mytek.tn
        
        Args:
            detail_pages: If True, also scrape detailed product pages
            max_products: Maximum number of products to scrape (None for all)
            
        Returns:
            List of product dictionaries
        """
        logger.info("=" * 80)
        logger.info("🕷️  STARTING MYTEK.TN PRODUCT SCRAPER")
        logger.info("=" * 80)
        
        if self.use_selenium:
            self.setup_selenium()
        
        try:
            # Step 1: Fetch main page
            logger.info(f"📄 Fetching main page: {BASE_URL}")
            main_html = self.fetch_page(BASE_URL)
            if not main_html:
                logger.error("Failed to fetch main page")
                return []
            
            # Step 2: Discover categories
            logger.info("🔍 Discovering categories...")
            category_urls = self.discover_categories(main_html)
            
            # If no categories found, try to scrape from main page
            if not category_urls:
                logger.info("No categories found, trying to scrape from main page")
                category_urls = [BASE_URL]
            
            # Step 3: Scrape products from each category
            all_products = []
            for i, cat_url in enumerate(category_urls[:10]):  # Limit to 10 categories initially
                if max_products and len(all_products) >= max_products:
                    break
                
                logger.info(f"📦 Scraping category {i+1}/{len(category_urls)}: {cat_url}")
                products = self.scrape_products_from_listing(cat_url, max_products)
                all_products.extend(products)
                
                logger.info(f"   Found {len(products)} products (total: {len(all_products)})")
                
                # Be respectful to the server
                time.sleep(1)
            
            # Step 4: Optionally scrape detailed product pages
            if detail_pages and all_products:
                logger.info(f"🔎 Fetching detailed info for {len(all_products)} products...")
                detailed_products = []
                
                for i, product in enumerate(all_products):
                    if max_products and i >= max_products:
                        break
                    
                    if product.get('url'):
                        logger.info(f"   Product {i+1}/{len(all_products)}: {product.get('name', 'Unknown')}")
                        detail_html = self.fetch_page(product['url'])
                        if detail_html:
                            detailed = self.parse_product_detail(detail_html, product['url'])
                            # Merge with basic info
                            for key, value in product.items():
                                if key not in detailed or not detailed[key]:
                                    detailed[key] = value
                            detailed_products.append(detailed)
                        
                        # Be respectful to the server
                        if i % 10 == 0:
                            time.sleep(2)
                        else:
                            time.sleep(0.5)
                
                self.products = detailed_products
            else:
                self.products = all_products
            
            # Step 5: Enrich products with metadata
            logger.info("📝 Adding metadata to products...")
            self.enrich_products()
            
            logger.info(f"✅ Scraping complete! Total products: {len(self.products)}")
            return self.products
            
        finally:
            if self.use_selenium:
                self.close_selenium()
    
    def enrich_products(self):
        """Add additional metadata to scraped products"""
        timestamp = datetime.now().isoformat()
        
        for i, product in enumerate(self.products):
            # Generate ID
            product['id'] = f"mytek_{i+1:05d}"
            
            # Add timestamps
            product['created_at'] = timestamp
            product['updated_at'] = timestamp
            
            # Default values
            product.setdefault('condition', 'new')
            product.setdefault('availability', 'in_stock')
            product.setdefault('seller', 'Mytek')
            product.setdefault('features', [])
            product.setdefault('colors_available', [])
            product.setdefault('images', [])
            
            # Calculate discount if applicable
            if product.get('original_price_TND') and product.get('price_TND'):
                original = product['original_price_TND']
                current = product['price_TND']
                if original > current:
                    product['discount_percentage'] = round(((original - current) / original) * 100, 1)
                else:
                    product['discount_percentage'] = 0
            else:
                product['discount_percentage'] = 0
            
            # Extract model from name if not present
            if not product.get('model') and product.get('name'):
                # Try to extract model number pattern
                model_match = re.search(r'([A-Z0-9]{3,}[-_]?[A-Z0-9]+)', product['name'])
                if model_match:
                    product['model'] = model_match.group(1)
    
    def save_to_json(self, filepath: Optional[Path] = None):
        """
        Save scraped products to JSON file
        
        Args:
            filepath: Output file path (default: OUTPUT_FILE)
        """
        if not filepath:
            filepath = OUTPUT_FILE
        
        # Create output directory if it doesn't exist
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.products, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved {len(self.products)} products to {filepath}")
        
        # Also save a summary
        summary = {
            'total_products': len(self.products),
            'scrape_date': datetime.now().isoformat(),
            'source': BASE_URL,
            'categories': list(set(p.get('category') for p in self.products if p.get('category'))),
            'brands': list(set(p.get('brand') for p in self.products if p.get('brand'))),
        }
        
        summary_file = filepath.parent / f"{filepath.stem}_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Saved summary to {summary_file}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape products from Mytek.tn')
    parser.add_argument('--detail', action='store_true', help='Scrape detailed product pages')
    parser.add_argument('--max-products', type=int, help='Maximum number of products to scrape')
    parser.add_argument('--no-selenium', action='store_true', help='Disable Selenium (use requests only)')
    parser.add_argument('--output', type=str, help='Output JSON file path')
    
    args = parser.parse_args()
    
    # Create scraper
    scraper = MytekScraper(use_selenium=not args.no_selenium)
    
    # Scrape products
    products = scraper.scrape_all_products(
        detail_pages=args.detail,
        max_products=args.max_products
    )
    
    # Save to JSON
    output_path = Path(args.output) if args.output else None
    scraper.save_to_json(output_path)
    
    print("\n" + "=" * 80)
    print(f"✅ SCRAPING COMPLETE!")
    print(f"   Total products: {len(products)}")
    print(f"   Output file: {output_path or OUTPUT_FILE}")
    print("=" * 80)


if __name__ == '__main__':
    main()
