# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_score.py
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from ..dados.schemas import (
    ScorePrevisao,
    DadosContexto,
    DadosTendencia,
    DadosNoticias,
    ClassificacaoGAP,
    AnaliseAjuste,
)


# Carregar configuração de pesos
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
PESOS_PATH = CONFIG_DIR / "pesos.yaml"


def carregar_pesos() -> Dict[str, Any]:
    if not PESOS_PATH.exists():
        return {
            "pesos": {
                "mercado_externo": 0.35,
                "adrs_brasileiras": 0.25,
                "vix": 0.10,
                "tendencia": 0.15,
                "gap_intensidade": 0.10,
                "noticias_impacto": 0.05,
            },
            "score_limiares": {
                "muito_forte": 80,
                "forte": 60,
                "moderado": 40,
                "fraco": 0,
            },
        }
    with open(PESOS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


CONFIG = carregar_pesos()
PESOS = CONFIG.get("pesos", {})
LIMIARES = CONFIG.get("score_limiares", {})


# Limiar de direção: abaixo disso em módulo, considera NEUTRO
LIMIAR_DIRECAO = 10.0


def _classificar_forca(magnitude: float) -> str:
    if magnitude >= LIMIARES.get("muito_forte", 80):
        return "MUITO FORTE"
    if magnitude >= LIMIARES.get("forte", 60):
        return "FORTE"
    if magnitude >= LIMIARES.get("moderado", 40):
        return "MODERADO"
    return "FRACO"


def calcular_score(
    contexto: Optional[DadosContexto],
    tendencia: Optional[DadosTendencia],
    noticias: Optional[DadosNoticias],
    gap: Optional[ClassificacaoGAP] = None,
    ajuste: Optional[AnaliseAjuste] = None,
) -> ScorePrevisao:
    """
    Calcula score direcional (signed interno).
    Retorna ScorePrevisao com valor (magnitude), direcao, forca, classificacao.
    """
    score_signed = 0.0  # positivo = COMPRA, negativo = VENDA
    detalhes: Dict[str, float] = {}

    # 1. Mercado Externo
    if contexto and contexto.indicador_mercado_externo is not None:
        me = contexto.indicador_mercado_externo
        peso = PESOS.get("mercado_externo", 0.35)
        contrib = me * peso * 10
        score_signed += contrib
        detalhes["mercado_externo"] = round(contrib, 2)

    # 2. ADRs Brasileiras
    if contexto and contexto.indicador_adrs_brasileiras is not None:
        adrs = contexto.indicador_adrs_brasileiras
        peso = PESOS.get("adrs_brasileiras", 0.25)
        contrib = adrs * peso * 10
        score_signed += contrib
        detalhes["adrs"] = round(contrib, 2)

    # 3. VIX (invertido: VIX sobe = risco = VENDA)
    if contexto and contexto.vix_var is not None:
        vix_var = contexto.vix_var
        peso = PESOS.get("vix", 0.10)
        contrib = -vix_var * peso * 5
        score_signed += contrib
        detalhes["vix"] = round(contrib, 2)

    # 4. Tendência
    if tendencia and tendencia.tendencia != "N/A":
        peso = PESOS.get("tendencia", 0.15)
        if tendencia.tendencia == "SUBIU":
            contrib = 5 * peso * 10
            score_signed += contrib
            detalhes["tendencia"] = round(contrib, 2)
        elif tendencia.tendencia == "DESCEU":
            contrib = -5 * peso * 10
            score_signed += contrib
            detalhes["tendencia"] = round(contrib, 2)

    # 5. GAP
    if gap:
        peso = PESOS.get("gap_intensidade", 0.10)
        mapa_intensidade = {
            "MICRO": 0,
            "PEQUENO": 2,
            "MODERADO": 5,
            "FORTE": 10,
            "EXTREMO": 15,
        }
        bonus = mapa_intensidade.get(gap.intensidade, 0)
        if gap.gap_pontos > 0:
            contrib = bonus * peso * 5
        else:
            contrib = -bonus * peso * 5
        score_signed += contrib
        detalhes["gap"] = round(contrib, 2)

    # 6. Notícias (sempre penaliza — risco não tem direção)
    if noticias:
        peso = PESOS.get("noticias_impacto", 0.05)
        if noticias.tem_3_estrelas_brasil_0900:
            contrib = -15 * peso * 10
            score_signed += contrib
            detalhes["noticia_3_estrelas"] = round(contrib, 2)
        elif noticias.classificacao_impacto == "EXTREMO":
            contrib = -10 * peso * 10
            score_signed += contrib
            detalhes["noticia_extrema"] = round(contrib, 2)

    # ---- Normalização e classificação ----
    score_signed = max(-100.0, min(100.0, score_signed))

    if score_signed > LIMIAR_DIRECAO:
        direcao = "COMPRA"
    elif score_signed < -LIMIAR_DIRECAO:
        direcao = "VENDA"
    else:
        direcao = "NEUTRO"

    magnitude = abs(score_signed)
    forca = _classificar_forca(magnitude)

    if direcao == "NEUTRO":
        classificacao = "NEUTRO"
    else:
        classificacao = f"{forca} {direcao}"

    return ScorePrevisao(
        valor=round(magnitude, 1),
        direcao=direcao,
        forca=forca,
        classificacao=classificacao,
        detalhes=detalhes,
    )
