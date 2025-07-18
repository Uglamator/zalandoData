import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
from urllib.parse import urljoin, urlparse
import time
import random
from typing import Dict, List, Optional, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException, TimeoutException, NoSuchElementException, InvalidSessionIdException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from multiprocessing import Pool
import os
import traceback
import ctypes
from ctypes import wintypes

CLEANED_DATA_COLUMNS = [
    'domain','country_code','url','sku','condition','gender','product_name','brand','description','manufacturer',
    'badges','initial_price','final_price','discount','currency','inventory','is_sale','in_stock','delivery',
    'root_category','category_tree','main_image','image_count','image_urls','rating','reviews_count','best_rating',
    'worst_rating','rating_count','review_count','top_reviews','product_url','name','SKU','other_attributes','color',
    'colors','sizes','similar_products','people_bought_together','related_products','has_sellback','brand_name',
    'timestamp','input','discovery_input','error','error_code','warning','warning_code'
]

# Manual overrides for brand slugs that are known to be incorrect on Zalando
MANUAL_SLUG_OVERRIDES = {
    "Agent Provocateur": "agent-provocatuer"
}

def extract_from_graphql_cache(driver) -> List[Dict]:
    """
    Extract product data from GraphQL cache in page scripts.
    Includes a retry mechanism for StaleElementReferenceException.
    """
    for attempt in range(3): # Retry loop for stale elements
        try:
            products = []
            scripts = driver.find_elements(By.TAG_NAME, "script")
            
            for script in scripts:
                try:
                    script_content = script.get_attribute("innerHTML")
                    if not script_content:
                        continue
                        
                    # Look for graphqlCache
                    if '"graphqlCache":' in script_content:
                        
                        # Extract the JSON part
                        start_idx = script_content.find('"graphqlCache":')
                        if start_idx == -1:
                            continue
                            
                        # Find the start of the cache object
                        cache_start = script_content.find('{', start_idx)
                        if cache_start == -1:
                            continue
                        
                        # Find the end of the cache object by matching braces
                        brace_count = 0
                        cache_end = cache_start
                        
                        for i, char in enumerate(script_content[cache_start:], cache_start):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    cache_end = i + 1
                                    break
                        
                        cache_json_str = script_content[cache_start:cache_end]
                        
                        try:
                            cache_data = json.loads(cache_json_str)
                            
                            # Extract product data from each cache entry
                            for cache_key, cache_value in cache_data.items():
                                try:
                                    if isinstance(cache_value, dict) and 'data' in cache_value:
                                        data = cache_value['data']
                                        
                                        # Look for product in various possible locations
                                        product_data = None
                                        if 'product' in data:
                                            product_data = data['product']
                                        elif 'article' in data:
                                            product_data = data['article']
                                        
                                        if product_data and isinstance(product_data, dict):
                                            product_info = extract_product_from_json(product_data)
                                            if product_info:
                                                products.append(product_info)
                                                
                                except Exception as e:
                                    # This error is for a single entry, not critical to stop the whole process
                                    print(f"  - Error processing a cache entry: {e}")
                                    continue
                                    
                        except json.JSONDecodeError as e:
                            print(f"  - Failed to parse GraphQL cache JSON: {e}")
                            continue
                            
                        # If we found products, we can break from the script loop
                        if products:
                            break
                            
                except StaleElementReferenceException:
                    # This is a critical error for this function. We need to break and retry the whole thing.
                    print("  - Stale element encountered while reading a script tag. Breaking to retry.")
                    raise StaleElementReferenceException # Re-raise to be caught by the outer loop
                except Exception as e:
                    print(f"  - Error processing a script: {e}")
                    continue
            
            # If we finished the loop without a stale exception, we are done.
            return products

        except StaleElementReferenceException:
            print(f"  - Stale element detected in GraphQL script search. Retrying... (Attempt {attempt + 1}/3)")
            if attempt < 2:
                time.sleep(0.5) # Wait before retrying
            else:
                print("  - Could not get GraphQL data due to persistent stale elements.")
        
        except Exception as e:
            print(f"An unexpected error occurred during GraphQL extraction: {e}")
            break # Break on other unexpected errors

    return [] # Return empty if all retries fail

