import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re
import json

# =====================
# Data Cleaning Helpers
# =====================
# Explicit mapping for main and specific categories
MAIN_CATEGORY_MAP = {
    # Bras
    'bh': 'Bras', 'bra': 'Bras', 'buegel': 'Bras', 'underwired-bra': 'Bras', 'triangle-bra': 'Bras', 'soft-bra': 'Bras', 'push-up-bra': 'Bras', 't-shirt-bra': 'Bras', 'balcony-bra': 'Bras', 'strapless-bra': 'Bras',
    # Underwear
    'briefs': 'Underwear', 'panties': 'Underwear', 'period-panties': 'Underwear', 'g-strings': 'Underwear', 'slip': 'Underwear',
    # Shapewear
    'shapewear': 'Shapewear', 'body': 'Shapewear', 'bustier': 'Shapewear', 'corset': 'Shapewear',
    # Sports
    'sports-bra': 'Sports Bras',
    # Tops
    'tank': 'Tops', 'top': 'Tops', 'sweater': 'Tops', 'undershirts': 'Tops',
    # Bodies
    'bodies': 'Bodies',
    # Suspenders
    'suspenders': 'Suspenders',
    # Jeans/Bottoms
    'jean': 'Bottoms',
    # Fallbacks
    'womens-clothing-lingerie-bodies': 'Bodies', 'women-clothing-underwear-undershirts': 'Tops', 'women-clothing-underwear-suspenders': 'Suspenders', 'women-clothing-underwear-corset': 'Shapewear',
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
    'panty': 'Panty',
    'panties': 'Panty',
    'tanga': 'Tanga',
    'hipster': 'Hipster',
    'brazilian': 'Brazilian',
    'string': 'String',
    'g-string': 'G-String',
    'g-strings': 'G-String',
    'thong': 'Thong',
    'slip': 'Slip',
    'boxer': 'Boxer',
    'boxers': 'Boxer',
    'shorts': 'Shorts',
    'boyshort': 'Boyshort',
    'boyshorts': 'Boyshort',
    'period-panties': 'Period Panties',
    # Shapewear
    'shapewear': 'Shapewear',
    'body': 'Body',
    'bodies': 'Body',
    'corset': 'Corset',
    'girdle': 'Girdle',
    'waist-cincher': 'Waist Cincher',
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
    'nightshirt': 'Nightshirt',
    'nightwear': 'Nightwear',
    'babydoll': 'Babydoll',
    'chemise': 'Chemise',
    'robe': 'Robe',
    'dressing-gown': 'Robe',
    # Hosiery
    'tights': 'Tights',
    'stockings': 'Stockings',
    'hold-ups': 'Hold-Ups',
    'socks': 'Socks',
    'knee-highs': 'Knee Highs',
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
    'garter-belt': 'Garter Belt',
    'pasties': 'Pasties',
    'accessories': 'Accessories',
}

def extract_main_category(text):
    """Assign main category using explicit keyword mapping."""
    if not isinstance(text, str):
        return 'Unknown'
    text = text.lower()
    for key, val in MAIN_CATEGORY_MAP.items():
        if key in text:
            return val
    return 'Other'

def extract_specific_category(text):
    """Assign specific category using explicit keyword mapping, handling JSON with 'url'."""
    if not isinstance(text, str):
        return 'Unknown'
    # Try to extract slug from JSON with 'url'
    slug = ''
    try:
        if text.startswith('{'):
            d = json.loads(text)
            url = d.get('url', '')
            if url:
                parts = [p for p in url.split('/') if p]
                slug = parts[-2] if parts and parts[-1].endswith('.html') and len(parts) > 1 else (parts[-1] if parts else '')
        else:
            # If not JSON, treat as path or slug
            parts = re.split(r'[/\\-]', text)
            slug = parts[-1] if parts else text
    except Exception:
        slug = text
    slug = slug.lower()
    # Try mapping
    for key, val in SPECIFIC_CATEGORY_MAP.items():
        if key in slug:
            return val
    # Fallback: clean up slug
    return slug.replace('-', ' ').replace('_', ' ').title() if slug else 'Unknown'

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
    # Use keyword mapping on discovery_input for category extraction
    if 'discovery_input' in df.columns:
        df['main_category'] = df['discovery_input'].apply(lambda x: extract_main_category(str(x)))
        df['category_clean'] = df['main_category']
        df['specific_category'] = df['discovery_input'].apply(lambda x: extract_specific_category(str(x)))
    else:
        df['main_category'] = 'Unknown'
        df['category_clean'] = 'Unknown'
        df['specific_category'] = 'Unknown'
    return df

