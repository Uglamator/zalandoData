import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re
import json
import requests
import io

# =====================
# Data Cleaning Helpers
# =====================
# Explicit mapping for main and specific categories
MAIN_CATEGORY_MAP = {
    # Bras
    'bh': 'Bras', 'bra': 'Bras', 'buegel': 'Bras', 'underwired': 'Bras', 'triangle': 'Bras', 'soft': 'Bras',
    'push': 'Bras', 't-shirt': 'Bras', 'balcony': 'Bras', 'balconette': 'Bras',
    'strapless': 'Bras', 'plunge': 'Bras', 'wireless': 'Bras', 'bralette': 'Bras', 'minimizer': 'Bras',
    'maternity': 'Bras', 'multiway': 'Bras', 'bustier': 'Bras',

    # Underwear
    'briefs': 'Underwear', 'brief': 'Underwear', 'panties': 'Underwear', 'panty': 'Underwear',
    'period-panties': 'Underwear', 'g-string': 'Underwear', 'slip': 'Underwear', 'thong': 'Underwear',
    'tanga': 'Underwear', 'hipster': 'Underwear', 'brazilian': 'Underwear', 'string': 'Underwear',
    'boxer': 'Underwear', 'shorts': 'Underwear', 'boyshort': 'Underwear',

    # Bodysuits & Corsetry
    'body': 'Bodysuits & Corsetry', 'bodysuit': 'Bodysuits & Corsetry', 'bodies': 'Bodysuits & Corsetry',
    'corset': 'Bodysuits & Corsetry',

    # Shapewear
    'shapewear': 'Shapewear', 'girdle': 'Shapewear',

    # Lingerie Sets
    'lingerie-set': 'Lingerie Sets', 'set': 'Lingerie Sets',

    # Nightwear
    'pyjama': 'Nightwear', 'pajama': 'Nightwear', 'nightdress': 'Nightwear', 'nightwear': 'Nightwear',
    'babydoll': 'Nightwear', 'chemise': 'Nightwear', 'robe': 'Nightwear',

    # Tops
    'tank': 'Tops', 'top': 'Tops', 'sweater': 'Tops', 'undershirt': 'Tops', 'camisole': 'Tops',

    # Hosiery
    'tights': 'Hosiery', 'stockings': 'Hosiery', 'hold-ups': 'Hosiery', 'socks': 'Hosiery', 'leggings': 'Hosiery',

    # Swimwear
    'bikini': 'Swimwear', 'swimsuit': 'Swimwear', 'tankini': 'Swimwear',

    # Sports
    'sports-bra': 'Sports Bras',

    # Accessories
    'suspenders': 'Accessories', 'garter': 'Accessories', 'pasties': 'Accessories',

    # Bottoms (likely from other data)
    'jean': 'Bottoms',

    # Fallbacks - updated for consistency
    'womens-clothing-lingerie-bodies': 'Bodysuits & Corsetry',
    'women-clothing-underwear-undershirts': 'Tops',
    'women-clothing-underwear-suspenders': 'Accessories',
    'women-clothing-underwear-corset': 'Bodysuits & Corsetry',
}
# You can expand this as needed for your business logic
SPECIFIC_CATEGORY_MAP = {
    # Bras
    'balconette': 'Balconette Bra',
    'balconette-bra': 'Balconette Bra',
    'plunge': 'Plunge Bra',
    'plunge-bra': 'Plunge Bra',
    'push': 'Push-up Bra',
    'push-up': 'Push-up Bra',
    'push-up-bra': 'Push-up Bra',
    'triangle': 'Triangle Bra',
    'triangle-bra': 'Triangle Bra',
    'wireless': 'Wireless Bra',
    'wireless-bra': 'Wireless Bra',
    'bustier': 'Bustier',
    'bustier-bra': 'Bustier',
    't-shirt-bra': 'T-shirt Bra',
    'strapless': 'Strapless Bra',
    'strapless-bra': 'Strapless Bra',
    'soft-bra': 'Soft Bra',
    'underwired-bra': 'Underwired Bra',
    'sports-bra': 'Sports Bra',
    'minimizer-bra': 'Minimizer Bra',
    'bralette': 'Bralette',
    'longline-bra': 'Longline Bra',
    'maternity-bra': 'Maternity Bra',
    'nursing-bra': 'Nursing Bra',
    'multiway-bra': 'Multiway Bra',
    'front-closure-bra': 'Front Closure Bra',
    'convertible-bra': 'Convertible Bra',
    'full-cup-bra': 'Full Cup Bra',
    'demi-bra': 'Demi Bra',
    'shelf-bra': 'Shelf Bra',
    'side-support-bra': 'Side Support Bra',
    # Underwear
    'brief': 'Brief',
    'briefs': 'Brief',
    'panty': 'Brief',
    'panties': 'Brief',
    'tanga': 'Tanga',
    'hipster': 'Hipster',
    'brazilian': 'Brazilian',
    'string': 'G-String',
    'g-string': 'G-String',
    'g-strings': 'G-String',
    'thong': 'Thong',
    'slip': 'Slip',
    'boxer': 'Boxer',
    'boxers': 'Boxer',
    'shorts': 'Shorts',
    'boyshort': 'Shorts',
    'boyshorts': 'Shorts',
    'period-panties': 'Period Panties',
    # Shapewear
    'shapewear': 'Shapewear',
    'body': 'Body',
    'bodies': 'Body',
    'corset': 'Corset',
    'girdle': 'Corset',
    'waist-cincher': 'Corset',
    # Lingerie sets
    'lingerie-set': 'Lingerie Set',
    'lingerie-sets': 'Lingerie Set',
    'set': 'Lingerie Set',
    # Tops
    'tank': 'Tank Top',
    'tank-top': 'Tank Top',
    'top': 'Top',
    'tops': 'Top',
    'sweater': 'Sweater',
    'undershirt': 'Undershirt',
    'undershirts': 'Undershirt',
    'camisole': 'Camisole',
    'crop-top': 'Crop Top',
    # Nightwear
    'pyjama': 'Pyjama',
    'pyjamas': 'Pyjama',
    'pajama': 'Pyjama',
    'pajamas': 'Pyjama',
    'nightdress': 'Nightdress',
    'nightgown': 'Nightdress',
    'nightshirt': 'Nightdress',
    'nightwear': 'Nightdress',
    'babydoll': 'Babydoll',
    'chemise': 'Chemise',
    'robe': 'Robe',
    'dressing-gown': 'Robe',
    # Hosiery
    'tights': 'Tights',
    'stockings': 'Stockings',
    'hold-ups': 'Hold-Ups',
    'socks': 'Socks',
    'knee-highs': 'Socks',
    'leggings': 'Leggings',
    # Swimwear (if present)
    'bikini': 'Bikini',
    'bikini-top': 'Bikini Top',
    'bikini-bottom': 'Bikini Bottom',
    'swimsuit': 'Swimsuit',
    'one-piece': 'Swimsuit',
    'tankini': 'Tankini',
    # Accessories
    'suspenders': 'Suspenders',
    'garter': 'Garter',
    'garter-belt': 'Garter',
    'pasties': 'Pasties',
    'accessories': 'Accessories',
}

def extract_main_category(text):
    if not isinstance(text, str):
        return None
    text_lc = text.lower()
    # Try to extract from discovery_input first
    for k, v in MAIN_CATEGORY_MAP.items():
        if k in text_lc:
            return v
    # Try again without hyphens
    text_lc_nohyphen = text_lc.replace('-', ' ')
    for k, v in MAIN_CATEGORY_MAP.items():
        if k in text_lc_nohyphen:
            return v
    return None

def extract_specific_category(text):
    if not isinstance(text, str):
        return None
    text_lc = text.lower()
    for k, v in SPECIFIC_CATEGORY_MAP.items():
        if k in text_lc:
            return v
    text_lc_nohyphen = text_lc.replace('-', ' ')
    for k, v in SPECIFIC_CATEGORY_MAP.items():
        if k in text_lc_nohyphen:
            return v
    return None

def extract_cat_from_discovery_input(di):
    try:
        if pd.isna(di):
            return None
        # If it's a JSON string with a 'url' field
        if isinstance(di, str) and di.startswith('{'):
            d = json.loads(di)
            url = d.get('url', '')
            if url:
                parts = [p for p in url.split('/') if p]
                if parts and parts[-1].endswith('.html') and len(parts) > 1:
                    return parts[-2]
                elif parts:
                    return parts[-1]
        # If it's already a path or slug
        elif isinstance(di, str):
            parts = [p for p in di.split('/') if p]
            if parts and parts[-1].endswith('.html') and len(parts) > 1:
                return parts[-2]
            elif parts:
                return parts[-1]
    except Exception:
        return None
    return None