def extract_product_from_json(product_data: Dict) -> Optional[Dict]:
    """Extract product information from JSON product data"""
    try:
        # Basic product info
        sku = product_data.get('sku', 'N/A')
        name = product_data.get('name', 'N/A').replace('\n', ' ').replace('\r', ' ').strip()
        brand_info = product_data.get('brand', {})
        brand_name = brand_info.get('name', 'N/A') if isinstance(brand_info, dict) else 'N/A'
        
        # Price information - enhanced debugging
        price_info = product_data.get('displayPrice', {})
        original_price = 0.0
        final_price = 0.0
        currency = 'EUR'
        discount = 0
        is_sale = False
        
        if isinstance(price_info, dict):
            # Original price
            original = price_info.get('original', {})
            if isinstance(original, dict):
                original_amount = original.get('amount', 0)
                original_price = original_amount / 100.0 if original_amount else 0.0  # Convert from cents
                currency = original.get('currency', 'EUR')
            
            # Check for trackingCurrentAmount first (this seems to be the actual display price)
            tracking_current = price_info.get('trackingCurrentAmount')
            if tracking_current:
                final_price = float(tracking_current)
                original_price = final_price  # Set as default
            
            # Promotional price
            promotional = price_info.get('promotional')
            if promotional and isinstance(promotional, dict):
                promo_amount = promotional.get('amount', 0)
                if promo_amount:
                    final_price = promo_amount / 100.0
                    is_sale = True
                    if original_price > 0:
                        discount = original_price - final_price
            elif promotional and isinstance(promotional, (int, float)):
                # Sometimes promotional is just a number
                final_price = promotional / 100.0
                is_sale = True
                if original_price > 0:
                    discount = original_price - final_price
                    
            # If we still don't have final_price, use original_price
            if final_price == 0.0 and original_price > 0.0:
                final_price = original_price
                
            # Check for trackingDiscountAmount
            tracking_discount = price_info.get('trackingDiscountAmount')
            if tracking_discount and tracking_discount > 0:
                discount = float(tracking_discount)
                is_sale = True
                # Recalculate original price if we have discount
                if final_price > 0 and discount > 0:
                    original_price = final_price + discount
                
        # --- Enhanced Color Extraction ---
        color = 'N/A'
        colors = []

        # Strategy 1: Extract from the 'color' object directly
        color_info = product_data.get('color', {})
        if isinstance(color_info, dict):
            color = color_info.get('name', 'N/A')
        elif isinstance(color_info, str) and color_info:
            color = color_info

        # Strategy 2: Extract all available colors from 'simples' (variants)
        simples = product_data.get('simples', [])
        if isinstance(simples, list):
            for simple in simples:
                if isinstance(simple, dict):
                    simple_color_info = simple.get('color', {})
                    if isinstance(simple_color_info, dict):
                        simple_color_name = simple_color_info.get('name')
                        if simple_color_name and simple_color_name not in colors:
                            colors.append(simple_color_name)

        # Strategy 3: Extract from 'colorVariations' in 'family' object
        family_data = product_data.get('family', {})
        if isinstance(family_data, dict):
            color_variations = family_data.get('colorVariations', [])
            if isinstance(color_variations, list):
                for var in color_variations:
                    if isinstance(var, dict):
                        var_color_name = var.get('color', {}).get('name')
                        if var_color_name and var_color_name not in colors:
                            colors.append(var_color_name)
        
        # Strategy 4: Extract from attributes as a fallback for the primary color
        if color == 'N/A':
            attributes = product_data.get('attributes', [])
            if isinstance(attributes, list):
                for attr in attributes:
                    if isinstance(attr, dict):
                        attr_name = attr.get('name', '').lower()
                        if 'color' in attr_name or 'colour' in attr_name:
                            color = attr.get('value', 'N/A')
                            break

        # Strategy 5: Parse from product name as a last resort for the primary color
        if color == 'N/A' and name != 'N/A' and ' - ' in name:
            potential_color = name.split(' - ')[-1].strip()
            # Basic validation to avoid grabbing parts of the product title
            if len(potential_color.split()) <= 2 and not any(char.isdigit() for char in potential_color):
                 color = potential_color.capitalize()

        # --- Consolidate and Finalize ---
        final_color_list = []
        
        # If primary color is still not found, try to get it from the list of colors
        if color == 'N/A' and colors:
            color = colors[0]

        # Use an ordered set to deduplicate while preserving order
        seen = set()
        
        # Add the primary color first
        if color and color != 'N/A':
            final_color_list.append(color)
            seen.add(color)
            
        # Add other unique colors
        for c in colors:
            if c and c not in seen:
                final_color_list.append(c)
                seen.add(c)

        colors_str = ', '.join(final_color_list)
        if not colors_str:
            colors_str = 'N/A'
        
        # Image information
        media_info = product_data.get('smallDefaultMedia', {}) or product_data.get('defaultMediaInfo', {})
        main_image = 'N/A'
        if isinstance(media_info, dict):
            main_image = media_info.get('uri', 'N/A')
            
        # --- Size & Stock Extraction from 'simples' ---
        # Based on analysis, the 'simples' array now only contains AVAILABLE sizes.
        simples = product_data.get('simples', [])
        available_sizes = []
        
        if isinstance(simples, list):
            size_curve = set()
            for simple in simples:
                if not isinstance(simple, dict):
                    continue

                # In the new format, 'size' is often a direct key in the simple object.
                size_name = simple.get('size')
                if not size_name:
                    # Fallback to the old dictionary format just in case.
                    size_info = simple.get('size', {})
                    size_name = size_info.get('name') if isinstance(size_info, dict) else None

                if size_name:
                    size_curve.add(size_name)

            # Sort the available sizes for consistent ordering
            if size_curve:
                try:
                    available_sizes = sorted(list(size_curve), key=lambda s: (s.isdigit() and int(s), s))
                except (ValueError, TypeError):
                    available_sizes = sorted(list(size_curve))
        
        # The 'sizes' column will now contain only available sizes.
        sizes_str = ', '.join(available_sizes) if available_sizes else 'N/A'
        # Stock count is not available in this data structure, so we set to 0.
        inventory_str = '0' 
        in_stock_str = 'In Stock' if available_sizes else 'Out of Stock'

        # Other attributes
        description = product_data.get('shortDescription', 'N/A')
        manufacturer = 'N/A'
        badges = 'N/A'
        people_bought_together = []
        related_products = []
        has_sellback = 'N/A'

        # --- Resilient Product URL Extraction ---
        # First, try to get a direct URL from the data. This is the most reliable.
        product_url = product_data.get('uri') or product_data.get('url')

        # If no direct URL is found, construct it from other pieces of data.
        if not product_url:
            # The 'path' is often a good alternative to the full URL.
            url_path = product_data.get('path')
            if url_path:
                product_url = f"https://en.zalando.de{url_path if url_path.startswith('/') else '/' + url_path}"
            else:
                # Fallback to the old SKU-based method if all else fails.
                product_url = f"https://en.zalando.de/{sku.lower().replace('_', '-')}.html"

        # Navigation target group for gender
        nav_group = product_data.get('navigationTargetGroup', 'WOMEN')
        gender = 'female' if nav_group == 'WOMEN' else 'male' if nav_group == 'MEN' else 'unisex'
        
        # Silhouette for specific category
        silhouette = product_data.get('silhouette', 'Unknown')
        
        # Category extraction - extract from product data
        root_category = 'N/A'
        category_tree = 'N/A'
        
        # Try to extract categories from various possible locations
        category_info = product_data.get('category', {})
        if isinstance(category_info, dict):
            root_category = category_info.get('name', 'N/A')
            category_tree = category_info.get('path', 'N/A')
        
        # Try alternative category paths
        if root_category == 'N/A':
            family_data = product_data.get('family', {})
            if isinstance(family_data, dict):
                categories = family_data.get('categories', [])
                if isinstance(categories, list) and categories:
                    root_category = categories[0].get('name', 'N/A') if isinstance(categories[0], dict) else str(categories[0])
                    category_tree = ' > '.join([cat.get('name', str(cat)) if isinstance(cat, dict) else str(cat) for cat in categories])
        
        # Try attributes for category information
        if root_category == 'N/A':
            attributes = product_data.get('attributes', [])
            if isinstance(attributes, list):
                for attr in attributes:
                    if isinstance(attr, dict):
                        attr_name = attr.get('name', '').lower()
                        if 'category' in attr_name or 'type' in attr_name:
                            root_category = attr.get('value', 'N/A')
                            break
        
        # Fallback to URL-based category if no dynamic data found
        if root_category == 'N/A':
            root_category = 'womens-clothing-underwear'
            category_tree = 'womens-clothing-underwear'
        
        product_info = {
            'domain': 'zalando.de',
            'country_code': 'DE',
            'url': product_url,
            'sku': sku,
            'condition': 'new',
            'gender': gender,
            'product_name': name,
            'brand': brand_name,
            'description': description,
            'manufacturer': manufacturer,
            'badges': badges,
            'initial_price': original_price,
            'final_price': final_price,
            'discount': discount,
            'currency': currency,
            'inventory': inventory_str,
            'is_sale': 'Yes' if is_sale else 'No',
            'in_stock': in_stock_str,
            'delivery': 'N/A',
            'root_category': root_category,
            'category_tree': category_tree,
            'main_image': main_image,
            'image_count': 1 if main_image != 'N/A' else 0,
            'image_urls': main_image,
            'rating': 'N/A',
            'reviews_count': 'N/A',
            'best_rating': 'N/A',
            'worst_rating': 'N/A',
            'rating_count': 'N/A',
            'review_count': 'N/A',
            'top_reviews': 'N/A',
            'product_url': product_url,
            'name': name,
            'other_attributes': 'N/A',
            'color': color,
            'colors': colors_str,
            'sizes': sizes_str,
            'similar_products': 'N/A',
            'people_bought_together': 'N/A',
            'related_products': 'N/A',
            'has_sellback': 'N/A',
            'brand_name': brand_name,
            'timestamp': pd.Timestamp.now().isoformat(),
            'input': product_url,
            'discovery_input': json.dumps({"url": product_url}),
            'error': 'N/A',
            'error_code': 'N/A',
            'warning': 'N/A',
            'warning_code': 'N/A'
        }
        
        return product_info
        
    except Exception as e:
        print(f"Error extracting product from JSON: {e}")
        return None

