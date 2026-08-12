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
            self.coletas_dir = coletas_dir
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
            preco=float(ativo_dict.get("preco", 0.0)),
            variacao_pct=float(ativo_dict.get("variacao_pct", 0.0)),
            high=ativo_dict.get("high"),
            low=ativo_dict.get("low"),
            volume=ativo_dict.get("volume"),
        )

    def build(self) -> Optional[MarketContext]:
        self._carregar_dados()
        if not self._ativos_data:
            return None

        ativos = self._ativos_data.get("ativos", {})
        def get_ativo(nome): return ativos.get(nome, {})

        win_fut = self._snapshot_from_dict(get_ativo("WIN_FUT"))
        wdo_fut = self._snapshot_from_dict(get_ativo("WDO_FUT"))
        sp500 = self._snapshot_from_dict(get_ativo("SP500_FUT"))
        nasdaq = self._snapshot_from_dict(get_ativo("NASDAQ_FUT"))
        vix = self._snapshot_from_dict(get_ativo("VIX"))
        dxy = self._snapshot_from_dict(get_ativo("DXY"))
        ewz = self._snapshot_from_dict(get_ativo("EWZ"))
        iron_ore = self._snapshot_from_dict(get_ativo("IRON_ORE"))
        crude_oil = self._snapshot_from_dict(get_ativo("CRUDE_OIL"))
        gold = self._snapshot_from_dict(get_ativo("GOLD"))

        win_ajuste = float(get_ativo("WIN_AJUSTE").get("preco", 0.0))
        wdo_ajuste = float(get_ativo("WDO_AJUSTE").get("preco", 0.0))
        ptax = float(get_ativo("USD_PTAX").get("preco", 0.0))

        adrs = {}
        for ticker in ["VALE_ADR", "PETR_ADR", "ITUB_ADR", "BBAS_ADR", "BBD_ADR", "B3_ADR"]:
            data = get_ativo(ticker)
            if data:
                adrs[ticker] = self._snapshot_from_dict(data)

        metricas = self._metricas_data
        indicadores = metricas.get("indicadores_compostos", {})
        cambio = metricas.get("cambio_e_arbitragem", {})
        curva = metricas.get("curva_juros_b3", {})

        tendencias = self._tendencias_data
        tendencia_win = None
        tendencia_win_padrao = None
        if tendencias:
            win_tend = tendencias.get("WIN_FUT") or tendencias.get("BMFBOVESPA:WIN1!")
            if win_tend:
                tendencia_win = win_tend.get("intervalo_5_para_0", {}).get("tendencia")
                tendencia_win_padrao = win_tend.get("padrao_comportamento")

        # Pivots do EstimativaAbertura.json
        pivots = {}
        if self._estimativa_data:
            p = self._estimativa_data.get("pivot_points", {}).get("WIN_FUT", {})
            pivots = {"r2": p.get("R2", 0), "r1": p.get("R1", 0), "pp": p.get("PP", 0),
                      "s1": p.get("S1", 0), "s2": p.get("S2", 0)}
        if not any(pivots.values()):
            preco = win_fut.preco
            pivots = {"r2": preco + 300, "r1": preco + 150, "pp": win_ajuste,
                      "s1": preco - 150, "s2": preco - 300}

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
            metadados={"pivots": pivots, "fonte_ativos": "DadosAtivosUnificados.json"}
        )