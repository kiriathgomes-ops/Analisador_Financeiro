"""
Dashboard: Setup Abertura 09:00 – 09:15
========================================
Versão 5.3 - SEM IA VISUAL (apenas texto)
"""

import json
import os
import subprocess
import sys
import re
from datetime import datetime, time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

# ============================================================
# CARREGAR VARIÁVEIS DE AMBIENTE
# ============================================================
load_dotenv()

# ============================================================
# ADICIONA A RAIZ AO PATH PARA IMPORTAR O KEYMANAGER
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.KeyManager import get_groq_client, key_manager

# ============================================================
# CONFIGURAÇÕES CENTRALIZADAS
# ============================================================

@dataclass(frozen=True)
class ConfigSetup09:
    janela_inicio: time = time(9, 0)
    janela_fim: time = time(9, 15)
    threshold_sinal: float = 1.5
    forca_max: int = 10
    loss_pts: int = 250
    alvo_min_pts: int = 250
    # Modelos apenas para texto (visão removida)
    modelo_groq_texto: str = "llama-3.3-70b-versatile"
    temperatura_groq: float = 0.2
    max_tokens_groq: int = 1200


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
# CAMINHOS
# ============================================================

COLETAS_DIR = Path(BASE_DIR) / "Coletas"
PROMPT_DIR = Path(BASE_DIR) / "PromptIA"

ARQUIVOS = {
    "noticias_0900": COLETAS_DIR / "Noticias_Calendario_0900.json",
    "metricas": COLETAS_DIR / "Metricas_Calculadas.json",
    "estimativa": COLETAS_DIR / "EstimativaAbertura.json",
    "decisao": COLETAS_DIR / "Decisao_Core.json",
    "ativos": COLETAS_DIR / "DadosAtivosUnificados.json",
    "tendencias": COLETAS_DIR / "Analise_Tendencias.json",
    "resultado_operacional": COLETAS_DIR / "Resultado_Calculadora_Operacional_Abertura.json",
}

SCRIPT_TENDENCIAS = BASE_DIR / "MapearTendencia15Min.py"

# ============================================================
# CSS PERSONALIZADO
# ============================================================

CSS_CUSTOM = """
<style>
.stApp { background-color: #0e1117; }

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
# FUNÇÕES AUXILIARES
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

# ============================================================
# CAMADA DE DADOS
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def carregar_json(caminho: str) -> Dict[str, Any]:
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}

def carregar_todos_dados() -> Dict[str, Dict[str, Any]]:
    return {chave: carregar_json(str(caminho)) for chave, caminho in ARQUIVOS.items()}

# ============================================================
# MODELO DE DOMÍNIO
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
# SERVIÇO DE LÓGICA
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
        
        self.ind_mercado_externo = 0.0
        self.ind_adrs = 0.0
        
        if indicadores:
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
            iron_data = macro.get("iron_ore", {})
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
                    self.ind_adrs = soma / count
        
        self.adrs: dict = metricas.get("performance_relativa", {}).get("adrs_brasileiras", {})

        est = self.dados.get("estimativa", {})
        self.est_win = est.get("estimativas_abertura", {}).get("WIN_INDICE", {})
        self.est_wdo = est.get("estimativas_abertura", {}).get("WDO_DOLAR", {})
        self.pivot_win = est.get("pivot_points", {}).get("WIN_FUT", {})
        self.pivot_wdo = est.get("pivot_points", {}).get("WDO_FUT", {})
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
            "loss": CONFIG.loss_pts,
            "alvo": CONFIG.alvo_min_pts,
        }

# ============================================================
# PROMPT PARA PRÉ-ABERTURA (SOMENTE TEXTO)
# ============================================================

def montar_prompt_pre_abertura(dados: Dict[str, Any]) -> str:
    """Prompt específico para análise de pré-abertura."""
    
    return f"""⚠️ RESPONDA EM PORTUGUÊS DO BRASIL. SEJA DIRETO E OBJETIVO.