def clean_color_column(df):
    basic_color_map = {
        'schwarz': 'Black', 'black': 'Black', 'noir': 'Black',
        'weiß': 'White', 'weiss': 'White', 'white': 'White',
        'blau': 'Blue', 'navy': 'Blue', 'blue': 'Blue',
        'rot': 'Red', 'red': 'Red',
        'rosa': 'Pink', 'pink': 'Pink',
        'beige': 'Beige',
        'braun': 'Brown', 'brown': 'Brown',
        'grün': 'Green', 'green': 'Green',
        'gelb': 'Yellow', 'yellow': 'Yellow',
        'lila': 'Purple', 'purple': 'Purple',
        'grau': 'Grey', 'gray': 'Grey', 'grey': 'Grey',
        'orange': 'Orange',
        'multi': 'Multicolor', 'mehrfarbig': 'Multicolor', 'multicolor': 'Multicolor',
        'silber': 'Silver', 'silver': 'Silver',
        'gold': 'Gold',
        'khaki': 'Khaki',
        'oliv': 'Olive', 'olive': 'Olive',
        'bordeaux': 'Burgundy', 'burgundy': 'Burgundy',
        'creme': 'Cream', 'cream': 'Cream',
        'mint': 'Mint',
        'coral': 'Coral',
        'turquoise': 'Turquoise', 'türkis': 'Turquoise',
        'camel': 'Camel',
        'ivory': 'Ivory',
        'peach': 'Peach',
        'apricot': 'Apricot',
        'taupe': 'Taupe',
        'stone': 'Stone',
        'sand': 'Sand',
        'offwhite': 'White', 'off-white': 'White',
        'anthrazit': 'Anthracite',
        'petrol': 'Petrol',
        'fuchsia': 'Fuchsia',
        'magenta': 'Magenta',
        'cyan': 'Cyan',
        'aubergine': 'Aubergine',
        'mauve': 'Mauve',
        'powder': 'Powder',
        'crystal': 'Crystal',
        'denim': 'Blue',
        'print': 'Print',
    }
    def map_color(raw_color):
        if pd.isna(raw_color):
            return 'Unknown'
        raw_color = str(raw_color).lower().strip()
        if raw_color in basic_color_map:
            return basic_color_map[raw_color]
        for part in re.split(r'[ ,/]+', raw_color):
            if part in basic_color_map:
                return basic_color_map[part]
        return raw_color.split()[0].capitalize() if raw_color else 'Unknown'
    if 'color' in df.columns:
        df['standard_color'] = df['color'].apply(map_color)
    elif 'colors' in df.columns:
        df['standard_color'] = df['colors'].apply(map_color)
    else:
        df['standard_color'] = 'Unknown'
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
    return df

RAW_CSV = 'https://github.com/Uglamator/zalandoData/releases/download/v1.0/bd_20250708_131602_0.csv'
CLEANED_CSV = 'https://github.com/Uglamator/zalandoData/releases/download/v1.0/cleaned_data.csv'

def ensure_cleaned_data():
    """
    Always clean the raw CSV and save as cleaned_data.csv on every run.
    """
    st.info('Cleaning raw data, please wait...')
    raw_df = pd.read_csv(RAW_CSV)
    cleaned_df = auto_clean_data(raw_df)
    #cleaned_df.to_csv(CLEANED_CSV, index=False)
    st.success('Data cleaned and saved to cleaned_data.csv!')

@st.cache_data
def load_data():
    ensure_cleaned_data()
    df = pd.read_csv(CLEANED_CSV)
    df = auto_clean_data(df)
    return df

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

