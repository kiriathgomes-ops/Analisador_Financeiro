# NOVO_MOTOR_PREVISAO_ABERTURA/dados/coletor_dados.py
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .schemas import (
    DadosEntrada, DadosAberturaTeorica, DadosPivot,
    DadosContexto, DadosTendencia, DadosNoticias
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
COLETAS_DIR = BASE_DIR / "Coletas"

def carregar_json(nome: str) -> Dict[str, Any]:
    caminho = COLETAS_DIR / nome
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def coletar_dados_entrada() -> Optional[DadosEntrada]:
    ativos = carregar_json("DadosAtivosUnificados.json").get("ativos", {})
    estimativa = carregar_json("EstimativaAbertura.json")
    est_win = estimativa.get("estimativas_abertura", {}).get("WIN_INDICE", {})
    pivots = estimativa.get("pivot_points", {}).get("WIN_FUT", {})
    metricas = carregar_json("Metricas_Calculadas.json")
    indicadores = metricas.get("indicadores_compostos", {})
    macro = metricas.get("indicadores_macro", {})
    adrs_data = metricas.get("performance_relativa", {}).get("adrs_brasileiras", {})
    decisao = carregar_json("Decisao_Core.json")
    win_core = decisao.get("analise_operacional", {}).get("WIN_INDICE", {})
    tendencias_raw = carregar_json("Analise_Tendencias.json")
    tendencia_win_data = None
    for chave in ["WIN_FUT", "BMFBOVESPA:WIN1!"]:
        if chave in tendencias_raw:
            tendencia_win_data = tendencias_raw[chave]
            break
    noticias = carregar_json("Noticias_Impacto_Dia.json")
    alertas = noticias.get("alertas", {})
    resumo_noticias = noticias.get("resumo", {})

    win_ativo = ativos.get("WIN_FUT", {})
    win_atual = win_ativo.get("preco")
    win_high = win_ativo.get("high")   # máxima da pré-abertura (se disponível)
    win_low = win_ativo.get("low")     # mínima da pré-abertura (se disponível)
    ajuste_win = ativos.get("WIN_AJUSTE", {}).get("preco")
    abertura_teorica_val = est_win.get("abertura_teorica_pontos", 0.0)
    if win_atual is None:
        win_atual = abertura_teorica_val
    fechamento_anterior = ajuste_win

    abertura_teorica = DadosAberturaTeorica(
        variacao_teorica_pct=est_win.get("variacao_teorica_pct", 0.0),
        abertura_teorica_pontos=abertura_teorica_val,
        pontos_ajuste_base=est_win.get("pontos_ajuste_base", 0.0)
    )

    pivot = DadosPivot(
        pp=pivots.get("PP", 0.0),
        r1=pivots.get("R1", 0.0),
        r2=pivots.get("R2", 0.0),
        s1=pivots.get("S1", 0.0),
        s2=pivots.get("S2", 0.0)
    )

    contexto = DadosContexto(
        vix=macro.get("vix"),
        vix_var=macro.get("vix_change_pct"),
        sp500=ativos.get("SP500_FUT", {}).get("preco"),
        sp500_var=ativos.get("SP500_FUT", {}).get("variacao_pct"),
        nasdaq=ativos.get("NASDAQ_FUT", {}).get("preco"),
        nasdaq_var=ativos.get("NASDAQ_FUT", {}).get("variacao_pct"),
        ewz=ativos.get("EWZ", {}).get("preco"),
        ewz_var=ativos.get("EWZ", {}).get("variacao_pct"),
        dxy=ativos.get("DXY", {}).get("preco"),
        dxy_var=ativos.get("DXY", {}).get("variacao_pct"),
        iron_ore=ativos.get("IRON_ORE", {}).get("preco"),
        iron_var=ativos.get("IRON_ORE", {}).get("variacao_pct"),
        crude_oil=ativos.get("CRUDE_OIL", {}).get("preco"),
        crude_var=ativos.get("CRUDE_OIL", {}).get("variacao_pct"),
        adrs={ticker: {"close": data.get("close"), "change_percent": data.get("change_percent")}
              for ticker, data in adrs_data.items()},
        indicador_mercado_externo=indicadores.get("indicador_mercado_externo"),
        indicador_adrs_brasileiras=indicadores.get("indicador_adrs_brasileiras")
    )

    tendencia = DadosTendencia()
    if tendencia_win_data:
        tendencia.padrao = tendencia_win_data.get("padrao_comportamento", "N/A")
        tendencia.variacao_pct = tendencia_win_data.get("intervalo_5_para_0", {}).get("variacao_pct", 0.0)
        tendencia.tendencia = tendencia_win_data.get("intervalo_5_para_0", {}).get("tendencia", "N/A")

    noticias_obj = DadosNoticias(
        tem_3_estrelas_brasil_0900=alertas.get("tem_3_estrelas_brasil_0900", False),
        tem_3_estrelas_outros=alertas.get("tem_3_estrelas_outros_horarios", False),
        tem_multiplas_2_estrelas=alertas.get("tem_multiplas_2_estrelas_mesmo_horario", False),
        classificacao_impacto=resumo_noticias.get("classificacao", "BAIXO"),
        risco_abertura_win=alertas.get("risco_abertura_WIN", False)
    )

    core_vies = win_core.get("vies_final")
    core_score = win_core.get("score_numeric")

    return DadosEntrada(
        timestamp=datetime.now().isoformat(),
        fechamento_anterior_win=fechamento_anterior,
        ajuste_win=ajuste_win,
        preco_atual_win=win_atual,
        maxima_pre_abertura=win_high,   # nova
        minima_pre_abertura=win_low,    # nova
        abertura_teorica=abertura_teorica,
        pivot_win=pivot,
        contexto=contexto,
        tendencia_win=tendencia,
        noticias=noticias_obj,
        core_win_vies=core_vies,
        core_win_score=core_score
    )