"""
Setup Abertura – Organizado
============================
Fluxo: Filtro → Decisão → Suporte → IA
Versão: 7.2 - Correção de tipos no resumo_macro
"""

import json
import os
import sys
import re
import subprocess
from datetime import datetime, time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ============================================================
# CARREGAR VARIÁVEIS DE AMBIENTE E KEYMANAGER
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from utils.KeyManager import get_groq_client, key_manager
except ImportError:
    key_manager = None

load_dotenv(BASE_DIR / ".env")

# ============================================================
# CSS UNIFICADO
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
    modelo_groq_texto: str = "llama-3.3-70b-versatile"
    temperatura_groq: float = 0.2
    max_tokens_groq: int = 2500

CONFIG = ConfigSetup09()

# ============================================================
# MAPEAMENTO DE TICKERS
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
COLETAS_DIR = BASE_DIR / "Coletas"
ARQUIVOS = {
    "noticias_0900": COLETAS_DIR / "Noticias_Calendario_0900.json",
    "metricas": COLETAS_DIR / "Metricas_Calculadas.json",
    "estimativa": COLETAS_DIR / "EstimativaAbertura.json",
    "decisao": COLETAS_DIR / "Decisao_Core.json",
    "ativos": COLETAS_DIR / "DadosAtivosUnificados.json",
    "tendencias": COLETAS_DIR / "Analise_Tendencias.json",
    "resultado_operacional": COLETAS_DIR / "Resultado_Calculadora_Operacional_Abertura.json",
    "analise_smc": COLETAS_DIR / "AnaliseGraficaSMC.json",
    "analise_smc_regras": COLETAS_DIR / "AnaliseGraficaSMC_Regras.json",
}
SCRIPT_TENDENCIAS = BASE_DIR / "MapearTendencia15Min.py"

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def carregar_json(caminho: str) -> Dict[str, Any]:
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def obter_preco(ativos: Dict, nome: str) -> Optional[float]:
    ativo = ativos.get(nome, {})
    if isinstance(ativo, dict):
        return ativo.get("preco", ativo.get("valor", 0.0))
    return None

def variacao(ativo: Dict) -> float:
    if isinstance(ativo, dict):
        return ativo.get("variacao_pct", ativo.get("var_pct", 0.0))
    return 0.0

def calcular_distancia(preco, ajuste):
    if not preco or not ajuste:
        return 0, 0
    pontos = preco - ajuste
    pct = (pontos / ajuste) * 100 if ajuste != 0 else 0
    return pontos, pct

def classificar_valor(valor: float) -> Dict[str, str]:
    abs_valor = abs(valor)
    if abs_valor < 0.3: intensidade = "LATERAL"
    elif abs_valor < 0.8: intensidade = "MUITO_FRACA"
    elif abs_valor < 1.5: intensidade = "FRACA"
    elif abs_valor < 2.5: intensidade = "MODERADA"
    elif abs_valor < 4.5: intensidade = "FORTE"
    else: intensidade = "MUITO_FORTE"

    if valor > 0.05: sinal = "COMPRA"
    elif valor < -0.05: sinal = "VENDA"
    else: sinal = "NEUTRO"
    return {"valor_pct": round(valor, 4), "rotulo": f"{intensidade}_{sinal}"}

def extrair_valor_macro(item: Union[Dict, float, str, None]) -> str:
    """Extrai o valor numérico de um item de macro que pode ser dict, float ou string."""
    if item is None:
        return "N/A"
    if isinstance(item, dict):
        # Tenta 'close' ou 'valor'
        val = item.get("close", item.get("valor", "N/A"))
        if isinstance(val, (int, float)):
            return f"{val:.2f}"
        return str(val) if val is not None else "N/A"
    if isinstance(item, (int, float)):
        return f"{item:.2f}"
    return str(item) if item else "N/A"

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