def virtual_shopping_room(df):
    """
    Streamlit interface for the Virtual Shopping Room.
    """
    st.header("Image Comparison")
    # Price slider with capped range
    min_price = float(df['final_price'].min())
    max_price = float(df['final_price'].max())
    slider_max = 50.0 if max_price > 50 else max_price
    price_range = st.slider("Select price range (€)", min_value=min_price, max_value=slider_max, value=(min_price, slider_max), step=1.0)
    show_50plus = st.checkbox("Show products above €50", value=False)
    # --- Category buttons as grid ---
    categories = sorted(df['category_clean'].dropna().unique())
    if 'selected_categories' not in st.session_state:
        st.session_state['selected_categories'] = set()
    selected_categories = st.session_state['selected_categories']
    st.write("**Selected Categories:**", ', '.join(selected_categories) if selected_categories else 'None')
    st.write("**Categories:**")
    cat_cols = st.columns(4)
    for i, cat in enumerate(categories):
        col = cat_cols[i % 4]
        if cat in selected_categories:
            if col.button(f"✅ {cat}", key=f"catbtn_{cat}"):
                selected_categories.remove(cat)
                # Reset subcategories if parent category is removed
                subcategories_for_cat = set(df[df['category_clean'] == cat]['specific_category'].dropna().unique())
                st.session_state['selected_subcategories'] = st.session_state.get('selected_subcategories', set()) - subcategories_for_cat
                st.session_state['selected_categories'] = selected_categories
                st.rerun()
        else:
            if col.button(cat, key=f"catbtn_{cat}"):
                selected_categories.add(cat)
                st.session_state['selected_categories'] = selected_categories
                st.rerun()
    # --- Subcategory buttons as grid ---
    subcategories = sorted(df[df['category_clean'].isin(selected_categories)]['specific_category'].dropna().unique()) if selected_categories else []
    if 'selected_subcategories' not in st.session_state:
        st.session_state['selected_subcategories'] = set()
    # Remove any selected subcategories that are no longer valid
    st.session_state['selected_subcategories'] = set([s for s in st.session_state['selected_subcategories'] if s in subcategories])
    selected_subcategories = st.session_state['selected_subcategories']
    st.write("**Selected Subcategories:**", ', '.join(selected_subcategories) if selected_subcategories else 'None')
    st.write("**Subcategories:**")
    subcat_cols = st.columns(4)
    for i, subcat in enumerate(subcategories):
        col = subcat_cols[i % 4]
        if subcat in selected_subcategories:
            if col.button(f"✅ {subcat}", key=f"subcatbtn_{subcat}"):
                selected_subcategories.remove(subcat)
                st.session_state['selected_subcategories'] = selected_subcategories
                st.rerun()
        else:
            if col.button(subcat, key=f"subcatbtn_{subcat}"):
                selected_subcategories.add(subcat)
                st.session_state['selected_subcategories'] = selected_subcategories
                st.rerun()
    # --- Brands as multiselect ---
    brands = sorted(df['brand_clean'].dropna().unique())
    # No brands selected by default
    selected_brands = st.multiselect("Select brands", brands, default=[])
    if not selected_brands:
        selected_brands = brands  # Select all brands if none are selected
    # --- Filtering logic ---
    if show_50plus:
        filtered = df[
            ((df['final_price'] >= price_range[0]) & (df['final_price'] <= price_range[1])) |
            (df['final_price'] > 50)
        ]
    else:
        filtered = df[
            (df['final_price'] >= price_range[0]) &
            (df['final_price'] <= price_range[1])
        ]
    if selected_categories:
        filtered = filtered[filtered['category_clean'].isin(selected_categories)]
    if selected_subcategories:
        filtered = filtered[filtered['specific_category'].isin(selected_subcategories)]
    filtered = filtered[filtered['brand_clean'].isin(selected_brands)]
    st.write(f"Showing {min(10, len(filtered))} of {len(filtered)} products")
    # Show up to 10 images with name, price, discount
    for i, row in filtered.head(10).iterrows():
        cols = st.columns([1, 3])
        with cols[0]:
            img_url = row.get('main_image')
            if img_url and pd.notna(img_url) and str(img_url).startswith('http'):
                st.image(img_url, width=120)
            else:
                st.write("No image")
        with cols[1]:
            st.markdown(f"**{row['best_name']}**")
            st.write(f"€{row['final_price']:.2f}")
            st.write(f"Discount: {row['discount_pct']:.1f}%")
            st.write(f"{row['category_clean']} | {row['specific_category']} | {row['brand_clean']}")
    if len(filtered) == 0:
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
    brand_prices = df[df['brand_clean'].isin(top_brands_by_count)].groupby('brand_clean')['final_price'].mean().reindex(top_brands_by_count)
    dorina_price = df[df['brand_clean'].str.lower() == 'dorina']['final_price'].mean()
    brand_prices = brand_prices.fillna(dorina_price)
    fig2 = px.bar(
        x=brand_prices.index,
        y=brand_prices.values,
        color=["Dorina" if "dorina" in str(b).lower() else "Other" for b in brand_prices.index],
        color_discrete_map={"Dorina": "#e74c3c", "Other": "#3498db"},
        labels={'x': 'Brand', 'y': 'Average Price (€)'},
        title="Average Price by Brand (Dorina Highlighted)"
    )
    st.plotly_chart(fig2, use_container_width=True)
    brand_price_table = pd.DataFrame({'Brand': brand_prices.index, 'Avg_Price': brand_prices.values})
    st.dataframe(smart_style(brand_price_table), use_container_width=True)

