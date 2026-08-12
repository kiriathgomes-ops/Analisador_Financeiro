# ============================================================
# ARQUIVO: Engine_Vies.py
# MOTIVO: Core Engine - Processamento de Viés de Abertura (WIN/WDO)
# INTEGRADO COM: Noticias_Impacto_Dia.json + DadosAtivosUnificados.json (Last)
# ============================================================

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")

FILE_ESTIMATIVA = os.path.join(COLETAS_DIR, "EstimativaAbertura.json")
FILE_METRICAS = os.path.join(COLETAS_DIR, "Metricas_Calculadas.json")
FILE_NOTICIAS = os.path.join(COLETAS_DIR, "Noticias_Impacto_Dia.json")
FILE_ATIVOS = os.path.join(COLETAS_DIR, "DadosAtivosUnificados.json")  # NOVO
FILE_OUTPUT = os.path.join(COLETAS_DIR, "Decisao_Core.json")


def carregar_json(caminho):
    if not os.path.exists(caminho):
        print(f"[AVISO] Arquivo não encontrado: {os.path.basename(caminho)}")
        return {}
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def calcular_vies_win(estimativa, metricas, noticias, spread_win_last_ajuste=0.0):
    """Calcula o Score do WIN de -10.0 (Forte Venda) a +10.0 (Forte Compra) com Trava de Volatilidade de Notícias."""
    score = 0.0
    fatos = []

    # 1. Abertura Teórica
    var_teorica = estimativa.get("WIN_INDICE", {}).get(
        "variacao_teorica_pct", 0.0
    )
    if var_teorica > 0.5:
        score += 3.0
        fatos.append(f"Teórico WIN positivo (+{var_teorica:.2f}%)")
    elif var_teorica < -0.5:
        score -= 3.0
        fatos.append(f"Teórico WIN negativo ({var_teorica:.2f}%)")

    # 2. Indicador Composto de ADRs
    ind_adrs = metricas.get("indicadores_compostos", {}).get(
        "indicador_adrs_brasileiras"
    )
    if ind_adrs is not None:
        if ind_adrs > 1.0:
            score += 2.5
            fatos.append(f"ADRs fortes no exterior (+{ind_adrs:.2f}%)")
        elif ind_adrs < -1.0:
            score -= 2.5
            fatos.append(f"ADRs fracas no exterior ({ind_adrs:.2f}%)")

    # 3. Risco Global (VIX)
    vix_change = metricas.get("indicadores_macro", {}).get("vix_change_pct")
    if vix_change is not None:
        if vix_change > 5.0:
            score -= 2.0
            fatos.append(
                f"Aumento de Risco Global / VIX em alta (+{vix_change:.1f}%)"
            )
        elif vix_change < -5.0:
            score += 1.5
            fatos.append(
                f"Queda de Risco Global / VIX caindo ({vix_change:.1f}%)"
            )

    # 4. Commodities (Petróleo/Minério)
    ind_ext = metricas.get("indicadores_compostos", {}).get(
        "indicador_mercado_externo"
    )
    if ind_ext is not None:
        if ind_ext > 0.8:
            score += 2.5
            fatos.append(
                f"Commodities e Mercado Externo favoráveis (+{ind_ext:.2f}%)"
            )
        elif ind_ext < -0.8:
            score -= 2.5
            fatos.append(
                f"Commodities e Mercado Externo pressionados ({ind_ext:.2f}%)"
            )

    # ============================================================
    # NOVA REGRA: Spread entre Last (Candle Anterior) e Ajuste Oficial
    # ============================================================
    LIMIAR_SPREAD_WIN = 100  # 100 pontos de diferença já é relevante
    if spread_win_last_ajuste != 0.0:
        if spread_win_last_ajuste > LIMIAR_SPREAD_WIN:
            score += 2.0
            fatos.append(f"🔺 Last acima do ajuste em {spread_win_last_ajuste:.0f} pts (viés comprador)")
        elif spread_win_last_ajuste < -LIMIAR_SPREAD_WIN:
            score -= 2.0
            fatos.append(f"🔻 Last abaixo do ajuste em {abs(spread_win_last_ajuste):.0f} pts (viés vendedor)")
        else:
            fatos.append(f"⚖️ Spread Last vs Ajuste dentro da normalidade ({spread_win_last_ajuste:+.0f} pts)")

    # ============================================================
    # REGRA DE IMPACTO DAS NOTÍCIAS NO WIN
    # ============================================================
    alertas_noticias = noticias.get("alertas", {})

    # Trava 1: Notícia 3 Estrelas no Brasil às 09:00 (Abertura WIN)
    if alertas_noticias.get("tem_3_estrelas_brasil_0900"):
        fatos.append("🚨 TRAVA CRÍTICA: Notícia ⭐⭐⭐ no Brasil às 09:00! Alta Volatilidade na abertura.")
        score *= 0.5

    # Trava 2: Risco Total do Dia Extremo
    classificacao_impacto = noticias.get("resumo", {}).get("classificacao", "")
    if classificacao_impacto == "EXTREMO":
        fatos.append("⚠️ Risco Global de Notícias EXTREMO no dia. Mão reduzida recomendada.")
        score *= 0.8

    # Trava 3: Acúmulo de Notícias 2 Estrelas no mesmo horário
    if alertas_noticias.get("tem_multiplas_2_estrelas_mesmo_horario"):
        horarios = [item["hora"] for item in alertas_noticias.get("horarios_multiplas_2_estrelas", [])]
        fatos.append(f"⚠️ Atenção para acúmulo de eventos ⭐⭐ nos horários: {', '.join(horarios)}")

    # Classificação Final
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


