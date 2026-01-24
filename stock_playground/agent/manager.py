import os
import json
import uuid
import sys
from datetime import datetime

# Add project root and stock_playground to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from stock_playground.agent.client import LLMClient
from stock_playground.agent.context import StrategyContext
from stock_playground.agent.executor import StrategyExecutor


class StrategyManager:
    """
    Manages the lifecycle of AI strategy generation.
    1. Prompts LLM to generate a strategy.
    2. Runs it in the executor.
    3. If fails, feeds back error to LLM to fix.
    4. If succeeds, saves the result.
    """

    def __init__(self, data_dir, symbol_list):
        self.client = LLMClient()
        self.executor = StrategyExecutor(data_dir, symbol_list)
        self.output_base = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../generated_strategies")
        )

        if not os.path.exists(self.output_base):
            os.makedirs(self.output_base)

    def generate_strategy(self, prompt_idea: str, max_retries=3):
        """
        Main loop to generate and fix a strategy.
        """
        print(f"--- Starting Strategy Generation: {prompt_idea} ---")

        # 1. Initial Prompt
        system_prompt = StrategyContext.get_system_prompt()
        current_prompt = f"Create a trading strategy based on this idea: {prompt_idea}"

        # Sanitize prompt for folder name (alphanumeric only, limited length)
        safe_name = "".join(
            [c if c.isalnum() else "_" for c in prompt_idea[:30]]
        ).strip("_")
        while "__" in safe_name:
            safe_name = safe_name.replace("__", "_")

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = str(uuid.uuid4())[:8]

        # New folder format: strategy_{timestamp}_{sanitized_prompt}_{id}
        strategy_dir_name = f"strategy_{timestamp_str}_{safe_name}_{session_id}"
        strategy_dir = os.path.join(self.output_base, strategy_dir_name)
        os.makedirs(strategy_dir, exist_ok=True)

        file_path = os.path.join(strategy_dir, "strategy.py")

        history = []  # Keep track of conversation logic if needed, but for now we iterate

        for attempt in range(max_retries + 1):
            print(f"\n[Attempt {attempt + 1}/{max_retries + 1}] Generating Code...")

            # Call LLM
            try:
                # If retrying, we append the error context to the user prompt
                code = self.client.generate_code(current_prompt, system_prompt)

                # Add timestamp header to code
                header = f'"""\nStrategy Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\nPrompt: {prompt_idea}\n"""\n\n'
                if not code.startswith('"""'):
                    code = header + code

            except Exception as e:
                print(f"LLM Error: {e}")
                return False

            # Save Code
            with open(file_path, "w") as f:
                f.write(code)

            # Verify / Run Backtest (Training Set)
            print("  > Verifying Code execution...")
            result = self.executor.run_strategy(
                file_path, start_date_str="2020-01-01", end_date_str="2023-12-31"
            )

            if result["success"]:
                print(f"  > Success! Metrics: {result['metrics']}")

                # Save Metadata
                meta = {
                    "id": session_id,
                    "prompt": prompt_idea,
                    "created_at": str(datetime.now()),
                    "metrics_train": result["metrics"],
                    "code_path": file_path,
                }
                with open(os.path.join(strategy_dir, "meta.json"), "w") as f:
                    json.dump(meta, f, indent=2)

                print(f"  > Strategy saved to {strategy_dir}")

                # --- AUTO VISUALIZATION START ---
                try:
                    print("  > Auto-generating visualization...")
                    from stock_playground.visualize_strategy import visualize

                    # Pick the first symbol to visualize
                    vis_symbol = self.executor.symbol_list[0]
                    vis_output = os.path.join(strategy_dir, "result.png")

                    visualize(
                        strategy_path=file_path,
                        data_dir=self.executor.data_dir,
                        symbol=vis_symbol,
                        output_file=vis_output,
                    )
                except Exception as ve:
                    print(f"  > Visualization failed: {ve}")
                # --- AUTO VISUALIZATION END ---

                return True
            else:
                print(f"  > Execution Failed: {result['error']}")
                # Prepare feedback for next loop
                current_prompt = f"""
The previous code you wrote failed with the following error:
{result["error"]}

Please fix the code. Return ONLY the full corrected Python code.
Original Request: {prompt_idea}
"""

        print("Max retries reached. Generation failed.")
        return False


def main():
    # Configuration
    # Point to the AI sector data we just fetched
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/ai"))
    # Use symbol list found in data dir
    files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    symbol_list = [f.replace(".csv", "") for f in files]

    if not symbol_list:
        print("No data found. Please run fetch script first.")
        return

    manager = StrategyManager(data_dir, symbol_list)

    # Interactive Mode
    if len(sys.argv) > 1:
        idea = " ".join(sys.argv[1:])
    else:
        print("Enter a strategy idea (e.g. 'Mean reversion using Bollinger Bands'):")
        idea = input("> ")

    manager.generate_strategy(idea)


if __name__ == "__main__":
    main()
