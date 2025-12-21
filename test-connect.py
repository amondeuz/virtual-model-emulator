import requests
import json

url = "http://localhost:11434/providers/connect"
data = {
    "provider": "anthropic",
    "accountName": "Test Account",
    "apiKey": "test-key-12345"
}

response = requests.post(url, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
