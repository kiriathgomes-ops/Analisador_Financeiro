# ============================================================
# ARQUIVO: Mapa_Projeto.py
# GERA MAPA AUTOMÁTICO DO PROJETO
# ============================================================

import json
import os
from datetime import datetime

# ------------------------------------------------------------
# CONFIGURAÇÃO DE CAMINHOS SEGUROS
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
PASTA_SAIDA = os.path.join(COLETAS_DIR, "Mapa_Projeto.json")

# ------------------------------------------------------------
# IMPORTA INVENTÁRIO AUTOMÁTICO
# ------------------------------------------------------------
try:
    from Coletas.ArquivosApp import ARQUIVOS_PROJETO
except ImportError:
    # Se chamado de dentro do módulo ou diretório diferente
    try:
        from ArquivosApp import ARQUIVOS_PROJETO
    except ImportError:
        ARQUIVOS_PROJETO = []


# ------------------------------------------------------------
# CLASSIFICAÇÃO DOS MÓDULOS
# ------------------------------------------------------------
def classificar_arquivo(nome):
    nome = nome.lower()

    # 1. Módulos de Notícias e Macro
    if "noticia" in nome or "calendario" in nome:
        if nome.endswith(".py"):
            return "NOTICIAS_MACRO"
        return "DADOS"

    # 2. Coletor Geral
    if "coleta" in nome or "coletor" in nome:
        return "COLETA"

    # 3. Validação e Testes
    if "valid" in nome or "teste" in nome or "fonte" in nome:
        return "VALIDACAO"

    # 4. Cálculos e Estimativas
    if "calcul" in nome or "metrica" in nome or "estimativa" in nome:
        return "CALCULOS"

    # 5. Core Engine / Decisao
    if "engine" in nome or "decisao" in nome or "pipeline" in nome:
        return "CORE"

    # 6. Relatórios
    if "relatorio" in nome or "mensagem" in nome:
        return "RELATORIOS"

    # 7. Interfaces (App / Streamlit Pages)
    if "app" in nome or "page" in nome or "pages" in nome:
        return "INTERFACE"

    # 8. Arquivos de Dados soltos
    if nome.endswith(".json") or nome.endswith(".csv"):
        return "DADOS"

    return "OUTROS"


# ------------------------------------------------------------
# GERA MAPA
# ------------------------------------------------------------
def gerar_mapa():
    mapa = {
        "metadata": {
            "projeto": "Analisador_Financeiro",
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fonte": "Coletas/Mapa_Inventario_Tecnico.json",
        },
        "estrutura": {},
        "total_arquivos": len(ARQUIVOS_PROJETO),
    }

    for item in ARQUIVOS_PROJETO:
        categoria = classificar_arquivo(item["arquivo"])

        if categoria not in mapa["estrutura"]:
            mapa["estrutura"][categoria] = []

        mapa["estrutura"][categoria].append(
            {
                "arquivo": item["arquivo"],
                "local": item["local"],
                "tipo": item["tipo"],
                "tamanho_kb": item["tamanho_kb"],
                "ultima_alteracao": item["ultima_alteracao"],
            }
        )

    return mapa


# ------------------------------------------------------------
# SALVAR JSON
# ------------------------------------------------------------
def salvar_mapa():
    if not ARQUIVOS_PROJETO:
        print("[ERRO] Nenhum arquivo foi encontrado no inventário `ARQUIVOS_PROJETO`.")
        return

    mapa = gerar_mapa()

    os.makedirs(COLETAS_DIR, exist_ok=True)

    with open(PASTA_SAIDA, "w", encoding="utf-8") as arquivo:
        json.dump(mapa, arquivo, indent=4, ensure_ascii=False)

    print("=" * 60)
    print(" MAPA DO PROJETO GERADO COM SUCESSO ")
    print("=" * 60)

    print(f"\nArquivos analisados: {mapa['total_arquivos']}\n")

    for categoria, lista in mapa["estrutura"].items():
        print(f"  • {categoria:<15} : {len(lista)} arquivos")

    print("\nArquivo criado:")
    print(os.path.abspath(PASTA_SAIDA))
    print("=" * 60)


if __name__ == "__main__":
    salvar_mapa()