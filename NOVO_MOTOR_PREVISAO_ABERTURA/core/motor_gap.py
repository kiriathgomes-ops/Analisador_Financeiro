# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_gap.py
#
# ATUALIZAÇÃO 18/09/2026:
#   Limiares de classificação migraram de pontos absolutos para % do
#   preço de referência. Ver LIMIARES_PCT para detalhes da calibração.
from typing import Dict, Any
from ..dados.schemas import ClassificacaoGAP

# ============================================================
# Limiares para classificação de GAP (% do preço de referência)
# ============================================================
# Antes eram pontos absolutos (20/50/100/200). Problema: não escalavam
# com o preço do WIN (que já esteve em 100k e hoje está em 188k).
# Um gap de 200 pts era 0.2% em 2026, mas seria 0.4% em 2020.
#
# Agora usamos % do preço de referência (fechamento anterior). Isso
# escala automaticamente com o tempo e com a inflação do índice.
#
# Valores calibrados com base no ATR M5 atual (~120 pts = 0.06%) e na
# experiência operacional do WIN:
#   MICRO    → até 0.05%    (~94 pts hoje)    — ruído de leilão
#   PEQUENO  → 0.05-0.15%   (~94-283 pts)     — gap normal
#   MODERADO → 0.15-0.30%   (~283-566 pts)    — gap relevante
#   FORTE    → 0.30-0.60%   (~566-1132 pts)   — gap de evento
#   EXTREMO  → >0.60%       (>1132 pts)       — gap histórico (raro)
# ============================================================
LIMIARES_PCT = {
    "MICRO": 0.05,
    "PEQUENO": 0.15,
    "MODERADO": 0.30,
    "FORTE": 0.60,
    "EXTREMO": 999.0
}

def classificar_gap(
    preco_abertura: float,
    referencia_fechamento: float,
    referencia_ajuste: float = None
) -> ClassificacaoGAP:
    """
    Classifica o GAP com base no preço de abertura projetado/real.
    
    Args:
        preco_abertura: preço de abertura (teórico ou real)
        referencia_fechamento: fechamento anterior (ou ajuste)
        referencia_ajuste: ajuste oficial (opcional, para gap contra ajuste)
    
    Returns:
        ClassificacaoGAP com todos os campos preenchidos
    """
    if referencia_fechamento == 0:
        referencia_fechamento = 1e-6  # evitar divisão por zero
    
    gap_pontos = preco_abertura - referencia_fechamento
    gap_percentual = (gap_pontos / referencia_fechamento) * 100
    
    # Gap contra ajuste (se fornecido)
    gap_ajuste = None
    if referencia_ajuste is not None:
        gap_ajuste = preco_abertura - referencia_ajuste
    
    # Classificação por % (não mais por pontos absolutos — ver LIMIARES_PCT)
    abs_gap_pct = abs(gap_percentual)
    
    if abs_gap_pct < LIMIARES_PCT["MICRO"]:
        intensidade = "MICRO"
    elif abs_gap_pct < LIMIARES_PCT["PEQUENO"]:
        intensidade = "PEQUENO"
    elif abs_gap_pct < LIMIARES_PCT["MODERADO"]:
        intensidade = "MODERADO"
    elif abs_gap_pct < LIMIARES_PCT["FORTE"]:
        intensidade = "FORTE"
    else:
        intensidade = "EXTREMO"
    
    # Log enxuto (facilita debug e ver o limiar aplicado)
    print(f"[GAP] {gap_pontos:+.0f} pts ({gap_percentual:+.4f}%) -> {intensidade}")
    
    return ClassificacaoGAP(
        gap_pontos=gap_pontos,
        gap_percentual=round(gap_percentual, 4),
        gap_contra_fechamento=gap_pontos,
        gap_contra_ajuste=gap_ajuste if gap_ajuste is not None else 0.0,
        intensidade=intensidade,
        classificacao=f"GAP {intensidade}"
    )