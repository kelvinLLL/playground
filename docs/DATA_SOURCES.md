# Data Sources

This project supports multiple data sources for acquiring historical market data.

## 1. Yahoo Finance (Default)
Used for general global stocks and simple testing.
- **Library**: `yfinance`
- **Script**: `scripts/fetch_data.py`
- **Command**: `python stock_playground/scripts/fetch_data.py`

## 2. TDX (TongDaXin) - Recommended for A-Shares
Direct interface to TongDaXin trade servers, providing faster and more reliable data for Chinese A-shares.
- **Library**: `pytdx`
- **Script**: `scripts/fetch_tdx_data.py`
- **Command**: `python stock_playground/scripts/fetch_tdx_data.py`

### Setup TDX
To use the TDX data source, you must install the `pytdx` library:
```bash
pip install pytdx
```

### Usage
The fetch script is configured to download the **last 5 years** of daily K-line data for a predefined list of symbols (e.g., Moutai, Ping An).

Supported Symbol Formats:
- `######.SS` (Shanghai)
- `######.SZ` (Shenzhen)

The data is saved to the `data/` directory in CSV format, compatible with the `HistoricCSVDataHandler`.
