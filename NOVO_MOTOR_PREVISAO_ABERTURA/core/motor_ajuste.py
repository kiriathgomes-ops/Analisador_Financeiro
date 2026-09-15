# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_ajuste.py
from typing import Dict, Any
from ..dados.schemas import AnaliseAjuste


# Tolerância padrão para considerar o preço "neutro" em relação ao ajuste.
# O WIN tem tick de 5 pontos; 50 pontos representa 10 ticks de margem.
# Valores menores (ex: 0.5) classificam ruído como sinal.
TOLERANCIA_AJUSTE_PADRAO = 50.0


def analisar_ajuste(
    preco: float,
    ajuste: float,
    tolerancia: float = TOLERANCIA_AJUSTE_PADRAO,
) -> AnaliseAjuste:
    """
    Analisa a posição do preço em relação ao ajuste.

    Args:
        preco: preço atual ou projetado
        ajuste: valor do ajuste oficial
        tolerancia: pontos para considerar como "NEUTRO"
                    (default: 50 pts — calibrado para o WIN)

    Returns:
        AnaliseAjuste com distância e posição
    """
    if ajuste == 0:
        return AnaliseAjuste(
            distancia_pontos=0.0,
            distancia_percentual=0.0,
            posicao="NEUTRO",
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
        posicao=posicao,
    )


def atualizar_analise_pos_abertura(
    ajuste: AnaliseAjuste,
    preco_atual: float,
    ajuste_ref: float,
    preco_anterior: float = None,
) -> AnaliseAjuste:
    """
    Atualiza a análise após a abertura real, verificando se houve teste,
    rejeição, aceitação, perda ou recuperação.
    """
    nova = analisar_ajuste(preco_atual, ajuste_ref)

    if preco_anterior is None:
        return nova

    # Teste: cruzou o ajuste
    if (preco_anterior > ajuste_ref and preco_atual <= ajuste_ref) or \
       (preco_anterior < ajuste_ref and preco_atual >= ajuste_ref):
        nova.testou_ajuste = True

        if (preco_atual > ajuste_ref and preco_anterior > ajuste_ref) or \
           (preco_atual < ajuste_ref and preco_anterior < ajuste_ref):
            nova.rejeitou = True
        else:
            nova.aceitou = True

    # Perda
    if preco_anterior > ajuste_ref + TOLERANCIA_AJUSTE_PADRAO and \
       preco_atual < ajuste_ref - TOLERANCIA_AJUSTE_PADRAO:
        nova.perdeu = True

    # Recuperação
    if preco_anterior < ajuste_ref - TOLERANCIA_AJUSTE_PADRAO and \
       preco_atual > ajuste_ref + TOLERANCIA_AJUSTE_PADRAO:
        nova.recuperou = True

    return nova