"""
Setup Abertura – Unificado
===========================
Página com abas para:
- Ajuste B3 (distância do ajuste, scores, semáforo)
- Abertura 09:00 (gap, sinal, IA de pré-abertura + Análise Gráfica SMC)

Versão 6.8 - Velocímetros Mercado Externo/ADRs + Leilão + Ajuste + Explosão + V2
"""

import json
import os
import sys
import re
import math
import subprocess
from datetime import datetime, time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dotenv import load_dotenv
from groq import Groq

# ============================================================
# CARREGAR VARIÁVEIS DE AMBIENTE E KEYMANAGER
# ============================================================
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.KeyManager import get_groq_client, key_manager

# ============================================================
# CSS UNIFICADO (mesclado de ambos os arquivos)
# ============================================================
CSS_CUSTOM = """
<style>
.stApp { background-color: #0e1117; }

/* Cards de sinal */
.card-bull {
    background-color: #0d381e;
    border-left: 5px solid #00c853;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 10px;
}
.card-bear {
    background-color: #380d0d;
    border-left: 5px solid #ff3d00;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 10px;
}
.card-neutral {
    background-color: #1a1c23;
    border-left: 5px solid #ffc107;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 10px;
}

/* Cards de IA */
.card-ai {
    background: linear-gradient(145deg, #12141c 0%, #1a1c2a 100%);
    border-left: 5px solid #7c5cfc;
    padding: 20px;
    border-radius: 8px;
    margin-top: 12px;
    border: 1px solid #2a2d4a;
}
.card-ai h4 {
    color: #7c5cfc;
    margin-top: 0;
}
.card-ai .analysis-content {
    color: #c9d1d9;
    font-size: 0.95rem;
    line-height: 1.6;
}
.card-ai .smc-tag {
    background: rgba(124, 92, 252, 0.15);
    color: #a78bfa;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    display: inline-block;
    margin: 2px 4px 2px 0;
}

/* Caixas de informação */
.info-box {
    background-color: #161b22;
    padding: 15px;
    border-radius: 8px;
    border: 1px solid #30363d;
}
.explicacao {
    background-color: #1a1c2a;
    border: 1px solid #2a2d3a;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 0.85rem;
    color: #cccccc;
    margin-top: 8px;
}

/* Containers de confluência e contexto */
.confluencia-container {
    font-size: 0.85rem !important;
}
.confluencia-container .stMetric {
    font-size: 0.85rem !important;
}
.confluencia-container .stMetric label {
    font-size: 0.75rem !important;
}
.confluencia-container .stMetric div {
    font-size: 0.9rem !important;
}
.confluencia-container .stAlert {
    font-size: 0.85rem !important;
    padding: 8px 12px !important;
}

.contexto-container .stMetric {
    font-size: 0.8rem !important;
}
.contexto-container .stMetric label {
    font-size: 0.7rem !important;
}
.contexto-container .stMetric div {
    font-size: 0.85rem !important;
}

.classificacao-container .stMetric {
    font-size: 1rem !important;
}
.classificacao-container .stMetric label {
    font-size: 0.8rem !important;
}
.classificacao-container .stMetric div {
    font-size: 1.1rem !important;
}

/* Cores de tendência (para o ajuste) */
.tendencia-up {
    color: #00c853;
    font-weight: bold;
}
.tendencia-down {
    color: #ff3d00;
    font-weight: bold;
}
.tendencia-neutral {
    color: #ffc107;
    font-weight: bold;
}
</style>
"""

# ============================================================
# CONFIGURAÇÕES DO SETUP 09H
# ============================================================
@dataclass(frozen=True)
class ConfigSetup09:
    janela_inicio: time = time(9, 0)
    janela_fim: time = time(9, 15)
    threshold_sinal: float = 1.5
    forca_max: int = 10
    loss_pts: int = 250
    alvo_min_pts: int = 250
    modelo_groq_texto: str = "openai/gpt-oss-20b"
    temperatura_groq: float = 0.2
    max_tokens_groq: int = 1200

CONFIG = ConfigSetup09()

# Modelos Groq — prioridade nos que a conta do usuário realmente acessa
# (teste: só openai/gpt-oss-* respondeu; Llama retornou 404)
MODELOS_GROQ_TEXTO = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "qwen/qwen3-32b",
]
MODELO_GROQ_PADRAO = "openai/gpt-oss-20b"


# ============================================================
# MAPEAMENTO DE TICKERS (usado pelo SetupService)
# ============================================================
TICKER_MAP = {
    "BMFBOVESPA:WIN1!": "WIN_FUT",
    "BMFBOVESPA:WDO1!": "WDO_FUT",
    "CME_MINI:ES1!": "SP500_FUT",
    "CME_MINI:NQ1!": "NASDAQ_FUT",
    "TVC:VIX": "VIX",
    "AMEX:EWZ": "EWZ",
    "TVC:DXY": "DXY",
    "NYSE:VALE": "VALE_ADR",
    "NYSE:PBR": "PETR_ADR",
    "NYSE:ITUB": "ITUB_ADR",
    "NYSE:BBD": "BBD_ADR",
    "OTC:BDORY": "BBAS_ADR",
    "OTC:BOLSY": "B3_ADR",
    "B3_AJUSTE_WIN": "WIN_AJUSTE",
    "B3_AJUSTE_WDO": "WDO_AJUSTE",
    "USD_PTAX": "USD_PTAX",
    "FX_IDC:USDBRL": "USD_BRL",
    "FX_IDC:USDMXN": "USD_MXN",
    "SGX:FEF1!": "IRON_ORE",
    "SGX:FEF2!": "IRON_ORE_2M",
    "NYMEX:CL1!": "CRUDE_OIL",
    "TVC:GOLD": "GOLD",
    "BMFBOVESPA:DI1F2027": "DI1_2027",
    "BMFBOVESPA:DI1F2029": "DI1_2029",
}

# ============================================================
# CAMINHOS DOS ARQUIVOS
# ============================================================
COLETAS_DIR = Path(BASE_DIR) / "Coletas"
PROMPT_DIR = Path(BASE_DIR) / "PromptIA"


ARQUIVOS = {
    "noticias_0900": COLETAS_DIR / "Noticias_Calendario_0900.json",
    "metricas": COLETAS_DIR / "Metricas_Calculadas.json",
    "estimativa": COLETAS_DIR / "EstimativaAbertura.json",
    "decisao": COLETAS_DIR / "Decisao_Core.json",              # V1 (fallback)
    "decisao_v2": COLETAS_DIR / "Decisao_V2.json",              # V2 (prioridade)
    "ativos": COLETAS_DIR / "DadosAtivosUnificados.json",
    "tendencias": COLETAS_DIR / "Analise_Tendencias.json",
    "resultado_operacional": COLETAS_DIR / "Resultado_Calculadora_Operacional_Abertura.json",
    "analise_smc": COLETAS_DIR / "AnaliseGraficaSMC.json",      # Análise gráfica SMC/ICT (visão)
    "analise_smc_regras": COLETAS_DIR / "AnaliseGraficaSMC_Regras.json",
    "metricas_penultimo": COLETAS_DIR / "Metricas_Penultimo.json",
}

SCRIPT_TENDENCIAS = BASE_DIR / "MapearTendencia15Min.py"

# ============================================================
# FUNÇÕES AUXILIARES COMPARTILHADAS
# ============================================================
def executar_mapear_tendencias() -> bool:
    try:
        if not os.path.exists(SCRIPT_TENDENCIAS):
            return False
        resultado = subprocess.run(
            [sys.executable, str(SCRIPT_TENDENCIAS)],
            capture_output=True,
            text=True,
            timeout=30
        )
        return resultado.returncode == 0
    except Exception:
        return False

def garantir_tendencias() -> tuple[bool, str]:
    if os.path.exists(ARQUIVOS["tendencias"]):
        try:
            with open(ARQUIVOS["tendencias"], "r", encoding="utf-8") as f:
                dados = json.load(f)
                if dados and len(dados) > 0:
                    return True, "Arquivo de tendências encontrado."
        except Exception:
            pass
    
    rom0 = COLETAS_DIR / "Coleta_rom-0.json"
    rom5 = COLETAS_DIR / "Coleta_rom-5.json"
    rom10 = COLETAS_DIR / "Coleta_rom-10.json"
    
    faltando = []
    if not os.path.exists(rom0): faltando.append("Coleta_rom-0.json")
    if not os.path.exists(rom5): faltando.append("Coleta_rom-5.json")
    if not os.path.exists(rom10): faltando.append("Coleta_rom-10.json")
    
    if faltando:
        return False, f"Faltando: {', '.join(faltando)}"
    
    with st.spinner("🔄 Gerando análise de tendência..."):
        sucesso = executar_mapear_tendencias()
    
    if sucesso and os.path.exists(ARQUIVOS["tendencias"]):
        return True, "Análise gerada!"
    else:
        return False, "Falha ao gerar."

@st.cache_data(ttl=60, show_spinner=False)
def carregar_json(caminho: str) -> Dict[str, Any]:
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}

# ============================================================
# MODELOS DE DOMÍNIO (para o SetupService)
# ============================================================
@dataclass
class SinalSetup:
    direcao: str
    forca: float
    classe_css: str
    emoji: str
    indicador_usado: str
    valor_indicador: float
    motivo_escolha: str

@dataclass
class DadosAbertura:
    var_teorica: float
    abertura_teorica: float
    pontos_base: float
    gap_pontos: float
    preco_atual: Optional[float]

@dataclass
class Escoras:
    pp: float
    r1: float
    r2: float
    s1: float
    s2: float

@dataclass
class DecisaoCore:
    vies: str
    score: float
    fatores: List[str]

@dataclass
class TendenciaAtivo:
    padrao: str
    ultima_variacao: float
    tendencia: str

