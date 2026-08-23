# ============================================================
# ARQUIVO: Engine_Vies.py (VERSÃO 3.1 - APENAS WIN)
# DATA: 22/08/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Core Engine - Processamento de Viés de Abertura do WIN
# INTEGRADO COM: Noticias_Impacto_Dia.json + DadosAtivosUnificados.json + Metricas
# ============================================================

import json
import os
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO DE CAMINHOS E DIRETÓRIOS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
COLETAS_DIR = BASE_DIR / "Coletas"

# Arquivos de entrada do pipeline
FILE_ESTIMATIVA = COLETAS_DIR / "EstimativaAbertura.json"
FILE_METRICAS = COLETAS_DIR / "Metricas_Calculadas.json"
FILE_NOTICIAS = COLETAS_DIR / "Noticias_Impacto_Dia.json"
FILE_ATIVOS = COLETAS_DIR / "DadosAtivosUnificados.json"

# Arquivo de saída consolidado com a decisão do Core
FILE_OUTPUT = COLETAS_DIR / "Decisao_Core.json"


def carregar_json(caminho: Path) -> dict:
    """Carrega arquivos JSON de forma defensiva para evitar parada do script."""
    if not caminho.exists():
        print(f"[AVISO] Arquivo não encontrado: {caminho.name}")
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERRO] Falha ao carregar {caminho.name}: {str(e)}")
        return {}


def calcular_vies_win(estimativa: dict, metricas: dict, noticias: dict, spread_win_last_ajuste: float = 0.0) -> dict:
    """
    Calcula o Score do WIN de -10.0 (Forte Venda) a +10.0 (Forte Compra).
    Aplica travas dinâmicas de volatilidade baseadas no calendário de notícias.
    """
    score = 0.0
    fatos = []

    # ------------------------------------------------------------
    # 1. ABERTURA TEÓRICA DO MINI ÍNDICE
    # ------------------------------------------------------------
    win_est = estimativa.get("WIN_INDICE", {})
    var_teorica = win_est.get("variacao_teorica_pct", 0.0)
    
    if var_teorica > 0.5:
        score += 3.0
        fatos.append(f"Teórico WIN positivo (+{var_teorica:.2f}%)")
    elif var_teorica < -0.5:
        score -= 3.0
        fatos.append(f"Teórico WIN negativo ({var_teorica:.2f}%)")

    # ------------------------------------------------------------
    # 2. INDICADOR COMPOSTO DE ADRs BRASILEIRAS
    # ------------------------------------------------------------
    ind_adrs = metricas.get("indicadores_compostos", {}).get("indicador_adrs_brasileiras")
    if ind_adrs is not None:
        if ind_adrs > 1.0:
            score += 2.5
            fatos.append(f"ADRs fortes no exterior (+{ind_adrs:.2f}%)")
        elif ind_adrs < -1.0:
            score -= 2.5
            fatos.append(f"ADRs fracas no exterior ({ind_adrs:.2f}%)")

    # ------------------------------------------------------------
    # 3. RISCO GLOBAL E VOLATILIDADE (VIX)
    # ------------------------------------------------------------
    vix_change = metricas.get("indicadores_macro", {}).get("vix_change_pct")
    if vix_change is not None:
        if vix_change > 5.0:
            score -= 2.0
            fatos.append(f"Aumento de Risco Global / VIX em alta (+{vix_change:.1f}%)")
        elif vix_change < -5.0:
            score += 1.5
            fatos.append(f"Queda de Risco Global / VIX caindo ({vix_change:.1f}%)")

    # ------------------------------------------------------------
    # 4. COMMODITIES E MERCADO EXTERNO
    # ------------------------------------------------------------
    ind_ext = metricas.get("indicadores_compostos", {}).get("indicador_mercado_externo")
    if ind_ext is not None:
        if ind_ext > 0.8:
            score += 2.5
            fatos.append(f"Commodities e Mercado Externo favoráveis (+{ind_ext:.2f}%)")
        elif ind_ext < -0.8:
            score -= 2.5
            fatos.append(f"Commodities e Mercado Externo pressionados ({ind_ext:.2f}%)")

    # ------------------------------------------------------------
    # 5. SPREAD ENTRE LAST (ÚLTIMO TICK) E AJUSTE OFICIAL
    # ------------------------------------------------------------
    LIMIAR_SPREAD_WIN = 100.0  # 100 pontos de desvio já indica força institucional
    if spread_win_last_ajuste != 0.0:
        if spread_win_last_ajuste > LIMIAR_SPREAD_WIN:
            score += 2.0
            fatos.append(f"🔺 Last acima do ajuste em {spread_win_last_ajuste:.0f} pts (viés comprador)")
        elif spread_win_last_ajuste < -LIMIAR_SPREAD_WIN:
            score -= 2.0
            fatos.append(f"🔻 Last abaixo do ajuste em {abs(spread_win_last_ajuste):.0f} pts (viés vendedor)")
        else:
            fatos.append(f"⚖️ Spread Last vs Ajuste na normalidade ({spread_win_last_ajuste:+.0f} pts)")

    # ------------------------------------------------------------
    # 6. FILTROS E TRAVAS DE NOTÍCIAS (GESTÃO DE RISCO)
    # ------------------------------------------------------------
    alertas_noticias = noticias.get("alertas", {})

    # Trava 1: Evento 3 Estrelas no Brasil às 09:00 (Abertura do Pregão)
    if alertas_noticias.get("tem_3_estrelas_brasil_0900"):
        fatos.append("🚨 TRAVA CRÍTICA: Notícia ⭐⭐⭐ no Brasil às 09:00! Alta Volatilidade na abertura.")
        score *= 0.5  # Reduz a exposição/confiança pela metade

    # Trava 2: Classificação de Risco do Dia
    classificacao_impacto = noticias.get("resumo", {}).get("classificacao", "")
    if classificacao_impacto == "EXTREMO":
        fatos.append("⚠️ Risco Global de Notícias EXTREMO no dia. Recomendado operar com mão reduzida.")
        score *= 0.8

    # Trava 3: Confluência de múltiplos eventos 2 Estrelas
    if alertas_noticias.get("tem_multiplas_2_estrelas_mesmo_horario"):
        horarios = [item["hora"] for item in alertas_noticias.get("horarios_multiplas_2_estrelas", [])]
        fatos.append(f"⚠️ Atenção para acúmulo de eventos ⭐⭐ nos horários: {', '.join(horarios)}")

    # ------------------------------------------------------------
    # 7. CLASSIFICAÇÃO FINAL DO VIÉS
    # ------------------------------------------------------------
    if score >= 4.0:
        vies = "FORTE_COMPRA"
    elif score >= 1.5:
        vies = "MODERADO_COMPRA"
    elif score <= -4.0:
        vies = "FORTE_VENDA"
    elif score <= -1.5:
        vies = "MODERADO_VENDA"
    else:
        vies = "NEUTRO"

    if alertas_noticias.get("tem_3_estrelas_brasil_0900") and vies != "NEUTRO":
        vies += " (ALTA VOLATILIDADE 09:00)"

    return {
        "score_numeric": round(score, 2),
        "vies_final": vies,
        "fatores_relevantes": fatos,
    }


