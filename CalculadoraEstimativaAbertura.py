# ============================================================
# ARQUIVO: CalculadoraEstimativaAbertura.py
# MOTIVO: Processar dados validados e gerar estimativas de abertura
# ============================================================

import json
import os
from datetime import datetime

# Configuração de Caminhos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
FILE_INPUT = os.path.join(COLETAS_DIR, "Dados_Validados.json")
FILE_OUTPUT = os.path.join(COLETAS_DIR, "EstimativaAbertura.json")


def calc_win(ativos_dict):
    ewz = ativos_dict.get("EWZ", {}).get("change_percent", 0.0) or 0.0
    sp500 = ativos_dict.get("SP500_FUT", {}).get("change_percent", 0.0) or 0.0
    vale = ativos_dict.get("VALE_ADR", {}).get("change_percent", 0.0) or 0.0
    petr = ativos_dict.get("PETR_ADR", {}).get("change_percent", 0.0) or 0.0
    itub = ativos_dict.get("ITUB_ADR", {}).get("change_percent", 0.0) or 0.0
    bbd = ativos_dict.get("BBD_ADR", {}).get("change_percent", 0.0) or 0.0
    iron = ativos_dict.get("IRON_ORE", {}).get("change_percent", 0.0) or 0.0
    oil = ativos_dict.get("CRUDE_OIL", {}).get("change_percent", 0.0) or 0.0

    cesta_adrs = (vale * 0.30) + (petr * 0.25) + (itub * 0.25) + (bbd * 0.20)
    cesta_commodities = (iron * 0.50) + (oil * 0.50)
    var_pct = (ewz * 0.30) + (cesta_adrs * 0.35) + (sp500 * 0.20) + (cesta_commodities * 0.15)

    ajuste = ativos_dict.get("WIN_AJUSTE", {}).get("close") or ativos_dict.get("WIN_FUT", {}).get("close", 0)
    abertura = ajuste * (1 + (var_pct / 100)) if ajuste else 0

    return {
        "variacao_teorica_pct": round(var_pct, 4),
        "pontos_ajuste_base": ajuste,
        "abertura_teorica_pontos": round(abertura, 0)
    }


def calc_wdo(ativos_dict):
    usd_brl = ativos_dict.get("USD_BRL", {}).get("change_percent", 0.0) or 0.0
    dxy = ativos_dict.get("DXY", {}).get("change_percent", 0.0) or 0.0
    usd_mxn = ativos_dict.get("USD_MXN", {}).get("change_percent", 0.0) or 0.0

    var_pct = (usd_brl * 0.40) + (dxy * 0.30) + (usd_mxn * 0.30)
    ajuste = ativos_dict.get("WDO_AJUSTE", {}).get("close") or ativos_dict.get("WDO_FUT", {}).get("close", 0)
    abertura = ajuste * (1 + (var_pct / 100)) if ajuste else 0

    return {
        "variacao_teorica_pct": round(var_pct, 4),
        "pontos_ajuste_base": ajuste,
        "abertura_teorica_pontos": round(abertura, 3)
    }


def calc_pivot(obj):
    if not obj:
        return None
    high = obj.get("high")
    low = obj.get("low")
    close = obj.get("close")
    
    if not (high and low and close):
        return None

    pp = (high + low + close) / 3
    return {
        "PP": round(pp, 2),
        "R1": round((2 * pp) - low, 2),
        "R2": round(pp + (high - low), 2),
        "S1": round((2 * pp) - high, 2),
        "S2": round(pp - (high - low), 2)
    }


def processar_calculos():
    print(f"--> Verificando diretório base: {BASE_DIR}")
    print(f"--> Procurando arquivo em: {FILE_INPUT}")

    if not os.path.exists(FILE_INPUT):
        print(f"\n[ERRO CRÍTICO] O arquivo '{FILE_INPUT}' NÃO EXISTE!")
        print("Certifique-se de que a pasta 'Coletas' existe e contém 'Dados_Validados.json'.")
        return

    print("--> Arquivo Dados_Validados.json encontrado! Lendo dados...")
    
    try:
        with open(FILE_INPUT, "r", encoding="utf-8") as f:
            dados_json = json.load(f)

        ativos_lista = dados_json.get("ativos_validados", [])
        print(f"--> Total de ativos carregados do JSON: {len(ativos_lista)}")

        ativos_dict = {item["ativo_id"]: item for item in ativos_lista}

        resultado = {
            "metadata_calculo": {
                "timestamp_calculo": datetime.now().isoformat(),
                "total_ativos_processados": len(ativos_dict)
            },
            "estimativas_abertura": {
                "WIN_INDICE": calc_win(ativos_dict),
                "WDO_DOLAR": calc_wdo(ativos_dict)
            },
            "pivot_points": {
                "WIN_FUT": calc_pivot(ativos_dict.get("WIN_FUT")),
                "WDO_FUT": calc_pivot(ativos_dict.get("WDO_FUT"))
            },
            "resumo_macro": {
                "vix": ativos_dict.get("VIX", {}).get("close"),
                "di1_2027": ativos_dict.get("DI1_2027", {}).get("close"),
                "di1_2029": ativos_dict.get("DI1_2029", {}).get("close"),
                "iron_ore": ativos_dict.get("IRON_ORE", {}).get("close"),
                "crude_oil": ativos_dict.get("CRUDE_OIL", {}).get("close"),
                "gold": ativos_dict.get("GOLD", {}).get("close")
            }
        }

        os.makedirs(COLETAS_DIR, exist_ok=True)
        with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)

        print("\n============================================================")
        print(f" SUCCESS: Arquivo gravado em: {FILE_OUTPUT}")
        print("============================================================")

    except Exception as e:
        print(f"\n[ERRO NA EXECUÇÃO] Falha ao processar os dados: {str(e)}")


if __name__ == "__main__":
    processar_calculos()