# ============================================================
# CLASSE SETUPSERVICE (mesma do arquivo 09h)
# ============================================================
class SetupService:
    def __init__(self, dados: Dict[str, Dict[str, Any]], config: ConfigSetup09 = CONFIG):
        self.cfg = config
        self.dados = dados
        self._parse()

        # Força a não usar V1, mesmo se presente
        self.decisao_v2_raw = self.dados.get("decisao_v2", {}) or {}
        self.tem_v2 = bool(self.decisao_v2_raw.get("decisao"))
        # Ignora completamente a chave "decisao" (V1)
        self.decisao_v1_raw = {}  # <-- força vazio

    def _parse(self):
        noticias = self.dados.get("noticias_0900", {})
        alerta = noticias.get("alerta_noticia_0900", {})
        self.tem_3estrelas: bool = alerta.get("tem_evento_3_estrelas", False)
        self.eventos_3e: list = alerta.get("eventos", [])
        self.alerta_texto: str = alerta.get("alerta", "")

        metricas = self.dados.get("metricas", {}) or {}
        indicadores = metricas.get("indicadores_compostos", {}) or {}

        # ÚNICA fonte: Metricas_Calculadas.json → indicadores_compostos
        # (Calculadora.py: ADRs = soma dos %; mercado = -VIX + petróleo + minério)
        def _num(v, default=0.0):
            try:
                if v is None:
                    return default
                return float(v)
            except (TypeError, ValueError):
                return default

        self.ind_mercado_externo = _num(indicadores.get("indicador_mercado_externo"), 0.0)
        self.ind_adrs = _num(indicadores.get("indicador_adrs_brasileiras"), 0.0)
        
        self.adrs: dict = metricas.get("performance_relativa", {}).get("adrs_brasileiras", {})

        est = self.dados.get("estimativa", {})
        self.est_win = est.get("estimativas_abertura", {}).get("WIN_INDICE", {})
        self.est_wdo = est.get("estimativas_abertura", {}).get("WDO_DOLAR", {})
        self.pivot_win = est.get("pivot_points", {}).get("WIN_FUT") or {}
        self.pivot_wdo = est.get("pivot_points", {}).get("WDO_FUT") or {}
        if not isinstance(self.pivot_win, dict):
            self.pivot_win = {}
        if not isinstance(self.pivot_wdo, dict):
            self.pivot_wdo = {}
        self.resumo_macro = est.get("resumo_macro", {})

        decisao = self.dados.get("decisao", {})
        analise_op = decisao.get("analise_operacional", {})
        self.win_core = analise_op.get("WIN_INDICE", {})
        self.wdo_core = analise_op.get("WDO_DOLAR", {})

        dados_ativos = self.dados.get("ativos", {})
        ativos = dados_ativos.get("ativos", dados_ativos)
        self.win_ativo = ativos.get("WIN_FUT", {})
        self.preco_win: Optional[float] = self.win_ativo.get("preco")
        if self.preco_win is None:
            self.preco_win = self.est_win.get("abertura_teorica_pontos")

        tendencias_data = self.dados.get("tendencias", {})
        self.tendencias = self._extrair_tendencias(tendencias_data)

        resultado_op = self.dados.get("resultado_operacional", {})
        self.classificacao_mercado = resultado_op.get("indicadores_compostos", {})

        # Análise gráfica SMC/ICT (gerada pela página de visão)
        self.analise_smc = self.dados.get("analise_smc", {})
        self.analise_smc_regras = self.dados.get("analise_smc_regras", {})

        # ---------- DECISÃO V2 (prioridade) ----------
        self.decisao_v2_raw = self.dados.get("decisao_v2", {}) or {}
        self.tem_v2 = bool(self.decisao_v2_raw.get("decisao"))

        d2 = self.decisao_v2_raw.get("decisao", {}) or {}
        self.v2_vies = d2.get("vies_final", "NEUTRO")
        try:
            self.v2_confianca = int(d2.get("confianca") or 0)
        except (TypeError, ValueError):
            self.v2_confianca = 0
        self.v2_entrada = d2.get("entrada")
        self.v2_stop = d2.get("stop_loss")
        self.v2_alvo1 = d2.get("alvo_1")
        self.v2_alvo2 = d2.get("alvo_2")
        self.v2_invalidacao = d2.get("invalidacao") or ""
        self.v2_motivos = d2.get("motivos") or []
        self.v2_riscos = d2.get("riscos") or []

        cenario = self.decisao_v2_raw.get("opening_scenario") or {}
        self.v2_direcao_cenario = cenario.get("direcao_provavel")
        rel = cenario.get("relacao_com_ajuste") or {}
        self.v2_posicao_ajuste = rel.get("posicao") if isinstance(rel, dict) else None

    def _extrair_tendencias(self, dados_tendencias: Dict) -> Dict[str, TendenciaAtivo]:
        tendencias = {}
        if not dados_tendencias:
            return tendencias
        
        ativos_desejados = ["WIN_FUT", "WDO_FUT", "SP500_FUT", "NASDAQ_FUT", "VIX", "EWZ"]
        
        for ativo_padrao in ativos_desejados:
            ticker_original = None
            for ticker, nome in TICKER_MAP.items():
                if nome == ativo_padrao:
                    ticker_original = ticker
                    break
            
            if ticker_original and ticker_original in dados_tendencias:
                info = dados_tendencias[ticker_original]
                tendencias[ativo_padrao] = TendenciaAtivo(
                    padrao=info.get("padrao_comportamento", "N/A"),
                    ultima_variacao=info.get("intervalo_5_para_0", {}).get("variacao_pct", 0),
                    tendencia=info.get("intervalo_5_para_0", {}).get("tendencia", "N/A")
                )
            elif ativo_padrao in dados_tendencias:
                info = dados_tendencias[ativo_padrao]
                tendencias[ativo_padrao] = TendenciaAtivo(
                    padrao=info.get("padrao_comportamento", "N/A"),
                    ultima_variacao=info.get("intervalo_5_para_0", {}).get("variacao_pct", 0),
                    tendencia=info.get("intervalo_5_para_0", {}).get("tendencia", "N/A")
                )
        
        return tendencias

    def tem_decisao_v2(self) -> bool:
        return bool(getattr(self, "tem_v2", False))

    def decisao_v2(self) -> Dict[str, Any]:
        return {
            "vies": getattr(self, "v2_vies", "NEUTRO"),
            "confianca": getattr(self, "v2_confianca", 0),
            "entrada": getattr(self, "v2_entrada", None),
            "stop": getattr(self, "v2_stop", None),
            "alvo1": getattr(self, "v2_alvo1", None),
            "alvo2": getattr(self, "v2_alvo2", None),
            "invalidacao": getattr(self, "v2_invalidacao", ""),
            "motivos": getattr(self, "v2_motivos", []) or [],
            "riscos": getattr(self, "v2_riscos", []) or [],
            "direcao_cenario": getattr(self, "v2_direcao_cenario", None),
            "posicao_ajuste": getattr(self, "v2_posicao_ajuste", None),
        }


    # ============================================================
    # OPERACIONAIS DE ABERTURA (Ajuste + Explosão)
    # ============================================================
    def _f(self, v, default=0.0):
        try:
            if v is None:
                return default
            return float(v)
        except (TypeError, ValueError):
            return default

    def contexto_ajuste(self) -> Dict[str, Any]:
        """Posição e distância vs ajuste oficial."""
        ativos = (self.dados.get("ativos") or {}).get("ativos") or self.dados.get("ativos") or {}
        if not isinstance(ativos, dict):
            ativos = {}

        def preco(chave):
            item = ativos.get(chave) or {}
            if isinstance(item, dict):
                return self._f(item.get("preco") or item.get("close") or item.get("valor"))
            return 0.0

        ajuste = preco("WIN_AJUSTE") or preco("WIN_FUT")
        last = preco("WIN_FUT") or preco("WIN_LAST_TICK") or self._f(self.preco_win)

        # Preferir V2 session se existir
        d2 = self.decisao_v2_raw.get("win_session") or {}
        precos = d2.get("precos") or {}
        if precos.get("ajuste"):
            ajuste = self._f(precos.get("ajuste"), ajuste)
        if precos.get("last_mt5"):
            last = self._f(precos.get("last_mt5"), last)

        dist = None
        if ajuste and last:
            dist = round(last - ajuste, 0)
        elif self.v2_posicao_ajuste and dist is None:
            dist = None

        if dist is None:
            posicao = self.v2_posicao_ajuste or "INDEFINIDO"
        elif dist > 20:
            posicao = "ACIMA"
        elif dist < -20:
            posicao = "ABAIXO"
        else:
            posicao = "NO_AJUSTE"

        return {
            "ajuste": ajuste if ajuste else None,
            "last": last if last else None,
            "dist_pts": dist,
            "posicao": posicao,
        }

    def operacional_ajuste(self) -> Dict[str, Any]:
        """
        Regra do usuário:
          - Abre ACIMA do ajuste → VENDA no ajuste | alvo 500 | loss 100
          - Abre ABAIXO do ajuste → COMPRA no ajuste | alvo 500 | loss 100
        Filtros: notícias, macro/explosão, V2.
        """
        ctx = self.contexto_ajuste()
        pos = ctx["posicao"]
        dist = ctx["dist_pts"]

        alvo_pts = 500
        loss_pts = 100

        if pos == "ACIMA":
            lado = "VENDA"
            entrada = ctx["ajuste"]
            stop = (entrada + loss_pts) if entrada else None
            alvo = (entrada - alvo_pts) if entrada else None
        elif pos == "ABAIXO":
            lado = "COMPRA"
            entrada = ctx["ajuste"]
            stop = (entrada - loss_pts) if entrada else None
            alvo = (entrada + alvo_pts) if entrada else None
        else:
            lado = "NEUTRO"
            entrada = stop = alvo = None

        # Filtros de qualidade
        bloqueios = []
        avisos = []

        if dist is not None and abs(dist) < 100:
            bloqueios.append(f"Distância pequena ({dist:+.0f} pts) — R:R do alvo 500 piora")
        elif dist is not None and abs(dist) < 150:
            avisos.append(f"Distância moderada ({dist:+.0f} pts)")

        # Notícias
        noticias = self.dados.get("noticias_0900") or {}
        alerta = (noticias.get("alerta_noticia_0900") or {})
        if alerta.get("tem_evento_3_estrelas"):
            bloqueios.append("Notícia ⭐⭐⭐ Brasil às 09:00 — aguardar reação")

        # Explosão (conflito com fade)
        exp = self.operacional_explosao()
        if lado == "VENDA" and exp["direcao"] == "COMPRA" and exp["forca"] in ("ALTA", "MODERADA"):
            bloqueios.append(f"Explosão de COMPRA ({exp['forca']}) — não fade o gap")
        if lado == "COMPRA" and exp["direcao"] == "VENDA" and exp["forca"] in ("ALTA", "MODERADA"):
            bloqueios.append(f"Explosão de VENDA ({exp['forca']}) — não fade o gap")

        # V2
        if self.tem_v2:
            vies_v2 = str(self.v2_vies or "").upper()
            conf = self.v2_confianca
            if conf >= 60:
                if lado == "VENDA" and vies_v2 in ("COMPRA", "ALTA", "BULL"):
                    bloqueios.append(f"V2 COMPRA com {conf}% — contra a venda no ajuste")
                if lado == "COMPRA" and vies_v2 in ("VENDA", "BAIXA", "BEAR"):
                    bloqueios.append(f"V2 VENDA com {conf}% — contra a compra no ajuste")

        if lado == "NEUTRO":
            status = "AGUARDAR"
            motivo = "Preço no ajuste / sem gap relevante"
        elif bloqueios:
            status = "BLOQUEADO"
            motivo = bloqueios[0]
        elif avisos:
            status = "ATENÇÃO"
            motivo = avisos[0]
        else:
            status = "LIBERADO"
            motivo = f"{lado} no ajuste com contexto favorável"

        return {
            "nome": "Retorno ao Ajuste",
            "lado": lado,
            "status": status,
            "motivo": motivo,
            "bloqueios": bloqueios,
            "avisos": avisos,
            "entrada": entrada,
            "stop": stop,
            "alvo": alvo,
            "alvo_pts": alvo_pts,
            "loss_pts": loss_pts,
            "dist_pts": dist,
            "posicao": pos,
            "ajuste": ctx["ajuste"],
            "last": ctx["last"],
        }

    def operacional_explosao(self) -> Dict[str, Any]:
        """
        Soma ADRs + cesta VIX/minério/petróleo para viés de explosão pós-abertura.
        """
        metricas = self.dados.get("metricas") or {}
        compostos = metricas.get("indicadores_compostos") or {}
        macro = metricas.get("indicadores_macro") or {}
        perf = metricas.get("performance_relativa") or {}

        ind_adrs = compostos.get("indicador_adrs_brasileiras")
        ind_ext = compostos.get("indicador_mercado_externo")

        # Fallback: montar a partir de ativos unificados
        ativos = (self.dados.get("ativos") or {}).get("ativos") or self.dados.get("ativos") or {}
        if not isinstance(ativos, dict):
            ativos = {}

        def var(chave):
            item = ativos.get(chave) or {}
            if isinstance(item, dict):
                return self._f(item.get("variacao_pct") or item.get("change_percent"))
            return 0.0

        if ind_adrs is None:
            adrs_keys = ["VALE_ADR", "PETR_ADR", "ITUB_ADR", "BBD_ADR", "BBAS_ADR", "B3_ADR"]
            vals = [var(k) for k in adrs_keys]
            vals = [v for v in vals if v != 0.0]
            ind_adrs = round(sum(vals), 4) if vals else 0.0

        vix_pct = self._f((macro.get("vix_change_pct") if macro else None) or var("VIX"))
        oil_pct = self._f((macro.get("crude_oil_change_pct") if macro else None) or var("CRUDE_OIL"))
        iron_pct = 0.0
        iron_obj = (macro.get("iron_ore_fef2") if macro else None) or {}
        if isinstance(iron_obj, dict) and iron_obj.get("change_percent") is not None:
            iron_pct = self._f(iron_obj.get("change_percent"))
        else:
            iron_pct = var("IRON_ORE") or var("IRON_ORE_2M")

        if ind_ext is None:
            # Fórmula alinhada ao Calculadora.py: -VIX + crude + iron
            ind_ext = round((-vix_pct) + oil_pct + iron_pct, 4)

        # Score combinado (pesos operacionais)
        # ADRs pesam mais no WIN; macro reforça
        score = (self._f(ind_adrs) * 0.55) + (self._f(ind_ext) * 0.45)

        if score >= 1.2:
            direcao, forca = "COMPRA", "ALTA"
        elif score >= 0.45:
            direcao, forca = "COMPRA", "MODERADA"
        elif score <= -1.2:
            direcao, forca = "VENDA", "ALTA"
        elif score <= -0.45:
            direcao, forca = "VENDA", "MODERADA"
        else:
            direcao, forca = "NEUTRO", "FRACA"

        if direcao == "NEUTRO":
            status = "SEM_EXPLOSAO"
            motivo = "Drivers externos equilibrados — sem combustível claro"
        elif forca == "ALTA":
            status = "EXPLOSAO"
            motivo = f"Drivers fortes para {direcao} após abertura"
        else:
            status = "VIÉS_MODERADO"
            motivo = f"Viés moderado de {direcao}"

        return {
            "nome": "Explosão Pós-Abertura",
            "direcao": direcao,
            "forca": forca,
            "status": status,
            "motivo": motivo,
            "score": round(score, 3),
            "ind_adrs": round(self._f(ind_adrs), 3),
            "ind_externo": round(self._f(ind_ext), 3),
            "vix_pct": round(vix_pct, 3),
            "oil_pct": round(oil_pct, 3),
            "iron_pct": round(iron_pct, 3),
        }


    def operacional_leilao(self) -> Dict[str, Any]:
        """
        Fase de leilão: gap projetado (teórico/last vs ajuste) cruzado com drivers.
        Não substitui abertura — prepara o lado (AJUSTE vs EXPLOSÃO vs AGUARDAR).
        """
        ctx = self.contexto_ajuste()
        exp = self.operacional_explosao()

        ajuste = ctx.get("ajuste")
        last = ctx.get("last")
        dist = ctx.get("dist_pts")
        pos = ctx.get("posicao")

        # Preço teórico do leilão: preferir last MT5 / pre_abertura se existir
        teorico = last
        d2 = self.decisao_v2_raw.get("win_session") or {}
        precos = d2.get("precos") or {}
        if precos.get("pre_abertura"):
            try:
                teorico = float(precos["pre_abertura"])
                if ajuste:
                    dist = round(teorico - float(ajuste), 0)
                    if dist > 20:
                        pos = "ACIMA"
                    elif dist < -20:
                        pos = "ABAIXO"
                    else:
                        pos = "NO_AJUSTE"
            except (TypeError, ValueError):
                pass

        # Classificação do gap no leilão
        if dist is None:
            gap_classe = "INDEFINIDO"
        elif abs(dist) < 80:
            gap_classe = "MORNO"
        elif abs(dist) < 150:
            gap_classe = "MODERADO"
        elif abs(dist) < 400:
            gap_classe = "RELEVANTE"
        else:
            gap_classe = "EXTREMO"

        # Alinhamento drivers x gap
        direcao_gap = "ALTA" if (dist or 0) > 20 else ("BAIXA" if (dist or 0) < -20 else "NEUTRO")
        dir_exp = exp.get("direcao") or "NEUTRO"
        forca = exp.get("forca") or "FRACA"

        alinhado = False
        divergente = False
        if direcao_gap == "ALTA" and dir_exp == "COMPRA" and forca in ("ALTA", "MODERADA"):
            alinhado = True
        elif direcao_gap == "BAIXA" and dir_exp == "VENDA" and forca in ("ALTA", "MODERADA"):
            alinhado = True
        elif direcao_gap == "ALTA" and dir_exp == "VENDA" and forca in ("ALTA", "MODERADA"):
            divergente = True
        elif direcao_gap == "BAIXA" and dir_exp == "COMPRA" and forca in ("ALTA", "MODERADA"):
            divergente = True

        # Notícia 3★
        noticias = self.dados.get("noticias_0900") or {}
        alerta = (noticias.get("alerta_noticia_0900") or {})
        tem_3est = bool(alerta.get("tem_evento_3_estrelas"))

        bloqueios = []
        if tem_3est:
            bloqueios.append("Notícia ⭐⭐⭐ Brasil 09:00 — leilão pode ser sujo")
        if gap_classe == "MORNO":
            bloqueios.append("Gap projetado pequeno — leilão sem edge claro")
        if gap_classe == "INDEFINIDO":
            bloqueios.append("Sem preço teórico/ajuste confiável")

        # Recomendação de preparação
        if bloqueios and (tem_3est or gap_classe in ("MORNO", "INDEFINIDO")):
            recomendacao = "AGUARDAR"
            lado = "NEUTRO"
            motivo = bloqueios[0]
        elif alinhado and gap_classe in ("RELEVANTE", "EXTREMO", "MODERADO"):
            recomendacao = "PREPARAR_EXPLOSAO"
            lado = "COMPRA" if direcao_gap == "ALTA" else "VENDA"
            motivo = f"Leilão {direcao_gap} alinhado com drivers ({forca}) — não fade"
        elif divergente:
            recomendacao = "PREPARAR_AJUSTE"
            lado = "VENDA" if direcao_gap == "ALTA" else "COMPRA"
            motivo = f"Leilão {direcao_gap} mas drivers contra — candidato a retorno ao ajuste"
        elif direcao_gap != "NEUTRO" and forca == "FRACA":
            recomendacao = "PREPARAR_AJUSTE"
            lado = "VENDA" if direcao_gap == "ALTA" else "COMPRA"
            motivo = f"Drivers fracos — gap {direcao_gap} candidato a devolver no ajuste"
        elif direcao_gap == "NEUTRO":
            recomendacao = "AGUARDAR"
            lado = "NEUTRO"
            motivo = "Leilão próximo do ajuste"
        else:
            recomendacao = "AGUARDAR"
            lado = "NEUTRO"
            motivo = "Sem confluência clara no leilão"

        return {
            "nome": "Operacional de Leilão",
            "teorico": teorico,
            "ajuste": ajuste,
            "dist_pts": dist,
            "posicao": pos,
            "gap_classe": gap_classe,
            "direcao_gap": direcao_gap,
            "drivers_direcao": dir_exp,
            "drivers_forca": forca,
            "score_drivers": exp.get("score"),
            "alinhado": alinhado,
            "divergente": divergente,
            "recomendacao": recomendacao,
            "lado_preparar": lado,
            "motivo": motivo,
            "bloqueios": bloqueios,
            "tem_noticia_3est": tem_3est,
        }

    def resumo_operacional(self) -> Dict[str, Any]:
        """Conflito / prioridade entre os dois operacionais."""
        aj = self.operacional_ajuste()
        ex = self.operacional_explosao()

        conflito = False
        preferencia = "AGUARDAR"
        texto = ""

        if aj["status"] == "LIBERADO" and ex["status"] == "EXPLOSAO":
            # Explosão na mesma direção do gap (contra o fade) já bloqueia o ajuste
            conflito = True
            preferencia = "EXPLOSAO"
            texto = "Explosão forte — priorizar continuação, não fade no ajuste"
        elif aj["status"] == "LIBERADO":
            preferencia = "AJUSTE"
            texto = f"Setup de {aj['lado']} no ajuste liberado"
        elif ex["status"] in ("EXPLOSAO", "VIÉS_MODERADO") and ex["direcao"] != "NEUTRO":
            preferencia = "EXPLOSAO"
            texto = f"Viés de explosão {ex['direcao']} ({ex['forca']})"
        elif aj["status"] == "ATENÇÃO":
            preferencia = "AJUSTE_ATENCAO"
            texto = aj["motivo"]
        else:
            preferencia = "AGUARDAR"
            texto = aj.get("motivo") or ex.get("motivo") or "Sem setup claro"

        lei = self.operacional_leilao()

        return {
            "preferencia": preferencia,
            "conflito": conflito,
            "texto": texto,
            "ajuste": aj,
            "explosao": ex,
            "leilao": lei,
        }


    def sinal(self) -> SinalSetup:
        if self.tem_3estrelas:
            indicador_usado = "ADRs"
            valor = self.ind_adrs
            motivo = "Notícia 3★ → prioridade ADRs"
        else:
            indicador_usado = "Mercado Ext."
            valor = self.ind_mercado_externo
            motivo = "Sem notícia 3★ → prioridade Mercado Ext."

        th = self.cfg.threshold_sinal
        if valor > th:
            direcao, classe, emoji = "COMPRA", "card-bull", "🟢"
        elif valor < -th:
            direcao, classe, emoji = "VENDA", "card-bear", "🔴"
        else:
            direcao, classe, emoji = "NEUTRO", "card-neutral", "🟡"

        forca = min(self.cfg.forca_max, round(abs(valor), 1))

        return SinalSetup(
            direcao=direcao,
            forca=forca,
            classe_css=classe,
            emoji=emoji,
            indicador_usado=indicador_usado,
            valor_indicador=valor,
            motivo_escolha=motivo,
        )

    def dados_abertura(self) -> DadosAbertura:
        var_teorica = self.est_win.get("variacao_teorica_pct", 0.0)
        abertura_teorica = self.est_win.get("abertura_teorica_pontos", 0.0)
        pontos_base = self.est_win.get("pontos_ajuste_base", 0.0)
        gap = abertura_teorica - pontos_base if abertura_teorica and pontos_base else 0.0
        return DadosAbertura(
            var_teorica=var_teorica,
            abertura_teorica=abertura_teorica,
            pontos_base=pontos_base,
            gap_pontos=gap,
            preco_atual=self.preco_win,
        )

    def escoras(self) -> Escoras:
        p = self.pivot_win if isinstance(self.pivot_win, dict) else {}
        def _n(key, *alts):
            for k in (key,) + alts:
                v = p.get(k)
                if v is not None:
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        continue
            return 0.0
        return Escoras(
            pp=_n("PP", "pp", "pivot"),
            r1=_n("R1", "r1"),
            r2=_n("R2", "r2"),
            s1=_n("S1", "s1"),
            s2=_n("S2", "s2"),
        )

    def core_win(self) -> DecisaoCore:
        return DecisaoCore(
            vies=(self.win_core or {}).get("vies_final", "N/D"),
            score=(self.win_core or {}).get("score_numeric", 0.0),
            fatores=(self.win_core or {}).get("fatores_relevantes", []) or [],
        )

    def core_wdo(self) -> DecisaoCore:
        return DecisaoCore(
            vies=self.wdo_core.get("vies_final", "N/D"),
            score=self.wdo_core.get("score_numeric", 0.0),
            fatores=self.wdo_core.get("fatores_relevantes", []),
        )

    def janela_ok(self) -> bool:
        agora = datetime.now().time()
        return self.cfg.janela_inicio <= agora <= self.cfg.janela_fim

    def dados_minimos_ok(self) -> bool:
        return bool(self.dados.get("metricas") or self.dados.get("estimativa"))

    def confluencia_tendencia(self) -> Dict[str, Any]:
        sinal = self.sinal()
        win_tendencia = self.tendencias.get("WIN_FUT")
        
        if not win_tendencia:
            return {"confluente": False, "motivo": "Sem dados de tendência"}
        
        if sinal.direcao == "COMPRA" and win_tendencia.tendencia == "SUBIU":
            return {"confluente": True, "motivo": "🟢 Tendência confirma COMPRA"}
        elif sinal.direcao == "VENDA" and win_tendencia.tendencia == "DESCEU":
            return {"confluente": True, "motivo": "🔴 Tendência confirma VENDA"}
        elif sinal.direcao == "NEUTRO":
            return {"confluente": True, "motivo": "🟡 Sinal neutro"}
        else:
            return {
                "confluente": False,
                "motivo": f"⚠️ Tendência ({win_tendencia.tendencia}) vs sinal ({sinal.direcao})"
            }

    def _resumir_analise_smc(self) -> str:
        """Extrai o essencial do AnaliseGraficaSMC.json para o prompt da IA."""
        if not self.analise_smc:
            return "Análise gráfica SMC não disponível."

        partes = []

        bias = self.analise_smc.get("bias_direcional")
        if bias:
            partes.append(f"Bias HTF: {bias}")

        tfs = self.analise_smc.get("timeframes_identificados")
        if tfs:
            partes.append(f"TFs: {tfs}")

        # Cenários (mais importantes para a pré-abertura)
        zonas = self.analise_smc.get("zonas_de_interesse_e_cenarios") or []
        if zonas:
            partes.append("Cenários SMC: " + " | ".join(str(z) for z in zonas[:3]))

        # Liquidez relevante
        liq = self.analise_smc.get("liquidez_relevante") or []
        if liq:
            partes.append("Liquidez: " + " | ".join(str(l) for l in liq[:4]))

        # Estruturas principais (limitado)
        estruturas = self.analise_smc.get("estruturas_coletadas") or []
        if estruturas:
            partes.append("Estruturas chave: " + " | ".join(str(e) for e in estruturas[:5]))

        return " • ".join(partes) if partes else "Análise SMC carregada (sem campos principais)."


    def soma_adrs_brutas(self) -> Dict[str, Any]:
        """Soma direta dos % das ADRs em performance_relativa (não depende do composto)."""
        metricas = self.dados.get("metricas") or {}
        adrs = (metricas.get("performance_relativa") or {}).get("adrs_brasileiras") or {}
        detalhe = {}
        soma = 0.0
        n = 0
        if isinstance(adrs, dict):
            for k, item in adrs.items():
                pct = None
                if isinstance(item, dict):
                    pct = item.get("change_percent")
                    if pct is None:
                        pct = item.get("variacao_pct")
                elif isinstance(item, (int, float)):
                    pct = item
                if pct is not None:
                    try:
                        pct = float(pct)
                        detalhe[k] = pct
                        soma += pct
                        n += 1
                    except (TypeError, ValueError):
                        pass
        return {
            "soma": round(soma, 4) if n else None,
            "qtd": n,
            "detalhe": detalhe,
            "composto": float(self.ind_adrs or 0.0),
        }

    def dados_para_ia_resumido(self) -> Dict[str, Any]:
        s = self.sinal()
        da = self.dados_abertura()
        e = self.escoras()
        cw = self.core_win()
        resumo = self.resumo_operacional()
        aj = resumo.get("ajuste") or {}
        ex = resumo.get("explosao") or {}
        lei = self.operacional_leilao() if hasattr(self, "operacional_leilao") else {}
        v2 = self.decisao_v2() if self.tem_decisao_v2() else {}

        win_tend = self.tendencias.get("WIN_FUT")
        tend_resumo = f"{win_tend.padrao} ({win_tend.ultima_variacao:+.2f}%)" if win_tend else "N/A"

        return {
            "sinal": f"{s.direcao} ({s.forca}/10)",
            "indicador": f"{s.indicador_usado}: {s.valor_indicador:+.2f}%",
            "abertura": f"{da.abertura_teorica:,.0f} pts (var: {da.var_teorica:+.2f}%, gap: {da.gap_pontos:+.0f})",
            "preco_atual": f"{da.preco_atual:,.0f}" if da.preco_atual else "N/A",
            "escoras": f"R2:{e.r2:,.0f} R1:{e.r1:,.0f} PP:{e.pp:,.0f} S1:{e.s1:,.0f} S2:{e.s2:,.0f}",
            "core": f"WIN: {cw.vies} (score:{cw.score})",
            "noticias": "🚨 3★" if self.tem_3estrelas else "Sem alerta 3★",
            "tendencia_win": tend_resumo,
            "confluencia": self.confluencia_tendencia()["motivo"],
            "analise_smc": self._resumir_analise_smc(),
            "loss": CONFIG.loss_pts,
            "alvo": CONFIG.alvo_min_pts,
            # Operacionais do trader
            "op_preferencia": resumo.get("preferencia"),
            "op_texto": resumo.get("texto"),
            "op_conflito": resumo.get("conflito"),
            "ajuste_status": aj.get("status"),
            "ajuste_lado": aj.get("lado"),
            "ajuste_dist": aj.get("dist_pts"),
            "ajuste_entrada": aj.get("entrada"),
            "ajuste_stop": aj.get("stop"),
            "ajuste_alvo": aj.get("alvo"),
            "ajuste_motivo": aj.get("motivo"),
            "explosao_status": ex.get("status"),
            "explosao_direcao": ex.get("direcao"),
            "explosao_forca": ex.get("forca"),
            "explosao_score": ex.get("score"),
            "explosao_adrs": ex.get("ind_adrs"),
            "explosao_macro": ex.get("ind_externo"),
            "explosao_motivo": ex.get("motivo"),
            "leilao_rec": lei.get("recomendacao"),
            "leilao_lado": lei.get("lado_preparar"),
            "leilao_gap": lei.get("dist_pts"),
            "leilao_motivo": lei.get("motivo"),
            "v2_vies": v2.get("vies"),
            "v2_conf": v2.get("confianca"),
            "v2_entrada": v2.get("entrada"),
            "v2_stop": v2.get("stop"),
            "v2_alvo1": v2.get("alvo1"),
            "v2_posicao": v2.get("posicao_ajuste"),
            "mercado_externo": f"{float(self.ind_mercado_externo or 0):+.2f}%",
            "adrs_soma": f"{float(self.ind_adrs or 0):+.2f}%",
        }