def category_deep_dives(df):
    """
    Streamlit interface for Category Deep Dives.
    """
    st.markdown("---")
    st.header("Category Deep Dives")
    selected_category = st.selectbox("Select a main category to deep dive:", sorted(df['category_clean'].dropna().unique()))
    cat_df = df[df['category_clean'] == selected_category]
    dorina_cat_df = cat_df[cat_df['brand_clean'].str.contains('Dorina', case=False, na=False)]
    # Market share in category
    cat_brand_counts = cat_df['brand_clean'].value_counts().head(10)
    dorina_cat_count = cat_df[cat_df['brand_clean'].str.lower() == 'dorina'].shape[0]
    cat_brand_counts = ensure_dorina_in_series(cat_brand_counts, dorina_cat_count)
    fig3 = px.bar(
        x=cat_brand_counts.index,
        y=cat_brand_counts.values,
        color=["Dorina" if "dorina" in str(b).lower() else "Other" for b in cat_brand_counts.index],
        color_discrete_map={"Dorina": "#e74c3c", "Other": "#3498db"},
        labels={'x': 'Brand', 'y': 'Number of Products'},
        title=f"Product Count by Brand in {selected_category} (Dorina Highlighted)"
    )
    st.plotly_chart(fig3, use_container_width=True)
    cat_brand_table = pd.DataFrame({'Brand': cat_brand_counts.index, 'Product_Count': cat_brand_counts.values})
    st.dataframe(smart_style(cat_brand_table), use_container_width=True)

    # NEW: Granular category breakdown within main category
    st.subheader(f"Breakdown of Specific Categories in {selected_category}")
    spec_breakdown = cat_df.groupby('specific_category').agg(
        Total_Products=('final_price', 'count'),
        Dorina_Products=('brand_clean', lambda x: (x.str.lower() == 'dorina').sum()),
        Avg_Price=('final_price', 'mean')
    ).sort_values('Total_Products', ascending=False).reset_index()
    spec_breakdown['Dorina_Share_%'] = (spec_breakdown['Dorina_Products'] / spec_breakdown['Total_Products'] * 100).round(1)
    st.dataframe(spec_breakdown, use_container_width=True)

    # Price distribution in category (by brand)
    fig4 = px.box(
        cat_df,
        x='brand_clean',
        y='final_price',
        color=cat_df['brand_clean'].apply(lambda x: 'Dorina' if 'dorina' in str(x).lower() else 'Other'),
        color_discrete_map={"Dorina": "#e74c3c", "Other": "#3498db"},
        points="all",
        labels={'brand_clean': 'Brand', 'final_price': 'Price (€)'},
        title=f"Price Distribution by Brand in {selected_category} (Dorina Highlighted)"
    )
    st.plotly_chart(fig4, use_container_width=True)
    # Table for price distribution
    cat_price_table = cat_df.groupby('brand_clean')['final_price'].agg(['count', 'mean', 'min', 'max']).reset_index()
    cat_price_table = ensure_dorina_in_df(cat_price_table, {
        'brand_clean': 'Dorina',
        'count': dorina_cat_df.shape[0],
        'mean': dorina_cat_df['final_price'].mean(),
        'min': dorina_cat_df['final_price'].min(),
        'max': dorina_cat_df['final_price'].max()
    })
    st.dataframe(smart_style(cat_price_table), use_container_width=True)
    # Dorina vs Market Table (main category)
    table = cat_df.groupby('brand_clean').agg(
        Product_Count=('final_price', 'count'),
        Avg_Price=('final_price', 'mean'),
        Avg_Discount=('discount_pct', 'mean')
    ).sort_values('Product_Count', ascending=False).head(10).reset_index()
    table = ensure_dorina_in_df(table, {
        'brand_clean': 'Dorina',
        'Product_Count': dorina_cat_df.shape[0],
        'Avg_Price': dorina_cat_df['final_price'].mean(),
        'Avg_Discount': dorina_cat_df['discount_pct'].mean()
    })
    if 'brand_clean' in table.columns:
        st.dataframe(smart_style(table).apply(highlight_dorina, axis=1), use_container_width=True)
    else:
        st.dataframe(smart_style(table), use_container_width=True)

    # --- Color Analysis for Main Category ---
    st.subheader(f"Color Analysis in {selected_category}")
    cat_color_counts = cat_df['standard_color'].value_counts().head(15)
    dorina_cat_color_counts = dorina_cat_df['standard_color'].value_counts().head(15)
    fig_cat_color = px.bar(
        x=cat_color_counts.index,
        y=cat_color_counts.values,
        color=cat_color_counts.index,
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={'x': 'Color', 'y': 'Number of Products'},
        title=f"Top Colors in {selected_category} (Market)"
    )
    st.plotly_chart(fig_cat_color, use_container_width=True)
    st.dataframe(smart_style(pd.DataFrame({'Color': cat_color_counts.index, 'Product_Count': cat_color_counts.values})), use_container_width=True)
    fig_dorina_cat_color = px.bar(
        x=dorina_cat_color_counts.index,
        y=dorina_cat_color_counts.values,
        color=dorina_cat_color_counts.index,
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={'x': 'Color', 'y': 'Number of Dorina Products'},
        title=f"Top Colors in {selected_category} (Dorina)"
    )
    st.plotly_chart(fig_dorina_cat_color, use_container_width=True)
    st.dataframe(smart_style(pd.DataFrame({'Color': dorina_cat_color_counts.index, 'Dorina_Product_Count': dorina_cat_color_counts.values})), use_container_width=True)