def extract_urls_from_graphql_cache(driver) -> List[str]:
    """Extracts all product URLs from the GraphQL cache in the page source."""
    try:
        scripts = driver.find_elements(By.TAG_NAME, "script")
        for script in scripts:
            script_content = script.get_attribute("innerHTML")
            if script_content and 'window.zalandoData' in script_content:
                json_str = script_content.split(' = ', 1)[1]
                if json_str.endswith(';'):
                    json_str = json_str[:-1]
                
                data = json.loads(json_str)
                graphql_cache = data.get('props', {}).get('graphqlCache', {})
                
                if graphql_cache:
                    all_urls = set()
                    for key, value in graphql_cache.items():
                        if value.get('__typename') == 'Article':
                            family = value.get('family')
                            if family and family.get('groups'):
                                for group in family['groups'].values():
                                    if 'articles' in group:
                                        for article_ref in group['articles'].values():
                                            if article_ref['__ref'] in graphql_cache:
                                                article_data = graphql_cache[article_ref['__ref']]
                                                if 'uri' in article_data:
                                                    all_urls.add(article_data['uri'])
                            else:
                                if 'uri' in value:
                                    all_urls.add(value['uri'])
                    return list(all_urls)
    except Exception as e:
        print(f"  - Could not extract from GraphQL cache. Error: {e}")
    return []

def extract_from_category_page(driver) -> List[Dict]:
    """
    Extracts product URLs from a category page.
    Scrolls to load all content, then extracts from full HTML in bulk.
    """
    
    # Wait for page to fully load before scrolling
    print("  - Waiting for page to fully load...")
    time.sleep(15)
    
    # Wait for product elements to be present
    print("  - Waiting for product elements to load...")
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
        )
        initial_products = len(driver.find_elements(By.CSS_SELECTOR, "article"))
        print(f"  - Found {initial_products} initial products, proceeding with scroll...")
    except TimeoutException:
        print("  - No products found initially, but continuing with scroll attempt...")
        initial_products = 0
    
    # Additional wait for JavaScript to fully initialize
    time.sleep(5)
    
    # Scroll to load all content
    total_products_found = scroll_to_load_content(driver)
    
    # **NEW APPROACH: Get all HTML at once and parse in bulk**
    print("  - Getting full page HTML for bulk parsing...")
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # Extract all products from HTML in one go
    products = extract_products_from_html_bulk(soup)
    
    print(f"  - Successfully extracted {len(products)} products from bulk HTML parsing")
    
    return products

def extract_products_from_html_bulk(soup) -> List[Dict]:
    """
    Extract all product data from parsed HTML in bulk - much faster than card-by-card
    """
    products = []
    
    # Find all product containers at once
    product_containers = soup.find_all('article') or soup.find_all(attrs={'data-testid': 'product-card'})
    
    if not product_containers:
        # Fallback selectors
        product_containers = soup.find_all(class_=lambda x: x and 'product' in x.lower())
    
    print(f"  - Found {len(product_containers)} product containers for bulk processing")
    
    for i, container in enumerate(product_containers):
        try:
            # Extract all data from this container's HTML
            product_data = extract_product_from_html_container(container, i)
            if product_data:
                products.append(product_data)
                
                # Debug output every 20 products to check quality
                if (i + 1) % 20 == 0:
                    brand = product_data.get('brand_name', 'N/A')
                    sizes = product_data.get('sizes', 'N/A')
                    name = product_data.get('name', 'N/A')[:30] + "..." if len(product_data.get('name', '')) > 30 else product_data.get('name', 'N/A')
                    size_status = "Available" if sizes != "N/A" else "Not on category page"
                    print(f"    - Sample #{i+1}: Brand='{brand}', Sizes={size_status}, Name='{name}'")
                    
        except Exception as e:
            print(f"    - Error processing container {i}: {e}")
            continue
    
    return products

def extract_product_from_html_container(container, index) -> Optional[Dict]:
    """
    Extract all product data from a single HTML container using BeautifulSoup
    Much faster and more reliable than Selenium DOM queries
    """
    try:
        # Get product URL - check multiple possible locations
        product_url = "N/A"
        link = container.find('a', href=True)
        if link:
            product_url = link['href']
            if not product_url.startswith('http'):
                product_url = f"https://en.zalando.de{product_url}"
        
        # Get all text content at once
        all_text = container.get_text(separator=' ', strip=True)
        
        # Extract product name using text patterns
        name = extract_name_from_text(all_text)
        
        # Extract brand from HTML structure (more accurate)
        brand = extract_brand_from_html_container(container)
        
        # Fallback to text-based if HTML extraction failed
        if brand == "N/A":
            brand = extract_brand_from_text(all_text, name)
        
        # Extract prices using regex on full text
        prices = extract_prices_from_text(all_text)
        original_price = prices.get('original', 0.0)
        final_price = prices.get('final', 0.0)
        discount = prices.get('discount', 0)
        is_sale = prices.get('is_sale', False)
        
        # Extract main image
        main_image = "N/A"
        img = container.find('img')
        if img:
            main_image = img.get('src') or img.get('data-src') or img.get('data-lazy-src', "N/A")
        
        # Extract multiple images if available
        all_images = []
        for img in container.find_all('img'):
            for attr in ['src', 'data-src', 'data-lazy-src']:
                img_url = img.get(attr)
                if img_url and img_url.startswith(('http', '//')):
                    all_images.append(img_url)
        
        # Remove duplicates and create image URLs string
        unique_images = list(dict.fromkeys(all_images))  # Preserves order
        image_urls = ', '.join(unique_images) if unique_images else "N/A"
        image_count = len(unique_images)
        
        # Extract SKU from URL
        sku = extract_sku_from_url(product_url)
        
        # Extract color from name or other text
        color = extract_color_from_text(all_text, name)
        
        # Sizes are typically not available on category pages - only on product pages
        # Most e-commerce sites load size data via AJAX or on individual product pages
        sizes = "N/A"  # Set to N/A for category page scraping
        
        # Optional: Try to extract if any size hints are available, but don't expect much
        try:
            size_hints = extract_basic_size_hints(container)
            if size_hints and size_hints != "N/A":
                sizes = size_hints
        except:
            pass
        
        # Build product info matching the expected format
        product_info = {
            'domain': 'www.zalando.de',
            'country_code': 'de',
            'url': product_url,
            'sku': sku,
            'condition': 'NewCondition',
            'gender': '',
            'product_name': name,
            'brand': json.dumps({"name": brand}) if brand != "N/A" else "N/A",
            'description': f"{brand} {name} for {final_price:.2f}€ ({pd.Timestamp.now().strftime('%Y-%m-%d')}). Free delivery on most orders*" if final_price > 0 else 'N/A',
            'manufacturer': brand,
            'badges': 'N/A',
            'initial_price': original_price,
            'final_price': final_price,
            'discount': discount if is_sale else '',
            'currency': 'EUR',
            'inventory': 'N/A',
            'is_sale': 'N/A',
            'in_stock': True,
            'delivery': 'N/A',
            'root_category': 'N/A',
            'category_tree': 'N/A',
            'main_image': main_image,
            'image_count': image_count,
            'image_urls': json.dumps(unique_images) if unique_images else "N/A",
            'rating': 0,
            'reviews_count': 0,
            'best_rating': 0,
            'worst_rating': 0,
            'rating_count': 0,
            'review_count': 0,
            'top_reviews': 'N/A',
            'product_url': product_url,
            'name': name,
            'SKU': sku,
            'other_attributes': 'N/A',
            'color': color,
            'colors': json.dumps([{"name": color, "availability": True, "is_current": True}]) if color != "N/A" else "N/A",
            'sizes': sizes,
            'similar_products': 'N/A',
            'people_bought_together': 'N/A',
            'related_products': 'N/A',
            'has_sellback': 'N/A',
            'brand_name': brand,
            'timestamp': pd.Timestamp.now().isoformat(),
            'input': json.dumps({"url": product_url}),
            'discovery_input': json.dumps({"url": product_url}),
            'error': 'N/A',
            'error_code': 'N/A',
            'warning': 'N/A',
            'warning_code': 'N/A'
        }
        
        return product_info
        
    except Exception as e:
        print(f"Error extracting product from HTML container {index}: {e}")
        return None

