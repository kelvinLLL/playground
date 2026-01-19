
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

def fetch_data(symbol, start_date, end_date, output_dir):
    """
    Fetches daily data for a given symbol and saves it to CSV.
    """
    print(f"Fetching data for {symbol} from {start_date} to {end_date}...")
    
    # Download data
    df = yf.download(symbol, start=start_date, end=end_date)
    
    if df.empty:
        print(f"No data found for {symbol}")
        return

    # Ensure index is datetime
    df.index = pd.to_datetime(df.index)
    
    # Flatten MultiIndex columns if present (common in new yfinance versions)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Standardize columns to: Open, High, Low, Close, Volume, Adj Close
    # yfinance returns: Open, High, Low, Close, Adj Close, Volume
    # We need to ensure they match what HistoricCSVDataHandler expects
    
    # Check if 'Adj Close' exists, if not, copy 'Close'
    if 'Adj Close' not in df.columns:
        df['Adj Close'] = df['Close']
        
    # Reorder and select columns
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
    
    # Filter only available columns
    available_cols = [c for c in required_cols if c in df.columns]
    
    # If any required column is missing, warn but proceed
    missing = set(required_cols) - set(available_cols)
    if missing:
        print(f"Warning: Missing columns {missing} for {symbol}")
        
    df = df[available_cols]

    # Save to CSV
    output_path = os.path.join(output_dir, f"{symbol}.csv")
    df.to_csv(output_path)
    print(f"Saved to {output_path}")

def main():
    # Define A-share symbols (Yahoo Finance format)
    # 600519.SS = Kweichow Moutai
    # 000001.SS = Ping An Bank (Note: 000001 is usually Shenzhen, 
    # but 000001.SS is the index? No, Ping An is 000001.SZ usually.
    # Let's check common mappings. 
    # 600519.SS is Shanghai.
    # 000001.SZ is Shenzhen (Ping An).
    # 000001.SS is Shanghai Composite Index?
    # Let's stick to stocks.
    # 601318.SS = Ping An Insurance (Group) Company of China, Ltd.
    
    symbols = ['600519.SS', '601318.SS'] 
    
    # Data directory
    data_dir = os.path.abspath(os.path.join(os.path.dirname('__file__'), '../data'))
    # Adjust path if running from root or scripts folder
    # simpler: just use relative path from where we run or absolute path
    # We will assume running from project root usually, but let's be robust.
    # If this script is in scripts/, ../data is correct relative to script.
    
    # But wait, __file__ might be weird in some contexts. 
    # Let's just use hardcoded relative path assuming execution from root
    if not os.path.exists("./data"):
        os.makedirs("./data")
        
    start_date = "2024-01-01"
    end_date = "2024-12-31" # Or today
    
    for s in symbols:
        fetch_data(s, start_date, end_date, "./data")

if __name__ == "__main__":
    main()
