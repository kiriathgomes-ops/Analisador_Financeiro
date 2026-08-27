# ============================================================
# v2/core/services/market_service.py
# Corrigido 27/08/2026: pivot_points.WIN_FUT pode ser None
# (calc_pivot retorna None quando high/low/close inválidos)
# ============================================================

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from ..contracts import MarketContext, AtivoSnapshot


class MarketService:
    def __init__(self, coletas_dir: Optional[Path] = None):
        if coletas_dir is None:
            self.coletas_dir = Path(__file__).resolve().parent.parent.parent.parent / "Coletas"
        else:
            self.coletas_dir = Path(coletas_dir)
        self._ativos_data = None
        self._metricas_data = None
        self._tendencias_data = None
        self._estimativa_data = None

    def _carregar_json(self, nome: str) -> Dict[str, Any]:
        caminho = self.coletas_dir / nome
        if not caminho.exists():
            return {}
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _carregar_dados(self):
        if self._ativos_data is None:
            self._ativos_data = self._carregar_json("DadosAtivosUnificados.json")
        if self._metricas_data is None:
            self._metricas_data = self._carregar_json("Metricas_Calculadas.json")
        if self._tendencias_data is None:
            self._tendencias_data = self._carregar_json("Analise_Tendencias.json")
        if self._estimativa_data is None:
            self._estimativa_data = self._carregar_json("EstimativaAbertura.json")

    def _snapshot_from_dict(self, ativo_dict: Dict) -> AtivoSnapshot:
        if not ativo_dict:
            return AtivoSnapshot(preco=0.0, variacao_pct=0.0)
        return AtivoSnapshot(
            preco=float(ativo_dict.get("preco", 0.0) or 0.0),
            variacao_pct=float(ativo_dict.get("variacao_pct", 0.0) or 0.0),
            high=ativo_dict.get("high"),
            low=ativo_dict.get("low"),
            volume=ativo_dict.get("volume"),
        )

    def _extrair_pivots(self, win_fut: AtivoSnapshot, win_ajuste: float) -> Dict[str, float]:
        """
        Lê pivots de EstimativaAbertura.json de forma defensiva.
        calc_pivot() pode gravar WIN_FUT = null → .get() retorna None, não {}.
        """
        pivots: Dict[str, float] = {}
        if self._estimativa_data:
            bloco = self._estimativa_data.get("pivot_points") or {}
            if not isinstance(bloco, dict):
                bloco = {}
            p = bloco.get("WIN_FUT")
            if isinstance(p, dict):
                pivots = {
                    "r2": float(p.get("R2") or 0),
                    "r1": float(p.get("R1") or 0),
                    "pp": float(p.get("PP") or 0),
                    "s1": float(p.get("S1") or 0),
                    "s2": float(p.get("S2") or 0),
                }

        # Fallback quando pivots ausentes ou zerados
        if not any(pivots.values()):
            preco = win_fut.preco or win_ajuste or 0.0
            base = win_ajuste if win_ajuste else preco
            pivots = {
                "r2": preco + 300,
                "r1": preco + 150,
                "pp": base,
                "s1": preco - 150,
                "s2": preco - 300,
            }
        return pivots

    def build(self) -> Optional[MarketContext]:
        self._carregar_dados()
        if not self._ativos_data:
            return None

        ativos = self._ativos_data.get("ativos") or {}
        if not isinstance(ativos, dict):
            ativos = {}

        def get_ativo(nome: str) -> Dict:
            item = ativos.get(nome) or {}
            return item if isinstance(item, dict) else {}

        win_fut = self._snapshot_from_dict(get_ativo("WIN_FUT"))
        wdo_fut = self._snapshot_from_dict(get_ativo("WDO_FUT"))
        sp500 = self._snapshot_from_dict(get_ativo("SP500_FUT"))
        nasdaq = self._snapshot_from_dict(get_ativo("NASDAQ_FUT"))
        vix = self._snapshot_from_dict(get_ativo("VIX"))
        dxy = self._snapshot_from_dict(get_ativo("DXY"))
        ewz = self._snapshot_from_dict(get_ativo("EWZ"))
        iron_ore = self._snapshot_from_dict(
            get_ativo("IRON_ORE_2M") or get_ativo("IRON_ORE")
        )
        crude_oil = self._snapshot_from_dict(get_ativo("CRUDE_OIL"))
        gold = self._snapshot_from_dict(get_ativo("GOLD"))

        win_ajuste = float(get_ativo("WIN_AJUSTE").get("preco", 0.0) or 0.0)
        wdo_ajuste = float(get_ativo("WDO_AJUSTE").get("preco", 0.0) or 0.0)
        ptax = float(get_ativo("USD_PTAX").get("preco", 0.0) or 0.0)

        # Se WIN_FUT vier zerado, usa WIN_LAST_TICK / ajuste como referência de preço
        if win_fut.preco <= 0:
            last_tick = get_ativo("WIN_LAST_TICK")
            if last_tick.get("preco"):
                win_fut = self._snapshot_from_dict(last_tick)
            elif win_ajuste > 0:
                win_fut = AtivoSnapshot(preco=win_ajuste, variacao_pct=0.0)

        adrs = {}
        for ticker in ["VALE_ADR", "PETR_ADR", "ITUB_ADR", "BBAS_ADR", "BBD_ADR", "B3_ADR"]:
            data = get_ativo(ticker)
            if data:
                adrs[ticker] = self._snapshot_from_dict(data)

        metricas = self._metricas_data or {}
        indicadores = metricas.get("indicadores_compostos") or {}
        cambio = metricas.get("cambio_e_arbitragem") or {}
        curva = metricas.get("curva_juros_b3") or {}

        tendencias = self._tendencias_data or {}
        tendencia_win = None
        tendencia_win_padrao = None
        if tendencias:
            win_tend = tendencias.get("WIN_FUT") or tendencias.get("BMFBOVESPA:WIN1!")
            if isinstance(win_tend, dict):
                intervalo = win_tend.get("intervalo_5_para_0") or {}
                tendencia_win = intervalo.get("tendencia") if isinstance(intervalo, dict) else None
                tendencia_win_padrao = win_tend.get("padrao_comportamento")

        pivots = self._extrair_pivots(win_fut, win_ajuste)

        return MarketContext(
            timestamp=datetime.now(),
            win_fut=win_fut,
            wdo_fut=wdo_fut,
            win_ajuste=win_ajuste,
            wdo_ajuste=wdo_ajuste,
            ptax=ptax,
            sp500=sp500,
            nasdaq=nasdaq,
            vix=vix,
            dxy=dxy,
            ewz=ewz,
            iron_ore=iron_ore,
            crude_oil=crude_oil,
            gold=gold,
            adrs=adrs,
            indicador_mercado_externo=indicadores.get("indicador_mercado_externo"),
            indicador_adrs_brasileiras=indicadores.get("indicador_adrs_brasileiras"),
            spread_wdo_ptax_pontos=cambio.get("spread_wdo_ptax_pontos"),
            inclinacao_di_bps=curva.get("inclinacao_29_27_bps"),
            tendencia_win=tendencia_win,
            tendencia_win_padrao=tendencia_win_padrao,
            metadados={"pivots": pivots, "fonte_ativos": "DadosAtivosUnificados.json"},
        )