# ============================================================
# FUNÇÕES DE IA PARA O SETUP 09H
# ============================================================
def montar_prompt_pre_abertura(dados: Dict[str, Any]) -> str:
    return f"""RESPONDA 100% EM PORTUGUÊS DO BRASIL. SEM RACIOCÍNIO INTERNO. SEJA DIRETO.

VOCÊ É O OPERADOR DE MESA DO WIN (mini índice B3) NA ABERTURA.
Sua função NÃO é dar opinião genérica de SMC — é decidir ENTRE OS OPERACIONAIS DO TRADER.

============================================================
OPERACIONAIS OFICIAIS DO TRADER (obrigatório respeitar)
============================================================
A) RETORNO AO AJUSTE (fade)
   - Abre ACIMA do ajuste → VENDA no ajuste | alvo 500 pts | loss 100 pts
   - Abre ABAIXO do ajuste → COMPRA no ajuste | alvo 500 pts | loss 100 pts

B) EXPLOSÃO (continuação)
   - Drivers fortes a favor do gap (Σ ADRs + (−VIX + minério + petróleo))
   - NÃO faz fade; opera CONTINUAÇÃO na direção dos drivers/gap

C) LEILÃO (preparação pré-09:00)
   - Prepara lado (AJUSTE ou EXPLOSÃO) com base em gap teórico vs drivers
   - Não substitui a confirmação pós-abertura

ORDEM DE PRIORIDADE NA DECISÃO:
1) Notícia 3★ no horário → cautela / priorizar ADRs
2) Conflito Ajuste × Explosão → NÃO forçar entrada; explicar o conflito
3) Explosão clara → preferir continuação
4) Sem explosão e distância útil ao ajuste → preferir Ajuste 500/100
5) V2 e SMC só como CONFLUÊNCIA (não anulam A/B)

============================================================
DADOS DO PIPELINE
============================================================
SINAL SETUP: {dados.get('sinal')}
INDICADOR: {dados.get('indicador')}
MERCADO EXTERNO (composto): {dados.get('mercado_externo')}
ADRs SOMA (6 ADRs): {dados.get('adrs_soma')}
ABERTURA / GAP: {dados.get('abertura')}
PREÇO ATUAL: {dados.get('preco_atual')}
PIVOTS: {dados.get('escoras')}
CORE V1: {dados.get('core')}
V2: viés={dados.get('v2_vies')} conf={dados.get('v2_conf')}% entrada={dados.get('v2_entrada')} stop={dados.get('v2_stop')} alvo1={dados.get('v2_alvo1')} pos_ajuste={dados.get('v2_posicao')}
NOTÍCIAS: {dados.get('noticias')}
TENDÊNCIA WIN: {dados.get('tendencia_win')}
CONFLUÊNCIA: {dados.get('confluencia')}
SMC (resumo): {dados.get('analise_smc')}

OPERACIONAL AJUSTE:
  status={dados.get('ajuste_status')} lado={dados.get('ajuste_lado')} dist={dados.get('ajuste_dist')} pts
  entrada={dados.get('ajuste_entrada')} stop={dados.get('ajuste_stop')} alvo={dados.get('ajuste_alvo')}
  motivo={dados.get('ajuste_motivo')}

OPERACIONAL EXPLOSÃO:
  status={dados.get('explosao_status')} direção={dados.get('explosao_direcao')} força={dados.get('explosao_forca')} score={dados.get('explosao_score')}
  ΣADRs={dados.get('explosao_adrs')} ΣMacro={dados.get('explosao_macro')}
  motivo={dados.get('explosao_motivo')}

LEILÃO:
  recomendação={dados.get('leilao_rec')} lado={dados.get('leilao_lado')} gap={dados.get('leilao_gap')}
  motivo={dados.get('leilao_motivo')}

PREFERÊNCIA DO APP: {dados.get('op_preferencia')} | conflito={dados.get('op_conflito')}
TEXTO APP: {dados.get('op_texto')}

============================================================
FORMATO OBRIGATÓRIO DA RESPOSTA
============================================================
1. OPERACIONAL ESCOLHIDO: AJUSTE | EXPLOSÃO | AGUARDAR
   - Lado: COMPRA | VENDA | —
   - Por quê (1 frase, citando dado numérico)

2. CONFIRMAÇÃO PÓS-ABERTURA (checklist):
   - O que precisa acontecer no preço nos primeiros minutos para VALIDAR
   - O que INVALIDA a entrada

3. GESTÃO (só se operacional ≠ AGUARDAR):
   - Entrada (preço ou condição)
   - Stop (pts e/ou preço)
   - Alvo (pts e/ou preço)
   - Se for AJUSTE: usar 500 alvo / 100 loss salvo bloqueio explícito

4. CONFLITOS E RISCOS:
   - Ajuste vs Explosão, notícia 3★, divergência V2/SMC

5. NÍVEIS DE MONITORAMENTO (máx. 4):
   - Ajuste + 1–3 níveis (pivot ou SMC) relevantes ao operacional escolhido

6. PLANO 5–10 MIN:
   - Ação objetiva (entrar / esperar toque no ajuste / não operar)

7. CONFIANÇA: X/10 (uma linha)

REGRAS FINAIS:
- Não recomende COMPRA se o operacional de ajuste for VENDA no ajuste (e vice-versa), salvo explosão dominante justificada pelos números.
- Gap pequeno + drivers fracos → tenda a AJUSTE ou AGUARDAR, não “explosão”.
- Não invente preços que não estejam nos dados.
- Resposta enxuta, em tópicos, português do Brasil.
"""

