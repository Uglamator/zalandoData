import pandas as pd
from app import auto_clean_data

# Load the raw data from the local file
raw_df = pd.read_csv('bd_20250708_131602_0.csv')

# Clean the data
cleaned_df = auto_clean_data(raw_df)

# Save the cleaned data to a new file
cleaned_df.to_csv('cleaned_zalando_data.csv', index=False)

print("Pre-processing complete. `cleaned_zalando_data.csv` has been created.") 