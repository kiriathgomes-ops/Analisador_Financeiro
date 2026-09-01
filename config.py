# ============================================================
# config.py — Configuração central do Analisador Financeiro
# Roadmap A2 | Fase 1 da migração V1 → V2
# Data: 27/08/2026 | Atualizado 01/09/2026 — FILE_LAST_TICK_CONGELADO (Fase 0)
#
# Única fonte de:
#   - Caminhos (BASE_DIR, Coletas, nomes de JSON)
#   - Listas de tickers (TradingView, Finnhub, MT5 B3)
#   - Mapeamento de tickers → IDs internos
#   - Pesos da estimativa de abertura e do NOVO_MOTOR
#   - Janelas temporais, timeouts, flags de migração
#
# Uso:
#   from config import COLETAS_DIR, FILE_UNIFICADO, TICKERS_TRADINGVIEW, ...
# ============================================================

from __future__ import annotations

import os
import sys
from datetime import time
from pathlib import Path
from typing import Any, Dict, List

# ------------------------------------------------------------
# 1. RAIZ DO PROJETO E PATH
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Carrega .env o mais cedo possível (chaves de API)
try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=BASE_DIR / ".env")
except ImportError:
    pass

# KeyManager (opcional — só falha se utils não existir ainda)
try:
    from utils.KeyManager import get_groq_client, key_manager  # noqa: F401
except ImportError:
    get_groq_client = None  # type: ignore
    key_manager = None  # type: ignore

# ------------------------------------------------------------
# 2. DIRETÓRIOS
# ------------------------------------------------------------
COLETAS_DIR = BASE_DIR / "Coletas"
LOGS_DIR = BASE_DIR / "logs"
IMAGENS_DIR = BASE_DIR / "Imagens"
PROMPT_IA_DIR = BASE_DIR / "PromptIA"
HISTORICO_ABERTURAS_DIR = COLETAS_DIR / "Historico_Aberturas"
HISTORICO_DECISOES_V2_DIR = COLETAS_DIR / "Historico_Decisoes_V2"
HISTORICO_MT5_DIR = COLETAS_DIR / "Historico_MT5"