def extract_main_category_from_discovery_input(di):
    """
    Extracts the category slug from discovery_input (JSON or path) and maps it to MAIN_CATEGORY_MAP.
    """
    try:
        # If it's a JSON string with a 'url' field
        if isinstance(di, str) and di.startswith('{'):
            d = json.loads(di)
            url = d.get('url', '')
            if url:
                parts = [p for p in url.split('/') if p]
                slug = parts[-2] if parts and parts[-1].endswith('.html') and len(parts) > 1 else (parts[-1] if parts else '')
            else:
                slug = ''
        # If it's already a path or slug
        elif isinstance(di, str):
            parts = [p for p in di.split('/') if p]
            slug = parts[-2] if parts and parts[-1].endswith('.html') and len(parts) > 1 else (parts[-1] if parts else '')
        else:
            slug = ''
        slug = slug.lower()
        return MAIN_CATEGORY_MAP.get(slug, 'Other')
    except Exception:
        return 'Other'

# --- Refactored Data Cleaning Functions ---
def clean_brand_column(df):
    def extract_clean_brand(brand_str):
        if pd.isna(brand_str) or not isinstance(brand_str, str):
            return 'Unknown'
        brand_str = brand_str.strip()
        if brand_str.startswith('{') and brand_str.endswith('}'):
            try:
                parsed = json.loads(brand_str)
                for key in ['brand', 'brand_name', 'name']:
                    if key in parsed and isinstance(parsed[key], str):
                        return parsed[key].strip().title()
                for v in parsed.values():
                    if isinstance(v, str):
                        return v.strip().title()
            except Exception:
                pass
        cleaned = re.sub(r'\s+', ' ', brand_str).strip().title()
        return cleaned
    if 'brand' in df.columns:
        df['brand_clean'] = df['brand'].fillna(df.get('brand_name', '')).apply(extract_clean_brand)
    elif 'brand_name' in df.columns:
        df['brand_clean'] = df['brand_name'].apply(extract_clean_brand)
    else:
        df['brand_clean'] = 'Unknown'
    return df

def clean_name_columns(df):
    def extract_clean_name(name_str):
        if pd.isna(name_str) or not isinstance(name_str, str):
            return 'Unknown'
        name_str = name_str.strip()
        if name_str.startswith('{') and name_str.endswith('}'):
            try:
                parsed = json.loads(name_str)
                for key in ['name', 'title', 'product_name', 'text']:
                    if key in parsed and isinstance(parsed[key], str):
                        return parsed[key].strip()
                for v in parsed.values():
                    if isinstance(v, str):
                        return v.strip()
            except Exception:
                pass
        cleaned = re.sub(r'\s+', ' ', name_str).strip()
        return cleaned
    df['product_name_clean'] = df.get('product_name', '').apply(extract_clean_name)
    df['name_clean'] = df.get('name', '').apply(extract_clean_name)
    df['best_name'] = df['product_name_clean'].fillna(df['name_clean']).fillna(df.get('product_name', '')).fillna(df.get('name', ''))
    return df

def clean_category_columns(df):
    # Use discovery_input if available and not generic, else fall back to name
    def get_main_cat(row):
        disc = row.get('discovery_input', '')
        name = row.get('name', '')
        main_cat = extract_main_category(disc)
        if (not main_cat) or (disc.lower() in ['womens-clothing-underwear', 'womens clothing underwear', 'lingerie', 'underwear']):
            main_cat = extract_main_category(name)
        return main_cat
    def get_spec_cat(row):
        disc = row.get('discovery_input', '')
        name = row.get('name', '')
        spec_cat = extract_specific_category(disc)
        if (not spec_cat) or (disc.lower() in ['womens-clothing-underwear', 'womens clothing underwear', 'lingerie', 'underwear']):
            spec_cat = extract_specific_category(name)
        return spec_cat
    df['category_clean'] = df.apply(get_main_cat, axis=1)
    df['specific_category'] = df.apply(get_spec_cat, axis=1)
    return df

def clean_color_column(df):
    basic_color_map = {
        'schwarz': 'Black', 'black': 'Black', 'noir': 'Black', 'jet': 'Black',
        'weiß': 'White', 'weiss': 'White', 'white': 'White', 'offwhite': 'White', 'off-white': 'White', 'ecru': 'White', 'ivory': 'White',
        'blau': 'Blue', 'navy': 'Blue', 'blue': 'Blue', 'dunkelblau': 'Blue', 'hellblau': 'Blue', 'denim': 'Blue', 'azur': 'Blue', 'marine': 'Blue',
        'rot': 'Red', 'red': 'Red', 'bordeaux': 'Red', 'burgunder': 'Red', 'weinrot': 'Red', 'karminrot': 'Red',
        'rosa': 'Pink', 'pink': 'Pink', 'altrosa': 'Pink', 'fuchsia': 'Pink', 'magenta': 'Pink', 'rosé': 'Pink',
        'beige': 'Beige', 'sand': 'Beige', 'stone': 'Beige', 'camel': 'Beige', 'champagner': 'Beige',
        'braun': 'Brown', 'brown': 'Brown', 'kastanie': 'Brown', 'espresso': 'Brown', 'mokka': 'Brown', 'chocolate': 'Brown',
        'grün': 'Green', 'green': 'Green', 'oliv': 'Green', 'olive': 'Green', 'mint': 'Green', 'türkis': 'Green', 'turquoise': 'Green', 'smaragd': 'Green', 'khaki': 'Green',
        'gelb': 'Yellow', 'yellow': 'Yellow', 'gold': 'Yellow', 'senf': 'Yellow', 'lemon': 'Yellow',
        'lila': 'Purple', 'purple': 'Purple', 'violett': 'Purple', 'aubergine': 'Purple', 'mauve': 'Purple', 'lavendel': 'Purple',
        'grau': 'Grey', 'gray': 'Grey', 'grey': 'Grey', 'anthrazit': 'Grey', 'silber': 'Grey', 'silver': 'Grey', 'platin': 'Grey',
        'orange': 'Orange', 'koralle': 'Orange', 'coral': 'Orange', 'apricot': 'Orange', 'aprikose': 'Orange',
        'multi': 'Multicolor', 'mehrfarbig': 'Multicolor', 'multicolor': 'Multicolor', 'bunt': 'Multicolor', 'print': 'Multicolor', 'gemustert': 'Multicolor',
        'creme': 'Cream', 'cream': 'Cream', 'milch': 'Cream',
        'khaki': 'Khaki',
        'peach': 'Peach', 'pfirsich': 'Peach',
        'taupe': 'Taupe',
        'petrol': 'Petrol',
        'powder': 'Powder', 'puder': 'Powder',
        'crystal': 'Crystal', 'kristall': 'Crystal',
        'smoke': 'Grey', 'rauch': 'Grey',
        'mintgrün': 'Green', 'pastellgrün': 'Green', 'pastellblau': 'Blue', 'pastellrosa': 'Pink',
        'pastellgelb': 'Yellow', 'pastelllila': 'Purple',
    }
    color_mix_patterns = [
        r'/', r'-', r',', r' & ', r' und ', r'\+', r'\s+mit\s+', r'\s+and\s+', r'\s*\+\s*'
    ]
    def map_color(raw_color):
        if pd.isna(raw_color):
            return 'Unknown'
        raw_color = str(raw_color).lower().strip()
        # Handle color mixes
        for pat in color_mix_patterns:
            if re.search(pat, raw_color):
                parts = re.split(pat, raw_color)
                mapped = [basic_color_map.get(p.strip(), None) for p in parts]
                mapped = [m for m in mapped if m]
                if len(set(mapped)) == 1:
                    return mapped[0]
                elif mapped:
                    return 'Multicolor'
        # Direct mapping
        if raw_color in basic_color_map:
            return basic_color_map[raw_color]
        for part in re.split(r'[ ,/\-]+', raw_color):
            if part in basic_color_map:
                return basic_color_map[part]
        return raw_color.split()[0].capitalize() if raw_color else 'Unknown'
    if 'color' in df.columns:
        df['color_clean'] = df['color'].apply(map_color)
    elif 'colors' in df.columns:
        df['color_clean'] = df['colors'].apply(map_color)
    else:
        df['color_clean'] = 'Unknown'
    return df

