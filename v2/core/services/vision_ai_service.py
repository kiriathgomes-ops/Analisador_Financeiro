# v2/core/services/vision_ai_service.py
"""
VisionAIService: Analisa imagens de graficos usando Groq Vision.
"""

import sys
import json
import base64
import re
from pathlib import Path
from typing import Optional, Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.KeyManager import get_groq_client, key_manager


class VisionAIService:
    def __init__(self, imagens_dir: Optional[Path] = None):
        if imagens_dir is None:
            self.imagens_dir = BASE_DIR / "Coletas"
        else:
            self.imagens_dir = imagens_dir

        self.modelos_visuais = [
            "llama-3.2-11b-vision-preview",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "qwen/qwen3.6-27b"
        ]

    def _carregar_imagem_base64(self, nome_arquivo: str) -> Optional[str]:
        caminho = self.imagens_dir / nome_arquivo
        if not caminho.exists():
            return None

        try:
            with open(caminho, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            print(f"Erro ao carregar {nome_arquivo}: {e}")
            return None

    def _montar_prompt(self) -> str:
        prompt = '''
VOCE E UM ESPECIALISTA EM SMART MONEY CONCEPTS (SMC) E ICT.

Analise o grafico anexado e extraia as seguintes informacoes. Responda APENAS em formato JSON valido, sem texto adicional. Use os campos exatamente como especificados.

{
    "direcao_estrutura": "ALTA" ou "BAIXA" ou "LATERAL",
    "bos": true ou false,
    "choch": true ou false,
    "liquidity_zones": [precos],
    "order_blocks": [
        {"tipo": "COMPRA", "preco": 123456},
        {"tipo": "VENDA", "preco": 123000}
    ],
    "fair_value_gaps": [
        {"tipo": "COMPRA", "superior": 123500, "inferior": 123200},
        {"tipo": "VENDA", "superior": 122800, "inferior": 122500}
    ],
    "suportes": [122000, 121500],
    "resistencias": [124000, 124500],
    "entrada_sugerida": 123450,
    "stop_sugerido": 122800,
    "alvos": [124200, 124800],
    "confianca_visual": 75
}

Use numeros inteiros para precos. Se nao conseguir identificar algum campo, use null ou lista vazia.
Apenas JSON.
'''
        return prompt

    def analisar_imagem(
        self,
        imagem_base64: str,
        modelo: str
    ) -> Optional[Dict[str, Any]]:
        try:
            client, key_utilizada = get_groq_client()
            print(f"Analisando com {modelo} (chave: {key_utilizada[:8]}...)")

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
                            {
                                "type": "text",
                                "text": self._montar_prompt()
                            },
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
                tokens = response.usage.total_tokens
                key_manager.registrar_uso(key_utilizada, tokens)
                print(f"Tokens usados: {tokens}")

            resposta_texto = response.choices[0].message.content

            json_match = re.search(
                r"```json\s*(\{.*?\})\s*```",
                resposta_texto,
                re.DOTALL
            )
            if json_match:
                resposta_texto = json_match.group(1)
            else:
                json_match = re.search(
                    r"(\{.*\})",
                    resposta_texto,
                    re.DOTALL
                )
                if json_match:
                    resposta_texto = json_match.group(1)

            return json.loads(resposta_texto)

        except Exception as e:
            print(f"Erro na analise com {modelo}: {e}")
            return None

    def analisar(
        self,
        nome_imagem: str = "WIN_1min.png"
    ) -> Optional[Dict[str, Any]]:
        b64 = self._carregar_imagem_base64(nome_imagem)
        if not b64:
            print(f"Imagem {nome_imagem} nao encontrada em {self.imagens_dir}")
            return None

        for modelo in self.modelos_visuais:
            resultado = self.analisar_imagem(b64, modelo)
            if resultado:
                return resultado

        print("Nenhum modelo conseguiu analisar a imagem.")
        return None