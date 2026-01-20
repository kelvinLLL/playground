
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
            raise

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
