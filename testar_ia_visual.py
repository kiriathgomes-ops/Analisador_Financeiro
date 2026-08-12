# testar_ia_visual.py
"""
Script para testar a analise visual com IA (Groq Vision).
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from v2.core.services.vision_ai_service import VisionAIService

def main():
    print("=" * 60)
    print("TESTE DE IA VISUAL - Groq Vision")
    print("=" * 60)

    caminho_imagem = BASE_DIR / "Coletas" / "WIN_1min.png"
    if not caminho_imagem.exists():
        print(f"Imagem nao encontrada: {caminho_imagem}")
        print("   Certifique-se de que WIN_1min.png esta na pasta Coletas/")
        return

    print(f"Imagem encontrada: {caminho_imagem}")

    service = VisionAIService()
    resultado = service.analisar("WIN_1min.png")

    if resultado:
        print("\nANALISE CONCLUIDA!\n")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        print("\n" + "=" * 60)

        print("\nRESUMO DA ANALISE:")
        print(f"  Estrutura: {resultado.get('direcao_estrutura', 'N/A')}")
        print(f"  BOS: {resultado.get('bos', False)}")
        print(f"  CHOCH: {resultado.get('choch', False)}")
        print(f"  Confianca: {resultado.get('confianca_visual', 0)}%")
        print(f"  Suportes: {resultado.get('suportes', [])}")
        print(f"  Resistencias: {resultado.get('resistencias', [])}")
        print(f"  Entrada sugerida: {resultado.get('entrada_sugerida', 'N/A')}")
        print(f"  Stop sugerido: {resultado.get('stop_sugerido', 'N/A')}")
        print(f"  Alvos: {resultado.get('alvos', [])}")
    else:
        print("\nFalha na analise. Verifique a chave API e a conexao.")

if __name__ == "__main__":
    main()