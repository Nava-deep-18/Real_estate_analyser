import pandas as pd

def analyze_data(filepath):
    try:
        df = pd.read_csv(filepath)
        print(f"--- Analysis of {filepath} ---")
        
        # 1. Area per Bedroom
        if 'Area' in df.columns and 'Bedrooms' in df.columns:
            df['Area_per_Bed'] = df['Area'] / df['Bedrooms']
            print("\nArea per Bedroom Stats:")
            print(df['Area_per_Bed'].describe())
            print("\nSmallest Area per Bedroom entries:")
            print(df.sort_values('Area_per_Bed')[['Name', 'Bedrooms', 'Area', 'Area_per_Bed']].head(10))

        # 2. Rent Yield (Annual Rent / Price)
        if 'Rent' in df.columns and 'Price' in df.columns:
            df['Yield'] = (df['Rent'] * 12) / df['Price']
            print("\nRental Yield Stats:")
            print(df['Yield'].describe())
            print("\nLowest Yield entries:")
            print(df.sort_values('Yield')[['Name', 'Price', 'Rent', 'Yield']].head(10))

        # 3. Rent absolute values
        if 'Rent' in df.columns:
            print("\nRent Stats:")
            print(df['Rent'].describe())
            print("\nLowest Rent entries:")
            print(df.sort_values('Rent')[['Name', 'Rent', 'Bedrooms']].head(10))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_data("kolkata_buy_vs_rent_full_analysis.csv")
