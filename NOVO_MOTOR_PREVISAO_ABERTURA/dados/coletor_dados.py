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


def _extrair_estimativa_win(estimativa: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai o bloco 'estimativa_abertura.WIN_INDICE' do EstimativaAbertura.json,
    aceitando tanto 'estimativa_abertura' (singular, formato atual) quanto
    'estimativas_abertura' (plural, formato legado).
    """
    if not isinstance(estimativa, dict):
        return {}

    for chave in ("estimativa_abertura", "estimativas_abertura"):
        bloco = estimativa.get(chave)
        if isinstance(bloco, dict):
            win = bloco.get("WIN_INDICE")
            if isinstance(win, dict) and win:
                return win

    return {}


def _extrair_preco_referencia_win(
    congelado: Dict[str, Any],
    validados: Dict[str, Any],
    mt5: Dict[str, Any],
) -> Optional[float]:
    """
    Busca o PREÇO DE REFERÊNCIA do WIN para previsão de abertura.

    SEMÂNTICA OPERACIONAL:
      Antes do pregão abrir, o dado relevante é o `close` do WIN_LAST_TICK
      (último preço congelado). O `fechamento_anterior` do MT5 só fica
      correto DEPOIS que o pregão abre e forma o candle D1 do dia.

    Ordem de prioridade:
      1. LastTick_Congelado.json → ticks.WIN_LAST_TICK.dados_reais.close
      2. Dados_Validados.json    → WIN_FUT.close
      3. Dados_MT5_v2_2.json     → ativos.WIN.last
      4. Fallback final          → ajuste_win (responsabilidade do caller)
    """
    # --- Fonte 1: LastTick_Congelado → close ---
    if isinstance(congelado, dict):
        ticks = congelado.get("ticks") or {}
        win_tick = ticks.get("WIN_LAST_TICK") or {}
        dados = win_tick.get("dados_reais") or {}
        valor = dados.get("close")
        if valor is not None and float(valor) > 0:
            return float(valor)

    # --- Fonte 2: Dados_Validados → close ---
    if isinstance(validados, dict):
        ativos_validados = validados.get("ativos_validados")
        if isinstance(ativos_validados, list):
            for item in ativos_validados:
                if not isinstance(item, dict):
                    continue
                if item.get("ativo_id") != "WIN_FUT":
                    continue
                valor = item.get("close")
                if valor is not None and float(valor) > 0:
                    return float(valor)
                break

    # --- Fonte 3: Dados_MT5_v2_2 → last ---
    if isinstance(mt5, dict):
        win_mt5 = (mt5.get("ativos") or {}).get("WIN") or {}
        valor = win_mt5.get("last")
        if valor is not None and float(valor) > 0:
            return float(valor)

    return None


def coletar_dados_entrada() -> Optional[DadosEntrada]:
    ativos = carregar_json("DadosAtivosUnificados.json").get("ativos", {})
    estimativa = carregar_json("EstimativaAbertura.json")
    validados = carregar_json("Dados_Validados.json")
    mt5 = carregar_json("Dados_MT5_v2_2.json")
    congelado = carregar_json("LastTick_Congelado.json")

    # ✅ Bug #1: aceita singular E plural
    est_win = _extrair_estimativa_win(estimativa)

    pivots = estimativa.get("pivot_points", {}).get("WIN_FUT", {})

    metricas = carregar_json("Metricas_Calculadas.json")
    indicadores = metricas.get("indicadores_compostos", {})
    macro = metricas.get("indicadores_macro", {})
    adrs_data = metricas.get("performance_relativa", {}).get("adrs_brasileiras", {})

    decisao_v2 = carregar_json("Decisao_V2.json")
    win_core = decisao_v2.get("decisao", {})

    tendencias_raw = carregar_json("Analise_Tendencias.json")
    tendencia_win_data = None
    for chave in ["WIN_FUT", "BMFBOVESPA:WIN1!"]:
        if chave in tendencias_raw:
            tendencia_win_data = tendencias_raw[chave]
            break

    noticias = carregar_json("Noticias_Impacto_Dia.json")
    alertas = noticias.get("alertas", {})
    resumo_noticias = noticias.get("resumo", {})

    # ---- WIN: preço atual ----
    win_ativo = ativos.get("WIN_FUT", {})
    win_atual = win_ativo.get("preco")
    win_high = win_ativo.get("high")
    win_low = win_ativo.get("low")
    ajuste_win = ativos.get("WIN_AJUSTE", {}).get("preco")

    # Abertura teórica com fallback
    abertura_teorica_val = float(est_win.get("abertura_teorica_pontos", 0.0) or 0.0)
    if abertura_teorica_val <= 0:
        abertura_teorica_val = float(ajuste_win or 0.0)

    # Preço atual com fallback em cascata
    if win_atual is None or float(win_atual or 0.0) <= 0:
        win_atual = abertura_teorica_val or ajuste_win or 0.0

    # ✅ Bug #2 v3: preço de referência operacional = close do congelado
    # (fechamento_anterior do MT5 só fica correto depois da abertura)
    fechamento_anterior = _extrair_preco_referencia_win(congelado, validados, mt5)
    if fechamento_anterior is None or fechamento_anterior <= 0:
        # Último recurso
        fechamento_anterior = float(ajuste_win or 0.0)

    # ✅ Bônus: high/low do congelado (mais completos que o unificado)
    if (win_high is None or win_low is None) and isinstance(congelado, dict):
        ticks = congelado.get("ticks") or {}
        win_tick = ticks.get("WIN_LAST_TICK") or {}
        dados = win_tick.get("dados_reais") or {}
        if win_high is None:
            win_high = dados.get("high")
        if win_low is None:
            win_low = dados.get("low")

    abertura_teorica = DadosAberturaTeorica(
        variacao_teorica_pct=est_win.get("variacao_teorica_pct", 0.0),
        abertura_teorica_pontos=abertura_teorica_val,
        pontos_ajuste_base=est_win.get("preco_referencia_base", 0.0),
    )

    pivot = DadosPivot(
        pp=pivots.get("PP", 0.0),
        r1=pivots.get("R1", 0.0),
        r2=pivots.get("R2", 0.0),
        s1=pivots.get("S1", 0.0),
        s2=pivots.get("S2", 0.0),
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
        adrs={
            ticker: {
                "close": data.get("close"),
                "change_percent": data.get("change_percent"),
            }
            for ticker, data in adrs_data.items()
        },
        indicador_mercado_externo=indicadores.get("indicador_mercado_externo"),
        indicador_adrs_brasileiras=indicadores.get("indicador_adrs_brasileiras"),
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
        risco_abertura_win=alertas.get("risco_abertura_WIN", False),
    )

    core_vies = win_core.get("vies_final")
    core_score = win_core.get("score_numeric")

    return DadosEntrada(
        timestamp=datetime.now().isoformat(),
        fechamento_anterior_win=fechamento_anterior,
        ajuste_win=ajuste_win,
        preco_atual_win=win_atual,
        maxima_pre_abertura=win_high,
        minima_pre_abertura=win_low,
        abertura_teorica=abertura_teorica,
        pivot_win=pivot,
        contexto=contexto,
        tendencia_win=tendencia,
        noticias=noticias_obj,
        core_win_vies=core_vies,
        core_win_score=core_score,
    )