def clean_price_columns(df):
    if 'initial_price' in df.columns and 'final_price' in df.columns:
        df['initial_price'] = pd.to_numeric(df['initial_price'], errors='coerce')
        df['final_price'] = pd.to_numeric(df['final_price'], errors='coerce')
        df['discount_pct'] = ((df['initial_price'] - df['final_price']) / df['initial_price'] * 100).round(2)
    else:
        df['discount_pct'] = np.nan
    return df

def auto_clean_data(df):
    """Clean and enrich the raw product DataFrame using modular helpers."""
    df = clean_brand_column(df)
    df = clean_name_columns(df)
    df = clean_category_columns(df)
    df = clean_color_column(df)
    df = clean_price_columns(df)
    df = adjust_for_pack_size(df)
    return df

def adjust_for_pack_size(df):
    """
    Extracts pack size from product name and calculates price per item.
    """
    # Regex to find patterns like "3 PACK", "3ER PACK", "3-PACK", "3x"
    pack_regex = re.compile(r'(\d+)\s*(?:pack|er pack|-pack|x)', re.IGNORECASE)

    def get_pack_size(name):
        if not isinstance(name, str):
            return 1
        match = pack_regex.search(name)
        if match:
            # Ensure the pack size is a reasonable number to avoid errors with product codes
            pack_size = int(match.group(1))
            return pack_size if pack_size > 0 and pack_size < 20 else 1
        return 1

    # Apply the function to the 'best_name' column
    df['pack_size'] = df['best_name'].apply(get_pack_size)

    # Calculate price_per_item, ensuring we don't divide by zero
    df['price_per_item'] = df['final_price'] / df['pack_size'].where(df['pack_size'] > 0, 1)
    
    return df

RAW_CSV = 'https://raw.githubusercontent.com/Uglamator/zalandoData/main/cleaned_zalando_data.csv'


@st.cache_data # Cache the data loading process
def load_data():
    """
    Downloads the pre-cleaned data from GitHub and returns a DataFrame.
    The result is cached to prevent re-downloading on every interaction.
    """
    try:
        # Use requests to reliably fetch the data, handling redirects
        response = requests.get(RAW_CSV)
        response.raise_for_status()  # Raise an exception for bad responses (4xx or 5xx)

        # Read the cleaned CSV content directly into a DataFrame
        cleaned_df = pd.read_csv(io.StringIO(response.text))
        
        return cleaned_df

    except requests.exceptions.RequestException as e:
        st.error(f"Failed to download data: {e}")
        return pd.DataFrame() # Return an empty DataFrame on error

def highlight_dorina(row):
    brand = row['brand_clean'] if 'brand_clean' in row else ''
    if 'dorina' in str(brand).lower():
        return ['background-color: #ffe599;'] * len(row)
    else:
        return [''] * len(row)

def ensure_dorina_in_series(series, dorina_value):
    if 'Dorina' not in [b.title() for b in series.index]:
        series = pd.concat([series, pd.Series([dorina_value], index=['Dorina'])])
    return series

def ensure_dorina_in_df(df, dorina_row, key_col='brand_clean'):
    if not (df[key_col].str.lower() == 'dorina').any():
        df = pd.concat([df, pd.DataFrame([dorina_row])], ignore_index=True)
    return df

# =====================
# UI Helper Functions
# =====================
def format_2dp(x):
    if isinstance(x, (float, int)):
        return f"{x:.2f}"
    return x

def smart_style(df):
    fmt = {}
    for col in df.columns:
        col_vals = pd.to_numeric(df[col], errors='coerce').dropna()
        if len(col_vals) == 0:
            continue
        if (col_vals == col_vals.astype(int)).all():
            fmt[col] = "{:.0f}"
        else:
            fmt[col] = "{:.2f}"
    return df.style.format(fmt)

# =====================
# Dashboard Sections
# =====================
# (Implement all dashboard section functions here, similar to virtual_shopping_room)

def dashboard_tab(df):
    st.header("Dashboard")
    st.markdown("---")
    # --- Category/Subcategory Filters ---
    categories = ['All'] + sorted(df['category_clean'].dropna().unique())
    selected_category = st.selectbox("Filter by Category", categories, index=0, key='dashboard_category')
    if selected_category != 'All':
        subcategories = ['All'] + sorted(df[df['category_clean'] == selected_category]['specific_category'].dropna().unique())
    else:
        subcategories = ['All'] + sorted(df['specific_category'].dropna().unique())
    selected_subcat = st.selectbox("Filter by Subcategory", subcategories, index=0, key='dashboard_subcat')
    filtered = df.copy()
    if selected_category != 'All':
        filtered = filtered[filtered['category_clean'] == selected_category]
    if selected_subcat != 'All':
        filtered = filtered[filtered['specific_category'] == selected_subcat]
    # --- Top Row: KPI Tiles ---
    total_skus = len(filtered)
    in_stock = (filtered['in_stock'] > 0).sum() if 'in_stock' in filtered.columns else 0
    pct_in_stock = (in_stock / total_skus * 100) if total_skus > 0 else 0
    discounted = (filtered['discount_pct'] > 0).sum()
    pct_discounted = (discounted / total_skus * 100) if total_skus > 0 else 0
    avg_discount = filtered.loc[filtered['discount_pct'] > 0, 'discount_pct'].mean() if discounted > 0 else 0
    avg_price_pack = filtered['final_price'].mean()
    avg_price_item = filtered['price_per_item'].mean()
    n_brands = filtered['brand_clean'].nunique()
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total SKUs", f"{total_skus:,}")
    col2.metric("% In Stock", f"{pct_in_stock:.1f}%")
    col3.metric("% Discounted", f"{pct_discounted:.1f}%")
    col4.metric("Avg Discount", f"{avg_discount:.1f}%")
    col5.metric("Avg Price (Pack)", f"€{avg_price_pack:.2f}")
    col6.metric("Avg Price (Item)", f"€{avg_price_item:.2f}")
    st.markdown("---")
    # --- Second Row: Visual Mixes ---
    colA, colB = st.columns(2)
    with colA:
        st.markdown("**Price Band Mix (Per Item)**")
        price_bins = [0, 20, 30, 40, 50, 60, 1e6]
        price_labels = ['<20€', '20-30€', '30-40€', '40-50€', '50-60€', '60€+']
        price_band_item = pd.cut(filtered['price_per_item'], bins=price_bins, labels=price_labels, right=False)
        price_counts_item = price_band_item.value_counts().reindex(price_labels, fill_value=0)
        st.plotly_chart(px.bar(x=price_labels, y=price_counts_item.values, labels={'x': 'Price Band (Per Item)', 'y': 'SKUs'}), use_container_width=True)
    with colB:
        st.markdown("**Color Mix**")
        if 'color_clean' in filtered.columns:
            color_counts = filtered['color_clean'].value_counts()
            sorted_colors = color_counts.sort_values(ascending=False)
            total_colors = sorted_colors.sum()
            cumsum = sorted_colors.cumsum() / total_colors
            main_colors = sorted_colors[cumsum <= 0.5]
            other_colors = sorted_colors[cumsum > 0.5]
            pie_labels = list(main_colors.index)
            pie_values = list(main_colors.values)
            if not other_colors.empty:
                pie_labels.append('Other')
                pie_values.append(other_colors.sum())
            st.plotly_chart(px.pie(names=pie_labels, values=pie_values, title=None), use_container_width=True)
    st.markdown("---")
    # --- Third Row: Actionable Tables ---
    with st.expander("Top Discounted Products", expanded=False):
        top_discounted = filtered[filtered['discount_pct'] > 0].sort_values('discount_pct', ascending=False).head(10)
        for i, row in top_discounted.iterrows():
            cols = st.columns([1, 3])
            with cols[0]:
                img_url = row.get('main_image')
                if img_url and pd.notna(img_url) and str(img_url).startswith('http'):
                    st.image(img_url, width=80)
                else:
                    st.write("No image")
            with cols[1]:
                st.markdown(f"**{row['best_name']}**")
                st.write(f"€{row['final_price']:.2f}")
                st.write(f"Discount: {row['discount_pct']:.1f}%")
                st.write(f"Brand: {row['brand_clean']}")
                if 'in_stock' in row:
                    st.write(f"In stock: {row['in_stock']}")
    st.subheader("Most Out-of-Stock Products")
    if 'in_stock' in filtered.columns and 'total' in filtered.columns:
        filtered['in_stock_pct'] = (filtered['in_stock'] / filtered['total'] * 100).round(1)
        low_instock = filtered[filtered['in_stock_pct'] < 60].sort_values('in_stock_pct').head(10)
        for i, row in low_instock.iterrows():
            cols = st.columns([1, 3])
            with cols[0]:
                img_url = row.get('main_image')
                if img_url and pd.notna(img_url) and str(img_url).startswith('http'):
                    st.image(img_url, width=80)
                else:
                    st.write("No image")
            with cols[1]:
                st.markdown(f"**{row['best_name']}**")
                st.write(f"€{row['final_price']:.2f}")
                st.write(f"Brand: {row['brand_clean']}")
                st.write(f"In-stock: {row['in_stock']} / {row['total']} sizes ({row['in_stock_pct']}%)")
    st.markdown("---")
    # --- Deep Dive Tabs ---
    st.subheader("Deep Dives")
    deepdive_tabs = st.tabs(["Category Deep Dive", "Subcategory Deep Dive"])
    with deepdive_tabs[0]:
        st.info("Select a main category below to see brand, color, and price analytics for that category.")
        category_deep_dives(filtered)
    with deepdive_tabs[1]:
        st.info("Select a subcategory below to see brand, color, and price analytics for that subcategory.")
        deep_dive_by_specific_category(filtered)

    # --- Pack Analysis Section ---
    st.markdown("---")
    st.header("Pack Analysis")

    # Filter for products sold in packs
    packs_df = filtered[filtered['pack_size'] > 1].copy()

    if not packs_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Distribution of Pack Sizes**")
            pack_counts = packs_df['pack_size'].value_counts().sort_index()
            st.plotly_chart(px.bar(pack_counts, 
                                   x=pack_counts.index, 
                                   y=pack_counts.values, 
                                   labels={'x': 'Pack Size', 'y': 'Number of SKUs'}),
                            use_container_width=True)

        with col2:
            st.markdown("**Top 10 Brands Selling in Packs**")
            brand_pack_counts = packs_df['brand_clean'].value_counts().head(10)
            st.dataframe(brand_pack_counts.reset_index().rename(columns={'index': 'Brand', 'brand_clean': 'SKU Count'}),
                         use_container_width=True)
    else:
        st.info("No products sold in packs match the current filter criteria.")