def deep_dive_by_specific_category(df):
    """
    Streamlit interface for Deep Dive by Specific Category.
    """
    st.markdown("---")
    st.header("Deep Dive by Specific Category")
    # Always get all unique specific categories and let user select
    all_specific = sorted(df['specific_category'].dropna().unique())
    selected_specific = st.selectbox("Select a specific category to deep dive:", all_specific, key='specific_category_deepdive')
    spec_df = df[df['specific_category'] == selected_specific]
    dorina_spec_df = spec_df[spec_df['brand_clean'].str.contains('Dorina', case=False, na=False)]
    # Market share in specific category
    spec_brand_counts = spec_df['brand_clean'].value_counts().head(10)
    dorina_spec_count = spec_df[spec_df['brand_clean'].str.lower() == 'dorina'].shape[0]
    spec_brand_counts = ensure_dorina_in_series(spec_brand_counts, dorina_spec_count)
    fig5 = px.bar(
        x=spec_brand_counts.index,
        y=spec_brand_counts.values,
        color=["Dorina" if "dorina" in str(b).lower() else "Other" for b in spec_brand_counts.index],
        color_discrete_map={"Dorina": "#e74c3c", "Other": "#3498db"},
        labels={'x': 'Brand', 'y': 'Number of Products'},
        title=f"Product Count by Brand in {selected_specific} (Dorina Highlighted)"
    )
    st.plotly_chart(fig5, use_container_width=True)
    spec_brand_table = pd.DataFrame({'Brand': spec_brand_counts.index, 'Product_Count': spec_brand_counts.values})
    st.dataframe(smart_style(spec_brand_table), use_container_width=True)
    # Price distribution in specific category
    fig6 = px.box(
        spec_df,
        x='brand_clean',
        y='final_price',
        color=spec_df['brand_clean'].apply(lambda x: 'Dorina' if 'dorina' in str(x).lower() else 'Other'),
        color_discrete_map={"Dorina": "#e74c3c", "Other": "#3498db"},
        points="all",
        labels={'brand_clean': 'Brand', 'final_price': 'Price (€)'},
        title=f"Price Distribution by Brand in {selected_specific} (Dorina Highlighted)"
    )
    st.plotly_chart(fig6, use_container_width=True)
    # Table for price distribution
    spec_price_table = spec_df.groupby('brand_clean')['final_price'].agg(['count', 'mean', 'min', 'max']).reset_index()
    spec_price_table = ensure_dorina_in_df(spec_price_table, {
        'brand_clean': 'Dorina',
        'count': dorina_spec_df.shape[0],
        'mean': dorina_spec_df['final_price'].mean(),
        'min': dorina_spec_df['final_price'].min(),
        'max': dorina_spec_df['final_price'].max()
    })
    st.dataframe(smart_style(spec_price_table), use_container_width=True)
    # Dorina vs Market Table (specific category)
    table2 = spec_df.groupby('brand_clean').agg(
        Product_Count=('final_price', 'count'),
        Avg_Price=('final_price', 'mean'),
        Avg_Discount=('discount_pct', 'mean')
    ).sort_values('Product_Count', ascending=False).head(10).reset_index()
    table2 = ensure_dorina_in_df(table2, {
        'brand_clean': 'Dorina',
        'Product_Count': dorina_spec_df.shape[0],
        'Avg_Price': dorina_spec_df['final_price'].mean(),
        'Avg_Discount': dorina_spec_df['discount_pct'].mean()
    })
    if 'brand_clean' in table2.columns:
        st.dataframe(smart_style(table2).apply(highlight_dorina, axis=1), use_container_width=True)
    else:
        st.dataframe(smart_style(table2), use_container_width=True)

    # --- Color Analysis for Specific Category ---
    st.subheader(f"Color Analysis in {selected_specific}")
    spec_color_counts = spec_df['standard_color'].value_counts().head(15)
    dorina_spec_color_counts = dorina_spec_df['standard_color'].value_counts().head(15)
    fig_spec_color = px.bar(
        x=spec_color_counts.index,
        y=spec_color_counts.values,
        color=spec_color_counts.index,
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={'x': 'Color', 'y': 'Number of Products'},
        title=f"Top Colors in {selected_specific} (Market)"
    )
    st.plotly_chart(fig_spec_color, use_container_width=True)
    st.dataframe(smart_style(pd.DataFrame({'Color': spec_color_counts.index, 'Product_Count': spec_color_counts.values})), use_container_width=True)
    fig_dorina_spec_color = px.bar(
        x=dorina_spec_color_counts.index,
        y=dorina_spec_color_counts.values,
        color=dorina_spec_color_counts.index,
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={'x': 'Color', 'y': 'Number of Dorina Products'},
        title=f"Top Colors in {selected_specific} (Dorina)"
    )
    st.plotly_chart(fig_dorina_spec_color, use_container_width=True)
    st.dataframe(smart_style(pd.DataFrame({'Color': dorina_spec_color_counts.index, 'Dorina_Product_Count': dorina_spec_color_counts.values})), use_container_width=True)

