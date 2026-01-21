
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMClient:
    """
    A generic client for interacting with an OpenAI-compatible API endpoint.
    Reads configuration from environment variables.
    """
    def __init__(self):
        self.api_url = os.getenv("MODEL_URL", "http://localhost:11434/v1/chat/completions")
        self.api_key = os.getenv("MODEL_API_KEY", "sk-placeholder") # Many local models don't need a key
        self.model_name = os.getenv("MODEL_NAME", "deepseek-coder") # Default model name

    def generate_code(self, prompt: str, system_prompt: str = None) -> str:
        """
        Sends a prompt to the LLM and returns the generated code content.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2, # Low temp for code generation stability
            "stream": False
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            # Simple cleanup to extract code block if wrapped in markdown
            return self._extract_code(content)
            
        except Exception as e:
            print(f"LLM API Error: {e}")
            print("Falling back to MOCK generation for demonstration...")
            return self._mock_generation(prompt)

    def _mock_generation(self, prompt):
        """
        Returns a valid strategy code for demonstration purposes when LLM is unavailable.
        """
        return """
from simple_quant.strategy.base import Strategy
from simple_quant.events import SignalEvent
import numpy as np

class GeneratedStrategy(Strategy):
    def __init__(self, bars, events):
        self.bars = bars
        self.events = events
        self.symbol_list = self.bars.symbol_list
        self.bought = {s: 'OUT' for s in self.symbol_list}
        
    def calculate_signals(self, event):
        if event.type == 'MARKET':
            for s in self.symbol_list:
                bars = self.bars.get_latest_bars_values(s, "Close", N=20)
                if len(bars) < 20:
                    continue
                    
                # Simple Momentum / Mean Reversion Hybrid
                # If price is above 20-day MA, buy
                ma20 = np.mean(bars)
                price = bars[-1]
                
                dt = self.bars.get_latest_bar_datetime(s)
                
                if price > ma20 and self.bought[s] == 'OUT':
                    print(f"LONG: {s} at {dt}")
                    self.events.put(SignalEvent(symbol=s, datetime=dt, signal_type='LONG', strength=1.0))
                    self.bought[s] = 'LONG'
                elif price < ma20 and self.bought[s] == 'LONG':
                    print(f"EXIT: {s} at {dt}")
                    self.events.put(SignalEvent(symbol=s, datetime=dt, signal_type='EXIT', strength=1.0))
                    self.bought[s] = 'OUT'
"""


    def _extract_code(self, text: str) -> str:
        """
        Extracts python code from markdown code blocks if present.
        """
        if "```python" in text:
            parts = text.split("```python")
            if len(parts) > 1:
                code_part = parts[1].split("```")[0]
                return code_part.strip()
        elif "```" in text:
            parts = text.split("```")
            if len(parts) > 1:
                code_part = parts[1]
                return code_part.strip()
        return text.strip()
