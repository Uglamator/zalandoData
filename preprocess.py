import pandas as pd
from app import auto_clean_data

# Define the columns that are essential for the dashboard
ESSENTIAL_COLUMNS = [
    'product_name', 'brand', 'initial_price', 'final_price', 'in_stock', 
    'main_image', 'color', 'sizes', 'discovery_input', 'name', 'product_url',
    'category_clean', 'specific_category'
]

# Load only the essential columns from the correct raw data file
try:
    raw_df = pd.read_csv('bd_20250708_131602_0.csv', usecols=ESSENTIAL_COLUMNS)
except (ValueError, FileNotFoundError) as e:
    print(f"Error loading CSV: {e}")
    if isinstance(e, ValueError):
        print("One of the essential columns might be missing from your CSV.")
        print("Attempting to load the full CSV to show available columns...")
        full_df = pd.read_csv('bd_20250708_131602_0.csv')
        print("Available columns:", full_df.columns.tolist())
    # Exit or handle the error as needed
    exit()

# Clean the data
cleaned_df = auto_clean_data(raw_df)

# Downcast numeric types to save memory
for col in cleaned_df.select_dtypes(include=['float64']).columns:
    cleaned_df[col] = pd.to_numeric(cleaned_df[col], downcast='float')
for col in cleaned_df.select_dtypes(include=['int64']).columns:
    cleaned_df[col] = pd.to_numeric(cleaned_df[col], downcast='integer')

# Save the optimized and cleaned data to a new file
cleaned_df.to_csv('cleaned_zalando_data.csv', index=False)

print("Pre-processing complete. `cleaned_zalando_data.csv` has been created with optimized memory usage.") 