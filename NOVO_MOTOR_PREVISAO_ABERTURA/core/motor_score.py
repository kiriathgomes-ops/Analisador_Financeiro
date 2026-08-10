# NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_score.py
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from ..dados.schemas import ScorePrevisao, DadosContexto, DadosTendencia, DadosNoticias
from .motor_gap import classificar_gap
from .motor_ajuste import analisar_ajuste

# Carregar configuração de pesos
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
PESOS_PATH = CONFIG_DIR / "pesos.yaml"

def carregar_pesos() -> Dict[str, Any]:
    if not PESOS_PATH.exists():
        # Fallback com pesos padrão
        return {
            "pesos": {
                "mercado_externo": 0.35,
                "adrs_brasileiras": 0.25,
                "vix": 0.10,
                "tendencia": 0.15,
                "gap_intensidade": 0.10,
                "noticias_impacto": 0.05
            },
            "score_limiares": {"muito_forte": 80, "forte": 60, "moderado": 40, "fraco": 0}
        }
    with open(PESOS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CONFIG = carregar_pesos()
PESOS = CONFIG.get("pesos", {})
LIMIARES = CONFIG.get("score_limiares", {})

def calcular_score(
    contexto: Optional[DadosContexto],
    tendencia: Optional[DadosTendencia],
    noticias: Optional[DadosNoticias],
    gap: Optional[ClassificacaoGAP] = None,
    ajuste: Optional[AnaliseAjuste] = None
) -> ScorePrevisao:
    """
    Calcula o score de confiança com base nos fatores e pesos configurados.
    """
    score_base = 50.0
    detalhes = {}
    
    # 1. Mercado Externo
    if contexto and contexto.indicador_mercado_externo is not None:
        me = contexto.indicador_mercado_externo
        peso = PESOS.get("mercado_externo", 0.35)
        contrib = me * peso * 10  # escalonamento para impacto no score
        score_base += contrib
        detalhes["mercado_externo"] = round(contrib, 2)
    
    # 2. ADRs Brasileiras
    if contexto and contexto.indicador_adrs_brasileiras is not None:
        adrs = contexto.indicador_adrs_brasileiras
        peso = PESOS.get("adrs_brasileiras", 0.25)
        contrib = adrs * peso * 10
        score_base += contrib
        detalhes["adrs"] = round(contrib, 2)
    
    # 3. VIX (risco)
    if contexto and contexto.vix_var is not None:
        vix_var = contexto.vix_var
        peso = PESOS.get("vix", 0.10)
        # VIX em alta é negativo
        contrib = -vix_var * peso * 5
        score_base += contrib
        detalhes["vix"] = round(contrib, 2)
    
    # 4. Tendência
    if tendencia and tendencia.tendencia != "N/A":
        peso = PESOS.get("tendencia", 0.15)
        if tendencia.tendencia == "SUBIU":
            contrib = 5 * peso * 10
            score_base += contrib
            detalhes["tendencia"] = round(contrib, 2)
        elif tendencia.tendencia == "DESCEU":
            contrib = -5 * peso * 10
            score_base += contrib
            detalhes["tendencia"] = round(contrib, 2)
    
    # 5. GAP Intensidade
    if gap:
        peso = PESOS.get("gap_intensidade", 0.10)
        # Mapeamento de intensidade para bônus/penalidade
        mapa_intensidade = {
            "MICRO": 0,
            "PEQUENO": 2,
            "MODERADO": 5,
            "FORTE": 10,
            "EXTREMO": 15
        }
        bonus = mapa_intensidade.get(gap.intensidade, 0)
        # Sinal: se gap positivo, bônus; se negativo, penalidade
        if gap.gap_pontos > 0:
            contrib = bonus * peso * 5
            score_base += contrib
            detalhes["gap"] = round(contrib, 2)
        else:
            contrib = -bonus * peso * 5
            score_base += contrib
            detalhes["gap"] = round(contrib, 2)
    
    # 6. Notícias de impacto
    if noticias:
        peso = PESOS.get("noticias_impacto", 0.05)
        if noticias.tem_3_estrelas_brasil_0900:
            contrib = -15 * peso * 10
            score_base += contrib
            detalhes["noticia_3_estrelas"] = round(contrib, 2)
        elif noticias.classificacao_impacto == "EXTREMO":
            contrib = -10 * peso * 10
            score_base += contrib
            detalhes["noticia_extrema"] = round(contrib, 2)
    
    # Normalizar entre 0 e 100
    score_final = max(0, min(100, score_base))
    
    # Classificação
    if score_final >= LIMIARES.get("muito_forte", 80):
        classificacao = "MUITO FORTE"
    elif score_final >= LIMIARES.get("forte", 60):
        classificacao = "FORTE"
    elif score_final >= LIMIARES.get("moderado", 40):
        classificacao = "MODERADO"
    else:
        classificacao = "FRACO"
    
    return ScorePrevisao(
        valor=round(score_final, 1),
        classificacao=classificacao,
        detalhes=detalhes
    )