def chamar_groq_texto(api_key: str, prompt: str, modelo: str) -> str:
    try:
        from groq import Groq
    except ImportError as exc:
        raise RuntimeError("Biblioteca 'groq' não instalada. Rode: pip install groq") from exc

    try:
        client, key_utilizada = get_groq_client()
        print(f"🔑 Usando chave: {key_utilizada[:20]}...")
    except Exception as e:
        return f"❌ Erro ao obter chave API: {str(e)}"
    
    messages = [
        {
            "role": "system",
            "content": """Você é operador de mesa WIN na abertura da B3.
Responda só em português do Brasil, direto, sem raciocínio interno.
Escolha entre os operacionais do trader: AJUSTE (500/100), EXPLOSÃO ou AGUARDAR.
Não dê setup SMC genérico que contradiga esses operacionais sem justificar com os números do prompt."""
        },
        {"role": "user", "content": prompt}
    ]
    
    try:
        completion = client.chat.completions.create(
            model=modelo,
            messages=messages,
            temperature=CONFIG.temperatura_groq,
            max_tokens=CONFIG.max_tokens_groq,
        )
        
        if hasattr(completion, 'usage'):
            tokens = completion.usage.total_tokens
            key_manager.registrar_uso(key_utilizada, tokens)
            print(f"📊 Tokens usados (texto): {tokens} (chave: {key_utilizada[:8]}...)")
        
        return completion.choices[0].message.content
        
    except Exception as e:
        erro_msg = str(e).lower()
        if "429" in erro_msg or "rate_limit" in erro_msg:
            print(f"⚠️ Rate limit detectado na chave {key_utilizada[:8]}...")
            key_manager.marcar_rate_limit(key_utilizada)
            try:
                client, key_utilizada = get_groq_client()
                print(f"🔑 Trocando para nova chave: {key_utilizada[:20]}...")
                return chamar_groq_texto(api_key, prompt, modelo)
            except:
                return "❌ Todas as chaves em rate limit. Tente novamente em algumas horas."
        raise e

def forcar_portugues(resposta: str) -> str:
    traducao = {
        "Market": "Mercado", "Trend": "Tendência", "Uptrend": "Alta",
        "Downtrend": "Baixa", "Sideways": "Lateral", "Range": "Lateral",
        "Bullish": "Altista", "Bearish": "Baixista",
        "Buy": "Compra", "Sell": "Venda", "Entry": "Entrada",
        "Exit": "Saída", "Price": "Preço", "Support": "Suporte",
        "Resistance": "Resistência", "Level": "Nível", "Target": "Alvo",
        "Stop": "Stop", "Loss": "Perda", "Analysis": "Análise",
        "Structure": "Estrutura", "Liquidity": "Liquidez",
        "Confirmation": "Confirmação", "Break": "Rompimento",
        "Retest": "Reteste", "Strong": "Forte", "Weak": "Fraco",
        "Moderate": "Moderado", "High": "Alto", "Low": "Baixo",
        "Open": "Abertura", "Close": "Fechamento", "Volume": "Volume",
        "Momentum": "Momentum", "Divergence": "Divergência",
        "is": "está", "are": "estão", "was": "estava", "were": "estavam",
        "has": "tem", "have": "têm", "will": "vai", "would": "iria",
        "could": "poderia", "should": "deveria",
        "and": "e", "or": "ou", "but": "mas", "because": "porque",
        "therefore": "portanto", "however": "no entanto",
        "although": "embora", "while": "enquanto",
        "when": "quando", "where": "onde",
        "more": "mais", "less": "menos", "above": "acima",
        "below": "abaixo", "near": "próximo", "far": "longe",
        "between": "entre", "among": "entre",
        "Order Block": "Order Block", "Fair Value Gap": "Fair Value Gap",
        "FVG": "FVG", "OB": "OB",
    }
    palavras = resposta.split()
    palavras_traduzidas = []
    for palavra in palavras:
        palavra_limpa = palavra.strip(".,!?;:")
        traducao_palavra = traducao.get(palavra_limpa, palavra)
        if palavra != palavra_limpa:
            pontuacao = palavra[-1] if palavra[-1] in ".,!?;:" else ""
            if pontuacao:
                traducao_palavra += pontuacao
        palavras_traduzidas.append(traducao_palavra)
    return " ".join(palavras_traduzidas)

def garantir_portugues(resposta: str) -> str:
    palavras_portugues = [
        "mercado", "tendência", "compra", "venda", "preço", "suporte", 
        "resistência", "análise", "estrutura", "liquidez", "entrada", 
        "alvo", "stop", "perda", "rompimento", "confirmação"
    ]
    tem_portugues = any(p in resposta.lower() for p in palavras_portugues)
    if tem_portugues:
        resultado = resposta
        traducao_simples = {
            "Market": "Mercado", "Trend": "Tendência", "Buy": "Compra",
            "Sell": "Venda", "Price": "Preço", "Support": "Suporte",
            "Resistance": "Resistência", "Entry": "Entrada", "Target": "Alvo",
            "Stop": "Stop", "Analysis": "Análise", "Structure": "Estrutura",
            "Liquidity": "Liquidez", "Break": "Rompimento",
            "Confirmation": "Confirmação",
        }
        for en, pt in traducao_simples.items():
            resultado = resultado.replace(en, pt)
        return resultado
    aviso = "⚠️ RESPOSTA TRADUZIDA PARA PORTUGUÊS:\n\n"
    return aviso + forcar_portugues(resposta)

