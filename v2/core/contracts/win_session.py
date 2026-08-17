# ============================================================
# ARQUIVO: v2/core/contracts/win_session.py
# FASE 4 — Modelo de Dados V2
# Foco: Previsão de Abertura WINFUT
# ============================================================
"""
Contratos semânticos para a sessão operacional do WINFUT.

Não misturar:
  - dado bruto com dado calculado
  - contexto com sinal de ordem
  - WDO como instrumento operacional (apenas contexto, se necessário)

Fontes prioritárias (ver mapeamento_campos_v2.md):
  1. Dados_MT5_v2_2.json
  2. DadosAtivosUnificados.json
  3. EstimativaAbertura.json
  4. Metricas_Calculadas.json
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------
# Blocos internos
# ------------------------------------------------------------

@dataclass
class WinSessionMetadata:
    data_sessao: Optional[date] = None
    timestamp_coleta: Optional[datetime] = None
    contrato_principal: Optional[str] = None   # ex: WINV26
    fonte_last: Optional[str] = None           # "MT5_v2.2" | "MT5_v1"


@dataclass
class PrecosReferencia:
    ajuste: Optional[float] = None             # TradingView close → WIN_AJUSTE
    last_mt5: Optional[float] = None           # last do contrato principal
    fechamento_anterior: Optional[float] = None  # ainda não disponível
    pre_abertura: Optional[float] = None       # ainda não disponível (pré 09:00)


@dataclass
class Distancias:
    last_vs_ajuste_pts: Optional[float] = None
    last_vs_ajuste_pct: Optional[float] = None
    pre_abertura_vs_ajuste_pts: Optional[float] = None
    pre_abertura_vs_fechamento_pts: Optional[float] = None


@dataclass
class GapInfo:
    gap_projetado_pts: Optional[float] = None
    gap_projetado_pct: Optional[float] = None
    direcao_gap: Optional[str] = None          # "ALTA" | "BAIXA" | "NEUTRO"


@dataclass
class NiveisPivot:
    pivot_pp: Optional[float] = None
    r1: Optional[float] = None
    r2: Optional[float] = None
    s1: Optional[float] = None
    s2: Optional[float] = None


# ------------------------------------------------------------
# Contexto externo (explica, não gera ordem)
# ------------------------------------------------------------

@dataclass
class SnapshotSimples:
    preco: Optional[float] = None
    variacao_pct: Optional[float] = None


@dataclass
class MarketContextWIN:
    """Contexto externo relevante para o WINFUT."""
    vix: SnapshotSimples = field(default_factory=SnapshotSimples)
    sp500_fut: SnapshotSimples = field(default_factory=SnapshotSimples)
    nasdaq_fut: SnapshotSimples = field(default_factory=SnapshotSimples)
    dxy: SnapshotSimples = field(default_factory=SnapshotSimples)
    usd_brl: SnapshotSimples = field(default_factory=SnapshotSimples)
    usd_ptax: Optional[float] = None

    vale: SnapshotSimples = field(default_factory=SnapshotSimples)
    petr: SnapshotSimples = field(default_factory=SnapshotSimples)
    itub: SnapshotSimples = field(default_factory=SnapshotSimples)
    bbd: SnapshotSimples = field(default_factory=SnapshotSimples)
    bbas: SnapshotSimples = field(default_factory=SnapshotSimples)
    b3: SnapshotSimples = field(default_factory=SnapshotSimples)
    indicador_adrs: Optional[float] = None

    iron_ore: SnapshotSimples = field(default_factory=SnapshotSimples)
    iron_ore_2m: SnapshotSimples = field(default_factory=SnapshotSimples)
    crude_oil: SnapshotSimples = field(default_factory=SnapshotSimples)
    gold: SnapshotSimples = field(default_factory=SnapshotSimples)

    di1_2027: Optional[float] = None
    di1_2029: Optional[float] = None
    inclinacao_bps: Optional[float] = None

    indicador_mercado_externo: Optional[float] = None


# ------------------------------------------------------------
# Dados econômicos / calendário (notícias de alto impacto)
# ------------------------------------------------------------

@dataclass
class EconomicNewsContext:
    """
    Impacto do calendário econômico no dia.
    Fonte: Noticias_Impacto_Dia.json (Analise_Noticias.py)
    """
    impacto_total: Optional[int] = None
    classificacao_risco: Optional[str] = None  # BAIXO | ATENÇÃO | ALTO | EXTREMO
    tem_3_estrelas_brasil_0900: bool = False
    tem_3_estrelas_outros_horarios: bool = False
    tem_multiplas_2_estrelas_mesmo_horario: bool = False
    risco_abertura_win: bool = False
    noticias_3_estrelas: List[Dict[str, Any]] = field(default_factory=list)
    horarios_multiplas_2_estrelas: List[Dict[str, Any]] = field(default_factory=list)
    disponivel: bool = False


# ------------------------------------------------------------
# Cenário de abertura
# ------------------------------------------------------------

@dataclass
class ComportamentosPossiveis:
    """Probabilidades (0–100) dos comportamentos em relação ao ajuste."""
    romper_e_continuar: Optional[float] = None
    testar_e_rejeitar: Optional[float] = None
    testar_e_recuperar: Optional[float] = None
    retornar_ao_ajuste: Optional[float] = None
    falso_rompimento: Optional[float] = None


@dataclass
class RelacaoComAjuste:
    posicao: Optional[str] = None              # "ACIMA" | "ABAIXO" | "NO_AJUSTE"
    cenario_principal: Optional[str] = None    # texto curto
    probabilidade_cenario: Optional[float] = None


@dataclass
class OpeningScenario:
    direcao_provavel: Optional[str] = None     # "ALTA" | "BAIXA" | "NEUTRO"
    probabilidade_direcao: Optional[float] = None

    relacao_com_ajuste: RelacaoComAjuste = field(default_factory=RelacaoComAjuste)
    comportamentos: ComportamentosPossiveis = field(default_factory=ComportamentosPossiveis)

    niveis_observacao: Dict[str, float] = field(default_factory=dict)
    contexto_resumo: List[str] = field(default_factory=list)
    cenario_alternativo: Optional[str] = None
    confianca_geral: Optional[float] = None    # 0–100


# ------------------------------------------------------------
# Histórico de sessão (FASE 5 — reservado)
# ------------------------------------------------------------

@dataclass
class SessionHistoryRecord:
    data: Optional[date] = None
    ajuste: Optional[float] = None
    last_pre: Optional[float] = None
    abertura_real: Optional[float] = None
    gap_real_pts: Optional[float] = None
    direcao_real: Optional[str] = None
    testou_ajuste: Optional[bool] = None
    rejeitou_ajuste: Optional[bool] = None
    rompeu_ajuste: Optional[bool] = None
    continuou_direcao: Optional[bool] = None
    reverteu: Optional[bool] = None
    maxima_sessao: Optional[float] = None
    minima_sessao: Optional[float] = None
    resultado_resumo: Optional[str] = None


# ------------------------------------------------------------
# Contrato principal da sessão WIN
# ------------------------------------------------------------

@dataclass
class WinSession:
    """
    Estado operacional do WINFUT para previsão de abertura.

    Uso típico:
      - builder lê fontes (MT5 v2.2, Unificados, Estimativa, Métricas)
      - preenche WinSession
      - motor de previsão consome WinSession e produz OpeningScenario
    """
    metadata: WinSessionMetadata = field(default_factory=WinSessionMetadata)
    precos: PrecosReferencia = field(default_factory=PrecosReferencia)
    distancias: Distancias = field(default_factory=Distancias)
    gap: GapInfo = field(default_factory=GapInfo)
    niveis: NiveisPivot = field(default_factory=NiveisPivot)
    contexto: MarketContextWIN = field(default_factory=MarketContextWIN)
    noticias: EconomicNewsContext = field(default_factory=EconomicNewsContext)
    cenario: OpeningScenario = field(default_factory=OpeningScenario)

    # Metadados livres (debug, versões, flags)
    extras: Dict = field(default_factory=dict)

    def calcular_distancias_basicas(self) -> None:
        """Preenche last_vs_ajuste quando ajuste e last_mt5 estão disponíveis."""
        if self.precos.ajuste and self.precos.last_mt5 and self.precos.ajuste != 0:
            pts = self.precos.last_mt5 - self.precos.ajuste
            pct = (self.precos.last_mt5 / self.precos.ajuste - 1.0) * 100.0
            self.distancias.last_vs_ajuste_pts = round(pts, 2)
            self.distancias.last_vs_ajuste_pct = round(pct, 4)

            if pts > 0:
                pos = "ACIMA"
            elif pts < 0:
                pos = "ABAIXO"
            else:
                pos = "NO_AJUSTE"
            self.cenario.relacao_com_ajuste.posicao = pos

    def definir_direcao_gap(self) -> None:
        """Define direcao_gap a partir do gap_projetado_pts ou last_vs_ajuste."""
        ref = self.gap.gap_projetado_pts
        if ref is None:
            ref = self.distancias.last_vs_ajuste_pts
        if ref is None:
            self.gap.direcao_gap = None
            return
        if ref > 0:
            self.gap.direcao_gap = "ALTA"
        elif ref < 0:
            self.gap.direcao_gap = "BAIXA"
        else:
            self.gap.direcao_gap = "NEUTRO"