def calcular_vies_wdo(estimativa, metricas, noticias, spread_wdo_last_ajuste=0.0):
    """Calcula o Score do WDO de -10.0 (Forte Venda) a +10.0 (Forte Compra) considerando Notícias."""
    score = 0.0
    fatos = []

    # 1. Abertura Teórica WDO
    var_teorica = estimativa.get("WDO_DOLAR", {}).get(
        "variacao_teorica_pct", 0.0
    )
    if var_teorica > 0.3:
        score += 3.5
        fatos.append(f"Teórico WDO em alta (+{var_teorica:.2f}%)")
    elif var_teorica < -0.3:
        score -= 3.5
        fatos.append(f"Teórico WDO em baixa ({var_teorica:.2f}%)")

    # 2. Spread WDO vs PTAX
    spread_pts = metricas.get("cambio_e_arbitragem", {}).get(
        "spread_wdo_ptax_pontos"
    )
    if spread_pts is not None:
        if spread_pts > 15.0:
            score -= 2.0
            fatos.append(f"Spread WDO x PTAX esticado (+{spread_pts} pts)")
        elif spread_pts < -15.0:
            score += 2.0
            fatos.append(f"Spread WDO x PTAX descontado ({spread_pts} pts)")

    # 3. Inclinação da Curva DI
    inclinacao_di = metricas.get("curva_juros_b3", {}).get(
        "inclinacao_29_27_bps"
    )
    if inclinacao_di is not None:
        if inclinacao_di > 30.0:
            score += 2.0
            fatos.append(f"Curva de Juros (DI) abrindo (+{inclinacao_di} bps)")
        elif inclinacao_di < -10.0:
            score -= 1.5
            fatos.append(f"Curva de Juros (DI) fechando ({inclinacao_di} bps)")

    # ============================================================
    # NOVA REGRA: Spread entre Last (Candle Anterior) e Ajuste Oficial
    # ============================================================
    LIMIAR_SPREAD_WDO = 10  # 10 pontos de diferença já é relevante para o dólar
    if spread_wdo_last_ajuste != 0.0:
        if spread_wdo_last_ajuste > LIMIAR_SPREAD_WDO:
            score += 1.5
            fatos.append(f"🔺 Last acima do ajuste em {spread_wdo_last_ajuste:.1f} pts (viés comprador dólar)")
        elif spread_wdo_last_ajuste < -LIMIAR_SPREAD_WDO:
            score -= 1.5
            fatos.append(f"🔻 Last abaixo do ajuste em {abs(spread_wdo_last_ajuste):.1f} pts (viés vendedor dólar)")
        else:
            fatos.append(f"⚖️ Spread Last vs Ajuste dentro da normalidade ({spread_wdo_last_ajuste:+.1f} pts)")

    # ============================================================
    # REGRA DE IMPACTO DAS NOTÍCIAS NO WDO
    # ============================================================
    alertas_noticias = noticias.get("alertas", {})

    if alertas_noticias.get("tem_3_estrelas_outros_horarios"):
        noticias_3 = alertas_noticias.get("noticias_3_estrelas_outros_horarios", [])
        for n in noticias_3:
            if n.get("moeda") in ["USD", "BRL"]:
                fatos.append(f"🚨 Atenção: Notícia ⭐⭐⭐ [{n['moeda']}] às {n['hora']} - {n['evento']}")

    # Classificação Final
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

    return {
        "score_numeric": round(score, 2),
        "vies_final": vies,
        "fatores_relevantes": fatos,
    }


