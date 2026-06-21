import os
import requests
from load_dotenv import load_dotenv
load_dotenv()


AZURE_OPENAI_ENDPOINT = "https://openai-gp-key.openai.azure.com/"
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
DEPLOYMENT_NAME = "gpt-4.1-mini-4"
API_VERSION = "2025-01-01-preview"


#url="https://openai-gp-key.openai.azure.com/openai/deployments/gpt-4.1-mini-4/chat/completions?api-version=2025-01-01-preview"

url = (
    f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/"
    f"{DEPLOYMENT_NAME}/chat/completions"
    f"?api-version={API_VERSION}"
)

headers = {
    "Content-Type": "application/json",
    "api-key": AZURE_OPENAI_API_KEY,
}

payload = {
    "messages": [
        {"role": "user", "content": "Reply with exactly: API key works"}
    ],
    "temperature": 0,
    "max_tokens": 20,
}

response = requests.post(url, headers=headers, json=payload)

print("Status:", response.status_code)
print("Response:", response.text)

response.raise_for_status()

data = response.json()
print(data["choices"][0]["message"]["content"])