def virtual_shopping_room(df):
    """
    Redesigned Product Finder for buyers: quick filters, summary panels, and a product gallery.
    """
    st.header("Product Finder")
    # --- Quick Filters ---
    col1, col2, col3, col4 = st.columns([2,2,2,2])
    with col1:
        categories = ['All'] + sorted(df['category_clean'].dropna().unique())
        selected_category = st.selectbox("Category", categories)
    with col2:
        if selected_category != 'All':
            subcats = ['All'] + sorted(df[df['category_clean'] == selected_category]['specific_category'].dropna().unique())
        else:
            subcats = ['All'] + sorted(df['specific_category'].dropna().unique())
        selected_subcat = st.selectbox("Subcategory", subcats)
    with col3:
        brands = ['All'] + sorted(df['brand_clean'].dropna().unique())
        selected_brand = st.selectbox("Brand", brands)
    with col4:
        if 'color_clean' in df.columns:
            color_options = sorted(df['color_clean'].dropna().unique())
            selected_colors = st.multiselect("Color(s)", color_options, default=[])
        else:
            selected_colors = []
    # --- Price Range Slider (capped at 60 EUR, 60+ means everything above) ---
    min_price = float(df['final_price'].min())
    max_slider = 60.0 if df['final_price'].max() > 60 else float(df['final_price'].max())
    price_range = st.slider("Price Range (€)", min_value=min_price, max_value=max_slider, value=(min_price, max_slider), step=1.0)
    filtered = df.copy()
    if price_range[1] == max_slider and max_slider == 60.0:
        filtered = filtered[(filtered['final_price'] >= price_range[0])]
    else:
        filtered = filtered[(filtered['final_price'] >= price_range[0]) & (filtered['final_price'] <= price_range[1])]
    # --- Filtering ---
    if selected_category != 'All':
        filtered = filtered[filtered['category_clean'] == selected_category]
    if selected_subcat != 'All':
        filtered = filtered[filtered['specific_category'] == selected_subcat]
    if selected_brand != 'All':
        filtered = filtered[filtered['brand_clean'] == selected_brand]
    if selected_colors:
        filtered = filtered[filtered['color_clean'].isin(selected_colors)]
    # --- Summary Panels ---
    st.markdown("---")
    colA, colB, colC = st.columns(3)
    with colA:
        st.markdown("**Brand Mix**")
        brand_counts = filtered['brand_clean'].value_counts()
        if not brand_counts.empty:
            # Sort brands by count descending
            sorted_counts = brand_counts.sort_values(ascending=False)
            total = sorted_counts.sum()
            cumsum = sorted_counts.cumsum() / total
            # Brands to show individually: those before the last 50% of volume
            main_brands = sorted_counts[cumsum <= 0.5]
            other_brands = sorted_counts[cumsum > 0.5]
            pie_labels = list(main_brands.index)
            pie_values = list(main_brands.values)
            if not other_brands.empty:
                pie_labels.append('Other')
                pie_values.append(other_brands.sum())
            st.plotly_chart(px.pie(names=pie_labels, values=pie_values, title=None), use_container_width=True)
        else:
            st.info("No brands in selection.")
    with colB:
        st.markdown("**Color Mix**")
        if 'color_clean' in filtered.columns:
            color_counts = filtered['color_clean'].value_counts()
            if not color_counts.empty and color_counts.shape[0] > 1:
                st.plotly_chart(px.pie(names=color_counts.index, values=color_counts.values, title=None), use_container_width=True)
        # else: do not show anything if no color data
    with colC:
        st.markdown("**Discounted & Out-of-Stock**")
        discounted = (filtered['discount_pct'] > 0).sum()
        total_styles = len(filtered)
        avg_discount = filtered.loc[filtered['discount_pct'] > 0, 'discount_pct'].mean() if discounted > 0 else 0
        pct_discounted = (discounted / total_styles * 100) if total_styles > 0 else 0
        out_of_stock = (filtered['in_stock'] == 0).sum() if 'in_stock' in filtered.columns else 0
        st.metric("% Discounted", f"{pct_discounted:.1f}%")
        st.metric("Avg Discount", f"{avg_discount:.1f}%")
        st.metric("Out of Stock", out_of_stock)
    st.markdown("---")
    # --- Product Gallery (Paginated Grid) ---
    page_size = 20
    total_products = len(filtered)
    page = st.number_input("Page", min_value=1, max_value=max(1, (total_products-1)//page_size+1), value=1, step=1)
    start = (page-1)*page_size
    end = start+page_size
    gallery = filtered.iloc[start:end]
    n_cols = 5
    for i in range(0, len(gallery), n_cols):
        row = gallery.iloc[i:i+n_cols]
        cols = st.columns(n_cols)
        for j, (_, prod) in enumerate(row.iterrows()):
            with cols[j]:
                img_url = prod.get('main_image')
                if img_url and pd.notna(img_url) and str(img_url).startswith('http'):
                    st.image(img_url, width=120)
                else:
                    st.write("No image")
                st.markdown(f"**{prod['best_name']}**")
                st.write(f"€{prod['final_price']:.2f}")
                if prod.get('discount_pct', 0) > 0:
                    st.markdown(f"<span style='color:red;font-weight:bold'>-{prod['discount_pct']:.0f}%</span>", unsafe_allow_html=True)
                if 'color_clean' in prod and pd.notna(prod['color_clean']):
                    st.write(f"Color: {prod['color_clean']}")
                st.write(f"Brand: {prod['brand_clean']}")
                if 'in_stock' in prod:
                    if prod['in_stock'] == 0:
                        st.markdown(f"<span style='color:gray'>Out of stock</span>", unsafe_allow_html=True)
                    else:
                        st.write(f"In stock: {prod['in_stock']}")
                if 'product_url' in prod and pd.notna(prod['product_url']):
                    st.markdown(f"[View on Zalando]({prod['product_url']})", unsafe_allow_html=True)
    # --- Product Modal ---
    if 'modal_sku' in st.session_state:
        sku = st.session_state['modal_sku']
        prod = df[df['sku'] == sku].iloc[0]
        with st.expander(f"Product Details: {prod['best_name']}", expanded=True):
            img_url = prod.get('main_image')
            if img_url and pd.notna(img_url) and str(img_url).startswith('http'):
                st.image(img_url, width=200)
            st.write(f"Price: €{prod['final_price']:.2f}")
            st.write(f"Discount: {prod['discount_pct']:.1f}%")
            st.write(f"Brand: {prod['brand_clean']}")
            st.write(f"Category: {prod['category_clean']} | {prod['specific_category']}")
            if 'color_clean' in prod and pd.notna(prod['color_clean']):
                st.write(f"Color: {prod['color_clean']}")
            if 'sizes' in prod and pd.notna(prod['sizes']):
                try:
                    sizes = json.loads(prod['sizes'])
                    st.write("**Variants (sizes, stock):**")
                    size_df = pd.DataFrame(sizes)
                    if not size_df.empty:
                        size_df['availability'] = size_df['availability'].map(lambda x: 'In stock' if x else 'Out of stock')
                        st.dataframe(size_df[['size', 'availability']], use_container_width=True)
                except Exception:
                    pass
            if st.button("Close Details"):
                del st.session_state['modal_sku']
    if total_products == 0:
        st.info("No products match your filters.")

def executive_summary(df):
    """
    Streamlit interface for the Executive Summary.
    """
    st.header("Executive Summary")
    col1, col2, col3, col4 = st.columns(4)
    dorina_df = df[df['brand_clean'].str.contains('Dorina', case=False, na=False)]
    col1.metric("Total Products (Dorina)", f"{len(dorina_df):,}")
    col2.metric("Avg Price (Dorina)", f"€{dorina_df['final_price'].mean():.2f}")
    col3.metric("Avg Discount (Dorina)", f"{dorina_df['discount_pct'].mean():.2f}%")
    col4.metric("Categories", f"{dorina_df['category_clean'].nunique()}")

def market_share_by_brand(df):
    """
    Streamlit interface for Market Share by Brand.
    """
    st.header("Market Share by Brand (Top 15 + Dorina)")
    brand_counts = df['brand_clean'].value_counts().head(15)
    dorina_count = df[df['brand_clean'].str.lower() == 'dorina'].shape[0]
    brand_counts = ensure_dorina_in_series(brand_counts, dorina_count)
    # Chart
    fig = px.bar(
        x=brand_counts.index,
        y=brand_counts.values,
        color=["Dorina" if "dorina" in str(b).lower() else "Other" for b in brand_counts.index],
        color_discrete_map={"Dorina": "#e74c3c", "Other": "#3498db"},
        labels={'x': 'Brand', 'y': 'Number of Products'},
        title="Product Count by Brand (Dorina Highlighted)"
    )
    st.plotly_chart(fig, use_container_width=True)
    # Table
    brand_table = pd.DataFrame({'Brand': brand_counts.index, 'Product_Count': brand_counts.values})
    st.dataframe(smart_style(brand_table), use_container_width=True)

def average_price_by_brand(df):
    """
    Streamlit interface for Average Price by Brand.
    """
    st.header("Average Price by Brand (Top 15 + Dorina)")
    
    # Get top 15 brands by product count
    top_brands_by_count = df['brand_clean'].value_counts().head(15).index.tolist()
    if 'Dorina' not in [b.title() for b in top_brands_by_count]:
        top_brands_by_count.append('Dorina')

    # Calculate both pack and item prices
    brand_prices_pack = df[df['brand_clean'].isin(top_brands_by_count)].groupby('brand_clean')['final_price'].mean()
    brand_prices_item = df[df['brand_clean'].isin(top_brands_by_count)].groupby('brand_clean')['price_per_item'].mean()
    
    # Combine into a single DataFrame for charting
    price_comparison_df = pd.DataFrame({
        'Avg Price (Pack)': brand_prices_pack,
        'Avg Price (Item)': brand_prices_item
    }).reindex(top_brands_by_count).reset_index().rename(columns={'index': 'Brand'})

    # Melt the DataFrame for Plotly Express
    price_comparison_melted = price_comparison_df.melt(id_vars='Brand', var_name='Price Type', value_name='Average Price (€)')

    # Highlight Dorina
    price_comparison_melted['Color'] = price_comparison_melted['Brand'].apply(lambda x: 'Dorina' if 'dorina' in str(x).lower() else 'Other')

    # Chart
    fig = px.bar(
        price_comparison_melted,
        x='Brand',
        y='Average Price (€)',
        color='Price Type',
        barmode='group',
        labels={'x': 'Brand', 'y': 'Average Price (€)'},
        title="Average Price by Brand: Pack vs. Item (Dorina Highlighted)",
        color_discrete_map={"Avg Price (Pack)": "#3498db", "Avg Price (Item)": "#e74c3c"}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Table
    st.dataframe(smart_style(price_comparison_df.set_index('Brand')), use_container_width=True)

def category_deep_dives(df):
    st.markdown("---")
    st.header("Category Deep Dive")
    categories = sorted(df['category_clean'].dropna().unique())
    selected_category = st.selectbox("Select a main category to deep dive:", categories, key='cat_deepdive')
    cat_df = df[df['category_clean'] == selected_category]
    brands = sorted(cat_df['brand_clean'].dropna().unique())
    dorina_idx = brands.index('Dorina') if 'Dorina' in brands else 0
    selected_brand = st.selectbox("Brand to Compare", ['All'] + brands, index=dorina_idx+1 if 'Dorina' in brands else 0, key='cat_brand_compare')
    if selected_brand != 'All':
        filtered = cat_df[cat_df['brand_clean'] == selected_brand]
    else:
        filtered = cat_df.copy()
    # --- KPI Tiles ---
    total_skus = len(filtered)
    n_brands = filtered['brand_clean'].nunique()
    avg_price = filtered['final_price'].mean()
    discounted = (filtered['discount_pct'] > 0).sum()
    pct_discounted = (discounted / total_skus * 100) if total_skus > 0 else 0
    avg_discount = filtered.loc[filtered['discount_pct'] > 0, 'discount_pct'].mean() if discounted > 0 else 0
    in_stock = (filtered['in_stock'] > 0).sum() if 'in_stock' in filtered.columns else 0
    pct_in_stock = (in_stock / total_skus * 100) if total_skus > 0 else 0
    top_color = filtered['color_clean'].mode()[0] if 'color_clean' in filtered.columns and not filtered['color_clean'].mode().empty else 'N/A'
    top_brand = filtered['brand_clean'].mode()[0] if not filtered['brand_clean'].mode().empty else 'N/A'
    # --- Comparative Visuals ---
    st.markdown("---")
    st.subheader("Brand vs. Category Comparison")
    # --- Average Price by Brand (top 10 + selected) ---
    brand_counts = cat_df['brand_clean'].value_counts()
    top_brands = brand_counts.head(10).index.tolist()
    if selected_brand != 'All' and selected_brand not in top_brands:
        top_brands.append(selected_brand)
    avg_price_by_brand = cat_df[cat_df['brand_clean'].isin(top_brands)].groupby('brand_clean')['final_price'].mean().reindex(top_brands)
    highlight_color = ['#e74c3c' if b == selected_brand else '#3498db' for b in avg_price_by_brand.index]
    fig_price = px.bar(x=avg_price_by_brand.index, y=avg_price_by_brand.values, color=avg_price_by_brand.index,
                      color_discrete_sequence=highlight_color,
                      labels={'x': 'Brand', 'y': 'Avg Price (€)'}, title="Average Price by Brand")
    st.plotly_chart(fig_price, use_container_width=True)
    # --- SKU Count by Brand (top 10 + selected) ---
    sku_count_by_brand = cat_df[cat_df['brand_clean'].isin(top_brands)].groupby('brand_clean').size().reindex(top_brands)
    fig_count = px.bar(x=sku_count_by_brand.index, y=sku_count_by_brand.values, color=sku_count_by_brand.index,
                      color_discrete_sequence=highlight_color,
                      labels={'x': 'Brand', 'y': 'SKU Count'}, title="SKU Count by Brand")
    st.plotly_chart(fig_count, use_container_width=True)
    # --- Color Mix: Separate Bar Charts, Top 10 Colors by Category/Subcategory ---
    st.markdown("**Color Mix (SKU Count)**")
    cat_color = cat_df['color_clean'].value_counts().head(10)
    color_order = cat_color.index.tolist()
    brand_color = filtered['color_clean'].value_counts().reindex(color_order, fill_value=0)
    # Category chart
    fig_cat_color = px.bar(x=color_order, y=cat_color.values,
                          labels={'x': 'Color', 'y': 'SKU Count'}, title="Category Color Mix (Top 10)")
    st.plotly_chart(fig_cat_color, use_container_width=True)
    # Brand chart
    fig_brand_color = px.bar(x=color_order, y=brand_color.values,
                            labels={'x': 'Color', 'y': 'SKU Count'}, title=f"{selected_brand} Color Mix (Top 10)")
    st.plotly_chart(fig_brand_color, use_container_width=True)
    # --- Price Band Mix (side-by-side barchart) ---
    st.markdown("**Price Band Mix**")
    price_bins = [0, 20, 30, 40, 50, 60, 1e6]
    price_labels = ['<20€', '20-30€', '30-40€', '40-50€', '50-60€', '60€+']
    brand_band = pd.cut(filtered['final_price'], bins=price_bins, labels=price_labels, right=False)
    cat_band = pd.cut(cat_df['final_price'], bins=price_bins, labels=price_labels, right=False)
    band_df = pd.DataFrame({selected_brand: brand_band.value_counts(normalize=True).reindex(price_labels, fill_value=0),
                           'Category': cat_band.value_counts(normalize=True).reindex(price_labels, fill_value=0)}, index=price_labels)
    fig_band = px.bar(band_df.reset_index(), x='index', y=[selected_brand, 'Category'], barmode='group',
                     labels={'value': 'Share', 'index': 'Price Band'}, title="Price Band Mix: Brand vs. Category")
    st.plotly_chart(fig_band, use_container_width=True)
    # --- Metric Cards for Discount and In-Stock % ---
    st.markdown("---")
    st.subheader("Brand vs. Category Metrics")
    cat_avg_discount = cat_df.loc[cat_df['discount_pct'] > 0, 'discount_pct'].mean()
    cat_in_stock = (cat_df['in_stock'] > 0).sum() if 'in_stock' in cat_df.columns else 0
    cat_pct_in_stock = (cat_in_stock / len(cat_df) * 100) if len(cat_df) > 0 else 0
    col1, col2 = st.columns(2)
    col1.metric("Avg Discount", f"{avg_discount:.1f}%", delta=f"vs {cat_avg_discount:.1f}% category avg")
    col2.metric("% In Stock", f"{pct_in_stock:.1f}%", delta=f"vs {cat_pct_in_stock:.1f}% category avg")
    # --- Raw Data Table ---
    st.markdown("---")
    st.subheader("Filtered Data Table")
    st.dataframe(filtered, use_container_width=True)

def deep_dive_by_specific_category(df):
    st.markdown("---")
    st.header("Subcategory Deep Dive")
    subcategories = sorted(df['specific_category'].dropna().unique())
    selected_subcat = st.selectbox("Select a subcategory to deep dive:", subcategories, key='subcat_deepdive')
    subcat_df = df[df['specific_category'] == selected_subcat]
    brands = sorted(subcat_df['brand_clean'].dropna().unique())
    dorina_idx = brands.index('Dorina') if 'Dorina' in brands else 0
    selected_brand = st.selectbox("Brand to Compare", ['All'] + brands, index=dorina_idx+1 if 'Dorina' in brands else 0, key='subcat_brand_compare')
    if selected_brand != 'All':
        filtered = subcat_df[subcat_df['brand_clean'] == selected_brand]
    else:
        filtered = subcat_df.copy()
    # --- KPI Tiles ---
    total_skus = len(filtered)
    n_brands = filtered['brand_clean'].nunique()
    avg_price = filtered['final_price'].mean()
    discounted = (filtered['discount_pct'] > 0).sum()
    pct_discounted = (discounted / total_skus * 100) if total_skus > 0 else 0
    avg_discount = filtered.loc[filtered['discount_pct'] > 0, 'discount_pct'].mean() if discounted > 0 else 0
    in_stock = (filtered['in_stock'] > 0).sum() if 'in_stock' in filtered.columns else 0
    pct_in_stock = (in_stock / total_skus * 100) if total_skus > 0 else 0
    top_color = filtered['color_clean'].mode()[0] if 'color_clean' in filtered.columns and not filtered['color_clean'].mode().empty else 'N/A'
    top_brand = filtered['brand_clean'].mode()[0] if not filtered['brand_clean'].mode().empty else 'N/A'
    # --- Comparative Visuals ---
    st.markdown("---")
    st.subheader("Brand vs. Subcategory Comparison")
    # --- Average Price by Brand (top 10 + selected) ---
    brand_counts = subcat_df['brand_clean'].value_counts()
    top_brands = brand_counts.head(10).index.tolist()
    if selected_brand != 'All' and selected_brand not in top_brands:
        top_brands.append(selected_brand)
    avg_price_by_brand = subcat_df[subcat_df['brand_clean'].isin(top_brands)].groupby('brand_clean')['final_price'].mean().reindex(top_brands)
    highlight_color = ['#e74c3c' if b == selected_brand else '#3498db' for b in avg_price_by_brand.index]
    fig_price = px.bar(x=avg_price_by_brand.index, y=avg_price_by_brand.values, color=avg_price_by_brand.index,
                      color_discrete_sequence=highlight_color,
                      labels={'x': 'Brand', 'y': 'Avg Price (€)'}, title="Average Price by Brand")
    st.plotly_chart(fig_price, use_container_width=True)
    # --- SKU Count by Brand (top 10 + selected) ---
    sku_count_by_brand = subcat_df[subcat_df['brand_clean'].isin(top_brands)].groupby('brand_clean').size().reindex(top_brands)
    fig_count = px.bar(x=sku_count_by_brand.index, y=sku_count_by_brand.values, color=sku_count_by_brand.index,
                      color_discrete_sequence=highlight_color,
                      labels={'x': 'Brand', 'y': 'SKU Count'}, title="SKU Count by Brand")
    st.plotly_chart(fig_count, use_container_width=True)
    # --- Color Mix (side-by-side barchart, absolute SKU count) ---
    st.markdown("**Color Mix (SKU Count)**")
    brand_color = filtered['color_clean'].value_counts()
    subcat_color = subcat_df['color_clean'].value_counts()
    color_index = list(set(brand_color.index).union(subcat_color.index))
    color_df = pd.DataFrame({selected_brand: brand_color.reindex(color_index, fill_value=0),
                            'Subcategory': subcat_color.reindex(color_index, fill_value=0)}, index=color_index)
    fig_color = px.bar(color_df.reset_index(), x='index', y=[selected_brand, 'Subcategory'], barmode='group',
                      labels={'value': 'SKU Count', 'index': 'Color'}, title="Color Mix (SKU Count): Brand vs. Subcategory")
    st.plotly_chart(fig_color, use_container_width=True)
    # --- Price Band Mix (side-by-side barchart) ---
    st.markdown("**Price Band Mix**")
    price_bins = [0, 20, 30, 40, 50, 60, 1e6]
    price_labels = ['<20€', '20-30€', '30-40€', '40-50€', '50-60€', '60€+']
    brand_band = pd.cut(filtered['final_price'], bins=price_bins, labels=price_labels, right=False)
    subcat_band = pd.cut(subcat_df['final_price'], bins=price_bins, labels=price_labels, right=False)
    band_df = pd.DataFrame({selected_brand: brand_band.value_counts(normalize=True).reindex(price_labels, fill_value=0),
                           'Subcategory': subcat_band.value_counts(normalize=True).reindex(price_labels, fill_value=0)}, index=price_labels)
    fig_band = px.bar(band_df.reset_index(), x='index', y=[selected_brand, 'Subcategory'], barmode='group',
                     labels={'value': 'Share', 'index': 'Price Band'}, title="Price Band Mix: Brand vs. Subcategory")
    st.plotly_chart(fig_band, use_container_width=True)
    # --- Metric Cards for Discount and In-Stock % ---
    st.markdown("---")
    st.subheader("Brand vs. Subcategory Metrics")
    subcat_avg_discount = subcat_df.loc[subcat_df['discount_pct'] > 0, 'discount_pct'].mean()
    subcat_in_stock = (subcat_df['in_stock'] > 0).sum() if 'in_stock' in subcat_df.columns else 0
    subcat_pct_in_stock = (subcat_in_stock / len(subcat_df) * 100) if len(subcat_df) > 0 else 0
    col1, col2 = st.columns(2)
    col1.metric("Avg Discount", f"{avg_discount:.1f}%", delta=f"vs {subcat_avg_discount:.1f}% subcat avg")
    col2.metric("% In Stock", f"{pct_in_stock:.1f}%", delta=f"vs {subcat_pct_in_stock:.1f}% subcat avg")
    # --- Raw Data Table ---
    st.markdown("---")
    st.subheader("Filtered Data Table")
    st.dataframe(filtered, use_container_width=True)

def all_dorina_products_table(df):
    """
    Streamlit interface for All Dorina Products Table.
    """
    st.markdown("---")
    st.header("All Dorina Products Table (Filterable)")
    dorina_df = df[df['brand_clean'].str.contains('Dorina', case=False, na=False)]
    
    # Define columns to display
    display_columns = [
        'best_name', 'category_clean', 'specific_category', 
        'final_price', 'price_per_item', 'pack_size', 'discount_pct', 
        'inventory', 'country_code'
    ]
    
    # Filter dorina_df to only include available columns
    available_columns = [col for col in display_columns if col in dorina_df.columns]
    
    styled = smart_style(
        dorina_df[available_columns]
        .sort_values(['category_clean', 'specific_category'])
    )
    st.dataframe(styled, use_container_width=True)

def download_data(df):
    """
    Streamlit interface for downloading data.
    """
    dorina_df = df[df['brand_clean'].str.contains('Dorina', case=False, na=False)]
    st.markdown("---")
    st.header("Download Data Slices")
    st.download_button(
        label="Download Dorina Data as CSV",
        data=dorina_df.to_csv(index=False),
        file_name="dorina_products.csv",
        mime="text/csv"
    )
    st.download_button(
        label="Download Full Cleaned Data as CSV",
        data=df.to_csv(index=False),
        file_name="cleaned_data.csv",
        mime="text/csv"
    )

def zalando_performance_tab(df):
    """
    Streamlit interface for Zalando Performance: ASP and discounts by category, brand, and subcategory.
    """
    st.header("Zalando Performance: ASP & Discounts by Category, Brand, and Subcategory")
    st.markdown("---")
    # ASP by Main Category
    st.subheader("Average Selling Price (ASP) by Main Category")
    cat_asp = df.groupby('category_clean')['final_price'].mean().round(2).sort_values(ascending=False)
    st.bar_chart(cat_asp)
    st.dataframe(cat_asp.reset_index().rename(columns={'final_price': 'ASP (€)'}).round(2), use_container_width=True)
    # ASP by Specific Category
    st.subheader("Average Selling Price (ASP) by Specific Category (Top 20)")
    subcat_asp = df.groupby('specific_category')['final_price'].mean().round(2).sort_values(ascending=False).head(20)
    st.bar_chart(subcat_asp)
    st.dataframe(subcat_asp.reset_index().rename(columns={'final_price': 'ASP (€)'}).round(2), use_container_width=True)
    st.markdown("---")
    # By Main Category
    st.subheader("Average Discount by Main Category")
    cat_discount = df.groupby('category_clean')['discount_pct'].mean().round(2).sort_values(ascending=False)
    st.bar_chart(cat_discount)
    st.dataframe(cat_discount.reset_index().rename(columns={'discount_pct': 'Avg Discount (%)'}).round(2), use_container_width=True)
    # By Brand
    st.subheader("Average Discount by Brand (Top 20)")
    brand_discount = df.groupby('brand_clean')['discount_pct'].mean().round(2).sort_values(ascending=False).head(20)
    st.bar_chart(brand_discount)
    st.dataframe(brand_discount.reset_index().rename(columns={'discount_pct': 'Avg Discount (%)'}).round(2), use_container_width=True)
    # By Specific Category
    st.subheader("Average Discount by Specific Category (Top 20)")
    subcat_discount = df.groupby('specific_category')['discount_pct'].mean().round(2).sort_values(ascending=False).head(20)
    st.bar_chart(subcat_discount)
    st.dataframe(subcat_discount.reset_index().rename(columns={'discount_pct': 'Avg Discount (%)'}).round(2), use_container_width=True)
    # Summary Table
    st.subheader("Discount Summary Table (Category x Brand)")
    summary = df.pivot_table(index='category_clean', columns='brand_clean', values='discount_pct', aggfunc='mean').round(2)
    st.dataframe(summary, use_container_width=True)

def brand_comparison_tab(df):
    st.header("Brand Comparison: Dorina vs Competitor")
    st.markdown("---")
    # Brand selection
    brands = sorted(df['brand_clean'].dropna().unique())
    default_brand1 = 'Dorina' if 'Dorina' in brands else brands[0]
    competitor_counts = df[df['brand_clean'].str.lower() != 'dorina']['brand_clean'].value_counts()
    default_brand2 = competitor_counts.index[0] if not competitor_counts.empty else brands[1] if len(brands) > 1 else brands[0]
    brand1 = st.selectbox("Select Brand 1", brands, index=brands.index(default_brand1))
    brand2 = st.selectbox("Select Brand 2", brands, index=brands.index(default_brand2))
    st.markdown(f"Comparing **{brand1}** vs **{brand2}**")
    comp_df = df[df['brand_clean'].isin([brand1, brand2])]

    # Product Count by Main Category
    st.subheader("Product Count by Main Category")
    cat_counts = comp_df.groupby(['category_clean', 'brand_clean']).size().reset_index(name='count')
    fig_cat = px.bar(cat_counts, x='category_clean', y='count', color='brand_clean', barmode='group', labels={'count': 'Product Count', 'category_clean': 'Main Category', 'brand_clean': 'Brand'})
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_cat, use_container_width=True)
    with col2:
        st.dataframe(cat_counts.pivot(index='category_clean', columns='brand_clean', values='count').fillna(0), use_container_width=True)

    # Product Count by Specific Category
    st.subheader("Product Count by Specific Category (Top 10)")
    subcat_counts = comp_df.groupby(['specific_category', 'brand_clean']).size().reset_index(name='count')
    top_subcats = subcat_counts.groupby('specific_category')['count'].sum().sort_values(ascending=False).head(10).index
    subcat_counts = subcat_counts[subcat_counts['specific_category'].isin(top_subcats)]
    fig_subcat = px.bar(subcat_counts, x='specific_category', y='count', color='brand_clean', barmode='group', labels={'count': 'Product Count', 'specific_category': 'Specific Category', 'brand_clean': 'Brand'})
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_subcat, use_container_width=True)
    with col2:
        st.dataframe(subcat_counts.pivot(index='specific_category', columns='brand_clean', values='count').fillna(0), use_container_width=True)

    # ASP Comparison
    st.subheader("Average Selling Price (ASP) by Main Category")
    asp = comp_df.groupby(['category_clean', 'brand_clean'])['final_price'].mean().reset_index()
    fig_asp = px.bar(asp, x='category_clean', y='final_price', color='brand_clean', barmode='group', labels={'final_price': 'ASP (€)', 'category_clean': 'Main Category', 'brand_clean': 'Brand'})
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_asp, use_container_width=True)
    with col2:
        st.dataframe(asp.pivot(index='category_clean', columns='brand_clean', values='final_price').round(2).fillna(0), use_container_width=True)

    # Discount Comparison
    st.subheader("Average Discount (%) by Main Category")
    disc = comp_df.groupby(['category_clean', 'brand_clean'])['discount_pct'].mean().reset_index()
    fig_disc = px.bar(disc, x='category_clean', y='discount_pct', color='brand_clean', barmode='group', labels={'discount_pct': 'Avg Discount (%)', 'category_clean': 'Main Category', 'brand_clean': 'Brand'})
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_disc, use_container_width=True)
    with col2:
        st.dataframe(disc.pivot(index='category_clean', columns='brand_clean', values='discount_pct').round(2).fillna(0), use_container_width=True)

    # Size Curve
    st.subheader("Size Curve (Available Sizes Count)")
    def get_size_counts(df, brand):
        size_counter = {}
        for sizes_json in df[df['brand_clean'] == brand]['sizes'].dropna():
            try:
                sizes = json.loads(sizes_json)
                for s in sizes:
                    if s.get('availability', True):
                        size_name = s.get('name', 'Unknown')
                        # Try to match 'NN/NN' (two digits only) first
                        match = re.match(r'^([0-9]{2}/[0-9]{2})', size_name)
                        if not match:
                            # Then try 'NNL'
                            match = re.match(r'^([0-9]+[A-Za-z]+)', size_name)
                        if not match:
                            # Then try just 'NN'
                            match = re.match(r'^([0-9]+)', size_name)
                        if match:
                            clean_size = match.group(1)
                            # If it's all digits and longer than 2, take first two digits
                            if clean_size.isdigit() and len(clean_size) > 2:
                                clean_size = clean_size[:2]
                        else:
                            # Then try any word (e.g., S, M, L, XL, 3XL)
                            match = re.match(r'^([A-Za-z0-9]+)', size_name)
                            clean_size = match.group(1) if match else size_name
                        size_counter[clean_size] = size_counter.get(clean_size, 0) + 1
            except Exception:
                continue
        return pd.Series(size_counter).sort_index()
    size_counts1 = get_size_counts(df, brand1)
    size_counts2 = get_size_counts(df, brand2)
    size_curve_df = pd.DataFrame({brand1: size_counts1, brand2: size_counts2}).fillna(0)
    fig_size = px.bar(size_curve_df, barmode='group', labels={'value': 'Count', 'index': 'Size'})
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_size, use_container_width=True)
    with col2:
        st.dataframe(size_curve_df, use_container_width=True)

    # Product Images
    st.subheader("Sample Products")
    for brand in [brand1, brand2]:
        st.markdown(f"**{brand}**")
        brand_products = comp_df[comp_df['brand_clean'] == brand].head(5)
        cols = st.columns(5)
        for i, (_, row) in enumerate(brand_products.iterrows()):
            with cols[i % 5]:
                img_url = row.get('main_image')
                if img_url and pd.notna(img_url) and str(img_url).startswith('http'):
                    st.image(img_url, width=120)
                st.caption(row['best_name'])