def extract_name_from_text(text):
    """Extract product name from card text using patterns"""
    if not text:
        return "N/A"
    
    # Split by common separators and find longest meaningful text
    text_parts = text.replace('\n', ' ').split()
    candidate_parts = []
    current_candidate = []
    
    for part in text_parts:
        if (len(part) > 2 and 
            not re.match(r'^\d+[,.]?\d*€?$', part) and  # Not price
            not re.match(r'^-?\d+%$', part) and        # Not percentage
            part not in ['heart_outlined', 'Sponsored', 'From', 'Quick', 'View']):
            current_candidate.append(part)
        else:
            if len(current_candidate) > 1:
                candidate_parts.append(' '.join(current_candidate))
            current_candidate = []
    
    # Add final candidate
    if len(current_candidate) > 1:
        candidate_parts.append(' '.join(current_candidate))
    
    # Pick longest candidate as product name
    if candidate_parts:
        name = max(candidate_parts, key=len)
        if len(name) > 50:
            name = name[:50] + "..."
        return name
    
    return "N/A"

def extract_brand_from_text(text, name):
    """Extract brand from card text with better filtering"""
    if not text:
        return "N/A"
    
    # Common non-brand words to filter out
    non_brand_words = {
        'sponsored', 'deal', 'sale', 'new', 'trending', 'popular', 'bestseller',
        'limited', 'exclusive', 'premium', 'luxury', 'designer', 'collection',
        'quick', 'view', 'add', 'wishlist', 'heart', 'outlined', 'from', 'to',
        'free', 'delivery', 'shipping', 'returns', 'sizes', 'colors', 'available',
        'only', 'left', 'stock', 'order', 'now', 'today', 'tomorrow', 'off'
    }
    
    words = text.split()
    
    # Strategy 1: Look for brand in first few words (before product name details)
    for word in words[:8]:  # Check first 8 words
        clean_word = word.strip('.,!?()[]{}').lower()
        if (len(word) > 2 and word[0].isupper() and 
            clean_word not in non_brand_words and
            word not in name and '€' not in word and 
            not word.isdigit() and '%' not in word and
            not re.match(r'^(XS|S|M|L|XL|XXL|XXXL)$', word)):  # Not a size
            return word
    
    # Strategy 2: Extract from product name (first word is usually brand)
    if name and name != "N/A":
        name_words = name.split()
        if name_words:
            first_word = name_words[0].strip('.,!?()[]{}')
            clean_first = first_word.lower()
            if (len(first_word) > 2 and 
                clean_first not in non_brand_words and
                not first_word.isdigit()):
                return first_word
    
    # Strategy 3: Look for known brand patterns in HTML
    # Try to find brand in structured data if available
    brand_indicators = ['brand:', 'by ', 'from ']
    text_lower = text.lower()
    for indicator in brand_indicators:
        if indicator in text_lower:
            start_idx = text_lower.find(indicator) + len(indicator)
            remaining_text = text[start_idx:start_idx+50]  # Next 50 chars
            words_after = remaining_text.split()
            if words_after:
                candidate = words_after[0].strip('.,!?()[]{}')
                if len(candidate) > 2 and candidate[0].isupper():
                    return candidate
    
    return "N/A"

def extract_prices_from_text(text):
    """Extract price information from text using regex"""
    if not text:
        return {'original': 0.0, 'final': 0.0, 'discount': 0, 'is_sale': False}
    
    # Find all prices
    price_matches = re.findall(r'(\d+[,.]?\d*)\s*€', text)
    price_values = []
    
    for match in price_matches:
        try:
            price_val = float(match.replace(',', '.'))
            price_values.append(price_val)
        except ValueError:
            continue
    
    if not price_values:
        return {'original': 0.0, 'final': 0.0, 'discount': 0, 'is_sale': False}
    
    if len(price_values) == 1:
        return {
            'original': price_values[0],
            'final': price_values[0], 
            'discount': 0,
            'is_sale': False
        }
    else:
        # Multiple prices - assume first is sale price, second is original
        final_price, original_price = price_values[0], price_values[1]
        if original_price > final_price:
            return {
                'original': original_price,
                'final': final_price,
                'discount': original_price - final_price,
                'is_sale': True
            }
        else:
            return {
                'original': final_price,
                'final': final_price,
                'discount': 0,
                'is_sale': False
            }

def extract_sku_from_url(url):
    """Extract SKU from product URL"""
    if not url or url == "N/A":
        return "N/A"
    
    url_parts = url.split('/')
    for part in url_parts:
        if '-' in part and any(c.isdigit() for c in part) and any(c.isalpha() for c in part):
            return part.split('.html')[0]  # Remove .html if present
    
    return "N/A"

def extract_color_from_text(text, name):
    """Extract color from text"""
    if not text:
        return "N/A"
    
    # Look for color keywords
    color_keywords = ['schwarz', 'black', 'white', 'weiß', 'nude', 'beige', 'red', 'blue', 'pink', 'green', 'yellow', 'grey', 'brown']
    text_lower = text.lower()
    
    for color_word in color_keywords:
        if color_word in text_lower:
            return color_word.title()
    
    return "N/A"

def extract_basic_size_hints(container):
    """
    Try to extract any basic size hints from category page (usually not available)
    This is a simplified approach that acknowledges sizes are rarely on category pages
    """
    try:
        # Look for any obvious size indicators in text (very rare on category pages)
        all_text = container.get_text(separator=' ', strip=True)
        
        # Only look for very obvious size patterns that might appear
        size_patterns = [
            r'Size[s]?:\s*([A-Z\d\-/,\s]+)',  # "Sizes: S, M, L" 
            r'Available[^:]*:\s*([A-Z\d\-/,\s]+)',  # "Available: S M L"
        ]
        
        for pattern in size_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                size_text = match.group(1).strip()
                # Extract individual sizes
                potential_sizes = re.findall(r'\b(XS|S|M|L|XL|XXL|XXXL|\d{2,3}[A-H]?)\b', size_text)
                if potential_sizes:
                    unique_sizes = sorted(list(set(potential_sizes)))
                    sizes_json_array = []
                    for size in unique_sizes:
                        sizes_json_array.append({
                            "sku": f"HINT-{size}",
                            "name": size,
                            "availability": True,
                            "url": ""
                        })
                    return json.dumps(sizes_json_array)
        
        return "N/A"
        
    except Exception:
        return "N/A"

# Removed unused size extraction functions - sizes are not available on category pages

def wait_for_dom_ready(driver, timeout=8):
    """Fast DOM ready check"""
    try:
        # Quick document ready check
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(0.5)  # Just a short pause
        return True
        
    except TimeoutException:
        print("Warning: DOM load timeout, proceeding anyway")
        return False

def wait_for_product_elements(driver, timeout=5):
    """Quick wait for product elements"""
    try:
        # Quick wait for at least one product card
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
        )
        return True
        
    except TimeoutException:
        print("Timeout waiting for product elements")
        return False

