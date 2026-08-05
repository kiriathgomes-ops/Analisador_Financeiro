import json
import os
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO DE CAMINHOS E PARÂMETROS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
PASTA_COLETAS = BASE_DIR / "Coletas"

# Tolerância em % para desconsiderar ruídos insignificantes (0.001 = 0.001%)
TOLERANCIA_PERCENTUAL = 0.0001


def carregar_e_mapear_coleta(nome_arquivo):
    """
    Lê o JSON da pasta Coletas e transforma a lista de coletas em um dicionário:
    { "NOME_DO_ATIVO": preco_close }
    """
    caminho = PASTA_COLETAS / nome_arquivo
    if not caminho.exists():
        print(f"⚠️ Aviso: Arquivo {nome_arquivo} não encontrado em {PASTA_COLETAS}")
        return {}

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)

        mapa_precos = {}
        # Iterar sobre a lista 'coletas' do JSON
        for item in dados.get("coletas", []):
            ativo = item.get("ativo")
            dados_reais = item.get("dados_reais", {})
            close = dados_reais.get("close")

            if ativo and close is not None:
                try:
                    mapa_precos[ativo] = float(close)
                except (ValueError, TypeError):
                    continue

        return mapa_precos

    except json.JSONDecodeError:
        print(f"❌ Erro: O arquivo {nome_arquivo} está corrompido ou vazio.")
        return {}


def determinar_tendencia(preco_anterior, preco_atual):
    """Calcula a variação relativa e a direção do movimento."""
    if preco_anterior == 0 or preco_atual == 0:
        return {"variacao_abs": 0.0, "variacao_pct": 0.0, "tendencia": "SEM_DADOS"}

    var_abs = preco_atual - preco_anterior
    var_pct = (var_abs / preco_anterior) * 100

    if var_pct > TOLERANCIA_PERCENTUAL:
        tendencia = "Alta"
    elif var_pct < -TOLERANCIA_PERCENTUAL:
        tendencia = "Baixa"
    else:
        tendencia = "Estavel"

    return {
        "variacao_abs": round(var_abs, 4),
        "variacao_pct": round(var_pct, 4),
        "tendencia": tendencia,
    }


def analisar_arquivos_e_gerar_comparativo():
    """Lê as 3 coletas e gera a estrutura comparativa sequencial."""
    print("============================================================")
    print("📊 INICIANDO ANÁLISE DE TENDÊNCIAS (10m ➔ 5m ➔ 0m)")
    print("============================================================")

    # 1. Carrega e mapeia as 3 coletas
    coletarom10 = carregar_e_mapear_coleta("Coleta_rom-10.json")
    coletarom5 = carregar_e_mapear_coleta("Coleta_rom-5.json")
    coletarom0 = carregar_e_mapear_coleta("Coleta_rom-0.json")

    comparativo = {}

    # 2. Une todos os ativos encontrados nas 3 coletas
    todos_ativos = (
        set(coletarom10.keys())
        | set(coletarom5.keys())
        | set(coletarom0.keys())
    )

    if not todos_ativos:
        print("⚠️ Nenhum ativo foi extraído dos arquivos. Verifique a pasta Coletas.")
        return

    # 3. Compara ativo por ativo
    for ativo in todos_ativos:
        p10 = coletarom10.get(ativo)
        p5 = coletarom5.get(ativo)
        p0 = coletarom0.get(ativo)

        # Se faltar o preço em algum dos 3 arquivos, pula para não distorcer a análise
        if p10 is None or p5 is None or p0 is None:
            continue

        mov_10_5 = determinar_tendencia(p10, p5)
        mov_5_0 = determinar_tendencia(p5, p0)

        padrao = f"{mov_10_5['tendencia']}_E_{mov_5_0['tendencia']}"

        comparativo[ativo] = {
            "precos": {"10m": p10, "5m": p5, "0m": p0},
            "intervalo_10_para_5": mov_10_5,
            "intervalo_5_para_0": mov_5_0,
            "padrao_comportamento": padrao,
        }

    # 4. Salva o resultado no JSON de saída
    caminho_saida = PASTA_COLETAS / "Analise_Tendencias.json"

    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(comparativo, f, indent=4, ensure_ascii=False)

    print(f"✅ Análise concluída com sucesso! {len(comparativo)} ativos processados.")
    print(f"📁 Arquivo salvo em: {caminho_saida}")
    print("============================================================")


if __name__ == "__main__":
    analisar_arquivos_e_gerar_comparativo()