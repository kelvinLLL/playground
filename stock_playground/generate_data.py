import pandas as pd
import numpy as np
import os

def generate_random_walk(symbol, start_price=100, days=1500, seed=42):
    np.random.seed(seed)
    dates = pd.date_range(start='2020-01-01', periods=days, freq='B')
    returns = np.random.normal(loc=0.0002, scale=0.02, size=days) # Slight drift
    price_path = start_price * (1 + returns).cumprod()
    
    df = pd.DataFrame(index=dates)
    df['Close'] = price_path
    df['Open'] = price_path * (1 + np.random.normal(0, 0.005, days))
    df['High'] = df[['Open', 'Close']].max(axis=1) * (1 + np.abs(np.random.normal(0, 0.005, days)))
    df['Low'] = df[['Open', 'Close']].min(axis=1) * (1 - np.abs(np.random.normal(0, 0.005, days)))
    df['Volume'] = np.random.randint(1000000, 5000000, days)
    df['Adj Close'] = df['Close']
    df.index.name = 'Date'
    
    return df

def main():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    symbols = [
        # Large Cap / Stable
        ("600519.SS", 1500.0, 42),  # Moutai-like
        ("601318.SS", 50.0, 123),   # PingAn-like
        ("000001.SZ", 15.0, 999),   # Bank-like
        ("600036.SS", 35.0, 101),   # CMB-like
        ("601166.SS", 18.0, 102),   # CIB-like
        
        # Tech / Volatile
        ("300750.SZ", 200.0, 201),  # CATL-like
        ("002594.SZ", 250.0, 202),  # BYD-like
        ("688981.SS", 55.0, 203),   # SMIC-like
        
        # Consumer / Cyclical
        ("000858.SZ", 180.0, 301),  # Wuliangye-like
        ("600887.SS", 30.0, 302),   # Yili-like
        ("000651.SZ", 60.0, 303),   # Gree-like
        
        # Small Cap / High Volatility
        ("002475.SZ", 25.0, 401),   # Luxshare-like
        ("300059.SZ", 15.0, 402),   # EastMoney-like
        ("000725.SZ", 4.0, 403),    # BOE-like
        ("600030.SS", 22.0, 404),   # CITIC-like
        
        # Random others
        ("601888.SS", 80.0, 501),   # CDFG-like
        ("603288.SS", 90.0, 502),   # Haitian-like
        ("002352.SZ", 45.0, 503),   # SF-like
        ("601012.SS", 60.0, 504),   # Longi-like
        ("300760.SZ", 350.0, 505)   # Mindray-like
    ]
    
    for sym, price, seed in symbols:
        print(f"Generating synthetic data for {sym}...")
        df = generate_random_walk(sym, start_price=price, days=1500, seed=seed)
        df.to_csv(os.path.join(data_dir, f"{sym}.csv"))
    
    print("Done. Synthetic data created for testing.")

if __name__ == "__main__":
    main()