# Garante pastas essenciais
for _d in (COLETAS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# 3. NOMES DE ARQUIVOS JSON (entrada / saída do pipeline)
# ------------------------------------------------------------
# Coleta / unificado
FILE_RAM = COLETAS_DIR / "Coleta_ram.json"
FILE_UNIFICADO = COLETAS_DIR / "DadosAtivosUnificados.json"
FILE_MT5 = COLETAS_DIR / "Dados_MT5.json"
FILE_MT5_V2 = COLETAS_DIR / "Dados_MT5_v2_2.json"
FILE_VALIDADOS = COLETAS_DIR / "Dados_Validados.json"

# Rotação temporal (12 slots = 60 min, a cada 5 min)
ROM_INTERVALOS_MIN = list(range(0, 60, 5))  # 0, 5, ..., 55
ARQUIVOS_ROM: List[Path] = [
    COLETAS_DIR / f"Coleta_rom-{i}.json" for i in ROM_INTERVALOS_MIN
]
FILE_ROM0 = ARQUIVOS_ROM[0]

# Notícias
FILE_NOTICIAS_CALENDARIO = COLETAS_DIR / "Noticias_Calendario.json"
FILE_NOTICIAS_CALENDARIO_0900 = COLETAS_DIR / "Noticias_Calendario_0900.json"
FILE_NOTICIAS_IMPACTO = COLETAS_DIR / "Noticias_Impacto_Dia.json"

# Métricas e estimativas
FILE_METRICAS = COLETAS_DIR / "Metricas_Calculadas.json"
FILE_ESTIMATIVA_ABERTURA = COLETAS_DIR / "EstimativaAbertura.json"
FILE_TENDENCIAS = COLETAS_DIR / "Analise_Tendencias.json"
FILE_RESULTADO_OPERACIONAL = COLETAS_DIR / "Resultado_Calculadora_Operacional_Abertura.json"

# Decisões
FILE_DECISAO_CORE = COLETAS_DIR / "Decisao_Core.json"  # legado V1
FILE_DECISAO_V2 = COLETAS_DIR / "Decisao_V2.json"  # oficial V2

# Pipeline / logs
FILE_PIPELINE_LOG = COLETAS_DIR / "Pipeline_Log.json"
FILE_TOKEN_USAGE = COLETAS_DIR / "token_usage.log"

# SMC / visão
FILE_SMC_REGRAS = COLETAS_DIR / "AnaliseGraficaSMC_Regras.json"
FILE_WIN_1MIN = COLETAS_DIR / "WIN_1min.png"
FILE_WIN_5MIN = COLETAS_DIR / "WIN_5min.png"

# LAST_TICK congelado (fora da rotação ROM) — Fase 0
# Grava fora do pregão; lido no pregão para manter chave estável
FILE_LAST_TICK_CONGELADO = COLETAS_DIR / "LastTick_Congelado.json"

# ------------------------------------------------------------
# 4. CHAVES DE API (via ambiente)
# ------------------------------------------------------------
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
# Demais chaves ficam no KeyManager / .env (GROQ, etc.)

# ------------------------------------------------------------
# 5. JANELAS TEMPORAIS E TIMEOUTS
# ------------------------------------------------------------
# Janela de ajuste oficial B3 / overnight (ajuste TV vivo)
JANELA_AJUSTE_INICIO = time(19, 0, 0)  # 19:00
JANELA_AJUSTE_FIM = time(8, 50, 0)  # 08:50

# Horário cheio do pregão WIN (B3)
# WIN_FUT (contrato MT5) → sempre
# WIN_LAST_TICK → somente FORA deste intervalo
HORA_PREGAO_INICIO = time(9, 0, 0)   # 09:00
HORA_PREGAO_FIM = time(18, 25, 0)    # 18:25

# Timeouts de HTTP (segundos)
TIMEOUT_TRADINGVIEW = 10
TIMEOUT_FINNHUB = 5
TIMEOUT_BACEN = 10
TIMEOUT_TRADINGVIEW_CALENDARIO = 15

MAX_TENTATIVAS_MT5 = 3
TICK_STALE_SEG = 120


# ------------------------------------------------------------
# 6. TICKERS — TRADINGVIEW SCANNER
# ------------------------------------------------------------
def _ticker_fef2() -> str:
    """Minério de ferro 2º mês (SGX) — ano corrente."""
    return f"SGX:FEFU{__import__('datetime').datetime.now().year}"


TICKER_FEF2 = _ticker_fef2()

TICKERS_TRADINGVIEW: List[str] = [
    # WIN/WDO NÃO vêm mais do TV — OHLC/last via MT5 (WIN_FUT / WDO_FUT)
    # Ajuste oficial continua em coletar_ajuste_oficial (B3_AJUSTE_*)
    "BMFBOVESPA:DI1F2027",
    "BMFBOVESPA:DI1F2029",
    "TVC:VIX",
    "SGX:FEF1!",
    TICKER_FEF2,
    "NYMEX:CL1!",
    "CME_MINI:ES1!",  # S&P 500 E-mini (preço real do futuro)
    "CME_MINI:NQ1!",  # Nasdaq 100 E-mini
    "TVC:DXY",
    "FX_IDC:USDMXN",
    "TVC:GOLD",
    "FX_IDC:USDBRL",
]

# Referências explícitas (ajuste dedicado / mapeamento)
TICKER_WIN_TV = "BMFBOVESPA:WIN1!"
TICKER_WDO_TV = "BMFBOVESPA:WDO1!"

# ------------------------------------------------------------
# 7. TICKERS — FINNHUB (ADRs + EWZ)  [Opção A]
# ------------------------------------------------------------
ATIVOS_FINNHUB: List[Dict[str, str]] = [
    {
        "ativo": "AMEX:EWZ",
        "ticker_coleta": "EWZ",
        "id_interno": "EWZ",
        "categoria": "Índices Globais",
    },
    {
        "ativo": "NYSE:VALE",
        "ticker_coleta": "VALE",
        "id_interno": "VALE_ADR",
        "categoria": "ADRs B3",
    },
    {
        "ativo": "NYSE:PBR",
        "ticker_coleta": "PBR",
        "id_interno": "PETR_ADR",
        "categoria": "ADRs B3",
    },
    {
        "ativo": "NYSE:ITUB",
        "ticker_coleta": "ITUB",
        "id_interno": "ITUB_ADR",
        "categoria": "ADRs B3",
    },
    {
        "ativo": "OTC:BDORY",
        "ticker_coleta": "BDORY",
        "id_interno": "BBAS_ADR",
        "categoria": "ADRs B3",
    },
    {
        "ativo": "NYSE:BBD",
        "ticker_coleta": "BBD",
        "id_interno": "BBD_ADR",
        "categoria": "ADRs B3",
    },
    {
        "ativo": "OTC:BOLSY",
        "ticker_coleta": "BOLSY",
        "id_interno": "B3_ADR",
        "categoria": "ADRs B3",
    },
]

# Mapeamento B3 → ADR (arbitragem pré-market / leilão)
MAPEAMENTO_ADR_B3: Dict[str, str] = {
    "VALE3": "VALE",
    "PETR4": "PBR-A",
    "PETR3": "PBR",
    "ITUB4": "ITUB",
    "BBDC4": "BBD",
}

# ------------------------------------------------------------
# 8. TICKERS — MT5 AÇÕES B3
# ------------------------------------------------------------
ATIVOS_MT5_B3: List[Dict[str, str]] = [
    {"ativo": "VALE3", "ticker_coleta": "VALE3", "id_interno": "VALE3", "categoria": "Ações B3"},
    {"ativo": "PETR4", "ticker_coleta": "PETR4", "id_interno": "PETR4", "categoria": "Ações B3"},
    {"ativo": "ITUB4", "ticker_coleta": "ITUB4", "id_interno": "ITUB4", "categoria": "Ações B3"},
    {"ativo": "BBAS3", "ticker_coleta": "BBAS3", "id_interno": "BBAS3", "categoria": "Ações B3"},
    {"ativo": "BBDC4", "ticker_coleta": "BBDC4", "id_interno": "BBDC4", "categoria": "Ações B3"},
    {"ativo": "B3SA3", "ticker_coleta": "B3SA3", "id_interno": "B3SA3", "categoria": "Ações B3"},
]

# ------------------------------------------------------------
# 9. MAPEAMENTO TICKER BRUTO → ID INTERNO
# ------------------------------------------------------------
MAPEAMENTO_TICKERS: Dict[str, str] = {
    "USD_PTAX": "USD_PTAX",
    "B3_AJUSTE_WIN": "WIN_AJUSTE",
    "B3_AJUSTE_WDO": "WDO_AJUSTE",
    "BMFBOVESPA:WIN1!": "WIN_FUT",
    "BMFBOVESPA:WDO1!": "WDO_FUT",
    "WIN_PREV_CLOSE": "WIN_PREV_CLOSE",
    "BMFBOVESPA:DI1F2027": "DI1_2027",
    "BMFBOVESPA:DI1F2029": "DI1_2029",
    "DI1_FUT": "DI1_FUT",
    "TVC:VIX": "VIX",
    "SGX:FEF1!": "IRON_ORE",
    "SGX:FEF2!": "IRON_ORE_2M",
    "NYMEX:CL1!": "CRUDE_OIL",
    "NYSE:VALE": "VALE_ADR",
    "NYSE:PBR": "PETR_ADR",
    "NYSE:ITUB": "ITUB_ADR",
    "OTC:BDORY": "BBAS_ADR",
    "NYSE:BBD": "BBD_ADR",
    "OTC:BOLSY": "B3_ADR",
    "AMEX:EWZ": "EWZ",
    "CME_MINI:ES1!": "SP500_FUT",
    "CME_MINI:NQ1!": "NASDAQ_FUT",
    "TVC:DXY": "DXY",
    "FX_IDC:USDMXN": "USD_MXN",
    "TVC:GOLD": "GOLD",
    "FX_IDC:USDBRL": "USD_BRL",
    "WIN_LAST_TICK": "WIN_LAST_TICK",
    "WDO_LAST_TICK": "WDO_LAST_TICK",
    "VALE3": "VALE3",
    "PETR4": "PETR4",
    "ITUB4": "ITUB4",
    "BBAS3": "BBAS3",
    "BBDC4": "BBDC4",
    "B3SA3": "B3SA3",
}

# ------------------------------------------------------------
# 10. PESOS — ESTIMATIVA DE ABERTURA WIN
#     (CalculadoraEstimativaAbertura / alinhado ao uso atual)
# ------------------------------------------------------------
PESOS_ESTIMATIVA_ABERTURA: Dict[str, Any] = {
    # Blocos principais (somam 1.0)
    "ewz": 0.30,
    "cesta_adrs": 0.35,
    "sp500_fut": 0.20,
    "cesta_commodities": 0.15,
    # Dentro da cesta de ADRs (somam 1.0)
    "adr_vale": 0.30,
    "adr_petr": 0.25,
    "adr_itub": 0.25,
    "adr_bbd": 0.20,
    # Dentro da cesta de commodities (somam 1.0)
    "iron_ore": 0.50,
    "crude_oil": 0.50,
}

# ------------------------------------------------------------
# 11. PESOS / LIMIARES — NOVO_MOTOR (score de previsão)
# ------------------------------------------------------------
PESOS_NOVO_MOTOR: Dict[str, float] = {
    "mercado_externo": 0.35,
    "adrs_brasileiras": 0.25,
    "vix": 0.10,
    "tendencia": 0.15,
    "gap_intensidade": 0.10,
    "noticias_impacto": 0.05,
}

SCORE_LIMIARES: Dict[str, int] = {
    "muito_forte": 80,
    "forte": 60,
    "moderado": 40,
    "fraco": 0,
}

GAP_LIMIARES_PTS: Dict[str, int] = {
    "micro": 20,
    "pequeno": 50,
    "moderado": 100,
    "forte": 200,
    "extremo": 999_999,
}

# Notícias — peso por estrela (Analise_Noticias)
PESO_ESTRELAS: Dict[int, int] = {1: 1, 2: 3, 3: 6}

# ------------------------------------------------------------
# 12. FLAGS DE MIGRAÇÃO V1 → V2
# ------------------------------------------------------------
USAR_DECISAO_V2 = True  # Páginas e orquestrador preferem Decisao_V2.json
ENGINE_VIES_COMO_FALLBACK = False  # PredictionService ainda pode usar Engine_Vies
# Quando False: PredictionService não chama mais Engine_Vies (Fase 2)

# Fonte oficial de previsão (documentação / logs)
FONTE_OFICIAL_PREVISAO = "NOVO_MOTOR+OpeningScenario"  # ou "Engine_Vies" durante transição

# ------------------------------------------------------------
# 13. HELPERS
# ------------------------------------------------------------
def esta_na_janela_ajuste() -> bool:
    """
    True entre 19:00 e 08:50 (overnight / pós-ajuste / pré-abertura).
    Controla coleta ao vivo do AJUSTE oficial (TV).
    """
    from datetime import datetime

    agora = datetime.now().time()
    return agora >= JANELA_AJUSTE_INICIO or agora <= JANELA_AJUSTE_FIM


def esta_no_pregao() -> bool:
    """True no horário cheio do WIN (09:00–18:25)."""
    from datetime import datetime

    agora = datetime.now().time()
    return HORA_PREGAO_INICIO <= agora <= HORA_PREGAO_FIM


def esta_fora_do_pregao() -> bool:
    """True fora do pregão — janela em que WIN_LAST_TICK deve ser coletado."""
    return not esta_no_pregao()


def caminho_json(nome: str) -> Path:
    """Atalho: retorna COLETAS_DIR / nome."""
    return COLETAS_DIR / nome


def id_interno(ticker_bruto: str) -> str:
    """Converte ticker de API para ID interno estável."""
    return MAPEAMENTO_TICKERS.get(ticker_bruto, ticker_bruto)


# Compatibilidade com código antigo que usa str
def _as_str(p: Path) -> str:
    return str(p)


# Aliases string (módulos legados que ainda usam os.path)
BASE_DIR_STR = str(BASE_DIR)
COLETAS_DIR_STR = str(COLETAS_DIR)
FILE_UNIFICADO_STR = str(FILE_UNIFICADO)
FILE_RAM_STR = str(FILE_RAM)
FILE_ROM0_STR = str(FILE_ROM0)
FILE_MT5_V2_STR = str(FILE_MT5_V2)
FILE_DECISAO_V2_STR = str(FILE_DECISAO_V2)
FILE_DECISAO_CORE_STR = str(FILE_DECISAO_CORE)