def executar_core():
    """Orquestra o carregamento de dados e gera o viés direcional do WIN."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Executando Core Engine de Viés (Apenas WIN)...")

    # Carrega dados dos arquivos de suporte
    estimativas_data = carregar_json(FILE_ESTIMATIVA)
    metricas = carregar_json(FILE_METRICAS)
    noticias = carregar_json(FILE_NOTICIAS)
    ativos_data = carregar_json(FILE_ATIVOS)

    # Tratamento defensivo da estrutura do dicionário de estimativas
    estimativas = estimativas_data.get("estimativa_abertura", {}) or estimativas_data.get("estimativas_abertura", {})

    # Extração de preço do último tick e ajuste do WIN
    ativos = ativos_data.get("ativos", {}) if isinstance(ativos_data, dict) else {}
    win_last = ativos.get("WIN_LAST_TICK", {}).get("preco", 0.0)
    win_ajuste = ativos.get("WIN_AJUSTE", {}).get("preco", 0.0)

    # Cálculo do spread entre Last e Ajuste
    spread_win_last_ajuste = (win_last - win_ajuste) if (win_last and win_ajuste) else 0.0

    # Processamento do viés do WIN
    vies_win = calcular_vies_win(
        estimativas, 
        metricas, 
        noticias,
        spread_win_last_ajuste
    )

    # Montagem da estrutura final de decisão
    decisao_final = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "status_pipeline": "OK",
            "ativo_foco": "WIN_INDICE"
        },
        "analise_operacional": {
            "WIN_INDICE": vies_win
        }
    }

    # Gravação do resultado
    try:
        os.makedirs(COLETAS_DIR, exist_ok=True)
        with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(decisao_final, f, indent=2, ensure_ascii=False)
        print(f"✅ Decisão do Core salva em: {FILE_OUTPUT.name}")
    except Exception as e:
        print(f"[ERRO CRÍTICO] Não foi possível salvar a decisão do Core: {str(e)}")

    # Exibição do resumo no terminal
    print("\n" + "=" * 60)
    print(" 🎯 DECISÃO CORE - VIÉS DE ABERTURA (MINI ÍNDICE) ")
    print("=" * 60)
    print(f" Mini Índice (WIN) : {vies_win['vies_final']} (Score: {vies_win['score_numeric']})")
    print(" Fatores Determinantes:")
    for fato in vies_win["fatores_relevantes"]:
        print(f"   • {fato}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    executar_core()