def scroll_to_load_content(driver, timeout=10):
    """
    Ultra-fast scroll function - stops immediately when enough products found
    """
    initial_products = len(driver.find_elements(By.CSS_SELECTOR, "article"))
    
    # If we already have enough products, don't scroll at all
    if initial_products >= 80:
        print(f"  - Already have {initial_products} products - skipping scroll")
        return initial_products
    
    print(f"  - Fast scroll: starting with {initial_products} products")
    
    # Quick scroll attempts with immediate exit
    for attempt in range(3):  # Max 3 attempts only
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)  # Even faster
        
        current_products = len(driver.find_elements(By.CSS_SELECTOR, "article"))
        
        # Exit immediately if we have enough
        if current_products >= 80:
            print(f"  - ✅ Found {current_products} products - stopping scroll")
            return current_products
            
        # Exit if no improvement
        if current_products <= initial_products:
            break
            
        initial_products = current_products
    
    final_products = len(driver.find_elements(By.CSS_SELECTOR, "article"))
    print(f"  - Scroll complete: {final_products} products")
    return final_products
    
    # Verify we're actually at the bottom
    max_scroll = final_height - driver.execute_script("return window.innerHeight")
    at_bottom = final_position >= max_scroll - 100
    print(f"    - At bottom: {at_bottom} (max_scroll={max_scroll})")
    
    if not at_bottom:
        print("    - ⚠️ Not at bottom, trying one more scroll...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        final_position = driver.execute_script("return window.pageYOffset")
        final_products = len(driver.find_elements(By.CSS_SELECTOR, "article"))
        print(f"    - After final scroll: Position={final_position}, Products={final_products}")
    
    if final_products < 50:
        print(f"    - ❌ WARNING: Only found {final_products} products - this may indicate scrolling failed")
    else:
        print(f"    - ✅ SUCCESS: Found {final_products} products")
    
    print(f"  - Scroll complete! Found {final_products} total products")
    return final_products

def scrape_page(driver, page_url: str) -> List[Dict]:
    """Scrape a single page using only category page extraction with robust scrolling"""
    try:
        driver.get(page_url)
        wait_for_dom_ready(driver)
        
        # Additional wait for full page load
        print("  - Waiting for full page load...")
        time.sleep(10)  # Increased wait for full page load

        # Only use category page extraction with robust scrolling
        print("  - Extracting products from category page...")
        products = extract_from_category_page(driver)
        
        if products:
            print(f"  ✅ SUCCESS: Found {len(products)} products from category page")
            return products
        else:
            print("  ❌ FAILURE: No products found on category page")
            return []
        
    except Exception as e:
        print(f"An error occurred in scrape_page: {e}")
        # Re-raise the exception so the retry wrapper can catch it
        raise

def respectful_delay():
    """Minimal delay for speed"""
    time.sleep(random.uniform(0.1, 0.3))

def exponential_backoff(attempt, max_attempts=3):
    """Calculates wait time for retries, e.g., 2s, 4s, 8s."""
    wait_time = 2 ** attempt + random.uniform(0, 1)
    print(f"    - Backing off for {wait_time:.2f} seconds...")
    time.sleep(wait_time)

def scrape_page_with_retry(driver, page_url: str, max_retries=2) -> List[Dict]:
    """
    Scrapes a single page with retries for transient errors
    """
    for attempt in range(max_retries):
        try:
            return scrape_page(driver, page_url)
        except InvalidSessionIdException as e:
            print(f"!!! Browser session crashed. Need to recreate driver. ({attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                # Browser crashed completely - can't recover with same driver
                print("  - Browser session is dead, need to recreate driver in main loop")
                raise e  # Re-raise so main loop can recreate driver
            else:
                print("!!! Browser crash on final attempt, giving up on this page")
                break
        except (StaleElementReferenceException, TimeoutException) as e:
            print(f"!!! Caught a transient error ({type(e).__name__}). Retrying... ({attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(1)  # Brief pause before retry
                try:
                    print("  - Refreshing page to get a fresh DOM state...")
                    driver.refresh()
                    time.sleep(1)  # Give page time to load
                except Exception as refresh_err:
                    print(f"!!! Critical error during page refresh: {refresh_err}. Stopping retries for this page.")
                    break
        except Exception as e:
            print(f"!!! An unexpected error occurred in scrape_page: {e}.")
            if attempt < max_retries - 1:
                print(f"Retrying... ({attempt + 1}/{max_retries})")
                time.sleep(1)
            else:
                traceback.print_exc()

    print(f"!!! Failed to scrape page {page_url} after {max_retries} attempts.")
    return []

def setup_driver():
    """
    Initializes and returns a more stable and lightweight Selenium WebDriver instance,
    configured for parallel execution.
    """
    options = webdriver.ChromeOptions()
    
    # --- Key Stability and Performance Options ---
    # options.add_argument("--headless") # Run without a UI for lower resource usage
    options.add_argument("--no-sandbox") # A common requirement for running in many environments
    options.add_argument("--disable-dev-shm-usage") # Overcomes limited resource problems
    options.add_argument("--window-size=1920,1080") # Set a standard window size
    
    # Removed problematic options that might interfere with scrolling:
    # - page_load_strategy = 'eager' (now uses default 'normal')
    # - disable-gpu (might interfere with rendering)
    # - disable-blink-features (might disable important features)
    # - anti-detection arguments (might interfere with page behavior)
    
    # Create driver with simpler setup like the working test
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set faster timeouts
        driver.set_page_load_timeout(30)
        driver.set_script_timeout(30)
        
        return driver
    except Exception as e:
        print(f"!!! CRITICAL: Failed to setup driver. Reason: {e}")
        # Re-raise the exception to ensure the multiprocessing pool handles the failure.
        raise

def get_brand_checkbox_info(driver, base_url):
    """
    Opens the brand filter and scrolls through it to collect the name and
    checkbox ID for every brand available.
    """
    try:
        driver.get(base_url)
        wait_for_dom_ready(driver)

        # 1. Wait for and click the brand filter button.
        brand_button_selector = (By.XPATH, "//div[@data-filter-id='brands']//button")
        brand_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(brand_button_selector)
        )
        driver.execute_script("arguments[0].click();", brand_button)
        print("Clicked brand filter button.")

        # 2. Wait for the dialog and find the scrollable container inside it.
        dialog_selector = (By.XPATH, "//div[@role='dialog' and contains(@aria-label, 'filter by Brand')]")
        dialog_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(dialog_selector)
        )
        scrollable_div = dialog_element.find_element(By.XPATH, ".//div[contains(@style, 'overflow: auto')]")
        print("Brand filter dialog and scrollable container found.")

        # 3. Loop by scrolling to get all brand info.
        all_brand_info = {}
        last_count = 0
        attempts = 0
        scroll_attempts = 0

        while scroll_attempts < 30:  # Safety break
            labels = dialog_element.find_elements(By.XPATH, ".//label[@for]")

            for label in labels:
                try:
                    brand_name = label.text.strip()
                    checkbox_id = label.get_attribute('for')
                    
                    if brand_name and checkbox_id and brand_name.lower() not in ['reset', 'save']:
                        if brand_name not in all_brand_info:
                            all_brand_info[brand_name] = checkbox_id
                except StaleElementReferenceException:
                    continue

            if len(all_brand_info) == last_count:
                attempts += 1
                if attempts >= 5:
                    print("No new brands found. Assuming end of list.")
                    break
            else:
                last_count = len(all_brand_info)
                attempts = 0

            print(f"Found {last_count} unique brands so far... Scrolling down.")
            driver.execute_script("arguments[0].scrollBy(0, 350);", scrollable_div)
            time.sleep(1)
            scroll_attempts += 1
        
        print(f"Finished scrolling. Found a total of {len(all_brand_info)} brands.")
        
        # Close the dialog by pressing Escape key
        from selenium.webdriver.common.keys import Keys
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.5)

        # 4. Format the collected data.
        brands = [{'name': name, 'id': checkbox_id} for name, checkbox_id in all_brand_info.items()]
        return sorted(brands, key=lambda x: x['name'])

    except Exception as e:
        print(f"A critical error occurred in get_brand_checkbox_info: {e}")
        traceback.print_exc()
        return []