# ============================================================
# DATACLASSES
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
# CLASSE SETUPSERVICE (CORE)
# ============================================================
class SetupService:
    def __init__(self, dados: Dict[str, Dict[str, Any]], config: ConfigSetup09 = CONFIG):
        self.cfg = config
        self.dados = dados
        self._parse()

    def _parse(self):
        noticias = self.dados.get("noticias_0900", {})
        alerta = noticias.get("alerta_noticia_0900", {})
        self.tem_3estrelas: bool = alerta.get("tem_evento_3_estrelas", False)
        self.eventos_3e: list = alerta.get("eventos", [])
        self.alerta_texto: str = alerta.get("alerta", "")

        metricas = self.dados.get("metricas", {})
        indicadores = metricas.get("indicadores_compostos", {})
        self.ind_mercado_externo = indicadores.get("indicador_mercado_externo", 0.0)
        self.ind_adrs = indicadores.get("indicador_adrs_brasileiras", 0.0)

        if self.ind_mercado_externo == 0.0 or self.ind_adrs == 0.0:
            resultado_op = self.dados.get("resultado_operacional", {})
            indicadores_op = resultado_op.get("indicadores_compostos", {})
            if indicadores_op:
                if self.ind_mercado_externo == 0.0:
                    mercado = indicadores_op.get("mercado_externo", {})
                    self.ind_mercado_externo = mercado.get("valor_pct", 0.0)
                if self.ind_adrs == 0.0:
                    adrs = indicadores_op.get("adrs_brasileiras", {})
                    self.ind_adrs = adrs.get("valor_pct", 0.0)

        if self.ind_mercado_externo == 0.0:
            macro = metricas.get("indicadores_macro", {})
            vix_change = macro.get("vix_change_pct")
            crude_change = macro.get("crude_oil_change_pct")
            iron_data = macro.get("iron_ore_fef2", {}) if "iron_ore_fef2" in macro else macro.get("iron_ore", {})
            iron_change = iron_data.get("change_percent") if isinstance(iron_data, dict) else None
            if vix_change is not None and crude_change is not None and iron_change is not None:
                self.ind_mercado_externo = (-vix_change) + crude_change + iron_change

        if self.ind_adrs == 0.0:
            adrs_data = metricas.get("performance_relativa", {}).get("adrs_brasileiras", {})
            if adrs_data:
                soma = 0.0
                count = 0
                for adr in adrs_data.values():
                    pct = adr.get("change_percent")
                    if pct is not None:
                        soma += pct
                        count += 1
                if count > 0:
                    self.ind_adrs = soma

        self.adrs: dict = metricas.get("performance_relativa", {}).get("adrs_brasileiras", {})

        est = self.dados.get("estimativa", {})
        self.est_win = est.get("estimativas_abertura", {}).get("WIN_INDICE", {})
        self.est_wdo = est.get("estimativas_abertura", {}).get("WDO_DOLAR", {})
        self.pivot_win = est.get("pivot_points", {}).get("WIN_FUT") or {}
        self.pivot_wdo = est.get("pivot_points", {}).get("WDO_FUT") or {}
        self.resumo_macro = est.get("resumo_macro", {})

        decisao = self.dados.get("decisao", {})
        analise_op = decisao.get("analise_operacional", {})
        self.win_core = analise_op.get("WIN_INDICE", {})
        self.wdo_core = analise_op.get("WDO_DOLAR", {})

        dados_ativos = self.dados.get("ativos", {})
        ativos = dados_ativos.get("ativos", dados_ativos)
        self.win_ativo = ativos.get("WIN_FUT", {})
        self.preco_win = self.win_ativo.get("preco")

        tendencias_data = self.dados.get("tendencias", {})
        self.tendencias = self._extrair_tendencias(tendencias_data)

        self.analise_smc = self.dados.get("analise_smc", {}) or {}
        self.analise_smc_regras = self.dados.get("analise_smc_regras", {}) or {}

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
        p = self.pivot_win
        return Escoras(
            pp=p.get("PP", 0.0),
            r1=p.get("R1", 0.0),
            r2=p.get("R2", 0.0),
            s1=p.get("S1", 0.0),
            s2=p.get("S2", 0.0),
        )

    def core_win(self) -> DecisaoCore:
        return DecisaoCore(
            vies=self.win_core.get("vies_final", "N/D"),
            score=self.win_core.get("score_numeric", 0.0),
            fatores=self.win_core.get("fatores_relevantes", []),
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

    def _resumir_bloco_smc(self, bloco: Dict[str, Any], rotulo: str) -> str:
        if not bloco or bloco.get("erro"):
            return ""

        partes = [f"[{rotulo}]"]
        bias = bloco.get("bias_direcional") or bloco.get("direcao_estrutura")
        if bias:
            partes.append(f"Bias: {bias}")
        if "bos" in bloco:
            partes.append(f"BOS: {bloco.get('bos')} | CHoCH: {bloco.get('choch')}")
        conf = bloco.get("confianca_visual")
        if conf is not None:
            partes.append(f"Conf: {conf}")
        tfs = bloco.get("timeframes_identificados")
        if tfs:
            partes.append(f"TF: {tfs}")
        if bloco.get("entrada_sugerida"):
            partes.append(
                f"Entrada: {bloco.get('entrada_sugerida')} | "
                f"Stop: {bloco.get('stop_sugerido')} | "
                f"Alvos: {bloco.get('alvos')}"
            )
        zonas = bloco.get("zonas_de_interesse_e_cenarios") or []
        if zonas:
            partes.append("Cenários: " + " | ".join(str(z) for z in zonas[:3]))
        liq = bloco.get("liquidez_relevante") or []
        if liq:
            partes.append("Liquidez: " + " | ".join(str(l) for l in liq[:4]))
        estruturas = bloco.get("estruturas_coletadas") or []
        if estruturas:
            partes.append("Estruturas: " + " | ".join(str(e) for e in estruturas[:6]))

        obs = bloco.get("order_blocks") or []
        if obs:
            partes.append(
                "OBs: "
                + " | ".join(
                    f"{o.get('tipo')}@{o.get('preco')}" for o in obs[:4]
                )
            )
        fvgs = bloco.get("fair_value_gaps") or []
        if fvgs:
            abertos = [f for f in fvgs if not f.get("preenchido")]
            partes.append(
                "FVGs: "
                + " | ".join(
                    f"{f.get('tipo')}({f.get('inferior')}-{f.get('superior')})"
                    for f in abertos[:4]
                )
            )
        return " • ".join(partes)

    def _resumir_analise_smc(self) -> str:
        partes = []
        r_regras = self._resumir_bloco_smc(self.analise_smc_regras, "REGRAS")
        r_visao = self._resumir_bloco_smc(self.analise_smc, "VISÃO")
        if r_regras:
            partes.append(r_regras)
        if r_visao:
            partes.append(r_visao)
        if not partes:
            return "Análise gráfica SMC não disponível (nem regras nem visão)."

        b1 = (self.analise_smc_regras or {}).get("bias_direcional")
        b2 = (self.analise_smc or {}).get("bias_direcional") or (
            self.analise_smc or {}
        ).get("direcao_estrutura")
        if b1 and b2:
            if str(b1).upper() == str(b2).upper():
                partes.append("[CONFLUÊNCIA] Regras e visão com o mesmo bias.")
            else:
                partes.append(
                    f"[DIVERGÊNCIA] Regras={b1} vs Visão={b2} — priorize confirmação de preço."
                )
        return " || ".join(partes)

    def dados_para_ia_resumido(self) -> Dict[str, Any]:
        s = self.sinal()
        da = self.dados_abertura()
        e = self.escoras()
        cw = self.core_win()

        win_tend = self.tendencias.get("WIN_FUT")
        tend_resumo = f"{win_tend.padrao} ({win_tend.ultima_variacao:+.2f}%)" if win_tend else "N/A"

        return {
            "sinal": f"{s.direcao} ({s.forca}/10)",
            "indicador": f"{s.indicador_usado}: {s.valor_indicador:+.2f}%",
            "abertura": f"{da.abertura_teorica:,.0f} pts (var: {da.var_teorica:+.2f}%, gap: {da.gap_pontos:+.0f})",
            "preco_atual": f"{da.preco_atual:,.0f}" if da.preco_atual else "N/A",
            "escoras": f"R2:{e.r2:,.0f} R1:{e.r1:,.0f} PP:{e.pp:,.0f} S1:{e.s1:,.0f} S2:{e.s2:,.0f}",
            "core": f"WIN: {cw.vies} (score:{cw.score})",
            "noticias": "🚨 3★" if self.tem_3estrelas else "Sem alerta",
            "tendencia_win": tend_resumo,
            "confluencia": self.confluencia_tendencia()["motivo"],
            "analise_smc": self._resumir_analise_smc(),
            "loss": CONFIG.loss_pts,
            "alvo": CONFIG.alvo_min_pts,
        }

# ============================================================
# FUNÇÕES DE IA (com KeyManager e limpeza PT-BR)
# ============================================================
def limpar_pensamento_ia(texto: str) -> str:
    if not texto:
        return texto

    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL | re.IGNORECASE)
    texto = re.sub(r"<thought>.*?</thought>", "", texto, flags=re.DOTALL | re.IGNORECASE)
    texto = re.sub(r"<reasoning>.*?</reasoning>", "", texto, flags=re.DOTALL | re.IGNORECASE)

    padroes = [
        r"(?is)Here's a thinking process:.*?(?=###|\Z)",
        r"(?is)Here is a thinking process:.*?(?=###|\Z)",
        r"(?is)Thinking process:.*?(?=###|\Z)",
        r"(?is)\*\*Analyze User Input:\*\*.*?(?=###|\Z)",
        r"(?is)1\.\s*\*\*Analyze User Input:\*\*.*?(?=###|\Z)",
        r"(?is)Draft generation \(mental refinement.*?(?=###|\Z)",
        r"(?is)Check Against Constraints:.*?(?=###|\Z)",
        r"(?is)Map Data to Required.*?(?=###|\Z)",
    ]
    for p in padroes:
        texto = re.sub(p, "", texto)

    marcadores = ["### 📊 1.", "### 1.", "1. **DIREÇÃO", "1. ANÁLISE DO AJUSTE"]
    melhor_idx = -1
    for m in marcadores:
        idx = texto.find(m)
        if idx != -1 and (melhor_idx == -1 or idx < melhor_idx):
            melhor_idx = idx
    if melhor_idx > 0:
        pre = texto[:melhor_idx].lower()
        if any(
            x in pre
            for x in (
                "thinking",
                "analyze user",
                "draft generation",
                "check against",
                "map data",
                "here's a",
                "here is a",
            )
        ):
            texto = texto[melhor_idx:]

    return texto.strip()

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
    if not resposta:
        return resposta

    resposta = limpar_pensamento_ia(resposta)

    palavras_portugues = [
        "mercado", "tendência", "compra", "venda", "preço", "suporte",
        "resistência", "análise", "estrutura", "liquidez", "entrada",
        "alvo", "stop", "perda", "rompimento", "confirmação", "nível",
        "abertura", "gap", "confiança",
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
        return resultado.strip()
    aviso = "⚠️ RESPOSTA TRADUZIDA PARA PORTUGUÊS:\n\n"
    return aviso + forcar_portugues(resposta)

def chamar_groq_texto(
    api_key: str,
    prompt: str,
    modelo: str,
    system_content: Optional[str] = None,
) -> str:
    try:
        from groq import Groq
    except ImportError as exc:
        raise RuntimeError("Biblioteca 'groq' não instalada. Rode: pip install groq") from exc

    try:
        if key_manager:
            client, key_utilizada = get_groq_client()
        else:
            client = Groq(api_key=api_key) if api_key else None
            key_utilizada = api_key
            if not client:
                return "❌ Nenhuma chave API fornecida e KeyManager não disponível."
    except Exception as e:
        if api_key:
            client = Groq(api_key=api_key)
            key_utilizada = api_key
        else:
            return f"❌ Erro ao obter chave API: {str(e)}"

    if not system_content:
        system_content = """VOCÊ É UM ESPECIALISTA EM MERCADO BRASILEIRO (B3 / WIN / WDO).

REGRAS OBRIGATÓRIAS:
1. RESPONDA 100% EM PORTUGUÊS DO BRASIL.
2. NÃO MOSTRE RACIOCÍNIO INTERNO, THINKING OU PLANEJAMENTO.
3. SEJA DIRETO E OBJETIVO.
4. USE TERMOS TÉCNICOS DO MERCADO.
5. COMPLETE TODA A ESTRUTURA PEDIDA NO PROMPT.
6. NÃO USE INGLÊS."""

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": prompt},
    ]

    try:
        completion = client.chat.completions.create(
            model=modelo,
            messages=messages,
            temperature=CONFIG.temperatura_groq,
            max_tokens=CONFIG.max_tokens_groq,
        )

        if hasattr(completion, "usage") and completion.usage:
            tokens = completion.usage.total_tokens
            if key_manager:
                try:
                    key_manager.registrar_uso(key_utilizada, tokens)
                except Exception:
                    pass
            print(f"📊 Tokens usados (texto): {tokens}")

        bruto = completion.choices[0].message.content or ""
        return garantir_portugues(limpar_pensamento_ia(bruto))

    except Exception as e:
        erro_msg = str(e).lower()
        if "429" in erro_msg or "rate_limit" in erro_msg:
            if key_manager:
                try:
                    key_manager.marcar_rate_limit(key_utilizada)
                except Exception:
                    pass
                try:
                    client, key_utilizada = get_groq_client()
                    return chamar_groq_texto(api_key, prompt, modelo, system_content)
                except Exception:
                    return "❌ Todas as chaves em rate limit. Tente novamente em algumas horas."
        raise e

