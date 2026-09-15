# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_previsao.py
from datetime import datetime
from typing import Optional, Dict, Any

from ..dados.coletor_dados import coletar_dados_entrada
from ..dados.schemas import (
    DadosEntrada, ResultadoPrevisao, ClassificacaoGAP,
    AnaliseAjuste, Cenario, ScorePrevisao,
)
from .motor_gap import classificar_gap
from .motor_ajuste import analisar_ajuste
from .motor_cenarios import gerar_cenarios
from .motor_score import calcular_score


MAX_GAP_REALISTA = 1000.0
MARGEM_FAIXA_PADRAO = 100.0


class PrevisaoAberturaOrquestrador:
    def __init__(self):
        self.entrada: Optional[DadosEntrada] = None
        self.resultado: Optional[ResultadoPrevisao] = None

    def carregar_dados(self) -> bool:
        self.entrada = coletar_dados_entrada()
        return self.entrada is not None

    def executar_previsao(self) -> Optional[ResultadoPrevisao]:
        if not self.entrada:
            if not self.carregar_dados():
                return None

        abertura_teorica = float(
            (self.entrada.abertura_teorica.abertura_teorica_pontos if self.entrada.abertura_teorica else 0.0)
            or 0.0
        )
        ajuste = float(self.entrada.ajuste_win or 0.0)

        fechamento_anterior = self.entrada.fechamento_anterior_win
        if fechamento_anterior is None or float(fechamento_anterior or 0.0) <= 0:
            fechamento_anterior = ajuste if ajuste > 0 else abertura_teorica

        preco_atual = self.entrada.preco_atual_win
        if preco_atual is None or float(preco_atual or 0.0) <= 0:
            preco_atual = abertura_teorica

        # 1. GAP
        gap = classificar_gap(abertura_teorica, fechamento_anterior, ajuste)

        # 2. Análise de ajuste
        preco_para_ajuste = preco_atual if preco_atual else abertura_teorica
        ajuste_analise = analisar_ajuste(preco_para_ajuste, ajuste)

        # 3. Cenários
        cenario_principal, cenario_alternativo = gerar_cenarios(gap, ajuste_analise)

        # 4. Score
        score = calcular_score(
            contexto=self.entrada.contexto,
            tendencia=self.entrada.tendencia_win,
            noticias=self.entrada.noticias,
            gap=gap,
            ajuste=ajuste_analise,
        )

        # 5. Faixa provável (sempre ± MARGEM_FAIXA_PADRAO da abertura)
        faixa_inf, faixa_sup = self._calcular_faixa(abertura_teorica)

        # 6. Direção
        direcao = self._determinar_direcao(gap, ajuste_analise)

        # 7. Legado
        legado = None
        if self.entrada.core_win_vies:
            legado = {
                "vies": self.entrada.core_win_vies,
                "score": self.entrada.core_win_score,
            }

        self.resultado = ResultadoPrevisao(
            timestamp=datetime.now(),
            ativo="WIN",
            abertura_projetada=abertura_teorica,
            faixa_provavel_inferior=faixa_inf,
            faixa_provavel_superior=faixa_sup,
            gap=gap,
            direcao_prevista=direcao,
            analise_ajuste=ajuste_analise,
            cenario_principal=cenario_principal,
            cenario_alternativo=cenario_alternativo,
            score=score,
            metadados={
                "fonte_dados": "Coletas/",
                "versao_motor": "1.4.0",
                "ajuste_utilizado": ajuste,
                "fechamento_anterior": fechamento_anterior,
                "preco_atual_utilizado": preco_para_ajuste,
                "max_pre_abertura": self.entrada.maxima_pre_abertura,
                "min_pre_abertura": self.entrada.minima_pre_abertura,
                "legado": legado,
                # Novos campos de abertura
                "abertura_leilao_real": self.entrada.abertura_leilao_real,
                "abertura_leilao_timestamp": self.entrada.abertura_leilao_timestamp,
                "abertura_teorica_calculada": self.entrada.abertura_teorica_calculada,
                "fonte_abertura": self.entrada.fonte_abertura,
            },
        )
        return self.resultado

    def _calcular_faixa(self, abertura: float):
        return (
            abertura - MARGEM_FAIXA_PADRAO,
            abertura + MARGEM_FAIXA_PADRAO,
        )

    def _determinar_direcao(self, gap: ClassificacaoGAP, ajuste: AnaliseAjuste) -> str:
        if abs(gap.gap_pontos) > MAX_GAP_REALISTA:
            return "NEUTRO"

        if gap.intensidade in ["EXTREMO", "FORTE"]:
            return "COMPRA" if gap.gap_pontos > 0 else "VENDA"
        if gap.gap_pontos > 50 and ajuste.posicao == "ACIMA":
            return "COMPRA"
        if gap.gap_pontos < -50 and ajuste.posicao == "ABAIXO":
            return "VENDA"
        if gap.gap_pontos > 100:
            return "COMPRA"
        if gap.gap_pontos < -100:
            return "VENDA"
        return "NEUTRO"

    def obter_resultado_json(self) -> Dict[str, Any]:
        if not self.resultado:
            return {"erro": "Nenhum resultado disponível"}

        ajuste_analise = self.resultado.analise_ajuste
        ajuste_dict = {
            "distancia_pontos": ajuste_analise.distancia_pontos,
            "distancia_percentual": ajuste_analise.distancia_percentual,
            "posicao": ajuste_analise.posicao,
            "testou_ajuste": ajuste_analise.testou_ajuste,
            "rejeitou": ajuste_analise.rejeitou,
            "aceitou": ajuste_analise.aceitou,
            "perdeu": ajuste_analise.perdeu,
            "recuperou": ajuste_analise.recuperou,
        }

        metadados = dict(self.resultado.metadados or {})
        pre_abertura = {
            "maxima": metadados.pop("max_pre_abertura", None),
            "minima": metadados.pop("min_pre_abertura", None),
            "preco_atual": metadados.pop("preco_atual_utilizado", None),
        }
        legado = metadados.pop("legado", None)

        # Extrai novos campos
        abertura_leilao_real = metadados.pop("abertura_leilao_real", None)
        abertura_leilao_timestamp = metadados.pop("abertura_leilao_timestamp", None)
        abertura_teorica_calculada = metadados.pop("abertura_teorica_calculada", None)
        fonte_abertura = metadados.pop("fonte_abertura", "DESCONHECIDA")

        return {
            "timestamp": self.resultado.timestamp.isoformat(),
            "ativo": self.resultado.ativo,
            "abertura_projetada": self.resultado.abertura_projetada,
            "abertura_leilao_real": abertura_leilao_real,
            "abertura_leilao_timestamp": abertura_leilao_timestamp,
            "abertura_teorica_calculada": abertura_teorica_calculada,
            "fonte_abertura": fonte_abertura,
            "faixa_provavel": [
                self.resultado.faixa_provavel_inferior,
                self.resultado.faixa_provavel_superior,
            ],
            "gap": {
                "pontos": self.resultado.gap.gap_pontos,
                "percentual": self.resultado.gap.gap_percentual,
                "intensidade": self.resultado.gap.intensidade,
                "classificacao": self.resultado.gap.classificacao,
            },
            "direcao_prevista": self.resultado.direcao_prevista,
            "analise_ajuste": ajuste_dict,
            "cenario_principal": {
                "nome": self.resultado.cenario_principal.nome,
                "descricao": self.resultado.cenario_principal.descricao,
                "gatilho": self.resultado.cenario_principal.gatilho_entrada,
                "confirmacao": self.resultado.cenario_principal.confirmacao,
                "invalidacao": self.resultado.cenario_principal.invalidacao,
            },
            "cenario_alternativo": {
                "nome": self.resultado.cenario_alternativo.nome,
                "descricao": self.resultado.cenario_alternativo.descricao,
            },
            "score": {
                "valor": self.resultado.score.valor,
                "direcao": self.resultado.score.direcao,
                "forca": self.resultado.score.forca,
                "classificacao": self.resultado.score.classificacao,
                "detalhes": self.resultado.score.detalhes,
            },
            "pre_abertura": pre_abertura,
            "legado": legado,
            "metadados": metadados,
        }


def executar_previsao() -> Optional[Dict[str, Any]]:
    orquestrador = PrevisaoAberturaOrquestrador()
    resultado = orquestrador.executar_previsao()
    if resultado:
        return orquestrador.obter_resultado_json()
    return None