def extract_brand_names_from_filter(driver, base_url):
    """
    Opens the brand filter and scrolls through it to collect the name of every brand.
    This is more reliable than trying to find links that may not exist.
    """
    try:
        driver.get(base_url)
        wait_for_dom_ready(driver)

        # 1. Open brand filter dialog
        brand_button_selector = (By.XPATH, "//div[@data-filter-id='brands']//button")
        brand_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(brand_button_selector))
        driver.execute_script("arguments[0].click();", brand_button)
        print("Clicked brand filter button.")

        dialog_selector = (By.XPATH, "//div[@role='dialog' and contains(@aria-label, 'filter by Brand')]")
        dialog_element = WebDriverWait(driver, 10).until(EC.visibility_of_element_located(dialog_selector))
        
        try:
            scrollable_div = dialog_element.find_element(By.XPATH, ".//div[contains(@style, 'overflow: auto')]")
        except NoSuchElementException:
            # Fallback: use the dialog element itself
            scrollable_div = dialog_element
            print("Using dialog element as scrollable container (fallback)")
        
        print("Brand filter dialog found.")

        # 2. Loop by scrolling to get all brand names
        all_brand_names = set()
        last_count = 0
        attempts = 0
        scroll_attempts = 0

        while scroll_attempts < 40: # Increased scroll attempts for very long lists
            labels = dialog_element.find_elements(By.XPATH, ".//label[@for]")
            for label in labels:
                for attempt in range(3): # Retry loop for stale elements
                    try:
                        brand_name = label.text.strip()
                        if brand_name and brand_name.lower() not in ['reset', 'save']:
                            all_brand_names.add(brand_name)
                        break # Success, exit retry loop
                    except StaleElementReferenceException:
                        print(f"  - Caught StaleElementReferenceException. Retrying... (Attempt {attempt + 1})")
                        time.sleep(0.5) # Wait a moment for DOM to settle
                        # On the last attempt, we don't need to do anything, it will just fail
                        if attempt == 2:
                             print(f"  - Failed to get brand name after multiple retries. Skipping this element.")

            if len(all_brand_names) == last_count:
                attempts += 1
                if attempts >= 5:
                    print("No new brands found after 5 scrolls. Assuming end of list.")
                    break
            else:
                last_count = len(all_brand_names)
                attempts = 0

            print(f"Found {last_count} unique brands so far... Scrolling down.")
            driver.execute_script("arguments[0].scrollBy(0, 400);", scrollable_div)
            time.sleep(1)
            scroll_attempts += 1
        
        print(f"Finished scrolling. Found a total of {len(all_brand_names)} brand names.")
        return sorted(list(all_brand_names))

    except Exception as e:
        print(f"A critical error occurred in extract_brand_names_from_filter: {e}")
        traceback.print_exc()
        return []

def generate_slugs(brand_name: str) -> List[str]:
    """Generates a list of potential URL slugs for a given brand name."""
    slugs = set()
    name = brand_name.lower()
    # This regex is a simplified and safe way to create a slug.
    # It replaces any character that is not a letter, number, or hyphen with a hyphen.
    slugs.add(re.sub(r'[^a-z0-9]+', '-', name).strip('-'))

    # This version is slightly more permissive, keeping whitespace for replacement.
    # It also handles a wider range of characters.
    slugs.add(re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '-'))
    return list(slugs)

def _brand_page_is_verified(driver, brand_name: str) -> bool:
    """
    Checks if the current page is the correct brand page by looking in the
    title, headings, or links within headings.
    """
    check_name = brand_name.split(' (')[0].strip().lower()

    # 1. Check page title
    if check_name in driver.title.lower():
        return True

    # 2. Check h1 and h2 tags directly
    for heading_tag in ['h1', 'h2']:
        for heading in driver.find_elements(By.TAG_NAME, heading_tag):
            try:
                if check_name in heading.get_attribute('textContent').lower():
                    return True
            except StaleElementReferenceException:
                continue
    
    # 3. Check for the brand name within a link inside an H1 tag, per user feedback
    try:
        for link in driver.find_elements(By.XPATH, "//h1//a"):
            if check_name in link.text.lower():
                return True
    except StaleElementReferenceException:
        pass

    return False


def log_failed_brand(brand_name: str, filename="failed_brands.txt"):
    """Appends a failed brand name to the specified log file."""
    try:
        # Using a with statement ensures the file is properly closed.
        # 'a' mode appends to the file, creating it if it doesn't exist.
        with open(filename, "a", encoding="utf-8") as f:
            f.write(f"{brand_name}\n")
    except IOError as e:
        # It's good practice to log that logging failed.
        print(f"!!! CRITICAL: Could not write failed brand '{brand_name}' to log file '{filename}'. Reason: {e}")


def create_brand_urls(base_url, brand_names):
    """
    Create a list of potential brand-specific URLs for scraping.
    Uses a manual override for known incorrect slugs.
    """
    brand_url_options = []
    print(f"Generating URL options for {len(brand_names)} brands...")
    
    for brand_name in brand_names:
        # Check for a manual override first
        if brand_name in MANUAL_SLUG_OVERRIDES:
            override_slug = MANUAL_SLUG_OVERRIDES[brand_name]
            print(f"  - Using manual slug override for '{brand_name}': '{override_slug}'")
            potential_urls = [f"{base_url.rstrip('/')}/{override_slug}/"]
        else:
            # Otherwise, generate slugs automatically
            slugs = generate_slugs(brand_name)
            if not slugs:
                print(f"  Could not generate any slugs for brand: '{brand_name}'. Skipping.")
                continue
            potential_urls = [f"{base_url.rstrip('/')}/{slug}/" for slug in slugs]

        brand_url_options.append({
            'brand_name': brand_name,
            'urls': potential_urls
        })
        
    print("Finished generating brand URLs.")
    return brand_url_options