def montar_prompt_unificado(dados: Dict[str, Any]) -> str:
    return f"""⚠️ RESPONDA EM PORTUGUÊS DO BRASIL. SEJA DIRETO E OBJETIVO.

VOCÊ É UM ESPECIALISTA EM PRÉ-ABERTURA E AJUSTE B3.

📊 DADOS DO PIPELINE:

SINAL DO SETUP: {dados['sinal']}
INDICADOR USADO: {dados['indicador']}
ABERTURA TEÓRICA: {dados['abertura']}
PREÇO ATUAL: {dados['preco_atual']}
ESCORAS (PIVOTS): {dados['escoras']}
CORE ENGINE: {dados['core']}
NOTÍCIAS RELEVANTES: {dados['noticias']}
TENDÊNCIA WIN: {dados['tendencia_win']}
CONFLUÊNCIA: {dados['confluencia']}
ANÁLISE GRÁFICA SMC: {dados.get('analise_smc', 'Não disponível')}
GESTÃO DE RISCO: Loss {dados['loss']}pts | Alvo >{dados['alvo']}pts

---

🎯 SUA ANÁLISE CONSOLIDADA - RESPONDA EM PORTUGUÊS:

1. ANÁLISE DO AJUSTE B3: O ajuste do WIN está distante ou próximo? O que esperar?
2. DIREÇÃO ESPERADA NA ABERTURA: Qual a direção provável para os primeiros minutos? (COMPRA/VENDA/LATERAL)
3. ANÁLISE DO GAP: O GAP está grande ou pequeno? Como isso impacta?
4. VOLATILIDADE E NÍVEIS CHAVE: O mercado deve abrir com alta ou baixa volatilidade? Quais níveis (pivots + SMC) são mais importantes?
5. CENÁRIOS PROVÁVEIS:
   - Cenário 1 (mais provável):
   - Cenário 2 (alternativo):
   - Cenário 3 (se romper):
6. RECOMENDAÇÃO: O que fazer nos primeiros 5-10 minutos?
7. GRAU DE CONFIANÇA: De 1 a 10 (justifique)

⚠️ OBSERVAÇÕES:
- Baseie-se nos dados fornecidos (quantitativo + SMC)
- Quando a análise SMC estiver alinhada com o sinal do setup, dê mais peso a ela
- Seja prático e objetivo
- RESPONDA 100% EM PORTUGUÊS DO BRASIL
- NÃO mostre raciocínio interno
- Complete TODAS as 7 seções
"""

