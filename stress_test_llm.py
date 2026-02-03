from openai import OpenAI
 
client = OpenAI(
    base_url="http://127.0.0.1:8045/v1",
    api_key="sk-699decf636704d4383f89d61979e75e5"
)

response = client.chat.completions.create(
    model="claude-sonnet-4-5",
    messages=[{"role": "user", "content": "Hello"}]
)

print(response.choices[0].message.content)