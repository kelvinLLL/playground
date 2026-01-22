
import os
import sys
import requests
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def test_connection():
    print("=== LLM Connection Tester ===")
    
    # 1. Load .env
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
    print(f"Loading configuration from: {env_path}")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        print("Error: .env file not found!")
        return

    # 2. Get Config
    api_url = os.getenv("MODEL_URL")
    api_key = os.getenv("MODEL_API_KEY", "sk-placeholder")
    model_name = os.getenv("MODEL_NAME", "deepseek-coder")

    print(f"URL: {api_url}")
    print(f"Model: {model_name}")
    print(f"API Key: {'*' * 6}{api_key[-4:] if len(api_key) > 4 else '****'}")

    if not api_url:
        print("Error: MODEL_URL is missing in .env")
        return

    # 3. Construct Payload
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Return the string 'CONNECTION_SUCCESS' and nothing else."}
        ],
        "temperature": 0.1,
        "max_completion_tokens": 20
        # "max_tokens": 20
    }

    # 4. Send Request
    print("\nSending request...")
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            try:
                content = data['choices'][0]['message']['content']
                print(f"\n✅ RESPONSE RECEIVED:\n{content}")
                
                if "CONNECTION_SUCCESS" in content:
                    print("\n🎉 GREAT! Your LLM is correctly configured and responding.")
                else:
                    print("\n⚠️  Warning: Received response but it wasn't the expected string. Check if the model is following instructions.")
            except Exception as e:
                print(f"\n⚠️  Error parsing JSON response: {e}")
                print(f"Raw Body: {response.text}")
        else:
            print(f"\n❌ Request Failed.")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Connection Refused.")
        print(f"Could not connect to {api_url}.")
        print("Tips: \n1. Is the service running? (e.g. 'ollama serve')\n2. Is the port correct?\n3. If running in Docker, use host.docker.internal")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")

if __name__ == "__main__":
    test_connection()
