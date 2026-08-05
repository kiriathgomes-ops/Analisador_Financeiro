import glob
import os
import re
import shutil
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO DE CAMINHOS E METAS
# ============================================================
PASTA_DOWNLOADS = os.path.expanduser(r"~\Downloads")
MANTER_RECENTES = 2

# Pasta Coletas relativa à raiz do projeto
BASE_DIR = Path(__file__).resolve().parent
PASTA_COLETAS = BASE_DIR / "Coletas"

# Padronização de Regex para capturar contratos do WIN (WINQ2026, WINV26, BMFBOVESPA_WIN, etc)
# e capturas padrão do TradingView
PADRAO_REGEX_TRADINGVIEW = re.compile(
    r"^(WIN[A-Z]\d{2,4}|tradingview|BMFBOVESPA_WIN)", re.IGNORECASE
)


def e_imagem_tradingview(nome_arquivo):
    """Verifica se o arquivo é uma imagem e atende aos padrões de nome do WIN ou TradingView."""
    extensao_valida = nome_arquivo.lower().endswith((".png", ".jpg", ".jpeg"))
    match_nome = bool(PADRAO_REGEX_TRADINGVIEW.search(nome_arquivo))
    return extensao_valida and match_nome


def limpar_e_processar_imagens():
    print("============================================================")
    print("🧹 GERENCIADOR DINÂMICO DE IMAGENS (WIN / TRADINGVIEW)")
    print("============================================================")

    if not os.path.exists(PASTA_DOWNLOADS):
        print(f"❌ Pasta não encontrada: {PASTA_DOWNLOADS}")
        return

    # Garante que a pasta Coletas existe no projeto
    PASTA_COLETAS.mkdir(exist_ok=True)

    # 1. Varre a pasta e filtra os arquivos dinamicamente
    todos_arquivos = os.listdir(PASTA_DOWNLOADS)
    imagens_filtradas = [
        os.path.join(PASTA_DOWNLOADS, f)
        for f in todos_arquivos
        if e_imagem_tradingview(f)
    ]

    if not imagens_filtradas:
        print(
            "ℹ️ Nenhuma imagem recente de contrato WIN/TradingView foi encontrada."
        )
        return

    # 2. Ordena da mais RECENTE [index 0] para a mais ANTIGA [index -1]
    imagens_ordenadas = sorted(
        imagens_filtradas, key=os.path.getmtime, reverse=True
    )

    total_encontrados = len(imagens_ordenadas)
    print(
        f"🔍 Total de imagens WIN/TradingView identificadas: {total_encontrados}"
    )

    # 3. Separa as 2 mais recentes do restante
    para_manter = imagens_ordenadas[:MANTER_RECENTES]
    para_deletar = imagens_ordenadas[MANTER_RECENTES:]

    print("\n✅ MANTIDAS (Mais recentes):")
    for arq in para_manter:
        print(f"  └─ {os.path.basename(arq)}")

    # ------------------------------------------------------------
    # 4. COPIA E RENOMEIA PARA A PASTA COLETAS
    # ------------------------------------------------------------
    if len(para_manter) >= 2:
        img_1min_origem = para_manter[0]  # Mais recente (1min)
        img_5min_origem = para_manter[1]  # Mais antiga das duas (5min)

        dest_1min = PASTA_COLETAS / "WIN_1min.png"
        dest_5min = PASTA_COLETAS / "WIN_5min.png"

        try:
            shutil.copy2(img_1min_origem, dest_1min)
            shutil.copy2(img_5min_origem, dest_5min)

            print("\n📁 COPIADAS PARA /Coletas:")
            print(
                f"  ├─ {os.path.basename(img_5min_origem)} ➔ Coletas/WIN_5min.png (5 min)"
            )
            print(
                f"  └─ {os.path.basename(img_1min_origem)} ➔ Coletas/WIN_1min.png (1 min)"
            )
        except Exception as err:
            print(f"❌ Erro ao copiar arquivos para Coletas: {err}")
    else:
        print("\n⚠️ Menos de 2 imagens encontradas. Cópia parcial cancelada.")

    # 5. Deleta as antigas da pasta Downloads
    if para_deletar:
        print(f"\n🗑️ REMOVENDO {len(para_deletar)} IMAGEM(NS) ANTIGA(S)...")
        for arq in para_deletar:
            try:
                os.remove(arq)
                print(f"  ❌ Removido: {os.path.basename(arq)}")
            except Exception as e:
                print(f"  ⚠️ Erro ao remover {os.path.basename(arq)}: {e}")
    else:
        print("\n✨ Nenhuma imagem antiga para deletar.")

    print("\n============================================================")


if __name__ == "__main__":
    limpar_e_processar_imagens()