VOCÊ É UM ESPECIALISTA EM PRÉ-ABERTURA DO MERCADO BRASILEIRO.

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
GESTÃO DE RISCO: Loss {dados['loss']}pts | Alvo >{dados['alvo']}pts

---

🎯 **SUA ANÁLISE DE PRÉ-ABERTURA - RESPONDA EM PORTUGUÊS:**

1. **DIREÇÃO ESPERADA:** Qual a direção provável para os primeiros minutos? (COMPRA/VENDA/LATERAL)

2. **ANÁLISE DO GAP:** O GAP está grande ou pequeno? Como isso impacta a abertura?

3. **VOLATILIDADE:** O mercado deve abrir com alta ou baixa volatilidade?

4. **NÍVEIS CHAVE:** Quais escoras (pivots) são mais importantes para monitorar?

5. **CENÁRIOS PROVÁVEIS:** 
   - Cenário 1 (mais provável):
   - Cenário 2 (alternativo):
   - Cenário 3 (se romper):

6. **RECOMENDAÇÃO:** O que fazer nos primeiros 5-10 minutos?

7. **GRAU DE CONFIANÇA:** De 1 a 10 (justifique)

---

⚠️ **OBSERVAÇÕES:**
- Baseie-se APENAS nos dados fornecidos acima
- Seja prático e objetivo
- Use termos técnicos do mercado
- RESPONDA EM PORTUGUÊS
- Não mostre raciocínio, apenas a análise final
"""

# ============================================================
# CHAMADA GROQ (SOMENTE TEXTO) - COM ROTAÇÃO DE CHAVES
# ============================================================

def chamar_groq_texto(api_key: str, prompt: str, modelo: str) -> str:
    """Chama o Groq apenas com texto."""
    try:
        from groq import Groq
    except ImportError as exc:
        raise RuntimeError("Biblioteca 'groq' não instalada. Rode: pip install groq") from exc

    # USA O GERENCIADOR DE CHAVES PARA ROTAÇÃO
    try:
        client, key_utilizada = get_groq_client()
        print(f"🔑 Usando chave: {key_utilizada[:20]}...")
    except Exception as e:
        return f"❌ Erro ao obter chave API: {str(e)}"
    
    messages = [
        {
            "role": "system",
            "content": """VOCÊ É UM ESPECIALISTA EM PRÉ-ABERTURA DO MERCADO BRASILEIRO.

REGRAS:
1. RESPONDA 100% EM PORTUGUÊS DO BRASIL.
2. NÃO MOSTRE SEU RACIOCÍNIO.
3. SEJA DIRETO E OBJETIVO.
4. USE TERMOS TÉCNICOS DO MERCADO.
5. SUA ANÁLISE DEVE AJUDAR O TRADER NA ABERTURA.