def all_dorina_products_table(df):
    """
    Streamlit interface for All Dorina Products Table.
    """
    st.markdown("---")
    st.header("All Dorina Products Table (Filterable)")
    dorina_df = df[df['brand_clean'].str.contains('Dorina', case=False, na=False)]
    styled = smart_style(
        dorina_df[['best_name', 'category_clean', 'specific_category', 'final_price', 'discount_pct', 'inventory', 'country_code']]
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
    cat_asp = df.groupby('main_category')['final_price'].mean().round(2).sort_values(ascending=False)
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
    cat_discount = df.groupby('main_category')['discount_pct'].mean().round(2).sort_values(ascending=False)
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
    summary = df.pivot_table(index='main_category', columns='brand_clean', values='discount_pct', aggfunc='mean').round(2)
    st.dataframe(summary, use_container_width=True)

def main():
    st.set_page_config(page_title="Zalando Underwear Summary", layout="wide")
    st.title("Zalando Underwear Summary")
    st.markdown("---")
    df = load_data()
    # Add Zalando Performance tab
    tab_labels = ["Product Viewer", "Dashboard", "Zalando Performance"]
    if 'selected_tab' not in st.session_state:
        st.session_state['selected_tab'] = 0
    selected_tab = st.radio("Select dashboard section:", tab_labels, index=st.session_state['selected_tab'], horizontal=True, key='tab_radio')
    st.session_state['selected_tab'] = tab_labels.index(selected_tab)
    if selected_tab == tab_labels[0]:
        virtual_shopping_room(df)
    elif selected_tab == tab_labels[1]:
        executive_summary(df)
        market_share_by_brand(df)
        average_price_by_brand(df)
        category_deep_dives(df)
        deep_dive_by_specific_category(df)
        all_dorina_products_table(df)
        download_data(df)
    elif selected_tab == tab_labels[2]:
        zalando_performance_tab(df)

if __name__ == "__main__":
    main() 