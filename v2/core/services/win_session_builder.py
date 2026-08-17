# ============================================================
# ARQUIVO: v2/core/services/win_session_builder.py
# FASE 4 — Builder do WinSession
#
# Lê as fontes atuais e monta o contrato WinSession.
# Não toma decisão. Não gera ordem. Apenas organiza dados.
# ============================================================

from __future__ import annotations

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, Optional

from v2.core.contracts.win_session import (
    WinSession,
    WinSessionMetadata,
    PrecosReferencia,
    Distancias,
    GapInfo,
    NiveisPivot,
    MarketContextWIN,
    EconomicNewsContext,
    SnapshotSimples,
    OpeningScenario,
    RelacaoComAjuste,
)


# ------------------------------------------------------------
# Caminhos padrão (relativos à raiz do projeto)
# ------------------------------------------------------------

def _raiz_projeto() -> Path:
    """Sobe até a raiz do projeto (onde está a pasta Coletas)."""
    # Este arquivo: v2/core/services/win_session_builder.py
    return Path(__file__).resolve().parent.parent.parent.parent


def _coletas_dir() -> Path:
    return _raiz_projeto() / "Coletas"


# ------------------------------------------------------------
# Utilitários de leitura
# ------------------------------------------------------------

def _carregar_json(caminho: Path) -> Dict[str, Any]:
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _snap(ativos: Dict, chave: str) -> SnapshotSimples:
    item = ativos.get(chave) or {}
    return SnapshotSimples(
        preco=_float(item.get("preco")),
        variacao_pct=_float(item.get("variacao_pct")),
    )


