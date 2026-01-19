import pandas as pd
import numpy as np
import os

def generate_random_walk(start_price=100, days=500):
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=days, freq='B')
    returns = np.random.normal(loc=0.0005, scale=0.02, size=days)
    price_path = start_price * (1 + returns).cumprod()
    
    df = pd.DataFrame(index=dates)
    df['Close'] = price_path
    df['Open'] = price_path * (1 + np.random.normal(0, 0.005, days))
    df['High'] = df[['Open', 'Close']].max(axis=1) * (1 + np.abs(np.random.normal(0, 0.005, days)))
    df['Low'] = df[['Open', 'Close']].min(axis=1) * (1 - np.abs(np.random.normal(0, 0.005, days)))
    df['Volume'] = np.random.randint(1000000, 5000000, days)
    df['Adj Close'] = df['Close']
    
    return df

def main():
    data_dir = "./data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    print("Generating AAPL.csv...")
    df = generate_random_walk()
    df.to_csv(os.path.join(data_dir, "AAPL.csv"))
    print("Done.")

if __name__ == "__main__":
    main()
