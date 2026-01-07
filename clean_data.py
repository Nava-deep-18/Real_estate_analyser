import pandas as pd
import os
import sys

def clean_file(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    print(f"Processing {filepath}...")
    try:
        df = pd.read_csv(filepath)
        initial_count = len(df)
        
        # Ensure numeric columns
        cols_to_numeric = ['Rent', 'Area', 'Bedrooms', 'Price']
        for col in cols_to_numeric:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop rows where critical data turned into NaN
        df.dropna(subset=[c for c in cols_to_numeric if c in df.columns], inplace=True)

        original_df = df.copy()
        
        if 'Area' in df.columns and 'Bedrooms' in df.columns:
            # Rule 1: Minimum Area per Bedroom (exclude tiny errors)
            # 5 BHK in 186 sqft -> 37 sqft/bedroom (Impossible)
            # Threshold: 150 sqft per bedroom is extemely conservative (600 sqft for 4bhk)
            df = df[df['Area'] / df['Bedrooms'] >= 150]
            
        if 'Rent' in df.columns and 'Area' in df.columns:
            # Rule 2: Minimum Rent per sq ft (exclude absurdly cheap rents)
            # 3000 rent for 1500 sqft -> 2 Rs/sqft. (Too low)
            # Threshold: 6 Rs/sqft
            df = df[df['Rent'] / df['Area'] >= 5]
            
        if 'Rent' in df.columns and 'Price' in df.columns:
            # Rule 3: Minimum Yield (Annual Rent / Price)
            # Exclude data where rent is disproportionately low compared to price
            # Threshold: 1% yield
            df['yield_temp'] = (df['Rent'] * 12) / df['Price']
            df = df[df['yield_temp'] >= 0.01]
            df.drop(columns=['yield_temp'], inplace=True)

        if 'Rent' in df.columns:
            # Rule 4: Absolute minimum rent
            df = df[df['Rent'] >= 3000]

        final_count = len(df)
        removed = initial_count - final_count
        
        if removed > 0:
            print(f"Removed {removed} invalid rows from {filepath}")
            # Show a sample of removed rows to verify logic
            removed_rows = original_df[~original_df.index.isin(df.index)]
            print("Sample removed data:")
            print(removed_rows[['Name', 'Rent', 'Area', 'Bedrooms', 'Price'] if 'Price' in removed_rows.columns else ['Name', 'Rent', 'Area']].head())
            
            df.to_csv(filepath, index=False)
            print(f"Saved cleaned file: {filepath}")
        else:
            print(f"No rows removed from {filepath}")
            
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

# Files to clean
files_to_clean = [
    'kolkata.csv',
    'kolkata_buy_vs_rent_full_analysis.csv',
    'buy_vs_rent_results.csv',
    'properties.csv',
    'properties_final.csv'
]

if __name__ == "__main__":
    for f in files_to_clean:
        clean_file(f)
    
    # Re-initialize the database
    sys.path.append(os.getcwd())
    try:
        from rag.db import init_db
        print("Re-initializing database...")
        init_db(reload=True)
        print("Database updated successfully.")
    except ImportError:
        print("Could not import init_db from rag.db")
    except Exception as e:
        print(f"Error initializing database: {e}")