def scrape_brand_pages(args):
    """
    Scrapes all pages for a single brand. Tries multiple URL slugs if necessary.
    """
    brand_info, num_pages_per_brand, process_id = args
    brand_name, potential_urls = brand_info['brand_name'], brand_info['urls']
    print(f"[PID {os.getpid()}] Starting brand: {brand_name}")
    
    driver = setup_driver()
    brand_products, seen_skus = [], set()
    
    try:
        verified_url = None
        # Try each potential URL until one is verified
        for url_to_try in potential_urls:
            driver.get(url_to_try)
            time.sleep(1) # Allow for immediate redirects to settle
            # 1. Primary verification: Check the URL first. This is the fastest way to detect a bad slug.
            slug = url_to_try.strip('/').split('/')[-1]
            if slug not in driver.current_url:
                print(f"    URL verification failed: Redirect detected from '{url_to_try}'")
                continue # Try the next potential URL

            # 2. Secondary verification: Check page content (title, headings)
            try:
                WebDriverWait(driver, 15).until(
                    lambda d: _brand_page_is_verified(d, brand_name)
                )
                verified_url = url_to_try
                print(f"[PID {os.getpid()}, Brand: {brand_name}] Page verified: {verified_url}")
                break # Exit the loop once a URL is verified
            except TimeoutException:
                print(f"    Content verification failed for {url_to_try}. Title was: '{driver.title}'")
                continue # Try the next URL

        if not verified_url:
            print(f"!!! [PID {os.getpid()}, Brand: {brand_name}] FAILED TO VERIFY ANY URLS. Skipping.")
            log_failed_brand(brand_name)
            return []

        # Loop through pages for the verified brand
        for page_num in range(1, num_pages_per_brand + 1):
            if page_num > 1:
                separator = '?' if '?' not in verified_url else '&'
                page_url = f"{verified_url}{separator}p={page_num}"
            else:
                page_url = verified_url
            
            print(f"[PID {os.getpid()}, Brand: {brand_name}] Scraping page {page_num}: {page_url}")
            products_on_page = scrape_page_with_retry(driver, page_url)
            
            if not products_on_page:
                # If it's the first page and we get nothing, the brand might be empty.
                print(f"[PID {os.getpid()}, Brand: {brand_name}] No more products found. Stopping.")
                break
                
            # Deduplicate within this brand's scrape
            new_products_count = 0
            for product in products_on_page:
                sku = product.get('sku', 'N/A')
                if sku not in seen_skus:
                    seen_skus.add(sku)
                    brand_products.append(product)
                    new_products_count += 1
            
            if new_products_count == 0 and page_num > 1:
                print(f"[PID {os.getpid()}, Brand: {brand_name}] Page {page_num} contained only duplicate products. Stopping.")
                break

            # A shorter delay to increase scraping speed. Can be increased if rate-limiting issues occur.
            time.sleep(random.uniform(1, 2.5))
            
    except Exception as e:
        print(f"[PID {os.getpid()}] A critical error occurred while scraping '{brand_name}': {e}")
        traceback.print_exc()
    finally:
        driver.quit()
        print(f"[PID {os.getpid()}] Finished brand: {brand_name}. Found {len(brand_products)} products.")

    return brand_products

def scrape_category_pages(category_url, max_pages=50, output_filename='zalando_underwear_category.csv'):
    """
    Scrape all pages of a category directly, writing to CSV continuously
    """
    print(f"🎯 Starting category-level scraping: {category_url}")
    
    # Check for previous progress
    checkpoint = load_progress_checkpoint(output_filename)
    
    # Prevent computer from sleeping during scraping
    prevent_sleep()
    
    driver = setup_driver()
    seen_skus = set()
    total_products = 0
    csv_initialized = False
    
    try:
        for page_num in range(1, max_pages + 1):
            # Construct page URL
            if page_num > 1:
                separator = '?' if '?' not in category_url else '&'
                page_url = f"{category_url}{separator}p={page_num}"
            else:
                page_url = category_url
            
            print(f"\n📄 Scraping page {page_num}: {page_url}")
            
            # Health check before scraping each page
            driver = ensure_driver_alive(driver)
            
            # Scrape the page with browser crash recovery
            try:
                products_on_page = scrape_page_with_retry(driver, page_url)
            except Exception as e:
                if "invalid session id" in str(e) or "InvalidSessionIdException" in str(e):
                    print(f"   💥 Browser crashed on page {page_num}. Recreating driver...")
                    try:
                        driver.quit()
                    except:
                        pass  # Driver might already be dead
                    
                    driver = setup_driver()
                    print(f"   🔄 Driver recreated. Retrying page {page_num}...")
                    
                    # Retry with new driver
                    try:
                        products_on_page = scrape_page_with_retry(driver, page_url)
                    except Exception as retry_e:
                        print(f"   ❌ Still failed after driver recreation: {retry_e}")
                        products_on_page = []
                else:
                    print(f"   ❌ Unexpected error on page {page_num}: {e}")
                    products_on_page = []
            
            if not products_on_page:
                print(f"   ⚠️ No products found on page {page_num}. Stopping pagination.")
                break
            
            print(f"   ✅ Found {len(products_on_page)} products on page {page_num}")
            
            # Deduplicate and collect new products
            new_products = []
            new_products_count = 0
            for product in products_on_page:
                sku = product.get('sku', 'N/A')
                if sku not in seen_skus:
                    seen_skus.add(sku)
                    new_products.append(product)
                    new_products_count += 1
            
            # Write new products to CSV immediately
            if new_products:
                try:
                    # Create DataFrame for new products
                    df_new = pd.DataFrame(new_products)
                    df_new_cleaned = df_new.reindex(columns=CLEANED_DATA_COLUMNS, fill_value='N/A')
                    
                    # Write to CSV - header only on first write
                    mode = 'w' if not csv_initialized else 'a'
                    header = not csv_initialized
                    
                    df_new_cleaned.to_csv(output_filename, mode=mode, header=header, index=False)
                    csv_initialized = True
                    total_products += new_products_count
                    
                    print(f"   💾 Saved {new_products_count} new products to CSV (total saved: {total_products})")
                    
                except Exception as e:
                    print(f"   ❌ Error writing to CSV: {e}")
            
            print(f"   📊 Added {new_products_count} new unique products (total unique: {len(seen_skus)})")
            
            # If no new products, we've reached the end
            if new_products_count == 0 and page_num > 1:
                print(f"   🏁 No new products on page {page_num}. Reached end of category.")
                break
            
            # Save checkpoint every 5 pages
            if page_num % 5 == 0:
                save_progress_checkpoint(page_num, total_products, output_filename)
            
            # Faster delay between pages
            time.sleep(random.uniform(0.5, 1.0))
            
    except Exception as e:
        print(f"❌ Error during category scraping: {e}")
        traceback.print_exc()
    finally:
        driver.quit()
        # Restore normal sleep behavior
        allow_sleep()
        
    print(f"\n🎉 Category scraping complete! Found {total_products} unique products across {page_num} pages.")
    print(f"💾 All data saved to: {output_filename}")
    return total_products

def analyze_csv_quality(filename):
    """Analyze the quality of the scraped data from CSV file"""
    try:
        if not os.path.exists(filename):
            print(f"❌ CSV file {filename} not found")
            return
            
        df = pd.read_csv(filename)
        total_products = len(df)
        
        if total_products == 0:
            print("❌ No products found in CSV")
            return
        
        # Quality metrics
        products_with_prices = sum(1 for _, row in df.iterrows() if row.get('final_price', 0) > 0)
        products_with_names = sum(1 for _, row in df.iterrows() if row.get('name', 'N/A') != 'N/A' and len(str(row.get('name', ''))) > 5)
        products_with_brands = sum(1 for _, row in df.iterrows() if row.get('brand_name', 'N/A') != 'N/A')
        products_with_sizes = sum(1 for _, row in df.iterrows() if row.get('sizes', 'N/A') != 'N/A')
        
        price_quality = products_with_prices / total_products * 100
        name_quality = products_with_names / total_products * 100  
        brand_quality = products_with_brands / total_products * 100
        size_quality = products_with_sizes / total_products * 100
        
        print(f"\n📊 FINAL QUALITY SUMMARY:")
        print(f"   Total products: {total_products}")
        print(f"   Products with prices: {products_with_prices}/{total_products} ({price_quality:.1f}%)")
        print(f"   Products with names: {products_with_names}/{total_products} ({name_quality:.1f}%)")
        print(f"   Products with brands: {products_with_brands}/{total_products} ({brand_quality:.1f}%)")
        print(f"   Products with sizes: {products_with_sizes}/{total_products} ({size_quality:.1f}%)")
        
        # Show brand diversity
        unique_brands = set(row.get('brand_name', 'N/A') for _, row in df.iterrows() if row.get('brand_name', 'N/A') != 'N/A')
        print(f"   Unique brands found: {len(unique_brands)}")
        
        overall_quality = (price_quality + name_quality + brand_quality + size_quality) / 4
        print(f"\n🎯 OVERALL QUALITY: {overall_quality:.1f}%")
        
    except Exception as e:
        print(f"❌ Error analyzing CSV: {e}")