SUA RESPOSTA DEVE SER 100% EM PORTUGUÊS."""
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
        
        # Registra uso de tokens
        if hasattr(completion, 'usage'):
            tokens = completion.usage.total_tokens
            key_manager.registrar_uso(key_utilizada, tokens)
            print(f"📊 Tokens usados (texto): {tokens} (chave: {key_utilizada[:8]}...)")
        
        return completion.choices[0].message.content
        
    except Exception as e:
        erro_msg = str(e).lower()
        
        # Rate limit detectado
        if "429" in erro_msg or "rate_limit" in erro_msg:
            print(f"⚠️ Rate limit detectado na chave {key_utilizada[:8]}...")
            key_manager.marcar_rate_limit(key_utilizada)
            
            # Tenta com a próxima chave
            try:
                client, key_utilizada = get_groq_client()
                print(f"🔑 Trocando para nova chave: {key_utilizada[:20]}...")
                return chamar_groq_texto(api_key, prompt, modelo)
            except:
                return "❌ Todas as chaves em rate limit. Tente novamente em algumas horas."
        
        raise e

# ============================================================
# GARANTIR PORTUGUÊS - TRADUÇÃO FORÇADA
# ============================================================

def forcar_portugues(resposta: str) -> str:
    """Converte qualquer resposta para português - FORÇA BRUTA."""
    
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
    """Versão final - combina detecção + tradução forçada."""
    
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
# UI - SIDEBAR
# ============================================================

def render_sidebar():
    """Sidebar do Setup 09:00."""
    st.sidebar.title("🎯 Setup 09:00")
    st.sidebar.caption("Abertura 09:00 – 09:15")
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
    }
    for nome, caminho in arquivos_status.items():
        existe = "✅" if os.path.exists(caminho) else "❌"
        st.sidebar.caption(f"{existe} {nome}")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Limpar Histórico", width="stretch"):
        if "historico_pre_abertura" in st.session_state:
            st.session_state.historico_pre_abertura = []
        st.rerun()

# ============================================================
# UI - BLOCO: SINAL
# ============================================================

def render_bloco_sinal(service: SetupService):
    s = service.sinal()
    da = service.dados_abertura()
    cw = service.core_win()
    cwdo = service.core_wdo()

    st.subheader("🎯 Decisão do Setup 09:00")
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
        st.markdown("#### Core Engine")
        st.info(f"""