# ============================================================
# SIDEBAR
# ============================================================
def render_sidebar():
    st.sidebar.title("🎯 Setup Abertura")
    st.sidebar.caption("Filtro → Decisão → Suporte → IA")
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
        "Decisão": ARQUIVOS["decisao"],
        "Tendências": ARQUIVOS["tendencias"],
        "Resultado": ARQUIVOS["resultado_operacional"],
        "SMC Visão": ARQUIVOS["analise_smc"],
        "SMC Regras": ARQUIVOS["analise_smc_regras"],
    }
    for nome, caminho in arquivos_status.items():
        existe = "✅" if os.path.exists(caminho) else "❌"
        st.sidebar.caption(f"{existe} {nome}")

    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Limpar Histórico IA", use_container_width=True):
        if "historico_pre_abertura" in st.session_state:
            st.session_state.historico_pre_abertura = []
        st.rerun()

# ============================================================
# RENDERIZAÇÃO PRINCIPAL
# ============================================================
def main():
    st.set_page_config(page_title="Setup Abertura", page_icon="🎯", layout="wide")
    st.markdown(CSS_CUSTOM, unsafe_allow_html=True)

    render_sidebar()

    st.title("🎯 Setup Abertura")
    st.caption("Fluxo: Filtro → Decisão → Suporte → IA")

    # Carrega dados
    dados = {}
    for chave, caminho in ARQUIVOS.items():
        dados[chave] = carregar_json(str(caminho))

    ativos_data = dados.get("ativos", {})
    ativos = ativos_data.get("ativos", ativos_data)

    dados_service = {
        "noticias_0900": dados.get("noticias_0900", {}),
        "metricas": dados.get("metricas", {}),
        "estimativa": dados.get("estimativa", {}),
        "decisao": dados.get("decisao", {}),
        "ativos": ativos_data,
        "tendencias": dados.get("tendencias", {}),
        "resultado_operacional": dados.get("resultado_operacional", {}),
        "analise_smc": dados.get("analise_smc", {}),
        "analise_smc_regras": dados.get("analise_smc_regras", {}),
    }
    service = SetupService(dados_service)

    if not service.dados_minimos_ok():
        st.warning("⚠️ Dados insuficientes. Execute o pipeline.")
        return

    # ============================================================
    # 1. FILTRO E DECISÃO
    # ============================================================
    st.markdown("---")
    st.subheader("📌 1. Filtro e Decisão")

    col_filtro, col_sinal, col_class = st.columns([1, 1.5, 1.5])

    with col_filtro:
        if service.tem_3estrelas:
            st.warning("🚨 Notícia ⭐⭐⭐ detectada → Prioridade: ADRs")
            if service.eventos_3e:
                for ev in service.eventos_3e:
                    st.caption(f"• {ev.get('hora', '')} | {ev.get('evento', '')}")
        else:
            st.success("✅ Sem notícia ⭐⭐⭐ → Prioridade: Mercado Externo")

    with col_sinal:
        s = service.sinal()
        st.markdown(
            f"""
            <div class="{s.classe_css}">
                <h3>{s.emoji} SINAL: {s.direcao}</h3>
                <b>Indicador:</b> {s.indicador_usado} ({s.valor_indicador:+.2f}%)
                <br><b>Força:</b> {s.forca}/10
                <br><small>{s.motivo_escolha}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_class:
        valor_usado = service.ind_adrs if service.tem_3estrelas else service.ind_mercado_externo
        classificacao = classificar_valor(valor_usado)
        st.metric("Classificação", classificacao["rotulo"], f"{valor_usado:+.2f}%")

    # ============================================================
    # 2. PAINEL DE SUPORTE (AJUSTE + ESCORAS + MACRO)
    # ============================================================
    st.markdown("---")
    st.subheader("📊 2. Suporte Técnico e Macro")

    win_ajuste = obter_preco(ativos, "WIN_AJUSTE")
    win_atual = obter_preco(ativos, "WIN_FUT")
    wdo_ajuste = obter_preco(ativos, "WDO_AJUSTE")
    wdo_atual = obter_preco(ativos, "WDO_FUT")
    dist_win, _ = calcular_distancia(win_atual, win_ajuste)
    dist_wdo, _ = calcular_distancia(wdo_atual, wdo_ajuste)

    col_ajuste, col_escoras, col_macro = st.columns(3)

    with col_ajuste:
        st.markdown("**📐 Ajuste B3**")
        st.metric("WIN distância", f"{dist_win:+.0f} pts")
        st.metric("WDO distância", f"{dist_wdo:+.2f}")

    with col_escoras:
        e = service.escoras()
        st.markdown("**📍 Pivots WIN**")
        r1, r2, pp, s1, s2 = st.columns(5)
        with r1: st.metric("R2", f"{e.r2:,.0f}")
        with r2: st.metric("R1", f"{e.r1:,.0f}")
        with pp: st.metric("PP", f"{e.pp:,.0f}")
        with s1: st.metric("S1", f"{e.s1:,.0f}")
        with s2: st.metric("S2", f"{e.s2:,.0f}")

    with col_macro:
        st.markdown("**🌍 Macro**")
        resumo = service.resumo_macro

        # Usa a função extrair_valor_macro para cada item
        vix_val = extrair_valor_macro(resumo.get("vix"))
        crude_val = extrair_valor_macro(resumo.get("crude_oil"))
        iron_val = extrair_valor_macro(resumo.get("iron_ore"))
        dxy_val = extrair_valor_macro(resumo.get("dxy"))

        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("VIX", vix_val)
        with m2: st.metric("Petróleo", crude_val)
        with m3: st.metric("Minério", iron_val)
        with m4: st.metric("DXY", dxy_val)

    # ============================================================
    # 3. TENDÊNCIA E SMC
    # ============================================================
    st.markdown("---")
    st.subheader("📈 3. Tendência e SMC")

    col_tend, col_smc = st.columns(2)

    with col_tend:
        tendencias = service.tendencias
        if tendencias:
            cols = st.columns(min(4, len(tendencias)))
            for i, (ativo, tend) in enumerate(tendencias.items()):
                with cols[i % len(cols)]:
                    delta_color = "normal" if tend.ultima_variacao > 0 else "inverse"
                    st.metric(
                        ativo,
                        f"{tend.padrao}",
                        f"{tend.ultima_variacao:+.2f}%",
                        delta_color=delta_color,
                    )
            confluencia = service.confluencia_tendencia()
            if confluencia["confluente"]:
                st.success(f"✅ {confluencia['motivo']}")
            else:
                st.warning(f"⚠️ {confluencia['motivo']}")

    with col_smc:
        st.markdown("**🔷 SMC (Smart Money)**")
        smc_resumo = service._resumir_analise_smc()
        st.info(smc_resumo)

    # ============================================================
    # 4. GESTÃO DE RISCO
    # ============================================================
    st.markdown("---")
    st.subheader("🛡️ 4. Gestão de Risco")

    col_loss, col_alvo, col_stop = st.columns(3)
    da = service.dados_abertura()
    with col_loss:
        st.metric("Loss", f"{CONFIG.loss_pts} pts")
    with col_alvo:
        st.metric("Alvo mínimo", f"> {CONFIG.alvo_min_pts} pts")
    with col_stop:
        preco = da.preco_atual
        if preco and s.direcao == "COMPRA":
            st.metric("Stop sugerido", f"{preco - CONFIG.loss_pts:,.0f}")
        elif preco and s.direcao == "VENDA":
            st.metric("Stop sugerido", f"{preco + CONFIG.loss_pts:,.0f}")
        else:
            st.metric("Stop sugerido", "N/A")

    # ============================================================
    # 5. IA DE CONFIRMAÇÃO
    # ============================================================
    st.markdown("---")
    st.subheader("🧠 5. Análise IA – Confirmação Final")

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        load_dotenv(BASE_DIR / ".env")
        groq_key = os.getenv("GROQ_API_KEY", "")

    with st.expander("⚙️ Configurações da IA", expanded=False):
        groq_key_input = st.text_input(
            "Groq API Key (opcional)",
            type="password",
            value=groq_key,
            key="groq_key_organizado",
        )
        modelo = st.selectbox(
            "Modelo",
            ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
            index=0,
            key="modelo_organizado",
        )
        st.caption("💡 KeyManager + limpeza PT-BR")

    if st.button("📊 Gerar Análise Consolidada", type="primary", key="btn_ia_organizado"):
        key_final = groq_key_input or groq_key or ""
        with st.spinner("🧠 Gerando análise..."):
            try:
                dados_ia = service.dados_para_ia_resumido()
                prompt = montar_prompt_unificado(dados_ia)
                resposta = chamar_groq_texto(key_final, prompt, modelo)

                st.markdown(
                    f"""
                    <div class="card-ai">
                        <h4>🤖 Análise Consolidada</h4>
                        <div style="color:#a78bfa; font-size:0.85rem; margin-bottom:8px;">
                            ⚡ Pipeline • KeyManager • PT-BR
                            <span style="margin-left:12px; background:rgba(124,92,252,0.15); padding:2px 10px; border-radius:12px; font-size:0.7rem;">{modelo}</span>
                        </div>
                        <div class="analysis-content">
                            {resposta.replace(chr(10), '<br>')}
                        </div>
                        <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
                            <span class="smc-tag">🎯 Ajuste B3</span>
                            <span class="smc-tag">📊 Pré-Abertura</span>
                            <span class="smc-tag">🔷 SMC</span>
                            <span class="smc-tag">🎯 Níveis</span>
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
                    "modelo": modelo,
                    "resposta": resposta,
                })

            except Exception as e:
                st.error(f"❌ Erro: {e}")

    if st.session_state.get("historico_pre_abertura"):
        with st.expander("📜 Histórico de Análises"):
            for i, h in enumerate(reversed(st.session_state.historico_pre_abertura), 1):
                st.markdown(f"**#{i} • {h['hora']}**")
                st.markdown(h["resposta"])
                st.markdown("---")

    # ============================================================
    # 6. CHECKLIST FINAL
    # ============================================================
    st.markdown("---")
    st.subheader("✅ 6. Checklist de Execução")

    col_check1, col_check2 = st.columns(2)
    with col_check1:
        st.markdown("**📈 WIN**")
        c1 = st.checkbox("Sinal alinhado com tendência", key="ck_win_1")
        c2 = st.checkbox("Stop e alvo definidos", key="ck_win_2")
        c3 = st.checkbox("Sem notícia de alto impacto iminente", key="ck_win_3")
    with col_check2:
        st.markdown("**💵 WDO**")
        c4 = st.checkbox("DXY e USD/MXN alinhados", key="ck_wdo_1")
        c5 = st.checkbox("Stop e alvo definidos", key="ck_wdo_2")
        c6 = st.checkbox("Fluxo observado", key="ck_wdo_3")

    if all([c1, c2, c3, c4, c5, c6]):
        st.success("🚀 SETUP VALIDADO – PRONTO PARA OPERAR")
    else:
        st.info("⏳ Complete o checklist antes de operar")

    st.caption("Setup Abertura v7.2 • Correção de tipos no resumo_macro")


if __name__ == "__main__":
    main()