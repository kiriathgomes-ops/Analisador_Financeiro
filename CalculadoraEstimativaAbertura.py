# ============================================================
# ARQUIVO: CalculadoraEstimativaAbertura.py
# DATA: 30/07/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Processar dados validados e gerar estimativas de abertura
#         e pontos de pivô EXCLUSIVAMENTE para o Mini Índice (WIN).
# DESCRICAO:
#   Aplica modelo ponderado de precificação teórica de abertura para o WIN:
#     - Ponderação: EWZ (30%), Cesta ADRs (35%), S&P 500 Futuro (20%), Commodities (15%).
#   Calcula os pontos de pivô (PP, R1, R2, S1, S2) do WIN_FUT.
#   Gera o arquivo EstimativaAbertura.json.
# ============================================================

import json
import os
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO DE DIRETÓRIOS E ARQUIVOS
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
FILE_INPUT = os.path.join(COLETAS_DIR, "Dados_Validados.json")
FILE_OUTPUT = os.path.join(COLETAS_DIR, "EstimativaAbertura.json")

# ============================================================
# FUNÇÕES AUXILIARES DE SEGURANÇA DE DADOS
# ============================================================

def extrair_variacao(ativos_dict: dict, ativo_id: str) -> float:
    """Extrai a variação percentual de um ativo garantindo retorno numérico seguro."""
    dado = ativos_dict.get(ativo_id, {}).get("change_percent")
    return float(dado) if isinstance(dado, (int, float)) else 0.0

# ============================================================
# MOTORES DE CÁLCULO (EXCLUSIVO MINI ÍNDICE)
# ============================================================

def calc_win(ativos_dict: dict) -> dict:
    """
    Calcula a variação teórica e o preço de abertura estimado para o WIN.
    Ponderação:
      - EWZ: 30%
      - Cesta ADRs (VALE 30%, PETR 25%, ITUB 25%, BBD 20%): 35%
      - S&P 500 Futuro: 20%
      - Cesta Commodities (Minério FEF2 50%, Petróleo WTI 50%): 15%
    """
    ewz = extrair_variacao(ativos_dict, "EWZ")
    sp500 = extrair_variacao(ativos_dict, "SP500_FUT")
    vale = extrair_variacao(ativos_dict, "VALE_ADR")
    petr = extrair_variacao(ativos_dict, "PETR_ADR")
    itub = extrair_variacao(ativos_dict, "ITUB_ADR")
    bbd = extrair_variacao(ativos_dict, "BBD_ADR")
    
    iron = extrair_variacao(ativos_dict, "IRON_ORE_2M") or extrair_variacao(ativos_dict, "IRON_ORE")
    oil = extrair_variacao(ativos_dict, "CRUDE_OIL")

    cesta_adrs = (vale * 0.30) + (petr * 0.25) + (itub * 0.25) + (bbd * 0.20)
    cesta_commodities = (iron * 0.50) + (oil * 0.50)
    
    var_pct = (ewz * 0.30) + (cesta_adrs * 0.35) + (sp500 * 0.20) + (cesta_commodities * 0.15)

    # Busca preço base no ajuste da B3 ou no último contrato futuro
    ajuste_obj = ativos_dict.get("WIN_AJUSTE", {}) or ativos_dict.get("WIN_FUT", {})
    ajuste = ajuste_obj.get("close")

    abertura = 0.0
    if isinstance(ajuste, (int, float)) and ajuste > 0:
        abertura = ajuste * (1 + (var_pct / 100))

    return {
        "variacao_teorica_pct": round(var_pct, 4),
        "pontos_ajuste_base": ajuste,
        "abertura_teorica_pontos": round(abertura, 0)
    }


def calc_pivot(obj: dict) -> dict:
    """Calcula os níveis de Pivot Point Floor clássico (PP, R1, R2, S1, S2) para o WIN."""
    if not isinstance(obj, dict):
        return None
        
    high = obj.get("high")
    low = obj.get("low")
    
    # Prioriza o fechamento do dia anterior (previous_close).
    # Se não existir, usa o close padrão como fallback.
    close = obj.get("previous_close") or obj.get("close")
    
    if not all(isinstance(v, (int, float)) and v > 0 for v in [high, low, close]):
        return None

    pp = (high + low + close) / 3
    return {
        "PP": round(pp, 2),
        "R1": round((2 * pp) - low, 2),
        "R2": round(pp + (high - low), 2),
        "S1": round((2 * pp) - high, 2),
        "S2": round(pp - (high - low), 2)
    }


def processar_calculos() -> None:
    """Orquestra o cálculo de estimativas do Índice e gera o arquivo JSON final."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando processamento de estimativas (Índice apenas)...")
    print(f"--> Procurando arquivo em: {FILE_INPUT}")

    if not os.path.exists(FILE_INPUT):
        print(f"\n[ERRO CRÍTICO] O arquivo '{FILE_INPUT}' NÃO EXISTE!")
        return

    try:
        with open(FILE_INPUT, "r", encoding="utf-8") as f:
            dados_json = json.load(f)

        ativos_lista = dados_json.get("ativos_validados", [])
        ativos_dict = {item["ativo_id"]: item for item in ativos_lista}
        
        print(f"--> Total de ativos carregados: {len(ativos_dict)}")

        resultado = {
            "metadata_calculo": {
                "timestamp_calculo": datetime.now().isoformat(),
                "total_ativos_processados": len(ativos_dict)
            },
            "estimativa_abertura": {
                "WIN_INDICE": calc_win(ativos_dict)
            },
            "pivot_points": {
                "WIN_FUT": calc_pivot(ativos_dict.get("WIN_FUT"))
            },
            "resumo_macro": {
                "vix": ativos_dict.get("VIX", {}).get("close"),
                "di1_2027": ativos_dict.get("DI1_2027", {}).get("close"),
                "di1_2029": ativos_dict.get("DI1_2029", {}).get("close"),
                "iron_ore": ativos_dict.get("IRON_ORE_2M", {}).get("close") or ativos_dict.get("IRON_ORE", {}).get("close"),
                "crude_oil": ativos_dict.get("CRUDE_OIL", {}).get("close"),
                "gold": ativos_dict.get("GOLD", {}).get("close")
            }
        }

        os.makedirs(COLETAS_DIR, exist_ok=True)
        with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)

        print("============================================================")
        print(f" SUCCESS: Arquivo gravado em: {os.path.basename(FILE_OUTPUT)}")
        print("============================================================")

    except Exception as e:
        print(f"\n[ERRO NA EXECUÇÃO] Falha ao processar os dados: {str(e)}")


if __name__ == "__main__":
    print("============================================================")
    print(" FASE 4B: ESTIMATIVA DE ABERTURA E NÍVEIS TÉCNICOS (WIN)")
    print("============================================================")
    processar_calculos()