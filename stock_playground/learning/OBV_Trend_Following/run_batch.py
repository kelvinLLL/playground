
import os
import sys
import subprocess
import glob

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
STRATEGY_PATH = os.path.join(PROJECT_ROOT, "stock_playground/learning/OBV_Trend_Following/strategy.py")
DATA_DIR = os.path.join(PROJECT_ROOT, "stock_playground/data/ai")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "stock_playground/learning/OBV_Trend_Following/images")
VIS_SCRIPT = os.path.join(PROJECT_ROOT, "stock_playground/visualize_strategy.py")

def run_command(cmd):
    """Runs a shell command and streams output."""
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    output = []
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            print(line.strip())
            output.append(line.strip())
    return output

def main():
    print(f"--- Starting Batch Visualization for OBV Strategy ---")
    
    # 1. Generate Sector Overview
    print("\n[1/11] Generating Sector Overview...")
    sector_img = os.path.join(os.path.dirname(OUTPUT_DIR), "sector_overview.png")
    run_command(f"uv run {VIS_SCRIPT} {STRATEGY_PATH} --data {DATA_DIR} --output {sector_img}")
    
    # 2. Generate Individual Plots
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    total = len(csv_files)
    
    for i, csv_file in enumerate(csv_files):
        symbol = os.path.basename(csv_file).replace(".csv", "")
        print(f"\n[{i+2}/{total+1}] Processing {symbol}...")
        
        output_img = os.path.join(OUTPUT_DIR, f"{symbol}_obv.png")
        logs = run_command(f"uv run {VIS_SCRIPT} {STRATEGY_PATH} --data {DATA_DIR} --symbol {symbol} --output {output_img}")
        
        # Save interesting logs for analysis
        log_file = os.path.join(OUTPUT_DIR, f"{symbol}.log")
        with open(log_file, "w") as f:
            for line in logs:
                if "LONG" in line or "EXIT" in line or "Return" in line or "Sharpe" in line:
                    f.write(line + "\n")

if __name__ == "__main__":
    main()
