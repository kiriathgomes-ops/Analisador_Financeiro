# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_ajuste.py
from typing import Dict, Any
from ..dados.schemas import AnaliseAjuste

def analisar_ajuste(preco: float, ajuste: float, tolerancia: float = 0.5) -> AnaliseAjuste:
    """
    Analisa a posição do preço em relação ao ajuste.
    
    Args:
        preco: preço atual ou projetado
        ajuste: valor do ajuste oficial
        tolerancia: pontos para considerar como "NEUTRO"
    
    Returns:
        AnaliseAjuste com distância e posição
    """
    if ajuste == 0:
        return AnaliseAjuste(
            distancia_pontos=0.0,
            distancia_percentual=0.0,
            posicao="NEUTRO"
        )
    
    distancia = preco - ajuste
    percentual = (distancia / ajuste) * 100
    
    if distancia > tolerancia:
        posicao = "ACIMA"
    elif distancia < -tolerancia:
        posicao = "ABAIXO"
    else:
        posicao = "NEUTRO"
    
    return AnaliseAjuste(
        distancia_pontos=distancia,
        distancia_percentual=round(percentual, 4),
        posicao=posicao
    )

def atualizar_analise_pos_abertura(
    ajuste: AnaliseAjuste,
    preco_atual: float,
    ajuste_ref: float,
    preco_anterior: float = None
) -> AnaliseAjuste:
    """
    Atualiza a análise após a abertura real, verificando se houve teste,
    rejeição, aceitação, perda ou recuperação.
    """
    # Primeiro, refaz a análise básica
    nova = analisar_ajuste(preco_atual, ajuste_ref)
    
    # Se não tivermos o preço anterior, não podemos detectar eventos
    if preco_anterior is None:
        return nova
    
    # Verifica teste: se o preço anterior estava do outro lado do ajuste
    if (preco_anterior > ajuste_ref and preco_atual <= ajuste_ref) or \
       (preco_anterior < ajuste_ref and preco_atual >= ajuste_ref):
        nova.testou_ajuste = True
        
        # Verifica se houve rejeição ou aceitação
        # Rejeição: preço volta para o lado original
        if (preco_atual > ajuste_ref and preco_anterior > ajuste_ref) or \
           (preco_atual < ajuste_ref and preco_anterior < ajuste_ref):
            nova.rejeitou = True
        else:
            nova.aceitou = True
    
    # Verifica perda: se estava acima e agora está abaixo com folga
    if preco_anterior > ajuste_ref + 0.5 and preco_atual < ajuste_ref - 0.5:
        nova.perdeu = True
    
    # Verifica recuperação: se estava abaixo e agora está acima com folga
    if preco_anterior < ajuste_ref - 0.5 and preco_atual > ajuste_ref + 0.5:
        nova.recuperou = True
    
    return nova