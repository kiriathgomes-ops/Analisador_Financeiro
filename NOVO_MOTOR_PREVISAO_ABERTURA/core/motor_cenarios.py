# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_cenarios.py
from typing import Tuple, Dict
from ..dados.schemas import Cenario, ClassificacaoGAP, AnaliseAjuste


def _calcular_probabilidades(
    gap: ClassificacaoGAP, ajuste: AnaliseAjuste
) -> Dict[str, float]:
    """
    Calcula probabilidades (0-100) dos 5 comportamentos possíveis, com base
    na distância do preço até o ajuste e na intensidade do gap.

    Retorna dict normalizado (soma ~100):
      continuar | rejeitar | recuperar | retornar | falso
    """
    dist = abs(ajuste.distancia_pontos or 0.0)

    # Base por proximidade ao ajuste
    if dist <= 50:
        base = {"continuar": 15, "rejeitar": 30, "recuperar": 20, "retornar": 25, "falso": 10}
    elif dist <= 150:
        base = {"continuar": 30, "rejeitar": 25, "recuperar": 15, "retornar": 15, "falso": 15}
    elif dist <= 300:
        base = {"continuar": 35, "rejeitar": 15, "recuperar": 10, "retornar": 15, "falso": 25}
    else:
        base = {"continuar": 25, "rejeitar": 10, "recuperar": 10, "retornar": 20, "falso": 35}

    # Ajuste por intensidade do gap
    if gap.intensidade in ("FORTE", "EXTREMO"):
        base["continuar"] += 5
        base["retornar"] = max(5, base["retornar"] - 5)
        base["falso"] = max(5, base["falso"] - 3)

    # Normaliza
    total = sum(base.values()) or 1
    return {k: round(v / total * 100, 1) for k, v in base.items()}


def gerar_cenarios(
    gap: ClassificacaoGAP, ajuste: AnaliseAjuste
) -> Tuple[Cenario, Cenario]:
    """
    Gera cenários principal e alternativo com probabilidades numéricas.

    A probabilidade_estimada é preenchida com o valor do comportamento
    dominante (principal) ou do alternativo.
    """
    probs = _calcular_probabilidades(gap, ajuste)

    # ---- Caso 1: Gap extremo ou forte ----
    if gap.intensidade in ("EXTREMO", "FORTE"):
        if gap.gap_pontos > 0:
            principal = Cenario(
                nome="CONTINUACAO_COMPRA",
                descricao="GAP positivo forte/extremo. Tendência compradora predominante.",
                condicao="Abertura com gap significativo acima do ajuste.",
                gatilho_entrada="Pullback com rejeição ou rompimento de topo.",
                confirmacao="Fechamento acima do ajuste após 15min.",
                invalidacao="Fechamento abaixo do ajuste ou perda total do gap.",
                probabilidade_estimada=probs["continuar"],
            )
            alternativo = Cenario(
                nome="TESTE_REJEICAO",
                descricao="Preço testa o gap e rejeita, mantendo viés comprador.",
                condicao="Retorno à zona do gap com candle de rejeição.",
                gatilho_entrada="Rejeição confirmada no nível do gap.",
                confirmacao="Fechamento acima do gap.",
                invalidacao="Perda total do gap com aceitação abaixo.",
                probabilidade_estimada=probs["rejeitar"],
            )
        else:
            principal = Cenario(
                nome="CONTINUACAO_VENDA",
                descricao="GAP negativo forte/extremo. Tendência vendedora predominante.",
                condicao="Abertura com gap significativo abaixo do ajuste.",
                gatilho_entrada="Pullback com rejeição ou rompimento de fundo.",
                confirmacao="Fechamento abaixo do ajuste após 15min.",
                invalidacao="Fechamento acima do ajuste ou recuperação total do gap.",
                probabilidade_estimada=probs["continuar"],
            )
            alternativo = Cenario(
                nome="RECUPERACAO",
                descricao="Preço testa o gap e o recupera, invertendo para compra.",
                condicao="Retorno ao gap com rompimento e aceitação acima.",
                gatilho_entrada="Romper o gap com volume.",
                confirmacao="Fechamento acima do gap.",
                invalidacao="Rejeição no gap e continuação da queda.",
                probabilidade_estimada=probs["recuperar"],
            )
        return principal, alternativo

    # ---- Caso 2: Gap moderado / pequeno → posição vs ajuste ----
    if ajuste.posicao == "ACIMA":
        principal = Cenario(
            nome="CONTINUACAO",
            descricao="Preço acima do ajuste. Viés comprador.",
            condicao="Abertura acima do ajuste e manutenção.",
            gatilho_entrada="Pullback com rejeição ou rompimento de topo.",
            confirmacao="Fechamento acima do ajuste após 15min.",
            invalidacao="Perda do ajuste com aceitação abaixo.",
            probabilidade_estimada=probs["continuar"],
        )
        alternativo = Cenario(
            nome="TESTE_REJEICAO",
            descricao="Testa o ajuste e rejeita, reforçando compra.",
            condicao="Retorno ao ajuste com candle de rejeição.",
            gatilho_entrada="Rejeição confirmada no ajuste.",
            confirmacao="Fechamento acima do ajuste.",
            invalidacao="Perda do ajuste com aceitação abaixo.",
            probabilidade_estimada=probs["rejeitar"],
        )
    elif ajuste.posicao == "ABAIXO":
        principal = Cenario(
            nome="CONTINUACAO",
            descricao="Preço abaixo do ajuste. Viés vendedor.",
            condicao="Abertura abaixo do ajuste e manutenção.",
            gatilho_entrada="Pullback com rejeição ou rompimento de fundo.",
            confirmacao="Fechamento abaixo do ajuste após 15min.",
            invalidacao="Recuperação do ajuste com aceitação acima.",
            probabilidade_estimada=probs["continuar"],
        )
        alternativo = Cenario(
            nome="RECUPERACAO",
            descricao="Testa o ajuste e o recupera, invertendo para compra.",
            condicao="Retorno ao ajuste com rompimento e aceitação acima.",
            gatilho_entrada="Romper o ajuste com volume.",
            confirmacao="Fechamento acima do ajuste.",
            invalidacao="Rejeição no ajuste e volta para baixo.",
            probabilidade_estimada=probs["recuperar"],
        )
    else:  # NEUTRO
        principal = Cenario(
            nome="NEUTRO",
            descricao="Preço próximo ao ajuste, aguardar definição.",
            condicao="Preço dentro da faixa de tolerância (±50 pts).",
            gatilho_entrada="Aguardar rompimento de topo ou fundo.",
            confirmacao="Fechamento fora da faixa com volume.",
            invalidacao="Permanência na faixa por mais de 15min.",
            probabilidade_estimada=probs["retornar"],
        )
        alternativo = principal

    return principal, alternativo