def save_progress_checkpoint(page_num, total_products, output_filename):
    """Save progress info to a checkpoint file"""
    try:
        checkpoint_data = {
            'last_page': page_num,
            'total_products': total_products,
            'output_file': output_filename,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        checkpoint_file = output_filename.replace('.csv', '_checkpoint.json')
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
            
        print(f"   💾 Checkpoint saved: Page {page_num}, {total_products} products")
    except Exception as e:
        print(f"   ⚠️ Could not save checkpoint: {e}")

def load_progress_checkpoint(output_filename):
    """Load progress info from checkpoint file if it exists"""
    try:
        checkpoint_file = output_filename.replace('.csv', '_checkpoint.json')
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            
            print(f"📋 Found previous checkpoint:")
            print(f"   Last page: {checkpoint_data.get('last_page', 'Unknown')}")
            print(f"   Products collected: {checkpoint_data.get('total_products', 'Unknown')}")
            print(f"   Timestamp: {checkpoint_data.get('timestamp', 'Unknown')}")
            return checkpoint_data
    except Exception as e:
        print(f"⚠️ Could not load checkpoint: {e}")
    
    return None

def prevent_sleep():
    """Prevent Windows from going to sleep during scraping"""
    try:
        # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000040)
        print("🔒 Prevented computer sleep mode during scraping")
        return True
    except Exception as e:
        print(f"⚠️ Could not prevent sleep mode: {e}")
        return False

def allow_sleep():
    """Allow Windows to go back to normal sleep behavior"""
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        print("🔓 Restored normal sleep mode")
    except Exception as e:
        print(f"⚠️ Could not restore sleep mode: {e}")

def is_driver_alive(driver):
    """Check if the WebDriver session is still alive"""
    try:
        # Simple check - get current URL
        _ = driver.current_url
        return True
    except InvalidSessionIdException:
        return False
    except Exception:
        return False

def ensure_driver_alive(driver):
    """Ensure driver is alive, recreate if needed"""
    if not is_driver_alive(driver):
        print("🔄 Driver session dead, recreating...")
        try:
            driver.quit()
        except:
            pass
        return setup_driver()
    return driver

def extract_brand_from_html_container(container):
    """Extract brand from HTML container using structure and attributes"""
    try:
        # Strategy 1: Look for brand-specific HTML elements and attributes
        brand_selectors = [
            '[data-testid*="brand"]',
            '[class*="brand"]',
            '[class*="Brand"]', 
            '[data-brand]',
            '.brand-name',
            '.manufacturer',
            '[data-testid*="manufacturer"]'
        ]
        
        for selector in brand_selectors:
            elements = container.select(selector)
            for elem in elements:
                # Check text content
                brand_text = elem.get_text(strip=True)
                if brand_text and len(brand_text) <= 50:
                    # Filter out common non-brand text
                    if not any(word in brand_text.lower() for word in ['sponsored', 'deal', 'sale', 'new']):
                        return brand_text
                
                # Check attributes
                for attr in ['data-brand', 'data-manufacturer', 'title', 'aria-label']:
                    attr_value = elem.get(attr, '')
                    if attr_value and len(attr_value) <= 50:
                        return attr_value
        
        # Strategy 2: Look in structured data (JSON-LD, microdata)
        json_attrs = ['data-product', 'data-brand-info', 'data-manufacturer']
        for attr in json_attrs:
            json_data = container.get(attr)
            if json_data:
                try:
                    data = json.loads(json_data)
                    brand = extract_brand_from_json_data(data)
                    if brand != "N/A":
                        return brand
                except:
                    pass
        
        # Strategy 3: Look for brand in link URLs (often contains brand slug)
        links = container.select('a[href]')
        for link in links:
            href = link.get('href', '')
            if href and '/brand/' in href:
                # Extract brand from URL like /brand/calvin-klein/
                brand_match = re.search(r'/brand/([^/]+)', href)
                if brand_match:
                    brand_slug = brand_match.group(1)
                    # Convert slug to readable name
                    brand_name = brand_slug.replace('-', ' ').title()
                    return brand_name
        
        # Strategy 4: Fallback to text-based extraction
        all_text = container.get_text(separator=' ', strip=True)
        return extract_brand_from_text(all_text, "")
        
    except Exception as e:
        print(f"Error in HTML brand extraction: {e}")
        return "N/A"

def extract_brand_from_json_data(data):
    """Extract brand from JSON data structures"""
    def recursive_search(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if 'brand' in key.lower() or 'manufacturer' in key.lower():
                    if isinstance(value, str) and len(value) <= 50:
                        return value
                    elif isinstance(value, dict) and 'name' in value:
                        return value['name']
                result = recursive_search(value)
                if result != "N/A":
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = recursive_search(item)
                if result != "N/A":
                    return result
        return "N/A"
    
    return recursive_search(data)

if __name__ == "__main__":
    # Configuration
    category_url = "https://en.zalando.de/womens-clothing-underwear/"
    max_pages = 500 # Adjust based on how deep you want to go
    output_filename = 'zalando_underwear_category.csv'
    
    print("🚀 ZALANDO CATEGORY SCRAPER - ROBUST BULK EXTRACTION")
    print("=" * 70)
    print(f"Target Category: {category_url}")
    print(f"Max Pages: {max_pages}")
    print(f"Output File: {output_filename}")
    print("")
    print("🛡️  NEW FEATURES:")
    print("   • Sleep mode prevention (no more crashes)")
    print("   • Browser crash recovery with driver recreation")
    print("   • Bulk HTML parsing (10x faster than card-by-card)")
    print("   • Progress checkpoints every 5 pages")
    print("   • Session health monitoring")
    print("")
    print("ℹ️   DATA AVAILABILITY:")
    print("   • ✅ Product names, brands, prices - Available on category pages")
    print("   • ❌ Size/variant data - Only available on individual product pages")
    print("   • 💡 To get sizes: scrape individual product pages (much slower)")
    print("=" * 70)
    
    # Scrape the entire category with continuous CSV writing
    total_products = scrape_category_pages(category_url, max_pages, output_filename)
    
    if total_products > 0:
        print(f"\n✅ SUCCESS: Continuously saved {total_products} products to '{output_filename}'")
        
        # Analyze the final CSV file quality
        analyze_csv_quality(output_filename)
    else:
        print("❌ No products found to save.")
    
    print(f"\n🏁 SCRAPING COMPLETE!")
    print("=" * 60)