# ============================================================
# RENDERIZAÇÃO DA ABA 09H (REORGANIZADA E NUMERADA)
# ============================================================
def render_sidebar_09h():
    st.sidebar.title("🎯 Setup Abertura")
    st.sidebar.caption("Ajuste B3 | Abertura 09:00")
    st.sidebar.markdown("---")
    st.sidebar.info(
        """
**Indicadores:**
- Mercado Externo
- ADRs Brasileiras

**Filtro:**
- Notícia 3★ → ADRs
- Sem notícia → Mercado Ext.

**Risco:**
- Loss: 250 pts
- Alvo: > 250 pts
"""
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Status dos Dados")
    arquivos_status = {
        "Notícias": ARQUIVOS["noticias_0900"],
        "Métricas": ARQUIVOS["metricas"],
        "Estimativa": ARQUIVOS["estimativa"],
        "Decisão V1 (legado)": ARQUIVOS["decisao"],
        "Decisão V2 (oficial)": ARQUIVOS["decisao_v2"],
        "Tendências": ARQUIVOS["tendencias"],
        "Resultado": ARQUIVOS["resultado_operacional"],
        "Análise SMC": ARQUIVOS["analise_smc"],
        "SMC Regras": ARQUIVOS["analise_smc_regras"],
    }
    for nome, caminho in arquivos_status.items():
        existe = "✅" if os.path.exists(caminho) else "❌"
        st.sidebar.caption(f"{existe} {nome}")
    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Limpar Histórico IA", width="stretch"):
        if "historico_pre_abertura" in st.session_state:
            st.session_state.historico_pre_abertura = []
        st.rerun()

# ---------- Bloco 1: Filtro de Notícias e Classificação ----------

# ---------- Decisão V2 ----------
def render_bloco_decisao_v2(service: SetupService):
    """Card prioritário com a decisão do motor V2."""
    st.markdown("---")
    st.subheader("🚀 Decisão V2 (motor prioritário)")
    st.info("✅ Esta é a decisão oficial do motor V2. O motor V1 (Core Engine) foi descontinuado.")

    if not service.tem_decisao_v2():
        st.warning(
            "Decisão V2 ainda não disponível. Rode `python v2_rodar_decisao_completa.py` "
            "ou o pipeline V2. Enquanto isso, use o Core V1 abaixo."
        )
        return

    d = service.decisao_v2()
    vies = str(d.get("vies") or "NEUTRO").upper()
    conf = int(d.get("confianca") or 0)

    if "COMPRA" in vies or vies in ("ALTA", "BULL"):
        classe = "card-bull"
        emoji = "🟢"
    elif "VENDA" in vies or vies in ("BAIXA", "BEAR"):
        classe = "card-bear"
        emoji = "🔴"
    else:
        classe = "card-neutral"
        emoji = "🟡"

    st.markdown(
        f"""
        <div class="{classe}">
            <h3 style="margin:0 0 6px;">{emoji} {vies} · confiança {conf}%</h3>
            <div>{d.get("invalidacao") or ""}</div>
            <div style="margin-top:6px;opacity:.9;">
                Posição vs ajuste: <b>{d.get("posicao_ajuste") or "—"}</b>
                &nbsp;|&nbsp; Cenário: <b>{d.get("direcao_cenario") or "—"}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Entrada", f"{d['entrada']:,.0f}" if d.get("entrada") else "—")
    with c2:
        st.metric("Stop", f"{d['stop']:,.0f}" if d.get("stop") else "—")
    with c3:
        st.metric("Alvo 1", f"{d['alvo1']:,.0f}" if d.get("alvo1") else "—")
    with c4:
        st.metric("Alvo 2", f"{d['alvo2']:,.0f}" if d.get("alvo2") else "—")

    col_m, col_r = st.columns(2)
    with col_m:
        motivos = d.get("motivos") or []
        if motivos:
            with st.expander("Motivos", expanded=False):
                for m in motivos:
                    st.write(f"• {m}")
    with col_r:
        riscos = d.get("riscos") or []
        if riscos:
            with st.expander("Riscos", expanded=False):
                for r in riscos:
                    st.write(f"• {r}")


# ---------- Leilão ----------
def render_bloco_leilao(service: SetupService):
    """Operacional de leilão: gap projetado x drivers → preparar Ajuste ou Explosão."""
    st.markdown("---")
    st.subheader("🔔 Operacional de Leilão")
    st.caption(
        "Usa preço teórico/last vs ajuste + Σ ADRs/Macro para preparar o lado "
        "antes da abertura (não substitui o operacional pós-abertura)."
    )

    lei = service.operacional_leilao()
    rec = lei.get("recomendacao") or "AGUARDAR"

    if rec == "PREPARAR_EXPLOSAO":
        classe = "card-bull" if lei.get("lado_preparar") == "COMPRA" else "card-bear"
        emoji = "🚀"
        titulo = f"{emoji} PREPARAR EXPLOSÃO — {lei.get('lado_preparar')}"
    elif rec == "PREPARAR_AJUSTE":
        classe = "card-bull" if lei.get("lado_preparar") == "COMPRA" else "card-bear"
        emoji = "🎯"
        titulo = f"{emoji} PREPARAR AJUSTE — {lei.get('lado_preparar')} NO AJUSTE"
    else:
        classe = "card-neutral"
        emoji = "🟡"
        titulo = f"{emoji} AGUARDAR — SEM EDGE NO LEILÃO"

    st.markdown(
        f"""
        <div class="{classe}">
            <h3 style="margin:0 0 6px;">{titulo}</h3>
            <div>{lei.get("motivo") or ""}</div>
            <div style="margin-top:6px;opacity:.9;">
                Gap leilão: <b>{lei.get("direcao_gap")}</b> ({lei.get("gap_classe")})
                &nbsp;|&nbsp; Drivers: <b>{lei.get("drivers_direcao")}</b> ({lei.get("drivers_forca")})
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        teo = lei.get("teorico")
        st.metric("Preço teórico / last", f"{teo:,.0f}" if teo else "—")
    with c2:
        aj = lei.get("ajuste")
        st.metric("Ajuste", f"{aj:,.0f}" if aj else "—")
    with c3:
        dist = lei.get("dist_pts")
        st.metric("Gap projetado", f"{dist:+.0f} pts" if dist is not None else "—")
    with c4:
        sc = lei.get("score_drivers")
        st.metric("Score drivers", f"{sc:+.2f}" if sc is not None else "—")

    tags = []
    if lei.get("alinhado"):
        tags.append("✅ Drivers alinhados com o gap")
    if lei.get("divergente"):
        tags.append("⚠️ Drivers divergentes do gap (fade candidato)")
    if lei.get("tem_noticia_3est"):
        tags.append("🚨 Notícia ⭐⭐⭐ no horário")
    if tags:
        st.caption(" · ".join(tags))

    if lei.get("bloqueios"):
        with st.expander("Bloqueios / alertas do leilão", expanded=False):
            for b in lei["bloqueios"]:
                st.write(f"• {b}")

    st.info(
        "**Fluxo sugerido:** leilão define a *preparação* → "
        "após abrir, confirme com o bloco Operacionais (Ajuste 500/100 ou Explosão)."
    )


# ---------- Operacionais Ajuste + Explosão ----------
def render_bloco_operacionais(service: SetupService):
    """Dois operacionais de abertura: Retorno ao Ajuste + Explosão."""
    st.markdown("---")
    st.subheader("🎯 Operacionais de Abertura")

    resumo = service.resumo_operacional()
    aj = resumo["ajuste"]
    ex = resumo["explosao"]

    pref = resumo["preferencia"]
    if pref == "AJUSTE":
        cor = "card-bull" if aj["lado"] == "COMPRA" else "card-bear"
        titulo = f"✅ PREFERÊNCIA: {aj['lado']} NO AJUSTE"
    elif pref == "EXPLOSAO":
        if ex["direcao"] == "COMPRA":
            cor = "card-bull"
        elif ex["direcao"] == "VENDA":
            cor = "card-bear"
        else:
            cor = "card-neutral"
        titulo = f"🚀 PREFERÊNCIA: EXPLOSÃO {ex['direcao']}"
    elif pref == "AJUSTE_ATENCAO":
        cor, titulo = "card-neutral", "⚠️ AJUSTE COM ATENÇÃO"
    else:
        cor, titulo = "card-neutral", "🟡 AGUARDAR — SEM SETUP CLARO"

    st.markdown(
        f"""
        <div class="{cor}">
            <h3 style="margin:0 0 6px;">{titulo}</h3>
            <div>{resumo.get("texto") or ""}</div>
            {"<div style='margin-top:6px;opacity:.85;'>⚠️ Conflito entre fade do ajuste e explosão</div>" if resumo.get("conflito") else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 1️⃣ Retorno ao Ajuste")
        st.caption("Abre acima → VENDA no ajuste | Abre abaixo → COMPRA no ajuste · Alvo 500 / Loss 100")

        status = aj["status"]
        if status == "LIBERADO":
            badge = "🟢 LIBERADO"
        elif status == "ATENÇÃO":
            badge = "🟡 ATENÇÃO"
        elif status == "BLOQUEADO":
            badge = "🔴 BLOQUEADO"
        else:
            badge = "⚪ AGUARDAR"

        st.markdown(f"**Status:** {badge}")
        st.markdown(f"**Lado:** `{aj['lado']}`")

        m1, m2, m3 = st.columns(3)
        with m1:
            dist = aj.get("dist_pts")
            st.metric("Dist. ajuste", f"{dist:+.0f} pts" if dist is not None else "—")
        with m2:
            st.metric("Entrada", f"{aj['entrada']:,.0f}" if aj.get("entrada") else "—")
        with m3:
            st.metric("Alvo / Stop", f"{aj['alvo_pts']}/{aj['loss_pts']}")

        if aj.get("entrada") and aj.get("stop") and aj.get("alvo"):
            st.caption(
                f"Stop: {aj['stop']:,.0f} · Alvo: {aj['alvo']:,.0f} · "
                f"Posição: {aj.get('posicao')} · Last: {aj.get('last') or '—'}"
            )

        st.caption(aj.get("motivo") or "")
        if aj.get("bloqueios"):
            with st.expander("Bloqueios", expanded=False):
                for b in aj["bloqueios"]:
                    st.write(f"• {b}")
        if aj.get("avisos"):
            with st.expander("Avisos", expanded=False):
                for a in aj["avisos"]:
                    st.write(f"• {a}")

    with c2:
        st.markdown("#### 2️⃣ Explosão Pós-Abertura")
        st.caption("Soma ADRs + (−VIX + Minério + Petróleo) → combustível de continuação")

        status = ex["status"]
        if status == "EXPLOSAO":
            badge = "🚀 EXPLOSÃO"
        elif status == "VIÉS_MODERADO":
            badge = "🟡 VIÉS MODERADO"
        else:
            badge = "⚪ SEM EXPLOSÃO"

        st.markdown(f"**Status:** {badge}")
        st.markdown(f"**Direção:** `{ex['direcao']}` · **Força:** `{ex['forca']}`")

        e1, e2, e3 = st.columns(3)
        with e1:
            st.metric("Score", f"{ex['score']:+.2f}")
        with e2:
            st.metric("Σ ADRs", f"{ex['ind_adrs']:+.2f}%")
        with e3:
            st.metric("Σ Macro", f"{ex['ind_externo']:+.2f}%")

        st.caption(
            f"VIX {ex['vix_pct']:+.2f}% · Petróleo {ex['oil_pct']:+.2f}% · "
            f"Minério {ex['iron_pct']:+.2f}%"
        )
        st.caption(ex.get("motivo") or "")

        st.info(
            "**Como usar:** drivers a favor do gap → não fade; "
            "drivers neutros/contra → retorno ao ajuste ganha prioridade."
        )




# ---------- Histórico simples: atual vs penúltima medição de compostos ----------
def _carregar_penultimo_metricas() -> Dict[str, Any]:
    caminho = ARQUIVOS.get("metricas_penultimo") or (COLETAS_DIR / "Metricas_Penultimo.json")
    return carregar_json(str(caminho)) or {}


def atualizar_penultimo_metricas(ind_mercado: float, ind_adrs: float, ts_metricas: str = "") -> Dict[str, Any]:
    """
    Mantém Coletas/Metricas_Penultimo.json com:
      atual    = última leitura vista
      anterior = penúltima (para o tracejado no relógio)
    Só rotaciona quando o valor (arredondado 2 casas) muda.
    """
    caminho = ARQUIVOS.get("metricas_penultimo") or (COLETAS_DIR / "Metricas_Penultimo.json")
    prev = _carregar_penultimo_metricas()
    atual_antigo = prev.get("atual") or {}
    anterior = prev.get("anterior") or {}

    def r2(x):
        try:
            return round(float(x) + 0.0, 2)
        except (TypeError, ValueError):
            return 0.0

    novo_atual = {
        "indicador_mercado_externo": r2(ind_mercado),
        "indicador_adrs_brasileiras": r2(ind_adrs),
        "timestamp": ts_metricas or datetime.now().isoformat(timespec="seconds"),
    }

    mudou = (
        r2(atual_antigo.get("indicador_mercado_externo")) != novo_atual["indicador_mercado_externo"]
        or r2(atual_antigo.get("indicador_adrs_brasileiras")) != novo_atual["indicador_adrs_brasileiras"]
    )

    if mudou and atual_antigo:
        anterior = dict(atual_antigo)
    elif not anterior and atual_antigo:
        anterior = dict(atual_antigo)

    payload = {
        "atual": novo_atual,
        "anterior": anterior if anterior else None,
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return payload


def render_bloco_1_filtro_classificacao(service: SetupService):
    st.markdown("---")
    st.subheader("📌 1. Filtro de Notícias e Classificação")

    # --- Notícias 3★ ---
    if service.tem_3estrelas:
        st.error("🚨 **NOTÍCIA 3★ BRASIL 09:00** — Filtro de prioridade ATIVADO (ADRs)")
        if service.eventos_3e:
            with st.expander("Eventos 3★", expanded=False):
                for ev in service.eventos_3e:
                    if isinstance(ev, dict):
                        st.write(f"• {ev.get('titulo') or ev.get('evento') or ev}")
                    else:
                        st.write(f"• {ev}")
        if service.alerta_texto:
            st.caption(service.alerta_texto)
    else:
        st.success("✅ Sem notícia 3★ no horário — Mercado Externo como referência principal")

    # --- Indicadores: SOMENTE Metricas_Calculadas.indicadores_compostos ---
    ind_mercado = round(float(service.ind_mercado_externo or 0.0), 2)
    ind_adrs = round(float(service.ind_adrs or 0.0), 2)

    # Penúltima medição (arquivo rotativo)
    ts_m = ""
    try:
        meta = (service.dados.get("metricas") or {}).get("metadata_calculo") or {}
        ts_m = str(meta.get("timestamp") or "")
    except Exception:
        ts_m = ""
    hist = atualizar_penultimo_metricas(ind_mercado, ind_adrs, ts_m)
    ant = hist.get("anterior") or {}
    ant_mercado = ant.get("indicador_mercado_externo")
    ant_adrs = ant.get("indicador_adrs_brasileiras")

    def classificar_valor(valor: float) -> dict:
        """
        Escala (módulo do %):
          < 1,5        → LATERAL
          1,5 a 2,5    → FRACA
          2,5 a 4,5    → MODERADA
          > 4,5        → FORTE
        Sinal: + COMPRA | − VENDA | ~0 NEUTRO
        """
        abs_valor = abs(valor)
        if abs_valor < 1.5:
            intensidade = "LATERAL"
        elif abs_valor < 2.5:
            intensidade = "FRACA"
        elif abs_valor <= 4.5:
            intensidade = "MODERADA"
        else:
            intensidade = "FORTE"
        if valor > 0.05:
            sinal = "COMPRA"
        elif valor < -0.05:
            sinal = "VENDA"
        else:
            sinal = "NEUTRO"
        # Se lateral por módulo, mantém intensidade LATERAL mesmo com sinal fraco
        if abs_valor < 1.5:
            rotulo = "LATERAL" if abs_valor < 0.05 else f"LATERAL_{sinal}"
        else:
            rotulo = f"{intensidade}_{sinal}"
        return {
            "valor_pct": round(valor, 4),
            "intensidade": intensidade,
            "sinal": sinal,
            "rotulo": rotulo,
        }

    def cor_ponteiro(valor: float) -> str:
        if valor > 0.05:
            return "#00c853"
        if valor < -0.05:
            return "#ff3d00"
        return "#ffc107"

    def velocimetro(
        valor: float,
        titulo: str,
        escala_minima: float = 30.0,
        valor_anterior: Optional[float] = None,
    ) -> "go.Figure":
        """% grande no CENTRO do relógio. Penúltima embaixo. 2 casas."""
        real = round(float(valor) + 0.0, 2)
        ant = None
        if valor_anterior is not None:
            try:
                ant = round(float(valor_anterior) + 0.0, 2)
            except (TypeError, ValueError):
                ant = None

        abs_v = abs(real)

        def _limite(a: float, base: float) -> float:
            precisa = max(base, a * 1.15)
            if ant is not None:
                precisa = max(precisa, abs(ant) * 1.15)
            for cand in (30, 40, 50, 60, 80, 100, 120, 150, 200):
                if precisa <= cand:
                    return float(cand)
            return float(math.ceil(precisa / 25.0) * 25.0)

        lim = _limite(abs_v, escala_minima)
        v_needle = max(-lim, min(lim, real))

        mid = [round(lim * x, 1) for x in (-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1)]
        for t in (-4.5, -2.5, -1.5, 1.5, 2.5, 4.5):
            if abs(t) < lim:
                mid.append(t)
        ticks = sorted(set(mid))

        steps = []
        for a, b, c in [
            (-lim, -4.5, "#3d1010"),
            (-4.5, -2.5, "#4a2010"),
            (-2.5, -1.5, "#3d2e10"),
            (-1.5, 1.5, "#2a2a1a"),
            (1.5, 2.5, "#1a2e1a"),
            (2.5, 4.5, "#0f2a18"),
            (4.5, lim, "#0a2414"),
        ]:
            lo, hi = max(a, -lim), min(b, lim)
            if lo < hi:
                steps.append({"range": [lo, hi], "color": c})

        if ant is not None and -lim <= ant <= lim:
            meia = max(lim * 0.012, 0.18)
            lo_m, hi_m = max(-lim, ant - meia), min(lim, ant + meia)
            if lo_m < hi_m:
                steps.append({"range": [lo_m, hi_m], "color": "rgba(255, 255, 255, 0.65)"})

        if ant is not None:
            diff = round(real - ant, 2)
            nota = f"penúltima {ant:+.2f}%  ·  Δ {diff:+.2f}%"
        else:
            nota = "◀ venda  |  0  |  compra ▶"

        fig = go.Figure(
            go.Indicator(
                mode="gauge",
                value=real,
                title={
                    "text": (
                        f"{titulo}<br>"
                        f"<span style='font-size:0.7em;color:#8b949e'>escala ±{lim:g}%</span>"
                    ),
                    "font": {"size": 14, "color": "#c9d1d9"},
                },
                gauge={
                    "axis": {
                        "range": [-lim, lim],
                        "tickwidth": 1,
                        "tickcolor": "#8b949e",
                        "tickfont": {"color": "#8b949e", "size": 9},
                        "tickvals": ticks,
                    },
                    "bar": {"color": "rgba(0,0,0,0)", "thickness": 0.01},
                    "bgcolor": "#161b22",
                    "borderwidth": 1,
                    "bordercolor": "#30363d",
                    "steps": steps,
                    "threshold": {
                        "line": {"color": cor_ponteiro(real), "width": 5},
                        "thickness": 0.85,
                        "value": v_needle,
                    },
                },
            )
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#e6edf3"},
            height=320,
            margin=dict(l=16, r=16, t=64, b=36),
            annotations=[
                dict(
                    x=0.5,
                    y=0.48,
                    xref="paper",
                    yref="paper",
                    text=f"<b>{real:+.2f}%</b>",
                    showarrow=False,
                    font={"size": 30, "color": cor_ponteiro(real)},
                    xanchor="center",
                    yanchor="middle",
                    align="center",
                ),
                dict(
                    x=0.5,
                    y=0.30,
                    xref="paper",
                    yref="paper",
                    text=nota,
                    showarrow=False,
                    font={"size": 11, "color": "#8b949e"},
                    xanchor="center",
                    yanchor="middle",
                    align="center",
                ),
            ],
        )
        return fig



    mercado_class = classificar_valor(ind_mercado)
    adrs_class = classificar_valor(ind_adrs)

    # --- Velocímetros ---
    st.markdown("##### ⏱️ Velocímetros de pressão")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            velocimetro(ind_mercado, "🌍 Mercado Externo", escala_minima=30.0, valor_anterior=ant_mercado),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        st.caption(
            f"**{mercado_class['rotulo']}** · "
            f"{'Prioritário' if not service.tem_3estrelas else 'Secundário (notícia 3★)'} · "
            f"atual **{ind_mercado:+.2f}%**"
            + (f" · penúltima **{float(ant_mercado):+.2f}%**" if ant_mercado is not None else "")
        )
    with c2:
        st.plotly_chart(
            velocimetro(ind_adrs, "🇧🇷 ADRs Brasileiras", escala_minima=30.0, valor_anterior=ant_adrs),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        st.caption(
            f"**{adrs_class['rotulo']}** · "
            f"{'Prioritário (notícia 3★)' if service.tem_3estrelas else 'Secundário'} · "
            f"atual **{ind_adrs:+.2f}%**"
            + (f" · penúltima **{float(ant_adrs):+.2f}%**" if ant_adrs is not None else "")
        )

    # Escala de leitura
    st.markdown("##### 📐 Faixas de intensidade")
    st.markdown(
        """
| Faixa (valor do indicador) | Intensidade | Direção |
|----------------------------|-------------|---------|
| **−1,5% a +1,5%** | 🟡 **LATERAL** | Sem pressão clara |
| **−2,5% a −1,5%** | 🟠 **FRACA** | Venda fraca |
| **+1,5% a +2,5%** | 🟠 **FRACA** | Compra fraca |
| **−4,5% a −2,5%** | 🔵 **MODERADA** | Venda moderada |
| **+2,5% a +4,5%** | 🔵 **MODERADA** | Compra moderada |
| **&lt; −4,5%** | 🔴 **FORTE** | Venda forte |
| **&gt; +4,5%** | 🟢 **FORTE** | Compra forte |
"""
    )
    st.caption(
        "Mercado externo = (−VIX) + petróleo + minério · "
        "ADRs = soma dos % (VALE, PETR, ITUB, BBD, BBAS, B3)."
    )

    # Interpretação de confluência
    st.markdown("**Interpretação:**")
    dir_mercado = mercado_class["sinal"]
    dir_adrs = adrs_class["sinal"]

    if service.tem_3estrelas:
        st.warning("⚠️ **Filtro ativado:** Notícia 3★ → prioridade às **ADRs**.")

    if dir_mercado == "COMPRA" and dir_adrs == "COMPRA":
        st.success("✅ Ambos COMPRA – Confluência positiva!")
    elif dir_mercado == "VENDA" and dir_adrs == "VENDA":
        st.error("🔴 Ambos VENDA – Confluência negativa!")
    elif dir_mercado == "NEUTRO" and dir_adrs == "NEUTRO":
        st.warning("🟡 Ambos neutros – Aguardar definição!")
    else:
        st.info(
            f"🔀 Divergência: Mercado **{dir_mercado}** × ADRs **{dir_adrs}** — "
            f"seguir {'ADRs' if service.tem_3estrelas else 'Mercado Externo'} como referência."
        )

    st.caption(
        f"📌 Filtro aplicado: "
        f"{'Notícia 3★ → ADRs' if service.tem_3estrelas else 'Sem notícia 3★ → Mercado Externo'}"
    )



def render_bloco_2_decisao_risco(service: SetupService):
    st.markdown("---")
    st.subheader("📌 2. Decisão do Setup e Gestão de Risco")

    s = service.sinal()
    da = service.dados_abertura()
    cw = service.core_win()
    cwdo = service.core_wdo()

    col_sinal, col_risco, col_core = st.columns([1.4, 1, 1])

    with col_sinal:
        st.markdown(
            f"""
            <div class="{s.classe_css}">
                <h3>{s.emoji} SINAL: {s.direcao}</h3>
                <b>Indicador:</b> {s.indicador_usado}<br>
                <b>Valor:</b> {s.valor_indicador:+.2f} &nbsp;|&nbsp; <b>Força:</b> {s.forca}/10<br><br>
                <small>{s.motivo_escolha}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_risco:
        st.markdown("#### Gestão de Risco")
        st.metric("Loss", f"{CONFIG.loss_pts} pts")
        st.metric("Alvo mínimo", f"> {CONFIG.alvo_min_pts} pts")
        if s.direcao == "COMPRA" and da.preco_atual is not None:
            st.caption(f"Stop ≈ {da.preco_atual - CONFIG.loss_pts:,.0f}")
            st.caption(f"Alvo ≈ {da.preco_atual + CONFIG.alvo_min_pts:,.0f}+")
        elif s.direcao == "VENDA" and da.preco_atual is not None:
            st.caption(f"Stop ≈ {da.preco_atual + CONFIG.loss_pts:,.0f}")
            st.caption(f"Alvo ≈ {da.preco_atual - CONFIG.alvo_min_pts:,.0f}-")

    with col_core:
         st.markdown("#### Core Engine (V2)")
         st.caption("Fonte oficial: **Decisao_V2.json**")
         d2 = service.decisao_v2()
         st.info(f"""
    **WIN:** `{d2.get('vies', 'NEUTRO')}` (confiança: {d2.get('confianca', 0)}%)
    **Entrada:** {d2.get('entrada', '—')}  |  **Stop:** {d2.get('stop', '—')}
    **Alvo 1:** {d2.get('alvo1', '—')}  |  **Alvo 2:** {d2.get('alvo2', '—')}
         """)


    if cw.fatores:
        with st.expander("Fatores relevantes"):
            for f in cw.fatores:
                st.write(f"• {f}")

# ---------- Bloco 3: Abertura Teórica e Escoras ----------
def render_bloco_3_abertura_escoras(service: SetupService):
    st.markdown("---")
    st.subheader("📌 3. Abertura Teórica e Escoras (Pivots)")

    da = service.dados_abertura()
    e = service.escoras()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Abertura WIN", f"{da.abertura_teorica:,.0f}")
    with c2:
        st.metric("Variação", f"{da.var_teorica:+.2f}%")
    with c3:
        st.metric("Gap", f"{da.gap_pontos:+.0f}")
    with c4:
        st.metric("Preço Atual", f"{da.preco_atual:,.0f}" if da.preco_atual is not None else "—")

    st.markdown("##### Escoras WIN")
    e1, e2, e3, e4, e5 = st.columns(5)
    with e1:
        st.metric("R2", f"{e.r2:,.0f}")
    with e2:
        st.metric("R1", f"{e.r1:,.0f}")
    with e3:
        st.metric("PP", f"{e.pp:,.0f}")
    with e4:
        st.metric("S1", f"{e.s1:,.0f}")
    with e5:
        st.metric("S2", f"{e.s2:,.0f}")

    if da.preco_atual is not None and e.pp:
        st.caption(
            f"Distância ao PP: {da.preco_atual - e.pp:+.0f} pts  |  "
            f"ao R1: {e.r1 - da.preco_atual:+.0f} pts  |  "
            f"ao S1: {da.preco_atual - e.s1:+.0f} pts"
        )

# ---------- Bloco 4: Contexto Macro e Confluência ----------
def render_bloco_4_contexto_confluencia(service: SetupService, dados: Dict):
    st.markdown("---")
    st.subheader("📌 4. Contexto Macro e Confluência")

    # Sub-blocos: ADRs e Macro
    resumo = service.resumo_macro
    metricas = dados.get("metricas", {})
    ativos_brutos = dados.get("ativos", {})

    if service.adrs:
        st.markdown("**ADRs Brasileiras**")
        cols_adr = st.columns(min(6, len(service.adrs)))
        for i, (ticker, dados_adr) in enumerate(service.adrs.items()):
            with cols_adr[i % len(cols_adr)]:
                st.metric(
                    ticker.replace("_ADR", ""),
                    f"{dados_adr.get('close', 0):.2f}",
                    f"{dados_adr.get('change_percent', 0):+.2f}%",
                )

    st.markdown("**Macro & Taxas**")
    m1, m2, m3, m4, m5 = st.columns(5)

    def buscar_preco_e_variacao(nome_padrao, chave_resumo=None, chave_metricas=None):
        if chave_resumo:
            item = resumo.get(chave_resumo, {})
            if isinstance(item, dict):
                close = item.get("close")
                change = item.get("change_percent")
                if close is not None:
                    return close, change
        macro = metricas.get("indicadores_macro", {})
        if macro and chave_metricas:
            if chave_metricas == "iron_ore":
                iron_data = macro.get("iron_ore", {})
                if isinstance(iron_data, dict):
                    close = iron_data.get("close")
                    change = iron_data.get("change_percent")
                    if close is not None:
                        return close, change
            else:
                close = macro.get(chave_metricas)
                change_var = f"{chave_metricas}_change_pct"
                change = macro.get(change_var)
                if close is not None:
                    return close, change
        if isinstance(ativos_brutos, dict):
            ativos_data = ativos_brutos.get("ativos", ativos_brutos)
            ativo = ativos_data.get(nome_padrao, {})
            if isinstance(ativo, dict):
                close = ativo.get("preco") or ativo.get("close")
                change = ativo.get("variacao_pct") or ativo.get("change_percent")
                if close is not None:
                    return close, change
        return None, None

    vix_val, vix_var = buscar_preco_e_variacao("VIX", "vix", "vix")
    crude_val, crude_var = buscar_preco_e_variacao("CRUDE_OIL", "crude_oil", "crude_oil")
    iron_val, iron_var = buscar_preco_e_variacao("IRON_ORE", "iron_ore", "iron_ore")

    di27 = resumo.get("di1_2027", 0)
    di29 = resumo.get("di1_2029", 0)
    if not di27:
        di27 = metricas.get("curva_juros_b3", {}).get("di1_2027_taxa", 0)
    if not di29:
        di29 = metricas.get("curva_juros_b3", {}).get("di1_2029_taxa", 0)

    with m1:
        if vix_val is not None:
            st.metric("VIX", f"{vix_val:.2f}", f"{vix_var:+.2f}%" if vix_var is not None else None, delta_color="inverse")
        else:
            st.metric("VIX", "N/A")
    with m2:
        if crude_val is not None:
            st.metric("Petróleo", f"{crude_val:.2f}", f"{crude_var:+.2f}%" if crude_var is not None else None)
        else:
            st.metric("Petróleo", "N/A")
    with m3:
        if iron_val is not None:
            st.metric("Minério", f"{iron_val:.2f}", f"{iron_var:+.2f}%" if iron_var is not None else None)
        else:
            st.metric("Minério", "N/A")
    with m4:
        st.metric("DI 2027", f"{di27:.2f}%" if di27 else "N/A")
    with m5:
        st.metric("DI 2029", f"{di29:.2f}%" if di29 else "N/A")

    # Confluência de tendência (bolinhas)
    st.markdown("**Confluência com Tendência (últimos 15min)**")
    arquivo_tendencias = ARQUIVOS["tendencias"]

    def padrao_para_bola(padrao: str) -> str:
        mapa = {"Alta": "🟢", "Baixa": "🔴", "Estavel": "🟡"}
        partes = padrao.split("_E_")
        if len(partes) != 2:
            return f"⚪ {padrao}"
        return f"{mapa.get(partes[0], '⚪')} → {mapa.get(partes[1], '⚪')}"

    if os.path.exists(arquivo_tendencias):
        try:
            with open(arquivo_tendencias, "r", encoding="utf-8") as f:
                dados_tendencias = json.load(f)
            if dados_tendencias and len(dados_tendencias) > 0:
                tendencias = service.tendencias
                if tendencias:
                    cols = st.columns(min(4, len(tendencias)))
                    for i, (ativo, tend) in enumerate(tendencias.items()):
                        with cols[i % len(cols)]:
                            bolas = padrao_para_bola(tend.padrao)
                            delta_color = "normal" if tend.ultima_variacao > 0 else "inverse" if tend.ultima_variacao < 0 else "off"
                            st.metric(
                                label=f"{ativo}",
                                value=bolas,
                                delta=f"{tend.ultima_variacao:+.2f}%",
                                delta_color=delta_color
                            )
                    # Exibe a confluência
                    confluencia = service.confluencia_tendencia()
                    if confluencia["confluente"]:
                        st.success(f"✅ {confluencia['motivo']}")
                    else:
                        st.warning(f"⚠️ {confluencia['motivo']}")
                else:
                    st.info("Nenhuma tendência disponível.")
            else:
                st.info("Arquivo de tendências vazio.")
        except Exception as e:
            st.error(f"Erro ao carregar tendências: {e}")
    else:
        st.info("📊 Analise_Tendencias.json não encontrado.")
        sucesso, mensagem = garantir_tendencias()
        if sucesso:
            st.success(f"✅ {mensagem}")
            st.rerun()
        else:
            st.warning(f"⚠️ {mensagem}")

# ---------- Bloco 5: Análise IA – Pré-Abertura ----------
def render_bloco_5_ia_pre_abertura(service: SetupService):
    st.markdown("---")
    st.subheader("📌 5. Análise IA – Pré-Abertura")
    st.caption("Previsão de direção, GAP e cenário para os primeiros minutos do pregão")

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        try:
            from dotenv import load_dotenv
            load_dotenv(BASE_DIR / ".env")
            groq_key = os.getenv("GROQ_API_KEY", "")
        except Exception:
            pass

    with st.expander("⚙️ Configurações da IA", expanded=not bool(groq_key)):
        groq_key_input = st.text_input("Groq API Key", type="password", value=groq_key, help="Obtenha em https://console.groq.com", key="groq_key_pre_abertura")
        modelo_texto = st.selectbox("Modelo (texto)", MODELOS_GROQ_TEXTO, index=0, key="modelo_pre_abertura")
        st.caption("💡 Llama 3.3 70B é o melhor modelo de texto da Groq.")

    if not service.dados_minimos_ok():
        st.warning("⚠️ Dados insuficientes. Execute `rodar_pipeline_3x.bat`")
        return

    if st.button("📊 Analisar Pré-Abertura (Texto)", type="primary", key="btn_pre_abertura"):
        key_final = groq_key_input or groq_key
        if not key_final:
            st.error("⚠️ Informe a Groq API Key")
            return
        with st.spinner("📊 Analisando dados para pré-abertura..."):
            try:
                dados_ia = service.dados_para_ia_resumido()
                prompt = montar_prompt_pre_abertura(dados_ia)
                resposta = chamar_groq_texto(key_final, prompt, modelo_texto)
                resposta_limpa = re.sub(r'<think>.*?</think>', '', resposta, flags=re.DOTALL)
                resposta_limpa = resposta_limpa.strip()
                st.markdown(
                    f"""
                    <div class="card-ai" style="border-left-color: #00d4ff;">
                        <h4 style="color:#00d4ff;">📊 Análise de Pré-Abertura</h4>
                        <div style="color:#a78bfa; font-size:0.85rem; margin-bottom:8px;">
                            ⚡ Análise baseada apenas nos dados do pipeline
                            <span style="margin-left:12px; background:rgba(0,212,255,0.15); padding:2px 10px; border-radius:12px; font-size:0.7rem;">{modelo_texto}</span>
                            <span style="margin-left:12px; background:rgba(0,200,83,0.15); padding:2px 10px; border-radius:12px; font-size:0.7rem;">🇧🇷 Português</span>
                            <span style="margin-left:12px; background:rgba(255,193,7,0.15); padding:2px 10px; border-radius:12px; font-size:0.7rem;">📊 Somente texto</span>
                        </div>
                        <div class="analysis-content">
                            {resposta_limpa.replace(chr(10), '<br>')}
                        </div>
                        <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
                            <span class="smc-tag">📊 Pré-Abertura</span>
                            <span class="smc-tag">🎯 Direção</span>
                            <span class="smc-tag">📈 GAP</span>
                            <span class="smc-tag">⚡ Volatilidade</span>
                            <span class="smc-tag">🎯 Níveis Chave</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if "historico_pre_abertura" not in st.session_state:
                    st.session_state.historico_pre_abertura = []
                st.session_state.historico_pre_abertura.append({
                    "hora": datetime.now().strftime("%H:%M:%S"),
                    "sinal": service.sinal().direcao,
                    "modelo": modelo_texto,
                    "resposta": resposta_limpa,
                })
            except Exception as e:
                st.error(f"❌ Erro ao chamar IA: {e}")

# ---------- Bloco 6: Checklist Final ----------
def render_bloco_6_checklist():
    st.markdown("---")
    st.subheader("📌 6. Checklist Final")

    keys = ["ck_09h_1", "ck_09h_2", "ck_09h_3", "ck_09h_4", "ck_09h_5"]
    labels = [
        "Indicador alinhado com Core Engine",
        "Abertura real observada",
        "Escora próxima identificada",
        "Loss e Alvo definidos",
        "Análise IA revisada",
    ]

    todos = True
    for key, label in zip(keys, labels):
        if key not in st.session_state:
            st.session_state[key] = False
        val = st.checkbox(label, key=key)
        if not val:
            todos = False

    if todos:
        st.success("🚀 SETUP VALIDADO")
    else:
        st.info("⏳ Complete o checklist")

# ============================================================
# RENDERIZAÇÃO DO SETUP AJUSTE B3 (extraído do arquivo original)
# ============================================================
def render_ajuste_metricas(ativos):
    st.markdown("---")
    st.subheader("📌 1. Ajuste Oficial x Preço Atual x Last (Candle Anterior)")

    def obter_preco(nome):
        ativo = ativos.get(nome, {})
        if isinstance(ativo, dict):
            return ativo.get("preco", ativo.get("valor", 0.0))
        return 0.0

    def calcular_distancia(preco, ajuste):
        if not preco or not ajuste:
            return 0, 0
        pontos = preco - ajuste
        percentual = (pontos / ajuste) * 100 if ajuste != 0 else 0
        return pontos, percentual

    win_ajuste = obter_preco("WIN_AJUSTE")
    win_atual = obter_preco("WIN_FUT")
    win_last = obter_preco("WIN_LAST_TICK")
    wdo_ajuste = obter_preco("WDO_AJUSTE")
    wdo_atual = obter_preco("WDO_FUT")
    wdo_last = obter_preco("WDO_LAST_TICK")
    ptax = obter_preco("USD_PTAX")

    dist_win_pts, dist_win_pct = calcular_distancia(win_atual, win_ajuste)
    dist_wdo_pts, dist_wdo_pct = calcular_distancia(wdo_atual, wdo_ajuste)

    spread_win_last = win_ajuste - win_last if win_last and win_ajuste else None
    spread_wdo_last = wdo_ajuste - wdo_last if wdo_last and wdo_ajuste else None

    st.write("**📍 Mini Índice WIN**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🎯 Ajuste", f"{win_ajuste:,.0f} pts")
    with col2:
        st.metric("📊 Futuro (Close)", f"{win_atual:,.0f} pts", f"{dist_win_pct:+.2f}%")
    with col3:
        if win_last:
            st.metric("🕯️ Last (Candle)", f"{win_last:,.0f} pts")
        else:
            st.metric("🕯️ Last (Candle)", "N/A")
    with col4:
        if spread_win_last is not None:
            cor_spread = "inverse" if spread_win_last > 0 else "normal"
            st.metric("📏 Spread (Ajuste - Last)", f"{spread_win_last:+,.0f} pts", delta_color=cor_spread)
        else:
            st.metric("📏 Spread", "N/A")

    st.write("**📍 Mini Dólar WDO**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🎯 Ajuste", f"{wdo_ajuste:,.2f}")
    with col2:
        st.metric("📊 Futuro (Close)", f"{wdo_atual:,.2f}", f"{dist_wdo_pct:+.2f}%")
    with col3:
        if wdo_last:
            st.metric("🕯️ Last (Candle)", f"{wdo_last:,.2f}")
        else:
            st.metric("🕯️ Last (Candle)", "N/A")
    with col4:
        if spread_wdo_last is not None:
            cor_spread = "inverse" if spread_wdo_last > 0 else "normal"
            st.metric("📏 Spread (Ajuste - Last)", f"{spread_wdo_last:+,.2f} pts", delta_color=cor_spread)
        else:
            st.metric("📏 Spread", "N/A")

    st.caption("💡 O 'Last' é o último tick negociado no pregão anterior (capturado via MT5).")

def render_ajuste_macro(ativos):
    st.markdown("---")
    st.subheader("🌐 2. Termômetro Macro (com %)")

    def variacao(ativo):
        if isinstance(ativo, dict):
            return ativo.get("variacao_pct", ativo.get("var_pct", 0))
        return 0

    sp500 = ativos.get("SP500_FUT", {})
    nasdaq = ativos.get("NASDAQ_FUT", {})
    ewz = ativos.get("EWZ", {})
    vix = ativos.get("VIX", {})
    dxy = ativos.get("DXY", {})
    iron = ativos.get("IRON_ORE", {})
    petr = ativos.get("PETR_ADR", {})

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric("🇺🇸 S&P500", f"{sp500.get('preco', 0):,.2f}", f"{variacao(sp500):+.2f}%")
    with m2:
        st.metric("💻 Nasdaq", f"{nasdaq.get('preco', 0):,.2f}", f"{variacao(nasdaq):+.2f}%")
    with m3:
        st.metric("🇧🇷 EWZ", f"${ewz.get('preco', 0):,.2f}", f"{variacao(ewz):+.2f}%")
    with m4:
        st.metric("⚠️ VIX", f"{vix.get('preco', 0):,.2f}", f"{variacao(vix):+.2f}%", delta_color="inverse")
    with m5:
        st.metric("💵 DXY", f"{dxy.get('preco', 0):,.2f}", f"{variacao(dxy):+.2f}%", delta_color="inverse")
    with m6:
        st.metric("⛏️ Minério", f"${iron.get('preco', 0):,.2f}", f"{variacao(iron):+.2f}%")

def render_ajuste_tendencia(ativos, dados_tendencias):
    st.markdown("---")
    st.subheader("📈 3. Confluência com Tendência")

    def extrair_tendencia_win():
        if not dados_tendencias:
            return None
        for chave in ["WIN_FUT", "BMFBOVESPA:WIN1!"]:
            if chave in dados_tendencias:
                info = dados_tendencias[chave]
                return {
                    "padrao": info.get("padrao_comportamento", "N/A"),
                    "variacao": info.get("intervalo_5_para_0", {}).get("variacao_pct", 0),
                    "tendencia": info.get("intervalo_5_para_0", {}).get("tendencia", "N/A")
                }
        return None

    def obter_preco(nome):
        ativo = ativos.get(nome, {})
        if isinstance(ativo, dict):
            return ativo.get("preco", ativo.get("valor", 0.0))
        return 0.0

    def calcular_distancia(preco, ajuste):
        if not preco or not ajuste:
            return 0, 0
        pontos = preco - ajuste
        return pontos, (pontos / ajuste) * 100 if ajuste != 0 else 0

    win_ajuste = obter_preco("WIN_AJUSTE")
    win_atual = obter_preco("WIN_FUT")
    dist_win_pts, _ = calcular_distancia(win_atual, win_ajuste)

    tendencia_win = extrair_tendencia_win()
    if tendencia_win:
        emoji = "🟢" if tendencia_win["variacao"] > 0 else "🔴" if tendencia_win["variacao"] < 0 else "🟡"
        st.metric("WIN - Tendência", f"{emoji} {tendencia_win['padrao']}", f"{tendencia_win['variacao']:+.2f}%")
        if dist_win_pts > 300 and tendencia_win["tendencia"] == "SUBIU":
            st.success("✅ WIN distante do ajuste e tendência de alta - Viés Comprador")
        elif dist_win_pts < -300 and tendencia_win["tendencia"] == "DESCEU":
            st.error("🔴 WIN distante do ajuste e tendência de baixa - Viés Vendedor")
        elif abs(dist_win_pts) > 300:
            st.warning(f"⚠️ WIN distante do ajuste ({dist_win_pts:+.0f} pts) - Aguardar confirmação")
        else:
            st.info("ℹ️ WIN próximo do ajuste - Aguardar definição")
    else:
        st.info("📊 Dados de tendência não disponíveis. Execute `MapearTendencia15Min.py`")

def render_ajuste_score_win(ativos, dados_tendencias):
    st.markdown("---")
    st.subheader("📊 4. Score Quantitativo WIN")

    def variacao(ativo):
        if isinstance(ativo, dict):
            return ativo.get("variacao_pct", ativo.get("var_pct", 0))
        return 0

    def obter_preco(nome):
        ativo = ativos.get(nome, {})
        if isinstance(ativo, dict):
            return ativo.get("preco", ativo.get("valor", 0.0))
        return 0.0

    def calcular_distancia(preco, ajuste):
        if not preco or not ajuste:
            return 0, 0
        pontos = preco - ajuste
        return pontos, (pontos / ajuste) * 100 if ajuste != 0 else 0

    def extrair_tendencia_win():
        if not dados_tendencias:
            return None
        for chave in ["WIN_FUT", "BMFBOVESPA:WIN1!"]:
            if chave in dados_tendencias:
                info = dados_tendencias[chave]
                return {
                    "padrao": info.get("padrao_comportamento", "N/A"),
                    "variacao": info.get("intervalo_5_para_0", {}).get("variacao_pct", 0),
                    "tendencia": info.get("intervalo_5_para_0", {}).get("tendencia", "N/A")
                }
        return None

    sp500 = ativos.get("SP500_FUT", {})
    nasdaq = ativos.get("NASDAQ_FUT", {})
    ewz = ativos.get("EWZ", {})
    vix = ativos.get("VIX", {})
    iron = ativos.get("IRON_ORE", {})
    win_ajuste = obter_preco("WIN_AJUSTE")
    win_atual = obter_preco("WIN_FUT")
    dist_win_pts, _ = calcular_distancia(win_atual, win_ajuste)
    tendencia_win = extrair_tendencia_win()

    score_win = 0
    criterios_win = []
    if variacao(sp500) > 0:
        score_win += 1
        criterios_win.append("✅ S&P500 positivo")
    else:
        criterios_win.append("❌ S&P500 negativo")
    if variacao(iron) > 0:
        score_win += 1
        criterios_win.append("✅ Minério positivo")
    else:
        criterios_win.append("❌ Minério negativo")
    if variacao(ewz) > 0:
        score_win += 1
        criterios_win.append("✅ EWZ positivo")
    else:
        criterios_win.append("❌ EWZ negativo")
    if variacao(vix) < 0:
        score_win += 1
        criterios_win.append("✅ VIX reduzindo risco")
    else:
        criterios_win.append("❌ VIX pressionando")
    if variacao(nasdaq) > 0:
        score_win += 1
        criterios_win.append("✅ Nasdaq positivo")
    else:
        criterios_win.append("❌ Nasdaq negativo")
    if tendencia_win and tendencia_win["tendencia"] == "SUBIU" and dist_win_pts > 300:
        score_win += 1
        criterios_win.append("✅ Tendência confirma ajuste")

    col_score, col_lista = st.columns(2)
    with col_score:
        st.metric("Score WIN", f"{score_win}/6")
        if score_win >= 5:
            st.success("🟢 VIÉS COMPRADOR FORTE")
        elif score_win >= 3:
            st.warning("🟡 VIÉS NEUTRO/MODERADO")
        else:
            st.error("🔴 VIÉS VENDEDOR")
    with col_lista:
        for item in criterios_win:
            st.write(item)

def render_ajuste_score_wdo(ativos):
    st.markdown("---")
    st.subheader("💵 5. Score Quantitativo WDO")

    def variacao(ativo):
        if isinstance(ativo, dict):
            return ativo.get("variacao_pct", ativo.get("var_pct", 0))
        return 0

    usd_mxn = ativos.get("USD_MXN", {})
    dxy = ativos.get("DXY", {})
    vix = ativos.get("VIX", {})

    score_wdo = 0
    criterios_wdo = []
    if variacao(dxy) > 0:
        score_wdo += 1
        criterios_wdo.append("✅ DXY fortalecendo dólar")
    else:
        criterios_wdo.append("❌ DXY enfraquecendo dólar")
    if variacao(usd_mxn) > 0:
        score_wdo += 1
        criterios_wdo.append("✅ USD/MXN favorece dólar")
    else:
        criterios_wdo.append("❌ USD/MXN favorece moedas emergentes")
    if variacao(vix) > 0:
        score_wdo += 1
        criterios_wdo.append("✅ VIX em alta (proteção)")
    else:
        criterios_wdo.append("❌ VIX em queda")

    c_score, c_lista = st.columns(2)
    with c_score:
        st.metric("Score WDO", f"{score_wdo}/3")
        if score_wdo >= 2:
            st.success("🟢 VIÉS COMPRADOR DÓLAR")
        elif score_wdo == 0:
            st.error("🔴 VIÉS VENDEDOR DÓLAR")
        else:
            st.warning("🟡 DÓLAR NEUTRO")
    with c_lista:
        for item in criterios_wdo:
            st.write(item)

def render_ajuste_checklist():
    st.markdown("---")
    st.subheader("📋 6. Checklist de Execução")
    col_check1, col_check2 = st.columns(2)
    with col_check1:
        st.markdown("### 📈 WIN Ajuste")
        check_win_dist = st.checkbox("WIN distante do ajuste (>300 pontos)", key="ajuste_win_dist")
        check_win_fluxo = st.checkbox("Fluxo confirmou defesa/rejeição no ajuste", key="ajuste_win_fluxo")
        check_win_noticia = st.checkbox("Sem notícia de alto impacto próxima", key="ajuste_win_noticia")
    with col_check2:
        st.markdown("### 💵 WDO Ajuste")
        check_wdo_dist = st.checkbox("WDO distante do ajuste (>10 pontos)", key="ajuste_wdo_dist")
        check_wdo_fluxo = st.checkbox("Tape Reading confirmou absorção", key="ajuste_wdo_fluxo")
        check_wdo_noticia = st.checkbox("Sem evento macro imediato", key="ajuste_wdo_noticia")

    check_win_total = sum([check_win_dist, check_win_fluxo, check_win_noticia])
    check_wdo_total = sum([check_wdo_dist, check_wdo_fluxo, check_wdo_noticia])
    return check_win_total, check_wdo_total

def render_ajuste_semaforo(score_win, check_win_total, score_wdo, check_wdo_total):
    st.markdown("---")
    st.subheader("🚦 7. Semáforo Operacional")

    def gerar_status(score, checklist):
        pontos = score + checklist
        if pontos >= 7:
            return "🟢", "SETUP LIBERADO", "Alta confluência"
        elif pontos >= 4:
            return "🟡", "AGUARDAR CONFIRMAÇÃO", "Confluência parcial"
        else:
            return "🔴", "NÃO OPERAR", "Risco elevado"

    status_win = gerar_status(score_win, check_win_total)
    status_wdo = gerar_status(score_wdo, check_wdo_total)

    cwin, cwdo = st.columns(2)
    with cwin:
        st.markdown(f"""
        <div class="info-box">
            <h3>📈 SETUP WIN</h3>
            <h2>{status_win[0]} {status_win[1]}</h2>
            <p>Score: {score_win}/6<br>Checklist: {check_win_total}/3<br>{status_win[2]}</p>
        </div>
        """, unsafe_allow_html=True)
    with cwdo:
        st.markdown(f"""
        <div class="info-box">
            <h3>💵 SETUP WDO</h3>
            <h2>{status_wdo[0]} {status_wdo[1]}</h2>
            <p>Score: {score_wdo}/3<br>Checklist: {check_wdo_total}/3<br>{status_wdo[2]}</p>
        </div>
        """, unsafe_allow_html=True)

def render_ajuste_ia(win_ajuste, win_atual, dist_win_pts, wdo_ajuste, wdo_atual, dist_wdo_pts, ptax, score_win, score_wdo, status_win, status_wdo, tendencia_win, sp500, nasdaq, vix, dxy, iron):
    st.markdown("---")
    st.subheader("🧠 8. Análise IA - Ajuste B3")

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(BASE_DIR, ".env"))
            groq_key = os.getenv("GROQ_API_KEY", "")
        except Exception:
            pass

    with st.expander("⚙️ Configurações da IA", expanded=not bool(groq_key)):
        groq_key_input = st.text_input("Groq API Key", type="password", value=groq_key, help="Obtenha em https://console.groq.com", key="groq_key_ajuste_unificado")
        modelo_texto = st.selectbox("Modelo (texto)", MODELOS_GROQ_TEXTO, index=0, key="modelo_ajuste_unificado")
        st.caption("💡 Modelos de texto são mais rápidos e baratos")

    if st.button("📊 Analisar Ajuste B3 (IA)", type="primary", key="btn_ajuste_unificado"):
        key_final = groq_key_input or groq_key
        if not key_final:
            st.error("⚠️ Informe a Groq API Key")
        else:
            with st.spinner("🧠 Analisando setup de ajuste..."):
                try:
                    def variacao(ativo):
                        return ativo.get("variacao_pct", ativo.get("var_pct", 0))
                    dados_ia = {
                        "win_ajuste": f"{win_ajuste:,.0f}",
                        "win_atual": f"{win_atual:,.0f}",
                        "dist_win": f"{dist_win_pts:+,.0f}",
                        "wdo_ajuste": f"{wdo_ajuste:,.2f}",
                        "wdo_atual": f"{wdo_atual:,.2f}",
                        "dist_wdo": f"{dist_wdo_pts:+,.2f}",
                        "ptax": f"{ptax:,.4f}" if ptax else "N/A",
                        "score_win": f"{score_win}/6",
                        "score_wdo": f"{score_wdo}/3",
                        "status_win": status_win,
                        "status_wdo": status_wdo,
                        "tendencia_win": tendencia_win["padrao"] if tendencia_win else "N/A",
                        "sp500": f"{variacao(sp500):+.2f}%",
                        "nasdaq": f"{variacao(nasdaq):+.2f}%",
                        "vix": f"{variacao(vix):+.2f}%",
                        "dxy": f"{variacao(dxy):+.2f}%",
                        "iron": f"{variacao(iron):+.2f}%",
                    }
                    prompt = f"""⚠️ RESPONDA EM PORTUGUÊS DO BRASIL. SEJA DIRETO.

VOCÊ É UM ESPECIALISTA EM AJUSTE B3.

DADOS DO SETUP:

WIN: Ajuste {dados_ia['win_ajuste']} | Atual {dados_ia['win_atual']} | Distância {dados_ia['dist_win']}
WDO: Ajuste {dados_ia['wdo_ajuste']} | Atual {dados_ia['wdo_atual']} | Distância {dados_ia['dist_wdo']}
PTAX: {dados_ia['ptax']}
Score WIN: {dados_ia['score_win']} | Status: {dados_ia['status_win']}
Score WDO: {dados_ia['score_wdo']} | Status: {dados_ia['status_wdo']}
Tendência WIN: {dados_ia['tendencia_win']}
S&P500: {dados_ia['sp500']} | Nasdaq: {dados_ia['nasdaq']}
VIX: {dados_ia['vix']} | DXY: {dados_ia['dxy']} | Minério: {dados_ia['iron']}

---

RESPONDA EM PORTUGUÊS:

1. ANÁLISE DO AJUSTE WIN: O ajuste está distante ou próximo? O que esperar?
2. ANÁLISE DO AJUSTE WDO: O ajuste está distante ou próximo? O que esperar?
3. CONFLUÊNCIA MACRO: O cenário macro favorece ou atrapalha o ajuste?
4. OPORTUNIDADE: Vale a pena operar o ajuste? (SIM/NÃO/PARCIAIS)
5. RECOMENDAÇÃO: Qual ativo (WIN/WDO) tem melhor setup?
6. CONFIANÇA: De 1 a 10

SEJA DIRETO. PORTUGUÊS APENAS."""
                    client = Groq(api_key=key_final)
                    completion = client.chat.completions.create(
                        model=modelo_texto,
                        messages=[
                            {"role": "system", "content": "Você é um especialista em ajuste B3. Responda em português."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2,
                        max_tokens=1200,
                    )
                    resposta = completion.choices[0].message.content
                    resposta_limpa = re.sub(r'<think>.*?</think>', '', resposta, flags=re.DOTALL)
                    resposta_limpa = resposta_limpa.strip()
                    st.markdown(f"""
                    <div class="card-ai">
                        <h4>🤖 Análise IA - Ajuste B3</h4>
                        <div style="color:#a78bfa; font-size:0.85rem; margin-bottom:8px;">
                            ⚡ Análise baseada nos dados do pipeline
                            <span style="margin-left:12px; background:rgba(124,92,252,0.15); padding:2px 10px; border-radius:12px; font-size:0.7rem;">{modelo_texto}</span>
                        </div>
                        <div class="analysis-content">
                            {resposta_limpa.replace(chr(10), '<br>')}
                        </div>
                        <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
                            <span class="smc-tag">🎯 Ajuste B3</span>
                            <span class="smc-tag">📊 WIN/WDO</span>
                            <span class="smc-tag">🏦 Fluxo</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if "historico_ia_ajuste" not in st.session_state:
                        st.session_state.historico_ia_ajuste = []
                    st.session_state.historico_ia_ajuste.append({
                        "hora": datetime.now().strftime("%H:%M:%S"),
                        "resposta": resposta_limpa,
                    })
                except Exception as e:
                    st.error(f"❌ Erro ao chamar IA: {e}")

    if st.session_state.get("historico_ia_ajuste"):
        with st.expander("📜 Histórico de análises IA"):
            for i, h in enumerate(reversed(st.session_state.historico_ia_ajuste), 1):
                st.markdown(f"**#{i} • {h['hora']}**")
                st.markdown(h["resposta"])
                st.markdown("---")

def render_ajuste_core_json(score_win, check_win_total, status_win, score_wdo, check_wdo_total, status_wdo, fonte_dados, tendencia_win):
    st.markdown("---")
    st.subheader("🤖 9. Dados Preparados para Core Engine")
    decisao_setup = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ativo_principal": "WIN/WDO",
        "win": {"score": score_win, "checklist": check_win_total, "status": status_win},
        "wdo": {"score": score_wdo, "checklist": check_wdo_total, "status": status_wdo},
        "fonte": fonte_dados,
        "tendencia_win": tendencia_win["padrao"] if tendencia_win else "N/A",
    }
    with st.expander("📄 Visualizar JSON de decisão"):
        st.json(decisao_setup)

# ============================================================
# MAIN - PÁGINA UNIFICADA COM ABAS
# ============================================================
def main():
    st.set_page_config(
        page_title="Setup Abertura",
        page_icon="🎯",
        layout="wide",
    )
    st.markdown(CSS_CUSTOM, unsafe_allow_html=True)

    # Sidebar comum
    render_sidebar_09h()

    st.title("🎯 Setup Abertura")
    st.caption("Unificado: Ajuste B3 | Abertura 09:00")

    # Carregamento de dados compartilhado
    @st.cache_data(ttl=60, show_spinner=False)
    def carregar_dados_unificados():
        dados = {}
        for chave, caminho in ARQUIVOS.items():
            dados[chave] = carregar_json(str(caminho))
        return dados

    dados = carregar_dados_unificados()

    # Dados para o ajuste
    ativos_data = dados.get("ativos", {})
    ativos = ativos_data.get("ativos", ativos_data)
    dados_tendencias = dados.get("tendencias", {})
    fonte_dados = "DadosAtivosUnificados.json" if ativos else "N/A"

    # "decisao": dados.get("decisao", {}),
    # Dados para o 09h
    dados_09h = {
        "noticias_0900": dados.get("noticias_0900", {}),
        "metricas": dados.get("metricas", {}),
        "estimativa": dados.get("estimativa", {}),
   
        "decisao_v2": dados.get("decisao_v2", {}),
        "ativos": ativos_data,
        "tendencias": dados_tendencias,
        "resultado_operacional": dados.get("resultado_operacional", {}),
        "analise_smc": dados.get("analise_smc", {}),
        "analise_smc_regras": dados.get("analise_smc_regras", {}),
    }
    service = SetupService(dados_09h)

    # Abas
    tab_ajuste, tab_09h = st.tabs(["🎯 Ajuste B3", "🎯 Abertura 09:00"])

    # ------------------------------------------------------------
    # ABA 1: AJUSTE B3 (mantido igual)
    # ------------------------------------------------------------
    with tab_ajuste:
        if not ativos:
            st.warning("⚠️ Dados de ativos não encontrados. Execute o pipeline.")
        else:
            render_ajuste_metricas(ativos)
            render_ajuste_macro(ativos)
            render_ajuste_tendencia(ativos, dados_tendencias)

            def obter_preco(nome):
                ativo = ativos.get(nome, {})
                return ativo.get("preco", ativo.get("valor", 0.0)) if isinstance(ativo, dict) else 0.0

            def variacao(ativo):
                return ativo.get("variacao_pct", ativo.get("var_pct", 0)) if isinstance(ativo, dict) else 0

            def calcular_distancia(preco, ajuste):
                if not preco or not ajuste:
                    return 0, 0
                pontos = preco - ajuste
                percentual = (pontos / ajuste) * 100 if ajuste != 0 else 0
                return pontos, percentual

            def extrair_tendencia_win():
                for chave in ["WIN_FUT", "BMFBOVESPA:WIN1!"]:
                    if chave in dados_tendencias:
                        info = dados_tendencias[chave]
                        return {
                            "padrao": info.get("padrao_comportamento", "N/A"),
                            "variacao": info.get("intervalo_5_para_0", {}).get("variacao_pct", 0),
                            "tendencia": info.get("intervalo_5_para_0", {}).get("tendencia", "N/A")
                        }
                return None

            win_ajuste = obter_preco("WIN_AJUSTE")
            win_atual = obter_preco("WIN_FUT")
            wdo_ajuste = obter_preco("WDO_AJUSTE")
            wdo_atual = obter_preco("WDO_FUT")
            ptax = obter_preco("USD_PTAX")
            dist_win_pts, _ = calcular_distancia(win_atual, win_ajuste)
            dist_wdo_pts, _ = calcular_distancia(wdo_atual, wdo_ajuste)
            sp500 = ativos.get("SP500_FUT", {})
            nasdaq = ativos.get("NASDAQ_FUT", {})
            ewz = ativos.get("EWZ", {})
            vix = ativos.get("VIX", {})
            dxy = ativos.get("DXY", {})
            iron = ativos.get("IRON_ORE", {})
            tendencia_win = extrair_tendencia_win()

            score_win = 0
            if variacao(sp500) > 0: score_win += 1
            if variacao(iron) > 0: score_win += 1
            if variacao(ewz) > 0: score_win += 1
            if variacao(vix) < 0: score_win += 1
            if variacao(nasdaq) > 0: score_win += 1
            if tendencia_win and tendencia_win["tendencia"] == "SUBIU" and dist_win_pts > 300:
                score_win += 1

            score_wdo = 0
            if variacao(dxy) > 0: score_wdo += 1
            if variacao(ativos.get("USD_MXN", {})) > 0: score_wdo += 1
            if variacao(vix) > 0: score_wdo += 1

            render_ajuste_score_win(ativos, dados_tendencias)
            render_ajuste_score_wdo(ativos)
            check_win_total, check_wdo_total = render_ajuste_checklist()

            def gerar_status(score, checklist):
                pontos = score + checklist
                if pontos >= 7: return "SETUP LIBERADO"
                elif pontos >= 4: return "AGUARDAR CONFIRMAÇÃO"
                else: return "NÃO OPERAR"

            status_win = gerar_status(score_win, check_win_total)
            status_wdo = gerar_status(score_wdo, check_wdo_total)

            render_ajuste_semaforo(score_win, check_win_total, score_wdo, check_wdo_total)
            render_ajuste_ia(win_ajuste, win_atual, dist_win_pts, wdo_ajuste, wdo_atual, dist_wdo_pts, ptax, score_win, score_wdo, status_win, status_wdo, tendencia_win, sp500, nasdaq, vix, dxy, iron)
            render_ajuste_core_json(score_win, check_win_total, status_win, score_wdo, check_wdo_total, status_wdo, fonte_dados, tendencia_win)

            st.caption("Setup Ajuste B3 - módulo quantitativo")

    # ------------------------------------------------------------
    # ABA 2: ABERTURA 09:00 (REORGANIZADA)
    # ------------------------------------------------------------
    with tab_09h:
        st.header("Setup Abertura 09:00 – 09:15")
        st.caption("Análise com IA e dados quantitativos")

        if not service.dados_minimos_ok():
            st.error("⚠️ Dados não encontrados.\n\nExecute: `rodar_pipeline_3x.bat`")
        else:
            if service.janela_ok():
                st.success("🟢 DENTRO DA JANELA (09:00 – 09:15)")
            else:
                st.warning(f"⏰ Fora da janela • {datetime.now().strftime('%H:%M:%S')}")

            # Nova ordem numerada
            # Prioridade: Decisão V2 no topo
            render_bloco_decisao_v2(service)

            # Leilão: preparar lado antes da abertura
            render_bloco_leilao(service)

            # Operacionais pós-abertura (Ajuste 500/100 + Explosão ADRs/Macro)
            render_bloco_operacionais(service)

            render_bloco_1_filtro_classificacao(service)
            render_bloco_2_decisao_risco(service)
            render_bloco_3_abertura_escoras(service)
            render_bloco_4_contexto_confluencia(service, dados_09h)
            render_bloco_5_ia_pre_abertura(service)
            render_bloco_6_checklist()

            st.caption("Setup Abertura 09:00 • v6.2 • IA texto + Análise SMC")

    st.markdown("---")
    st.caption("Setup Abertura Unificado • v6.2 • Analisador Financeiro Quant + SMC")

if __name__ == "__main__":
    main()
