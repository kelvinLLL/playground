
import os
import sys
import argparse
from datetime import datetime, timedelta

# Add project root to path to import simple_quant
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import yfinance as yf
import pandas as pd
from simple_quant.data.tdx_source import TDXSource

def fetch_via_yahoo(symbol, start_date, end_date):
    """
    Fallback fetcher using yfinance
    """
    print(f"  [Yahoo] Fetching {symbol}...")
    try:
        # yfinance expects '600519.SS' format directly
        df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        if df.empty:
            return None
        
        # Check if columns are MultiIndex and flatten if necessary
        if isinstance(df.columns, pd.MultiIndex):
            # If MultiIndex, it's usually (Price, Ticker). We want Price level.
            # Example: ('Close', 'AAPL') -> 'Close'
            # Or sometimes levels are swapped.
            # Let's try to just drop the ticker level if it exists.
            try:
                df.columns = df.columns.droplevel(1)
            except:
                pass

        # Standardize columns
        # yfinance returns: Open, High, Low, Close, Adj Close, Volume
        # Our system expects: Open, High, Low, Close, Volume, Adj Close
        if 'Adj Close' not in df.columns:
            if 'Close' in df.columns:
                df['Adj Close'] = df['Close']
            
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
        # Filter only existing columns
        cols_to_use = [c for c in required_cols if c in df.columns]
        df = df[cols_to_use]
        
        return df
    except Exception as e:
        print(f"  [Yahoo] Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Fetch stock data from TDX with Yahoo fallback.')
    parser.add_argument('--sector', type=str, default='ai', choices=['ai', 'stable', 'all'], help='Sector to fetch data for (ai, stable, or all)')
    args = parser.parse_args()

    # Configuration
    # Fetch past 5 years of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # 1. AI & Hard Tech (10 Symbols)
    ai_symbols = [
        "002230.SZ", # iFlytek
        "601138.SS", # Foxconn Ind
        "300308.SZ", # Zhongji Innolight
        "688256.SS", # Cambricon
        "601360.SS", # 360 Security
        "000977.SZ", # Inspur Info
        "300418.SZ", # Kunlun Tech
        "002371.SZ", # Northern Huachuang
        "688981.SS", # SMIC
        "002415.SZ"  # Hikvision
    ]

    # 2. Stable & High Dividend
    stable_symbols = [
        "600900.SS", # Yangtze Power
        "601088.SS", # China Shenhua
        "600036.SS", # CM Bank
        "601398.SS", # ICBC
        "600519.SS"  # Moutai
    ]

    symbols_to_fetch = []
    output_subdir = ""

    if args.sector == 'ai':
        symbols_to_fetch = ai_symbols
        output_subdir = "ai"
    elif args.sector == 'stable':
        symbols_to_fetch = stable_symbols
        output_subdir = "stable"
    else:
        symbols_to_fetch = ai_symbols + stable_symbols
        output_subdir = "all" 

    # Output directory
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), f'../data/{output_subdir}'))
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    print(f"--- Fetching Data for Sector: {args.sector.upper()} ---")
    print(f"Range: {start_date_str} to {end_date_str}")
    
    # Init TDX Source
    tdx_source = TDXSource()
    tdx_available = tdx_source.available

    for symbol in symbols_to_fetch:
        output_path = os.path.join(data_dir, f"{symbol}.csv")
        
        # 1. Try TDX
        success = False
        if tdx_available:
            print(f"Attempting TDX for {symbol}...")
            try:
                # We reuse the logic from tdx_source but handle the save here to be uniform
                # Or just call fetch_daily_bars directly
                df = tdx_source.fetch_daily_bars(symbol, start_date_str, end_date_str, limit=1500)
                if not df.empty:
                    df.to_csv(output_path)
                    print(f"  > Saved (TDX): {output_path}")
                    success = True
            except Exception as e:
                print(f"  > TDX Failed: {e}")
        
        # 2. Fallback to Yahoo
        if not success:
            df = fetch_via_yahoo(symbol, start_date_str, end_date_str)
            if df is not None and not df.empty:
                df.to_csv(output_path)
                print(f"  > Saved (Yahoo): {output_path}")
                success = True
            else:
                print(f"  > FAILED: Could not fetch {symbol} from any source.")

if __name__ == "__main__":
    main()
