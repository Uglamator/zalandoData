import pandas as pd
from app import auto_clean_data

print("--- Starting pre-processing script ---")

# Define the complete list of columns that are essential for the dashboard
ESSENTIAL_COLUMNS = [
    'product_name', 'brand', 'brand_name', 'initial_price', 'final_price', 'in_stock', 
    'main_image', 'color', 'colors', 'sizes', 'discovery_input', 'name', 'product_url',
    'total', 'sku', 'inventory', 'country_code'
]
print(f"1. Defined {len(ESSENTIAL_COLUMNS)} essential columns.")

# Load only the essential columns from the correct raw data file
try:
    print("2. Attempting to load `bd_20250708_131602_0.csv`...")
    raw_df = pd.read_csv(
        'bd_20250708_131602_0.csv', 
        usecols=lambda c: c in ESSENTIAL_COLUMNS,
        low_memory=False
    )
    print("   - Success! Loaded the following columns:")
    print(f"     {raw_df.columns.tolist()}")

except Exception as e:
    print(f"   - FAILED to load CSV: {e}")
    exit()

# Clean the data
try:
    print("3. Running the data cleaning and processing pipeline...")
    cleaned_df = auto_clean_data(raw_df)
    print("   - Data cleaning complete.")
except Exception as e:
    print(f"   - FAILED during data cleaning: {e}")
    exit()


# Verification Step
print("4. Verifying final columns...")
final_columns = cleaned_df.columns.tolist()
print(f"   - Final columns are: {final_columns}")

if 'price_per_item' in final_columns and 'pack_size' in final_columns:
    print("   - SUCCESS! `price_per_item` and `pack_size` columns are present.")
else:
    print("   - FAILED! `price_per_item` or `pack_size` column is MISSING.")
    exit()


# Downcast numeric types to save memory
print("5. Optimizing memory usage...")
for col in cleaned_df.select_dtypes(include=['float64']).columns:
    cleaned_df[col] = pd.to_numeric(cleaned_df[col], downcast='float')
for col in cleaned_df.select_dtypes(include=['int64']).columns:
    cleaned_df[col] = pd.to_numeric(cleaned_df[col], downcast='integer')
print("   - Memory optimization complete.")

# Save the optimized and cleaned data to a new file
print("6. Saving the final `cleaned_zalando_data.csv` file...")
cleaned_df.to_csv('cleaned_zalando_data.csv', index=False)

print("\n--- Pre-processing finished successfully! ---")
print("You can now upload `cleaned_zalando_data.csv` to GitHub.") 