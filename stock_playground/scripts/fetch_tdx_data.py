
import os
import sys
from datetime import datetime, timedelta

# Add project root to path to import simple_quant
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from simple_quant.data.tdx_source import TDXSource

def main():
    # Configuration
    # Fetch past 5 years of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # Symbols to fetch (A-shares)
    # 600519.SS: Kweichow Moutai
    # 601318.SS: Ping An Insurance
    # 000001.SZ: Ping An Bank
    # 000300.SS: CSI 300 Index (Note: Indexes might need different handling in some APIs, 
    # but TDX treats them similarly often. Market code 1 for SH Index)
    symbols = ['600519.SS', '601318.SS', '000001.SZ']
    
    # Output directory
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data'))
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    print(f"--- Fetching TDX Data (5 Years: {start_date_str} to {end_date_str}) ---")
    
    source = TDXSource()
    
    if not source.available:
        print("Skipping download due to missing pytdx library.")
        return

    for symbol in symbols:
        source.fetch_and_save(symbol, data_dir, start_date=start_date_str, end_date=end_date_str)

if __name__ == "__main__":
    main()