**WIN:** `{cw.vies}` (score: {cw.score})
**WDO:** `{cwdo.vies}` (score: {cwdo.score})
        """)

    if cw.fatores:
        with st.expander("Fatores relevantes"):
            for f in cw.fatores:
                st.write(f"• {f}")

    st.markdown("---")

# ============================================================
# UI - BLOCO: ABERTURA
# ============================================================

def render_bloco_abertura(service: SetupService):
    da = service.dados_abertura()
    e = service.escoras()

    st.subheader("🧱 Abertura Teórica + Escoras")
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
    st.markdown("---")

# ============================================================
# UI - BLOCO: CONTEXTO RÁPIDO
# ============================================================

def render_bloco_contexto(service: SetupService, dados: Dict):
    """Contexto rápido com % para VIX, Petróleo e Minério."""
    resumo = service.resumo_macro
    metricas = dados.get("metricas", {})
    ativos_brutos = dados.get("ativos", {})

    st.subheader("🌐 Contexto Rápido")
    
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

    st.markdown("---")

# ============================================================
# UI - BLOCO: CONFLUÊNCIA
# ============================================================
###################
def render_bloco_confluencia(service: SetupService):
    """Bloco mostrando confluência com análise de tendência usando indicadores visuais (bolas coloridas)."""
    st.subheader("📈 Confluência com Análise de Tendência")
    
    arquivo_tendencias = ARQUIVOS["tendencias"]
    
    # Função auxiliar para converter padrão em bola colorida
    def padrao_para_bola(padrao: str) -> str:
        """
        Converte padrões como 'Alta_E_Alta', 'Baixa_E_Estavel' etc.
        em bolas coloridas (🟢, 🔴, 🟠) com texto amigável.
        """
        # Mapeia cada parte do padrão para símbolo e cor
        mapa = {
            "Alta": ("🟢", "verde"),
            "Baixa": ("🔴", "vermelho"),
            "Estavel": ("🟡", "amarelo"),
        }
        
        # Divide o padrão (ex: "Alta_E_Alta" -> ["Alta", "Alta"])
        partes = padrao.split("_E_")
        if len(partes) != 2:
            # Fallback para padrões inesperados
            return f"⚪ {padrao}"
        
        # Pega os símbolos de cada parte
        simbolo1, cor1 = mapa.get(partes[0], ("⚪", "desconhecido"))
        simbolo2, cor2 = mapa.get(partes[1], ("⚪", "desconhecido"))
        
        # Cria um texto curto com as duas bolas
        # Exemplo: "🟢 → 🟢" para Alta_E_Alta
        return f"{simbolo1} → {simbolo2}"
    
    # --- Início da função principal ---
    if os.path.exists(arquivo_tendencias):
        try:
            with open(arquivo_tendencias, "r", encoding="utf-8") as f:
                dados_tendencias = json.load(f)
            
            if dados_tendencias and len(dados_tendencias) > 0:
                tendencias = service.tendencias
                
                if tendencias:
                    st.markdown('<div class="confluencia-container">', unsafe_allow_html=True)
                    
                    cols = st.columns(min(4, len(tendencias)))
                    for i, (ativo, tend) in enumerate(tendencias.items()):
                        with cols[i % len(cols)]:
                            # Converte o padrão para bolas
                            bolas = padrao_para_bola(tend.padrao)
                            # Define a cor do delta (variação) com base no sinal
                            delta_color = "normal" if tend.ultima_variacao > 0 else "inverse" if tend.ultima_variacao < 0 else "off"
                            st.metric(
                                label=f"{ativo}",
                                value=bolas,
                                delta=f"{tend.ultima_variacao:+.2f}%",
                                delta_color=delta_color
                            )
                    
                    # Exibe a confluência (lógica original)
                    confluencia = service.confluencia_tendencia()
                    if confluencia["confluente"]:
                        st.success(f"✅ {confluencia['motivo']}")
                    else:
                        st.warning(f"⚠️ {confluencia['motivo']}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.warning("⚠️ Nenhuma tendência encontrada")
            else:
                st.warning("⚠️ Arquivo de tendências vazio.")
                
        except Exception as e:
            st.error(f"❌ Erro: {e}")
    else:
        st.info("📊 Analise_Tendencias.json não encontrado.")
        sucesso, mensagem = garantir_tendencias()
        if sucesso:
            st.success(f"✅ {mensagem}")
            st.rerun()
        else:
            st.warning(f"⚠️ {mensagem}")
#####
# ============================================================
# UI - BLOCO: CLASSIFICAÇÃO OPERACIONAL
# ============================================================
def render_bloco_classificacao(service: SetupService):
    """Mostra a classificação operacional + alerta de notícias 3★."""
    
    # ============================================================
    # 1. SEÇÃO DE NOTÍCIAS (ANTES DAS MÉTRICAS)
    # ============================================================
    if service.tem_3estrelas:
        st.markdown("### 📰 Alerta de Notícia 3★")
        st.warning("🚨 **Notícia ⭐⭐⭐ detectada!**")
        
        if service.alerta_texto:
            st.info(service.alerta_texto)
        
        if service.eventos_3e:
            for ev in service.eventos_3e:
                st.write(f"• **{ev.get('hora', '')}** | {ev.get('evento', '')} ({ev.get('pais', '')})")
        
        st.caption("⚠️ Notícias de alto impacto podem aumentar a volatilidade na abertura.")
        st.markdown("---")
    else:
        st.success("✅ **Nenhuma notícia ⭐⭐⭐** para hoje. Mercado com menor risco de surpresa.")
        st.markdown("---")
    
    # ============================================================
    # 2. EXPLICAÇÃO (EXPANDER)
    # ============================================================
    with st.expander("📖 O que é a Classificação Operacional?", expanded=False):
        st.markdown("""
        <div class="explicacao">
        <b>Classificação gerada pelo pipeline:</b><br>
        • <b>Mercado Externo:</b> -VIX + Petróleo + Minério<br>
        • <b>ADRs:</b> Soma das ADRs brasileiras<br><br>
        <b>Legenda das classificações:</b><br>
        • <b>MUITO_FORTE</b> → > 4.5%<br>
        • <b>FORTE</b> → 2.5% a 4.5%<br>
        • <b>MODERADA</b> → 1.5% a 2.5%<br>
        • <b>FRACA</b> → 0.8% a 1.5%<br>
        • <b>MUITO_FRACA</b> → 0.3% a 0.8%<br>
        • <b>LATERAL</b> → < 0.3%<br>
        • <b>Sinal:</b> COMPRA / VENDA / NEUTRO
        </div>
        """, unsafe_allow_html=True)
    
    # ============================================================
    # 3. MÉTRICAS DOS INDICADORES
    # ============================================================
    st.subheader("📊 Indicadores Compostos")
    
    # Busca os valores (já disponíveis no service)
    ind_mercado = service.ind_mercado_externo
    ind_adrs = service.ind_adrs
    
    # Fallback: tenta buscar do resultado operacional se estiver zerado
    if ind_mercado == 0.0 and ind_adrs == 0.0:
        resultado_op = service.dados.get("resultado_operacional", {})
        indicadores_op = resultado_op.get("indicadores_compostos", {})
        if indicadores_op:
            mercado = indicadores_op.get("mercado_externo", {})
            ind_mercado = mercado.get("valor_pct", 0.0)
            adrs = indicadores_op.get("adrs_brasileiras", {})
            ind_adrs = adrs.get("valor_pct", 0.0)
    
    def classificar_valor(valor):
        abs_valor = abs(valor)
        if abs_valor < 0.3:
            intensidade = "LATERAL"
        elif abs_valor < 0.8:
            intensidade = "MUITO_FRACA"
        elif abs_valor < 1.5:
            intensidade = "FRACA"
        elif abs_valor < 2.5:
            intensidade = "MODERADA"
        elif abs_valor < 4.5:
            intensidade = "FORTE"
        else:
            intensidade = "MUITO_FORTE"
        
        if valor > 0.05:
            sinal = "COMPRA"
        elif valor < -0.05:
            sinal = "VENDA"
        else:
            sinal = "NEUTRO"
        
        return {
            "valor_pct": round(valor, 4),
            "rotulo_completo": f"{intensidade}_{sinal}"
        }
    
    mercado_class = classificar_valor(ind_mercado)
    adrs_class = classificar_valor(ind_adrs)
    
    col1, col2 = st.columns(2)
    
    with col1:
        rotulo = mercado_class.get("rotulo_completo", "N/A")
        if "COMPRA" in rotulo:
            delta_color = "normal"
        elif "VENDA" in rotulo:
            delta_color = "inverse"
        else:
            delta_color = "off"
        
        st.metric(
            "🌍 Mercado Externo",
            f"{ind_mercado:+.2f}%",
            rotulo,
            delta_color=delta_color
        )
    
    with col2:
        rotulo = adrs_class.get("rotulo_completo", "N/A")
        if "COMPRA" in rotulo:
            delta_color = "normal"
        elif "VENDA" in rotulo:
            delta_color = "inverse"
        else:
            delta_color = "off"
        
        st.metric(
            "🇧🇷 ADRs Brasileiras",
            f"{ind_adrs:+.2f}%",
            rotulo,
            delta_color=delta_color
        )
    
    # ============================================================
    # 4. INTERPRETAÇÃO
    # ============================================================
    st.markdown("**Interpretação:**")
    
    def extrair_direcao(rotulo):
        if "COMPRA" in rotulo:
            return "COMPRA"
        elif "VENDA" in rotulo:
            return "VENDA"
        return "NEUTRO"
    
    dir_mercado = extrair_direcao(mercado_class.get("rotulo_completo", ""))
    dir_adrs = extrair_direcao(adrs_class.get("rotulo_completo", ""))
    
    # Adiciona o filtro de notícias na interpretação
    if service.tem_3estrelas:
        st.warning("⚠️ **Filtro ativado:** Notícia 3★ → Prioridade dada às ADRs.")
    
    if dir_mercado == "COMPRA" and dir_adrs == "COMPRA":
        st.success("✅ Ambos COMPRA - Confluência positiva!")
    elif dir_mercado == "VENDA" and dir_adrs == "VENDA":
        st.error("🔴 Ambos VENDA - Confluência negativa!")
    elif dir_mercado == "NEUTRO" and dir_adrs == "NEUTRO":
        st.warning("🟡 Ambos neutros - Aguardar definição!")
    elif dir_mercado != dir_adrs:
        st.warning(f"⚠️ Divergência: Mercado Externo ({dir_mercado}) vs ADRs ({dir_adrs})")
    else:
        st.info(f"ℹ️ Mercado: {dir_mercado} | ADRs: {dir_adrs}")
    
    # ============================================================
    # 5. RESUMO DO FILTRO (exibição extra para clareza)
    # ============================================================
    st.caption(f"📌 Filtro aplicado: {'Notícia 3★ → ADRs' if service.tem_3estrelas else 'Sem notícia 3★ → Mercado Externo'}")


# ============================================================
# UI - BLOCO: ANÁLISE IA - PRÉ-ABERTURA (SOMENTE TEXTO)
# ============================================================

def render_bloco_ia_pre_abertura(service: SetupService):
    """Bloco de análise IA - PRÉ-ABERTURA (somente texto, mais leve)."""
    st.subheader("📊 Análise IA - Pré-Abertura (Somente Texto)")
    st.caption("Previsão de direção, GAP e cenário para os primeiros minutos do pregão")
    
    # Configuração da IA
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        try:
            from dotenv import load_dotenv
            load_dotenv(BASE_DIR / ".env")
            groq_key = os.getenv("GROQ_API_KEY", "")
        except Exception:
            pass
    
    with st.expander("⚙️ Configurações Pré-Abertura", expanded=not bool(groq_key)):
        groq_key_input = st.text_input(
            "Groq API Key",
            type="password",
            value=groq_key,
            help="Obtenha em https://console.groq.com",
            key="groq_key_pre_abertura"
        )
        modelo_texto = st.selectbox(
            "Modelo (texto)",
            [
                "llama-3.3-70b-versatile",
                "llama-3.1-70b-versatile",
                "llama-3.1-8b-instant",
            ],
            index=0,
            help="Modelos de texto são mais rápidos e baratos",
            key="modelo_pre_abertura"
        )
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
                
                # USA A FUNÇÃO COM ROTAÇÃO DE CHAVES
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

# ============================================================
# UI - CHECKLIST
# ============================================================

def render_checklist():
    st.markdown("---")
    st.subheader("✅ Checklist Operacional")

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
# MAIN
# ============================================================

def main():
    st.set_page_config(
        page_title="Setup Abertura 09:00",
        page_icon="🎯",
        layout="wide",
    )
    st.markdown(CSS_CUSTOM, unsafe_allow_html=True)

    render_sidebar()

    st.title("🎯 Setup Abertura 09:00 – 09:15")
    st.caption("Análise SMC/ICT com IA + Visão de Gráficos + Pré-Abertura")

    dados = carregar_todos_dados()
    service = SetupService(dados)

    if not service.dados_minimos_ok():
        st.error("⚠️ Dados não encontrados.\n\nExecute: `rodar_pipeline_3x.bat`")
        st.stop()

    if service.janela_ok():
        st.success("🟢 DENTRO DA JANELA (09:00 – 09:15)")
    else:
        st.warning(f"⏰ Fora da janela • {datetime.now().strftime('%H:%M:%S')}")
    st.markdown("---")

    
    render_bloco_classificacao(service)
    render_bloco_sinal(service)
    render_bloco_abertura(service)
    render_bloco_contexto(service, dados)
    render_bloco_confluencia(service)
    
    render_bloco_ia_pre_abertura(service)
    render_checklist()

    st.markdown("---")
    st.caption("Setup Abertura 09:00 • v5.3 • Sem IA visual • Com rotação de chaves API")

if __name__ == "__main__":
    main()