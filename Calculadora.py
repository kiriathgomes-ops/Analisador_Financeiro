# ============================================================
# ARQUIVO: Calculadora.py
# DATA: 30/07/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Fase 4 - Cálculo de Spreads, Curva DI, Mercado Externo
#         e Indicadores Compostos alinhados aos IDs do Validador.
# ============================================================

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
FILE_INPUT = os.path.join(COLETAS_DIR, "Dados_Validados.json")
FILE_OUTPUT = os.path.join(COLETAS_DIR, "Metricas_Calculadas.json")


def carregar_dados():
    if not os.path.exists(FILE_INPUT):
        print(f"[ERRO] Arquivo não encontrado: {FILE_INPUT}")
        return None
    with open(FILE_INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Transforma a lista em dicionário chaveado pelo ativo_id padronizado
    mapa = {
        item["ativo_id"]: item for item in data.get("ativos_validados", [])
    }
    return mapa


def calcular_metricas():
    mapa = carregar_dados()
    if not mapa:
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando engine de cálculos...")

    # 1. SPREAD DÓLAR FUTURO VS PTAX
    ptax = mapa.get("USD_PTAX", {}).get("close")
    wdo = mapa.get("WDO_FUT", {}).get("close")

    spread_wdo_ptax_pts = None
    spread_wdo_ptax_pct = None
    if ptax and wdo:
        ptax_em_pontos = ptax * 1000
        spread_wdo_ptax_pts = round(wdo - ptax_em_pontos, 2)
        spread_wdo_ptax_pct = round(((wdo / ptax_em_pontos) - 1) * 100, 4)

    # 2. INCLINAÇÃO DA CURVA DE JUROS (DI1)
    di27 = mapa.get("DI1_2027", {}).get("close")
    di29 = mapa.get("DI1_2029", {}).get("close")

    inclinacao_di_bps = None
    if di27 and di29:
        inclinacao_di_bps = round((di29 - di27) * 100, 1)

    # 3. MÉTRICA DE RISCO GLOBAL & INDICADOR MERCADO EXTERNO
    vix_obj = mapa.get("VIX", {})
    vix_close = vix_obj.get("close")
    vix_pct = vix_obj.get("change_percent")

    dxy = mapa.get("DXY", {}).get("close")

    crude_obj = mapa.get("CRUDE_OIL", {})
    crude_close = crude_obj.get("close")
    crude_pct = crude_obj.get("change_percent")

    # Minério FEF2! (Utilizando a chave padronizada pelo Validador: IRON_ORE_2M)
    fef2_obj = mapa.get("IRON_ORE_2M", {})
    iron_fef2_close = fef2_obj.get("close")
    iron_fef2_pct = fef2_obj.get("change_percent")

    # --- CÁLCULO 1: Indicador Mercado Externo ---
    # Fórmula: -(VIX_pct) + CL1!_pct + FEF2!_pct
    ind_mercado_externo = None
    if vix_pct is not None and crude_pct is not None and iron_fef2_pct is not None:
        ind_mercado_externo = round((-vix_pct) + crude_pct + iron_fef2_pct, 4)

    # 4. RESUMO DE ADRs & INDICADOR ADRs BRASILEIRAS
    ewz_var = mapa.get("EWZ", {}).get("change_percent")
    sp_var = mapa.get("SP500_FUT", {}).get("change_percent")
    nq_var = mapa.get("NASDAQ_FUT", {}).get("change_percent")

    adrs_chaves = [
        "BBD_ADR",
        "ITUB_ADR",
        "PETR_ADR",
        "VALE_ADR",
        "BBAS_ADR",
        "B3_ADR",
    ]

    resumo_adrs = {}
    soma_variacoes_adrs = 0.0
    qtd_adrs_validas = 0

    for adr_id in adrs_chaves:
        if adr_id in mapa:
            obj = mapa[adr_id]
            c_val = obj.get("close")
            pct_val = obj.get("change_percent")

            resumo_adrs[adr_id] = {
                "close": c_val,
                "change_percent": pct_val,
            }

            if pct_val is not None:
                soma_variacoes_adrs += pct_val
                qtd_adrs_validas += 1

    # --- CÁLCULO 2: Indicador ADRs Brasileiras ---
    ind_adrs_brasileiras = None
    if qtd_adrs_validas > 0:
        ind_adrs_brasileiras = round(soma_variacoes_adrs, 4)

    # Estrutura de Métricas Consolidadas
    metricas = {
        "metadata_calculo": {
            "timestamp": datetime.now().isoformat(),
            "total_ativos_processados": len(mapa),
        },
        "cambio_e_arbitragem": {
            "usd_ptax": ptax,
            "wdo_fut": wdo,
            "spread_wdo_ptax_pontos": spread_wdo_ptax_pts,
            "spread_wdo_ptax_percentual": spread_wdo_ptax_pct,
        },
        "curva_juros_b3": {
            "di1_2027_taxa": di27,
            "di1_2029_taxa": di29,
            "inclinacao_29_27_bps": inclinacao_di_bps,
        },
        "indicadores_macro": {
            "vix": vix_close,
            "vix_change_pct": vix_pct,
            "dxy": dxy,
            "crude_oil": crude_close,
            "crude_oil_change_pct": crude_pct,
            "iron_ore_fef2": {
                "close": iron_fef2_close,
                "change_percent": iron_fef2_pct,
            },
        },
        "performance_relativa": {
            "ewz_change_pct": ewz_var,
            "sp500_fut_change_pct": sp_var,
            "nasdaq_fut_change_pct": nq_var,
            "adrs_brasileiras": resumo_adrs,
        },
        "indicadores_compostos": {
            "indicador_mercado_externo": ind_mercado_externo,
            "indicador_adrs_brasileiras": ind_adrs_brasileiras,
        },
    }

    with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(metricas, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(" PAINEL DE MÉTRICAS CALCULADAS ")
    print("=" * 60)
    print(
        f"Spread WDO vs PTAX      : {spread_wdo_ptax_pts} pts"
        f" ({spread_wdo_ptax_pct}%)"
    )
    print(f"Inclinação DI (29-27)   : {inclinacao_di_bps} bps")
    print(f"VIX (Volatilidade)      : {vix_close} ({vix_pct}%)")
    print(f"Minério FEF2 (2º Mês)   : {iron_fef2_close} ({iron_fef2_pct}%)")
    print("------------------------------------------------------------")
    print(f"IND. MERCADO EXTERNO    : {ind_mercado_externo}%")
    print(f"IND. ADRs BRASILEIRAS   : {ind_adrs_brasileiras}%")
    print("=" * 60)
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Arquivo gerado:"
        f" {os.path.basename(FILE_OUTPUT)}\n"
    )


if __name__ == "__main__":
    print("============================================================")
    print(" FASE 4: ENGINE DE CÁLCULO E MÉTRICAS FINANCEIRAS")
    print("============================================================")
    calcular_metricas()