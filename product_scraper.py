import pandas as pd
import requests
import json
import re
import time
import os
from multiprocessing import Pool, Manager
from typing import List, Dict, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# --- Configuration ---
INPUT_CSV = 'zalando_underwear_category.csv'
OUTPUT_CSV = 'zalando_product_details.csv'
PROCESS_COUNT = 2  # Reduced to avoid overwhelming the server
URL_COLUMN = 'url'
REQUEST_TIMEOUT = 30  # Increased timeout
MAX_RETRIES = 1  # Reduced retries to speed up fallback

# User agents to rotate for requests
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
]


def get_session():
    """Create a requests session with proper headers."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    return session


def extract_product_data_from_html(html_content: str, url: str) -> Dict:
    """Extract product data from HTML using multiple strategies."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Strategy 1: JSON-LD structured data
    json_ld_data = extract_json_ld(soup)
    if json_ld_data:
        return json_ld_data
    
    # Strategy 2: Meta tags and page title
    meta_data = extract_meta_data(soup, url)
    if meta_data:
        return meta_data
    
    # Strategy 3: Direct HTML parsing
    return extract_from_html_elements(soup, url)


def extract_json_ld(soup: BeautifulSoup) -> Optional[Dict]:
    """Extract product data from JSON-LD structured data."""
    try:
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if not script.string:
                continue
            
            try:
                data = json.loads(script.string)
                
                # Handle both single objects and arrays
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    if item.get('@type') == 'Product':
                        return parse_json_ld_product(item)
                        
            except (json.JSONDecodeError, KeyError):
                continue
                
    except Exception as e:
        print(f"  -> Error extracting JSON-LD: {e}")
    
    return None


def parse_json_ld_product(product_data: Dict) -> Dict:
    """Parse product data from JSON-LD format."""
    name = product_data.get('name', 'N/A')
    
    # Extract brand
    brand = 'N/A'
    if 'brand' in product_data:
        brand_data = product_data['brand']
        if isinstance(brand_data, dict):
            brand = brand_data.get('name', 'N/A')
        elif isinstance(brand_data, str):
            brand = brand_data
    
    # Extract description
    description = product_data.get('description', 'N/A')
    if isinstance(description, list):
        description = ' '.join(str(d) for d in description)
    
    # Extract images
    images = []
    if 'image' in product_data:
        img_data = product_data['image']
        if isinstance(img_data, list):
            images = [img for img in img_data if isinstance(img, str)]
        elif isinstance(img_data, str):
            images = [img_data]
    
    # Extract price
    price = 'N/A'
    if 'offers' in product_data:
        offers = product_data['offers']
        if isinstance(offers, dict):
            price = offers.get('price', 'N/A')
        elif isinstance(offers, list) and offers:
            price = offers[0].get('price', 'N/A')
    
    return {
        'name': name,
        'brand': brand,
        'description': description[:500] if description != 'N/A' else 'N/A',  # Limit description length
        'price': str(price),
        'image_urls': json.dumps(images),
        'extraction_method': 'JSON-LD'
    }


def extract_meta_data(soup: BeautifulSoup, url: str) -> Optional[Dict]:
    """Extract product data from meta tags and title."""
    try:
        # Get product name from title
        title_tag = soup.find('title')
        name = 'N/A'
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            # Clean up title (remove site name)
            name = title_text.split(' | Zalando')[0] if ' | Zalando' in title_text else title_text
        
        # Try to extract brand from meta tags or title
        brand = 'N/A'
        
        # Look for Open Graph data
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            name = og_title['content']
        
        og_description = soup.find('meta', property='og:description')
        description = og_description['content'] if og_description else 'N/A'
        
        og_image = soup.find('meta', property='og:image')
        images = [og_image['content']] if og_image else []
        
        if name != 'N/A':
            return {
                'name': name,
                'brand': brand,
                'description': description[:500] if description != 'N/A' else 'N/A',
                'price': 'N/A',
                'image_urls': json.dumps(images),
                'extraction_method': 'Meta tags'
            }
            
    except Exception as e:
        print(f"  -> Error extracting meta data: {e}")
    
    return None


def extract_from_html_elements(soup: BeautifulSoup, url: str) -> Dict:
    """Last resort: extract data from HTML elements."""
    name = 'N/A'
    brand = 'N/A'
    price = 'N/A'
    description = 'N/A'
    images = []
    
    try:
        # Try to find product name in common selectors
        name_selectors = ['h1', '.product-title', '.product-name', '[data-testid="product-title"]']
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get_text(strip=True)
                break
        
        # Try to find price
        price_selectors = ['.price', '.product-price', '[data-testid="price"]', '.price-current']
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                price = element.get_text(strip=True)
                break
        
        # Extract images from img tags
        img_tags = soup.find_all('img')
        for img in img_tags[:5]:  # Limit to first 5 images
            src = img.get('src') or img.get('data-src')
            if src and ('product' in src.lower() or 'image' in src.lower()):
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    parsed_url = urlparse(url)
                    src = f"{parsed_url.scheme}://{parsed_url.netloc}{src}"
                images.append(src)
        
    except Exception as e:
        print(f"  -> Error in HTML element extraction: {e}")
    
    return {
        'name': name,
        'brand': brand,
        'description': description,
        'price': price,
        'image_urls': json.dumps(images),
        'extraction_method': 'HTML parsing'
    }


