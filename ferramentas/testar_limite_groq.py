import os
import requests
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# ✅ find_dotenv sobe as pastas automaticamente até achar a raiz do projeto
load_dotenv(find_dotenv())

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY não encontrada no .env")
    exit()

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "openai/gpt-oss-120b",
    "messages": [{"role": "user", "content": "Diga 'ok'"}],
    "max_tokens": 1,
    "temperature": 0.0
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 401:
        print("❌ Erro 401: Chave inválida ou expirada.")
    elif response.status_code == 429:
        print("\n⚠️ Limite atingido (429). Aguarde alguns segundos.")
    elif response.status_code == 200:
        print("✅ Chave válida! Lendo os limites...\n")
    
    print("--- Headers de Rate Limit ---")
    achou_header = False
    for key, value in response.headers.items():
        if "ratelimit" in key.lower():
            print(f"{key}: {value}")
            achou_header = True
            
    if not achou_header:
        print("(A API não retornou os headers de rate limit nesta chamada)")

except Exception as e:
    print(f"Erro de conexão: {e}")