def executar_core():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Executando Core Engine de Viés...")

    estimativas = carregar_json(FILE_ESTIMATIVA)
    metricas = carregar_json(FILE_METRICAS)
    noticias = carregar_json(FILE_NOTICIAS)
    
    # ============================================================
    # NOVO: Carrega DadosAtivosUnificados para pegar WIN_LAST_TICK e WDO_LAST_TICK
    # ============================================================
    ativos_data = carregar_json(FILE_ATIVOS)
    ativos = ativos_data.get("ativos", {}) if ativos_data else {}
    
    win_last = ativos.get("WIN_LAST_TICK", {}).get("preco", 0.0)
    wdo_last = ativos.get("WDO_LAST_TICK", {}).get("preco", 0.0)
    win_ajuste = ativos.get("WIN_AJUSTE", {}).get("preco", 0.0)
    wdo_ajuste = ativos.get("WDO_AJUSTE", {}).get("preco", 0.0)

    # Calcula os spreads
    spread_win_last_ajuste = win_last - win_ajuste if win_last and win_ajuste else 0.0
    spread_wdo_last_ajuste = wdo_last - wdo_ajuste if wdo_last and wdo_ajuste else 0.0

    vies_win = calcular_vies_win(
        estimativas.get("estimativas_abertura", {}), 
        metricas, 
        noticias,
        spread_win_last_ajuste
    )
    vies_wdo = calcular_vies_wdo(
        estimativas.get("estimativas_abertura", {}), 
        metricas, 
        noticias,
        spread_wdo_last_ajuste
    )

    decisao_final = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "status_pipeline": "OK",
        },
        "analise_operacional": {
            "WIN_INDICE": vies_win,
            "WDO_DOLAR": vies_wdo,
        },
    }

    os.makedirs(COLETAS_DIR, exist_ok=True)
    with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(decisao_final, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(" 🎯 DECISÃO CORE - VIÉS DE ABERTURA ")
    print("=" * 60)
    print(
        f" Mini Índice (WIN) : {vies_win['vies_final']} (Score: {vies_win['score_numeric']})"
    )
    for f in vies_win["fatores_relevantes"]:
        print(f"   • {f}")
    print("------------------------------------------------------------")
    print(
        f" Mini Dólar (WDO)  : {vies_wdo['vies_final']} (Score: {vies_wdo['score_numeric']})"
    )
    for f in vies_wdo["fatores_relevantes"]:
        print(f"   • {f}")
    print("=" * 60)
    print(f"Arquivo gerado: {os.path.basename(FILE_OUTPUT)}\n")


if __name__ == "__main__":
    executar_core()