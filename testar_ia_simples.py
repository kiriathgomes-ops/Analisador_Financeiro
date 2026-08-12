# testar_ia_simples.py
"""
Script isolado para testar a Groq Vision.
Le a chave diretamente do .env, sem depender do KeyManager.
"""

import sys
import json
import base64
from pathlib import Path


def ler_chave_do_env():
    env_path = Path(".env")
    if not env_path.exists():
        print("Arquivo .env nao encontrado!")
        return None

    with open(env_path, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha.startswith("GROQ_API_KEY") and "=" in linha:
                chave = linha.split("=", 1)[1].strip().strip('"').strip("'")
                if chave and len(chave) > 10:
                    return chave

    print("Nenhuma chave GROQ_API_KEY encontrada no .env")
    return None


API_KEY = ler_chave_do_env()
if not API_KEY:
    print("\nAdicione a chave no arquivo .env:")
    print('   GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"')
    sys.exit(1)

print(f"Chave carregada: {API_KEY[:10]}...")

imagem_path = Path("Coletas/WIN_1min.png")
if not imagem_path.exists():
    print(f"Imagem nao encontrada: {imagem_path}")
    sys.exit(1)

print(f"Imagem encontrada: {imagem_path}")

with open(imagem_path, "rb") as f:
    imagem_base64 = base64.b64encode(f.read()).decode("utf-8")

PROMPT = '''
VOCE E UM ESPECIALISTA EM SMART MONEY CONCEPTS (SMC) E ICT.

Analise o grafico anexado e extraia as seguintes informacoes. Responda APENAS em formato JSON valido, sem texto adicional.

{
    "direcao_estrutura": "ALTA" ou "BAIXA" ou "LATERAL",
    "bos": true ou false,
    "choch": true ou false,
    "liquidity_zones": [],
    "order_blocks": [],
    "fair_value_gaps": [],
    "suportes": [],
    "resistencias": [],
    "entrada_sugerida": null,
    "stop_sugerido": null,
    "alvos": [],
    "confianca_visual": 0
}

Use numeros inteiros para precos. Se nao conseguir identificar algum campo, use null ou lista vazia.
Apenas JSON.
'''

print("\nChamando Groq Vision...")

try:
    from groq import Groq
except ImportError:
    print("Biblioteca 'groq' nao instalada. Execute: pip install groq")
    sys.exit(1)

client = Groq(api_key=API_KEY)

modelos = [
    "llama-3.2-11b-vision-preview",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "qwen/qwen3.6-27b"
]


resultado = None

for modelo in modelos:
    try:
        print(f" Tentando {modelo}...")
        response = client.chat.completions.create(
            model=modelo,
            messages=[
                {
                    "role": "system",
                    "content": "Voce e um especialista em SMC/ICT. Responda apenas em JSON."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{imagem_base64}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=1500,
        )

        if hasattr(response, "usage"):
            print(f" Tokens: {response.usage.total_tokens}")

        resposta_texto = response.choices[0].message.content

        import re

        json_match = re.search(
            r"```json\s*(\{.*?\})\s*```",
            resposta_texto,
            re.DOTALL
        )
        if json_match:
            resposta_texto = json_match.group(1)
        else:
            json_match = re.search(r"(\{.*\})", resposta_texto, re.DOTALL)
            if json_match:
                resposta_texto = json_match.group(1)

        resultado = json.loads(resposta_texto)
        print(f" Sucesso com {modelo}!")
        break

    except Exception as e:
        print(f" Erro: {e}")
        continue

if resultado:
    print("\n" + "=" * 60)
    print("ANALISE CONCLUIDA!")
    print("=" * 60)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    print("\n" + "=" * 60)

    print("\nRESUMO:")
    print(f" Estrutura: {resultado.get('direcao_estrutura', 'N/A')}")
    print(f" BOS: {resultado.get('bos', False)}")
    print(f" CHOCH: {resultado.get('choch', False)}")
    print(f" Confianca: {resultado.get('confianca_visual', 0)}%")

    if resultado.get("suportes"):
        print(f" Suportes: {resultado.get('suportes')}")
    if resultado.get("resistencias"):
        print(f" Resistencias: {resultado.get('resistencias')}")
    if resultado.get("order_blocks"):
        print(f" Order Blocks: {len(resultado.get('order_blocks'))} encontrados")
    if resultado.get("fair_value_gaps"):
        print(f" FVGs: {len(resultado.get('fair_value_gaps'))} encontrados")
else:
    print("\nFalha na analise. Verifique a chave API e a conexao.")