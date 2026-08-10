# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_gap.py
from typing import Dict, Any
from ..dados.schemas import ClassificacaoGAP

# Limiares para classificação de GAP (em pontos)
LIMIARES = {
    "MICRO": 20,
    "PEQUENO": 50,
    "MODERADO": 100,
    "FORTE": 200,
    "EXTREMO": 999999
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
    
    abs_gap = abs(gap_pontos)
    
    # Determinar intensidade
    if abs_gap < LIMIARES["MICRO"]:
        intensidade = "MICRO"
    elif abs_gap < LIMIARES["PEQUENO"]:
        intensidade = "PEQUENO"
    elif abs_gap < LIMIARES["MODERADO"]:
        intensidade = "MODERADO"
    elif abs_gap < LIMIARES["FORTE"]:
        intensidade = "FORTE"
    else:
        intensidade = "EXTREMO"
    
    return ClassificacaoGAP(
        gap_pontos=gap_pontos,
        gap_percentual=round(gap_percentual, 4),
        gap_contra_fechamento=gap_pontos,
        gap_contra_ajuste=gap_ajuste if gap_ajuste is not None else 0.0,
        intensidade=intensidade,
        classificacao=f"GAP {intensidade}"
    )