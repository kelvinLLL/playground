
import yfinance as yf
import pandas as pd

try:
    print("Testing Yahoo Finance connection...")
    # Fetch Moutai (600519.SS)
    ticker = yf.Ticker("600519.SS")
    hist = ticker.history(period="5d")
    
    if not hist.empty:
        print("Success! Data fetched:")
        print(hist.head())
    else:
        print("Failed: Empty data returned.")
except Exception as e:
    print(f"Failed: {e}")