def brand_performance_tab(df):
    st.header("Brand Performance")
    st.markdown("---")
    brands = sorted(df['brand_clean'].dropna().unique())
    default_brand = brands.index('Dorina') if 'Dorina' in brands else 0
    brand = st.selectbox("Select Brand", brands, index=default_brand)
    brand_df = df[df['brand_clean'] == brand]

    # --- Product Mix by Category and Subcategory with Images ---
    st.subheader(f"{brand} Product Mix by Category & Subcategory")
    categories = brand_df['category_clean'].dropna().unique()
    for cat in sorted(categories):
        cat_df = brand_df[brand_df['category_clean'] == cat]
        st.markdown(f"### {cat}")
        subcats = cat_df['specific_category'].dropna().unique()
        for subcat in sorted(subcats):
            subcat_df = cat_df[cat_df['specific_category'] == subcat]
            st.markdown(f"**{subcat}**")
            # Tile images in a grid (max 5 per row)
            images = subcat_df[['main_image', 'best_name']].drop_duplicates().head(15)
            img_cols = st.columns(5)
            for idx, (img_url, name) in enumerate(images.values):
                with img_cols[idx % 5]:
                    if img_url and pd.notna(img_url) and str(img_url).startswith('http'):
                        st.image(img_url, width=100)
                    st.caption(str(name)[:40])

    # 1. In-stock % by SKU (product)
    st.subheader("In-stock % by SKU (Product)")
    sku_instock = {}
    for i, row in brand_df.iterrows():
        sku = row.get('sku') or row.get('SKU') or row.get('product_url') or str(i)
        sizes_json = row.get('sizes')
        if not sizes_json or pd.isna(sizes_json):
            continue
        try:
            sizes = json.loads(sizes_json)
            total = 0
            in_stock = 0
            for s in sizes:
                total += 1
                if s.get('availability', True):
                    in_stock += 1
            if total > 0:
                sku_instock[sku] = {
                    'in_stock': in_stock,
                    'total': total,
                    'in_stock_pct': round(in_stock / total * 100, 2),
                    'name': row.get('best_name', sku),
                    'main_image': row.get('main_image'),
                    'final_price': row.get('final_price'),
                    'discount_pct': row.get('discount_pct'),
                }
        except Exception:
            continue
    sku_instock_df = pd.DataFrame.from_dict(sku_instock, orient='index')
    sku_instock_df = sku_instock_df.sort_values('in_stock_pct', ascending=False)

    # Pie chart of in-stock rate buckets
    st.subheader("SKU In-stock Rate Distribution")
    def bucket_instock(pct):
        if pct == 100:
            return '100%'
        elif pct > 90:
            return '>90%'
        elif pct > 80:
            return '>80%'
        elif pct > 70:
            return '>70%'
        else:
            return '<70%'
    sku_instock_df['instock_bucket'] = sku_instock_df['in_stock_pct'].apply(bucket_instock)
    bucket_counts = sku_instock_df['instock_bucket'].value_counts().sort_index()
    import plotly.express as px
    fig_pie = px.pie(bucket_counts, names=bucket_counts.index, values=bucket_counts.values, title='SKU In-stock Rate Buckets')
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        st.dataframe(sku_instock_df[['name', 'in_stock', 'total', 'in_stock_pct', 'instock_bucket', 'final_price', 'discount_pct']], use_container_width=True)

    # Images for products with <60% in-stock rate
    st.subheader("Products with <60% In-stock Rate (Most Out of Stock)")
    low_instock_df = sku_instock_df[sku_instock_df['in_stock_pct'] < 60]
    if not low_instock_df.empty:
        for i, row in low_instock_df.head(10).iterrows():
            cols = st.columns([1, 3])
            with cols[0]:
                img_url = row.get('main_image')
                if img_url and pd.notna(img_url) and str(img_url).startswith('http'):
                    st.image(img_url, width=120)
                else:
                    st.write("No image")
            with cols[1]:
                st.markdown(f"**{row['name']}**")
                st.write(f"Price: €{row['final_price']:.2f}")
                st.write(f"In-stock: {row['in_stock']} / {row['total']} sizes ({row['in_stock_pct']}%)")
                st.write(f"Discount: {row['discount_pct']:.1f}%")
    else:
        st.info("No products with <60% in-stock rate.")

    # 2. Highlight products with severe discounting (>50%)
    st.subheader("Products with Severe Discounting (>50%)")
    severe_discount_df = brand_df[brand_df['discount_pct'] > 50].sort_values('discount_pct', ascending=False)
    if not severe_discount_df.empty:
        for i, row in severe_discount_df.head(10).iterrows():
            cols = st.columns([1, 3])
            with cols[0]:
                img_url = row.get('main_image')
                if img_url and pd.notna(img_url) and str(img_url).startswith('http'):
                    st.image(img_url, width=120)
                else:
                    st.write("No image")
            with cols[1]:
                st.markdown(f"**{row['best_name']}**")
                st.write(f"Price: €{row['final_price']:.2f}")
                st.write(f"Discount: {row['discount_pct']:.1f}%")
                st.write(f"Category: {row['category_clean']} | Subcategory: {row['specific_category']}")
    else:
        st.info("No products with >50% discount.")

    # 3. Summary stats
    st.subheader("Brand Summary Stats")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Products", f"{len(brand_df):,}")
    col2.metric("Avg Price", f"€{brand_df['final_price'].mean():.2f}")
    col3.metric("Avg Discount", f"{brand_df['discount_pct'].mean():.2f}%")
    col4.metric("# Categories", f"{brand_df['category_clean'].nunique()}")