def _float(valor: Any) -> Optional[float]:
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _parse_ts(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor
    texto = str(valor).replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(texto[:26], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(texto)
    except Exception:
        return None


# ------------------------------------------------------------
# Builder principal
# ------------------------------------------------------------

class WinSessionBuilder:
    """
    Monta WinSession a partir das fontes do pipeline atual.

    Ordem de leitura (conforme mapeamento_campos_v2.md):
      1. Dados_MT5_v2_2.json
      2. DadosAtivosUnificados.json
      3. EstimativaAbertura.json
      4. Metricas_Calculadas.json
      5. Noticias_Impacto_Dia.json  (calendário econômico)
    """

    def __init__(self, coletas_dir: Optional[Path] = None):
        self.coletas = Path(coletas_dir) if coletas_dir else _coletas_dir()

    def build(self) -> WinSession:
        mt5 = _carregar_json(self.coletas / "Dados_MT5_v2_2.json")
        unificados = _carregar_json(self.coletas / "DadosAtivosUnificados.json")
        estimativa = _carregar_json(self.coletas / "EstimativaAbertura.json")
        metricas = _carregar_json(self.coletas / "Metricas_Calculadas.json")
        noticias = _carregar_json(self.coletas / "Noticias_Impacto_Dia.json")

        # Fallback: se v2.2 não existir, tenta formato antigo
        if not mt5:
            mt5 = _carregar_json(self.coletas / "Dados_MT5.json")

        session = WinSession()
        self._preencher_metadata(session, mt5, unificados)
        self._preencher_precos(session, mt5, unificados)
        self._preencher_gap_e_niveis(session, estimativa)
        self._preencher_contexto(session, unificados, metricas)
        self._preencher_noticias(session, noticias)

        # Cálculos derivados
        session.calcular_distancias_basicas()
        session.definir_direcao_gap()

        if session.gap.direcao_gap and not session.cenario.direcao_provavel:
            session.cenario.direcao_provavel = session.gap.direcao_gap

        session.extras["fontes_lidas"] = {
            "mt5_v2_2": bool(mt5.get("versao_coletor") == "2.2" or mt5.get("ativos")),
            "unificados": bool(unificados.get("ativos")),
            "estimativa": bool(estimativa),
            "metricas": bool(metricas),
            "noticias": bool(noticias),
        }
        session.extras["timestamp_build"] = datetime.now().isoformat()

        return session

    # ----------------------------------------------------------
    # Preenchimento por bloco
    # ----------------------------------------------------------

    def _preencher_metadata(
        self,
        session: WinSession,
        mt5: Dict,
        unificados: Dict,
    ) -> None:
        ts = _parse_ts(mt5.get("timestamp")) or _parse_ts(
            unificados.get("metadata", {}).get("timestamp")
        )
        data_sessao = ts.date() if ts else date.today()

        # Contrato principal (formato v2.2)
        win_mt5 = (mt5.get("ativos") or {}).get("WIN") or {}
        contrato = win_mt5.get("contrato_principal")

        # Fallback formato antigo
        if not contrato and mt5.get("contratos"):
            for nome in mt5["contratos"]:
                if str(nome).upper().startswith("WIN"):
                    contrato = nome
                    break

        fonte = "MT5_v2.2" if mt5.get("versao_coletor") == "2.2" else None
        if not fonte and mt5:
            fonte = "MT5_v1"

        session.metadata = WinSessionMetadata(
            data_sessao=data_sessao,
            timestamp_coleta=ts,
            contrato_principal=contrato,
            fonte_last=fonte,
        )

    def _preencher_precos(
        self,
        session: WinSession,
        mt5: Dict,
        unificados: Dict,
    ) -> None:
        ativos = unificados.get("ativos") or {}

        # Ajuste (TradingView)
        ajuste = _float((ativos.get("WIN_AJUSTE") or {}).get("preco"))
        if ajuste is None:
            ajuste = _float((ativos.get("WIN_FUT") or {}).get("preco"))

        # Last MT5 (preferencial: v2.2)
        win_mt5 = (mt5.get("ativos") or {}).get("WIN") or {}
        last = _float(win_mt5.get("last"))

        # Fallback: unificado WIN_LAST_TICK
        if last is None:
            last = _float((ativos.get("WIN_LAST_TICK") or {}).get("preco"))

        # Fallback: formato antigo contratos
        if last is None and mt5.get("contratos"):
            for nome, info in mt5["contratos"].items():
                if str(nome).upper().startswith("WIN"):
                    last = _float(info.get("last"))
                    if last:
                        break

        session.precos = PrecosReferencia(
            ajuste=ajuste,
            last_mt5=last,
            fechamento_anterior=None,  # FASE 5
            pre_abertura=None,         # FASE 5 / coleta dedicada
        )

    def _preencher_gap_e_niveis(
        self,
        session: WinSession,
        estimativa: Dict,
    ) -> None:
        win_est = (estimativa.get("estimativas_abertura") or {}).get("WIN_INDICE") or {}
        pivots = (estimativa.get("pivot_points") or {}).get("WIN_FUT") or {}

        abertura_teorica = _float(win_est.get("abertura_teorica_pontos"))
        base_ajuste = _float(win_est.get("pontos_ajuste_base"))
        var_pct = _float(win_est.get("variacao_teorica_pct"))

        gap_pts = None
        if abertura_teorica is not None and base_ajuste is not None:
            gap_pts = round(abertura_teorica - base_ajuste, 2)

        session.gap = GapInfo(
            gap_projetado_pts=gap_pts,
            gap_projetado_pct=var_pct,
            direcao_gap=None,  # preenchido depois por definir_direcao_gap()
        )

        session.niveis = NiveisPivot(
            pivot_pp=_float(pivots.get("PP")),
            r1=_float(pivots.get("R1")),
            r2=_float(pivots.get("R2")),
            s1=_float(pivots.get("S1")),
            s2=_float(pivots.get("S2")),
        )

        # Níveis de observação preliminares no cenário
        obs = {}
        if session.precos.ajuste is not None:
            obs["ajuste"] = session.precos.ajuste
        if abertura_teorica is not None:
            obs["abertura_projetada"] = abertura_teorica
        if session.niveis.pivot_pp is not None:
            obs["pp"] = session.niveis.pivot_pp
        session.cenario.niveis_observacao = obs

    def _preencher_contexto(
        self,
        session: WinSession,
        unificados: Dict,
        metricas: Dict,
    ) -> None:
        ativos = unificados.get("ativos") or {}
        ind = metricas.get("indicadores_compostos") or {}
        curva = metricas.get("curva_juros_b3") or {}
        macro = metricas.get("indicadores_macro") or {}

        ctx = MarketContextWIN(
            vix=_snap(ativos, "VIX"),
            sp500_fut=_snap(ativos, "SP500_FUT"),
            nasdaq_fut=_snap(ativos, "NASDAQ_FUT"),
            dxy=_snap(ativos, "DXY"),
            usd_brl=_snap(ativos, "USD_BRL"),
            usd_ptax=_float((ativos.get("USD_PTAX") or {}).get("preco")),
            vale=_snap(ativos, "VALE_ADR"),
            petr=_snap(ativos, "PETR_ADR"),
            itub=_snap(ativos, "ITUB_ADR"),
            bbd=_snap(ativos, "BBD_ADR"),
            bbas=_snap(ativos, "BBAS_ADR"),
            b3=_snap(ativos, "B3_ADR"),
            indicador_adrs=_float(ind.get("indicador_adrs_brasileiras")),
            iron_ore=_snap(ativos, "IRON_ORE"),
            iron_ore_2m=_snap(ativos, "IRON_ORE_2M"),
            crude_oil=_snap(ativos, "CRUDE_OIL"),
            gold=_snap(ativos, "GOLD"),
            di1_2027=_float((ativos.get("DI1_2027") or {}).get("preco")),
            di1_2029=_float((ativos.get("DI1_2029") or {}).get("preco")),
            inclinacao_bps=_float(curva.get("inclinacao_29_27_bps")),
            indicador_mercado_externo=_float(ind.get("indicador_mercado_externo")),
        )
        session.contexto = ctx

    def _preencher_noticias(self, session: WinSession, noticias: Dict) -> None:
        """Integra Noticias_Impacto_Dia.json (calendário econômico)."""
        if not noticias:
            session.noticias = EconomicNewsContext(disponivel=False)
            return

        resumo = noticias.get("resumo") or {}
        alertas = noticias.get("alertas") or {}

        impacto = resumo.get("impacto_total")
        try:
            impacto = int(impacto) if impacto is not None else None
        except (TypeError, ValueError):
            impacto = None

        session.noticias = EconomicNewsContext(
            impacto_total=impacto,
            classificacao_risco=resumo.get("classificacao"),
            tem_3_estrelas_brasil_0900=bool(
                alertas.get("tem_3_estrelas_brasil_0900")
            ),
            tem_3_estrelas_outros_horarios=bool(
                alertas.get("tem_3_estrelas_outros_horarios")
            ),
            tem_multiplas_2_estrelas_mesmo_horario=bool(
                alertas.get("tem_multiplas_2_estrelas_mesmo_horario")
            ),
            risco_abertura_win=bool(alertas.get("risco_abertura_WIN")),
            noticias_3_estrelas=list(
                alertas.get("noticias_3_estrelas_outros_horarios") or []
            ),
            horarios_multiplas_2_estrelas=list(
                alertas.get("horarios_multiplas_2_estrelas") or []
            ),
            disponivel=True,
        )


# ------------------------------------------------------------
# Atalho de uso
# ------------------------------------------------------------

def build_win_session(coletas_dir: Optional[str | Path] = None) -> WinSession:
    """Função de conveniência para montar o WinSession."""
    builder = WinSessionBuilder(Path(coletas_dir) if coletas_dir else None)
    return builder.build()


# ------------------------------------------------------------
# Execução direta (debug)
# ------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print(" WIN SESSION BUILDER — debug")
    print("=" * 60)

    session = build_win_session()

    print(f"Data sessão     : {session.metadata.data_sessao}")
    print(f"Contrato        : {session.metadata.contrato_principal}")
    print(f"Fonte last      : {session.metadata.fonte_last}")
    print(f"Ajuste          : {session.precos.ajuste}")
    print(f"Last MT5        : {session.precos.last_mt5}")
    print(f"Last vs Ajuste  : {session.distancias.last_vs_ajuste_pts} pts")
    print(f"Posição         : {session.cenario.relacao_com_ajuste.posicao}")
    print(f"Gap projetado   : {session.gap.gap_projetado_pts} pts ({session.gap.direcao_gap})")
    print(f"VIX             : {session.contexto.vix.preco}")
    print(f"Notícias        : impacto={session.noticias.impacto_total} "
          f"risco={session.noticias.classificacao_risco} "
          f"risco_abertura_WIN={session.noticias.risco_abertura_win}")
    print(f"Fontes lidas    : {session.extras.get('fontes_lidas')}")
    print("=" * 60)
