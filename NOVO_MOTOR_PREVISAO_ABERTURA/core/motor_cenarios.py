# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_cenarios.py
from typing import Tuple
from ..dados.schemas import Cenario, ClassificacaoGAP, AnaliseAjuste

def gerar_cenarios(gap: ClassificacaoGAP, ajuste: AnaliseAjuste) -> Tuple[Cenario, Cenario]:
    """
    Gera cenários principal e alternativo com base no gap e na posição em relação ao ajuste.
    """
    # Caso 1: GAP extremo ou forte (prioridade máxima)
    if gap.intensidade in ["EXTREMO", "FORTE"]:
        if gap.gap_pontos > 0:
            principal = Cenario(
                nome="CONTINUACAO_COMPRA",
                descricao="GAP positivo forte/extremo. Tendência compradora predominante.",
                condicao="Abertura com gap significativo acima do ajuste.",
                gatilho_entrada="Pullback com rejeição ou rompimento de topo.",
                confirmacao="Fechamento acima do ajuste após 15min.",
                invalidacao="Fechamento abaixo do ajuste ou perda total do gap."
            )
            alternativo = Cenario(
                nome="TESTE_REJEICAO",
                descricao="Preço testa o gap e rejeita, mantendo viés comprador.",
                condicao="Retorno à zona do gap com candle de rejeição.",
                gatilho_entrada="Rejeição confirmada no nível do gap.",
                confirmacao="Fechamento acima do gap.",
                invalidacao="Perda total do gap com aceitação abaixo."
            )
        else:
            principal = Cenario(
                nome="CONTINUACAO_VENDA",
                descricao="GAP negativo forte/extremo. Tendência vendedora predominante.",
                condicao="Abertura com gap significativo abaixo do ajuste.",
                gatilho_entrada="Pullback com rejeição ou rompimento de fundo.",
                confirmacao="Fechamento abaixo do ajuste após 15min.",
                invalidacao="Fechamento acima do ajuste ou recuperação total do gap."
            )
            alternativo = Cenario(
                nome="RECUPERACAO",
                descricao="Preço testa o gap e o recupera, invertendo para compra.",
                condicao="Retorno ao gap com rompimento e aceitação acima.",
                gatilho_entrada="Romper o gap com volume.",
                confirmacao="Fechamento acima do gap.",
                invalidacao="Rejeição no gap e continuação da queda."
            )
        return principal, alternativo
    
    # Caso 2: GAP moderado ou pequeno – usar posição em relação ao ajuste
    if ajuste.posicao == "ACIMA":
        principal = Cenario(
            nome="CONTINUACAO",
            descricao="Preço acima do ajuste. Viés comprador.",
            condicao="Abertura acima do ajuste e manutenção.",
            gatilho_entrada="Pullback com rejeição ou rompimento de topo.",
            confirmacao="Fechamento acima do ajuste após 15min.",
            invalidacao="Perda do ajuste com aceitação abaixo."
        )
        alternativo = Cenario(
            nome="TESTE_REJEICAO",
            descricao="Testa o ajuste e rejeita, reforçando compra.",
            condicao="Retorno ao ajuste com candle de rejeição.",
            gatilho_entrada="Rejeição confirmada no ajuste.",
            confirmacao="Fechamento acima do ajuste.",
            invalidacao="Perda do ajuste com aceitação abaixo."
        )
    elif ajuste.posicao == "ABAIXO":
        principal = Cenario(
            nome="CONTINUACAO",
            descricao="Preço abaixo do ajuste. Viés vendedor.",
            condicao="Abertura abaixo do ajuste e manutenção.",
            gatilho_entrada="Pullback com rejeição ou rompimento de fundo.",
            confirmacao="Fechamento abaixo do ajuste após 15min.",
            invalidacao="Recuperação do ajuste com aceitação acima."
        )
        alternativo = Cenario(
            nome="RECUPERACAO",
            descricao="Testa o ajuste e o recupera, invertendo para compra.",
            condicao="Retorno ao ajuste com rompimento e aceitação acima.",
            gatilho_entrada="Romper o ajuste com volume.",
            confirmacao="Fechamento acima do ajuste.",
            invalidacao="Rejeição no ajuste e volta para baixo."
        )
    else:  # NEUTRO
        principal = Cenario(
            nome="NEUTRO",
            descricao="Preço próximo ao ajuste, aguardar definição.",
            condicao="Preço dentro da faixa de tolerância (±0,5 ponto).",
            gatilho_entrada="Aguardar rompimento de topo ou fundo.",
            confirmacao="Fechamento fora da faixa com volume.",
            invalidacao="Permanência na faixa por mais de 15min."
        )
        alternativo = principal
    
    return principal, alternativo