def scrape_product_requests(url: str) -> Dict:
    """Scrape product using requests library."""
    try:
        session = get_session()
        
        for attempt in range(MAX_RETRIES):
            try:
                response = session.get(url, timeout=REQUEST_TIMEOUT)
                
                if response.status_code == 200:
                    product_data = extract_product_data_from_html(response.text, url)
                    product_data['url'] = url
                    product_data['status'] = 'success'
                    return product_data
                    
                elif response.status_code in [403, 429]:
                    print(f"  -> Blocked (HTTP {response.status_code}), will try Selenium fallback")
                    break
                    
                else:
                    print(f"  -> HTTP {response.status_code}, retrying...")
                    time.sleep(2)
                    
            except requests.RequestException as e:
                print(f"  -> Request failed (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2)
        
        # If requests failed, try Selenium
        return scrape_product_selenium(url)
        
    except Exception as e:
        return {
            'url': url,
            'name': f'ERROR: {type(e).__name__}',
            'brand': 'N/A',
            'description': 'N/A',
            'price': 'N/A',
            'image_urls': '[]',
            'extraction_method': 'Failed',
            'status': 'error'
        }


def scrape_product_selenium(url: str) -> Dict:
    """Fallback scraping using Selenium."""
    driver = None
    try:
        # Configure Chrome options
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.prefs = {"profile.managed_default_content_settings.images": 2}
        chrome_options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(45)  # Increased timeout
        
        # Add stealth settings
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 15).until(  # Increased wait time
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Extract data from page source
        product_data = extract_product_data_from_html(driver.page_source, url)
        product_data['url'] = url
        product_data['status'] = 'success_selenium'
        
        return product_data
        
    except Exception as e:
        return {
            'url': url,
            'name': f'ERROR: Selenium failed - {type(e).__name__}',
            'brand': 'N/A',
            'description': 'N/A',
            'price': 'N/A',
            'image_urls': '[]',
            'extraction_method': 'Failed',
            'status': 'error'
        }
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def worker(url_batch: List[str], temp_file_path: str):
    """Worker process for scraping a batch of URLs."""
    results = []
    
    for i, url in enumerate(url_batch):
        print(f"  -> Processing {i+1}/{len(url_batch)}: {url}")
        
        # Add random delay to avoid being blocked
        time.sleep(random.uniform(2, 5))  # Increased delay
        
        result = scrape_product_requests(url)
        results.append(result)
        
        # Show success message
        if result['status'].startswith('success'):
            method = result.get('extraction_method', 'Unknown')
            print(f"     ✓ Extracted: {result['name']} (via {method})")
        else:
            print(f"     ✗ Failed: {result['name']}")
    
    # Save results to temporary file
    if results:
        df = pd.DataFrame(results)
        df.to_csv(temp_file_path, index=False)


def main():
    """Main function to orchestrate the scraping process."""
    print("🚀 Starting Zalando Product Scraper...")
    
    # Read URLs from input file
    try:
        df_urls = pd.read_csv(INPUT_CSV)
        if URL_COLUMN not in df_urls.columns:
            print(f"❌ Column '{URL_COLUMN}' not found in {INPUT_CSV}")
            print(f"Available columns: {list(df_urls.columns)}")
            return
            
        urls = df_urls[URL_COLUMN].dropna().unique().tolist()
        print(f"📋 Found {len(urls)} unique URLs to process")
        
    except FileNotFoundError:
        print(f"❌ Input file '{INPUT_CSV}' not found")
        return
    except Exception as e:
        print(f"❌ Error reading input file: {e}")
        return
    
    # Split URLs into batches for multiprocessing
    url_chunks = [urls[i::PROCESS_COUNT] for i in range(PROCESS_COUNT)]
    temp_files = [f"temp_worker_{i}.csv" for i in range(PROCESS_COUNT)]
    
    # Clean up any existing temp files
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    print(f"🔧 Starting {PROCESS_COUNT} worker processes...")
    
    # Run workers in parallel
    with Pool(PROCESS_COUNT) as pool:
        pool.starmap(worker, zip(url_chunks, temp_files))
    
    # Combine results from all workers
    print("📊 Combining results from all workers...")
    all_results = []
    
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            try:
                df = pd.read_csv(temp_file)
                all_results.append(df)
                os.remove(temp_file)
            except Exception as e:
                print(f"⚠️  Error reading {temp_file}: {e}")
    
    if all_results:
        # Combine all dataframes
        final_df = pd.concat(all_results, ignore_index=True)
        
        # Add summary columns
        final_df = final_df.reindex(columns=[
            'url', 'name', 'brand', 'description', 'price', 'image_urls', 
            'extraction_method', 'status'
        ])
        
        # Save final results
        final_df.to_csv(OUTPUT_CSV, index=False)
        
        # Print summary
        total = len(final_df)
        successful = len(final_df[final_df['status'].str.startswith('success')])
        selenium_used = len(final_df[final_df['status'] == 'success_selenium'])
        
        print(f"\n🎉 Scraping completed!")
        print(f"📈 Results: {successful}/{total} products successfully scraped")
        print(f"🔧 Selenium fallback used: {selenium_used} times")
        print(f"💾 Data saved to: {OUTPUT_CSV}")
        
        # Show extraction method breakdown
        method_counts = final_df['extraction_method'].value_counts()
        print(f"\n📊 Extraction methods used:")
        for method, count in method_counts.items():
            print(f"   {method}: {count}")
            
    else:
        print("❌ No results to save")


if __name__ == "__main__":
    main() 