def show_user_guide():
    st.markdown("""
    # 👋 Welcome to the Zalando Product Analytics Dashboard!
    
    **Here's what you can do in each tab:**
    
    - **Dashboard**: Executive summary, market share, average price, and deep-dive analytics for Dorina and competitors.
    - **Brand Performance**: Visualize assortment, in-stock %, severe discounting, and summary stats for a selected brand. Includes product images and mix by category/subcategory.
    - **Brand Comparison**: Side-by-side analysis of Dorina vs. a competitor: product counts, ASP, discounts, size curves, grouped bar charts, and tables.
    - **Zalando Performance**: Discounts and ASP by category, brand, and subcategory, with all numbers rounded to 2 decimals.
    - **Product Viewer**: Explore and filter all products, with images, prices, and details.
    
    **Tips:**
    - Use the sidebar to filter by brand, category, subcategory, and price.
    - Click the help button (❓) in the sidebar to view this guide again.
    - Hover over charts and tables for more details.
    """)

# --- Main App ---
def main():
    st.set_page_config(
        page_title="Zalando Product Analytics", 
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://docs.streamlit.io/',
            'Report a bug': None,
            'About': 'Zalando Product Analytics Dashboard'
        }
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 4rem;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1rem;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar help button
    with st.sidebar:
        if st.button("❓ User Guide"):
            st.session_state['show_guide'] = True
    # Show user guide modal on first load or when triggered
    if 'show_guide' not in st.session_state:
        st.session_state['show_guide'] = True
    if st.session_state['show_guide']:
        import streamlit.components.v1 as components
        with st.expander("User Guide", expanded=True):
            show_user_guide()
            if st.button("Close Guide"):
                st.session_state['show_guide'] = False
    df = load_data()
    # --- Tab order and names ---
    tab_labels = [
        "🏠 Dashboard",
        "📊 Brand Performance",
        "🤝 Brand Comparison",
        "📈 Zalando Performance",
        "🛍️ Product Viewer"
    ]
    tabs = st.tabs(tab_labels)
    with tabs[0]:
        dashboard_tab(df)
    with tabs[1]:
        brand_performance_tab(df)
    with tabs[2]:
        brand_comparison_tab(df)
    with tabs[3]:
        zalando_performance_tab(df)
    with tabs[4]:
        virtual_shopping_room(df)

if __name__ == "__main__":
    main() 