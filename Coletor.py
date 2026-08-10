# ============================================================
# ARQUIVO: Coletor.py
# DATA: 30/07/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Ingestão de Dados (BACEN SGS 10813 + TV + B3 WIN/WDO Separados)
#         Engine de Rotação Temporal de Memória e
#         Geração do Arquivo Unificado dos 24 Ativos Mapeados.
# ============================================================

import json
import os
import shutil
import ssl
import sys
import urllib.request
from datetime import datetime, time

# ------------------------------------------------------------
# CONFIGURAÇÃO DE DIRETÓRIOS E ARQUIVOS
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")

# Garante que a pasta 'Coletas' existe
os.makedirs(COLETAS_DIR, exist_ok=True)

# Definição dos caminhos para Rotação Temporal (Janela Móvel)
FILE_ROM0 = os.path.join(COLETAS_DIR, "Coleta_rom-0.json")
FILE_ROM5 = os.path.join(COLETAS_DIR, "Coleta_rom-5.json")
FILE_ROM10 = os.path.join(COLETAS_DIR, "Coleta_rom-10.json")
FILE_RAM = os.path.join(COLETAS_DIR, "Coleta_ram.json")
FILE_UNIFICADO = os.path.join(COLETAS_DIR, "DadosAtivosUnificados.json")

# Dynamic Ticker Generation para Minério de Ferro (FEF2 - 2º Mês)
ANO_ATUAL = datetime.now().year
TICKER_FEF2 = f"SGX:FEFU{ANO_ATUAL}"

# Lista oficial dos 21 ativos coletados via TradingView Scanner API
TICKERS_TRADINGVIEW = [
    "BMFBOVESPA:WIN1!",
    "BMFBOVESPA:WDO1!",
    "BMFBOVESPA:DI1F2027",
    "BMFBOVESPA:DI1F2029",
    "TVC:VIX",
    "SGX:FEF1!",
    TICKER_FEF2,
    "NYMEX:CL1!",
    "NYSE:VALE",
    "NYSE:PBR",
    "NYSE:ITUB",
    "OTC:BDORY",
    "NYSE:BBD",
    "OTC:BOLSY",
    "AMEX:EWZ",
    "CME_MINI:ES1!",
    "CME_MINI:NQ1!",
    "TVC:DXY",
    "FX_IDC:USDMXN",
    "TVC:GOLD",
    "FX_IDC:USDBRL",
]

# Mapeamento Oficial dos Tickers Internos / Amigáveis
MAPEAMENTO_TICKERS = {
    "USD_PTAX": "USD_PTAX",
    "B3_AJUSTE_WIN": "WIN_AJUSTE",
    "B3_AJUSTE_WDO": "WDO_AJUSTE",
    "BMFBOVESPA:WIN1!": "WIN_FUT",
    "BMFBOVESPA:WDO1!": "WDO_FUT",
    "BMFBOVESPA:DI1F2027": "DI1_2027",
    "BMFBOVESPA:DI1F2029": "DI1_2029",
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
}


# ------------------------------------------------------------
# FUNÇÕES DE COLETA DE DADOS (FASE 1)
# ------------------------------------------------------------


def coletar_bacen_ptax():
    """Coleta a PTAX oficial no Bacen via API SGS (Série 10813) com fallback via TradingView."""
    timestamp = datetime.now().isoformat()

    url_sgs = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.10813/dados/ultimos/5?formato=json"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req_sgs = urllib.request.Request(
        url_sgs,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )

    try:
        with urllib.request.urlopen(
            req_sgs, context=ctx, timeout=10
        ) as response:
            if response.getcode() == 200:
                res = json.loads(response.read().decode("utf-8"))
                if res:
                    ultimo_valor = float(res[-1]["valor"].replace(",", "."))
                    return {
                        "ativo": "USD_PTAX",
                        "fonte": "BACEN_SGS_10813",
                        "timestamp": timestamp,
                        "status": "OK",
                        "dados_reais": {
                            "close": ultimo_valor,
                            "open": None,
                            "high": None,
                            "low": None,
                            "change_percent": None,
                            "volume": None,
                        },
                    }
    except Exception as e:
        print(f"[AVISO] Falha na API SGS Bacen: {e}. Executando fallback...")

    # Fallback TradingView
    try:
        url_tv = "https://scanner.tradingview.com/global/scan"
        payload = {
            "symbols": {"tickers": ["FX_IDC:USDBRL"]},
            "columns": ["close"],
        }
        req_tv = urllib.request.Request(
            url_tv,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
        )
        with urllib.request.urlopen(req_tv, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            vals = res.get("data", [])[0].get("d", [])
            if vals and vals[0] is not None:
                return {
                    "ativo": "USD_PTAX",
                    "fonte": "TRADINGVIEW_FALLBACK",
                    "timestamp": timestamp,
                    "status": "OK",
                    "dados_reais": {
                        "close": float(vals[0]),
                        "open": None,
                        "high": None,
                        "low": None,
                        "change_percent": None,
                        "volume": None,
                    },
                }
    except Exception:
        pass

    return {
        "ativo": "USD_PTAX",
        "fonte": "BACEN_API",
        "timestamp": timestamp,
        "status": "SEM_DADOS",
        "dados_reais": None,
    }

######
def coletar_ajuste_oficial():
    """
    Coleta os valores de Ajuste Oficial APENAS entre 19:00 e 08:50.
    Fora desse horário, busca o último valor salvo no cache (RAM/ROM) para não quebrar o sistema.
    """
    timestamp = datetime.now().isoformat()
    hora_atual = datetime.now().time()

    # Define os limites de horário (Brasília)
    hora_inicio = time(19, 0, 0)  # 19:00
    hora_fim = time(8, 50, 0)     # 08:50

    # --- LÓGICA DE HORÁRIO ---
    # Se estiver entre 08:50 e 19:00, NÃO faz a coleta ao vivo
    if hora_fim < hora_atual < hora_inicio:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Fora da janela de ajuste (19:00 - 08:50). Buscando último cache...")
        
        # Tenta carregar o último ajuste salvo no arquivo de RAM (ou ROM0)
        cache_encontrado = []
        for arquivo_cache in [FILE_RAM, FILE_ROM0]:
            if os.path.exists(arquivo_cache):
                try:
                    with open(arquivo_cache, 'r', encoding='utf-8') as f:
                        dados_cache = json.load(f)
                        itens = dados_cache.get("coletas", [])
                        # Filtra os ajustes
                        for item in itens:
                            if item.get("ativo") in ["B3_AJUSTE_WIN", "B3_AJUSTE_WDO"]:
                                cache_encontrado.append(item)
                    if cache_encontrado:
                        break
                except:
                    continue
        
        if cache_encontrado:
            # Retorna os dados do cache, mas marca a fonte como "CACHE"
            for item in cache_encontrado:
                item["fonte"] = "CACHE_DISCO (Fora da janela)"
                # Garante que o timestamp seja atualizado
                item["timestamp"] = timestamp
            return cache_encontrado
        else:
            # Se não encontrar cache, retorna erro para não corromper o JSON com zeros
            print("   ⚠️ Nenhum cache de ajuste encontrado. Retornando dados vazios.")
            return [
                {
                    "ativo": "B3_AJUSTE_WIN",
                    "fonte": "NENHUM_DADO",
                    "timestamp": timestamp,
                    "status": "FORA_JANELA_SEM_CACHE",
                    "dados_reais": None
                },
                {
                    "ativo": "B3_AJUSTE_WDO",
                    "fonte": "NENHUM_DADO",
                    "timestamp": timestamp,
                    "status": "FORA_JANELA_SEM_CACHE",
                    "dados_reais": None
                }
            ]

    # --- SE ESTIVER DENTRO DA JANELA (19:00 até 08:50) ---
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Dentro da janela de ajuste. Coletando da API...")
    headers = {"User-Agent": "Mozilla/5.0"}

    simbolos = [
        {"ativo": "B3_AJUSTE_WIN", "ticker": "BMFBOVESPA:WIN1!"},
        {"ativo": "B3_AJUSTE_WDO", "ticker": "BMFBOVESPA:WDO1!"},
    ]

    resultados = []
    for item in simbolos:
        url = f"https://scanner.tradingview.com/symbol?symbol={item['ticker']}&fields=close,change"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                res = json.loads(response.read().decode("utf-8"))
                close_val = res.get("close")
                change_val = res.get("change", 0.0)

                resultados.append({
                    "ativo": item["ativo"],
                    "fonte": "TRADINGVIEW_DIRECT_SYMBOL",
                    "timestamp": timestamp,
                    "status": "OK" if close_val is not None else "ERRO",
                    "dados_reais": {
                        "close": float(close_val) if close_val is not None else None,
                        "open": None,
                        "high": None,
                        "low": None,
                        "change_percent": float(change_val) if change_val is not None else 0.0,
                        "volume": None,
                    },
                })
        except Exception as e:
            print(f"   ❌ Erro ao coletar {item['ativo']}: {e}")
            resultados.append({
                "ativo": item["ativo"],
                "fonte": "TRADINGVIEW_DIRECT_SYMBOL",
                "timestamp": timestamp,
                "status": "ERRO",
                "dados_reais": None,
            })
    
    return resultados


def coletar_tradingview():
    """Coleta os ativos mapeados via Scanner API Oculta do TradingView."""
    url = "https://scanner.tradingview.com/global/scan"
    timestamp = datetime.now().isoformat()

    payload = {
        "symbols": {"tickers": TICKERS_TRADINGVIEW},
        "columns": ["close", "open", "high", "low", "change", "volume"],
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)

        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            resultados = []

            for item in res.get("data", []):
                ticker = item.get("s")
                vals = item.get("d", [])

                ticker_chave = "SGX:FEF2!" if ticker == TICKER_FEF2 else ticker

                if len(vals) >= 5 and vals[0] is not None:
                    close = float(vals[0])
                    change_pct = (
                        float(vals[4]) if vals[4] is not None else 0.0
                    )

                    resultados.append(
                        {
                            "ativo": ticker_chave,
                            "fonte": "TRADINGVIEW_SCANNER",
                            "timestamp": timestamp,
                            "status": "OK",
                            "dados_reais": {
                                "close": close,
                                "open": (
                                    float(vals[1])
                                    if vals[1] is not None
                                    else None
                                ),
                                "high": (
                                    float(vals[2])
                                    if vals[2] is not None
                                    else None
                                ),
                                "low": (
                                    float(vals[3])
                                    if vals[3] is not None
                                    else None
                                ),
                                "change_percent": change_pct,
                                "volume": (
                                    float(vals[5])
                                    if len(vals) > 5 and vals[5] is not None
                                    else None
                                ),
                            },
                        }
                    )
                else:
                    resultados.append(
                        {
                            "ativo": ticker_chave,
                            "fonte": "TRADINGVIEW_SCANNER",
                            "timestamp": timestamp,
                            "status": "DADOS_INCOMPLETOS",
                            "dados_reais": None,
                        }
                    )
            return resultados
    except Exception as e:
        print(f"[ERRO] Falha na coleta TradingView: {e}")
        return []


# ------------------------------------------------------------
# ENGINE DE ROTAÇÃO E FORMATADOR UNIFICADO
# ------------------------------------------------------------


def executar_rotacao_memoria(is_ram_mode=False):
    """Executa a rotação temporal (rom-0 -> rom-5 -> rom-10) ou grava em RAM."""
    if is_ram_mode:
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] Modo RAM ativado. Ignorando rotação temporal."
        )
        return FILE_RAM

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Executando rotação de memória física (Janela Móvel)..."
    )

    if os.path.exists(FILE_ROM5):
        shutil.copy(FILE_ROM5, FILE_ROM10)
        print("  └─ Rotação: Coleta_rom-5.json ──> Coleta_rom-10.json")

    if os.path.exists(FILE_ROM0):
        shutil.copy(FILE_ROM0, FILE_ROM5)
        print("  └─ Rotação: Coleta_rom-0.json ──> Coleta_rom-5.json")

    return FILE_ROM0


def gerar_arquivo_unificado(coletas):
    """Gera o arquivo DadosAtivosUnificados.json com as chaves tratadas dos 24 ativos."""
    ativos_map = {}

    for item in coletas:
        ativo_raw = item.get("ativo")
        dados_reais = item.get("dados_reais") or {}

        # Mapeia para o nome limpo do ativo
        nome_limpo = MAPEAMENTO_TICKERS.get(ativo_raw, ativo_raw)

        preco = dados_reais.get("close", 0.0) or 0.0
        var = dados_reais.get("change_percent", 0.0) or 0.0

        ativos_map[nome_limpo] = {
            "preco": float(preco),
            "variacao_pct": float(var),
            "ticker_original": ativo_raw,
            "status": item.get("status", "OK"),
        }

    estrutura_unificada = {
        "metadata": {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_ativos": len(ativos_map),
        },
        "ativos": ativos_map,
    }

    with open(FILE_UNIFICADO, "w", encoding="utf-8") as f:
        json.dump(estrutura_unificada, f, indent=4, ensure_ascii=False)

    print(f"✅ Arquivo unificado dos 24 ativos salvo em: {FILE_UNIFICADO}")


# ------------------------------------------------------------
# EXECUÇÃO PRINCIPAL
# ------------------------------------------------------------


def executar_pipeline_coleta():
    is_ram = "--ram" in sys.argv
    arquivo_destino = executar_rotacao_memoria(is_ram)

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando extração de dados brutos..."
    )

    coletas = []

    # 1. Extração BACEN PTAX
    ptax = coletar_bacen_ptax()
    coletas.append(ptax)

    # 2. Extração Ajustes
    ajustes = coletar_ajuste_oficial()
    coletas.extend(ajustes)

    # 3. Extração TradingView Scanner
    tv_dados = coletar_tradingview()
    coletas.extend(tv_dados)

    # Monta estrutura da coleta bruta
    conteudo_saida = {
        "metadata_coleta": {
            "timestamp_coleta": datetime.now().isoformat(),
            "modo_execucao": "RAM" if is_ram else "PADRAO_ROTATIVO",
            "total_ativos_solicitados": len(coletas),
            "arquivo_gerado": os.path.basename(arquivo_destino),
        },
        "coletas": coletas,
    }

    # Grava Coleta de Rotação (ex: Coleta_rom-0.json)
    with open(arquivo_destino, "w", encoding="utf-8") as f:
        json.dump(conteudo_saida, f, indent=2, ensure_ascii=False)

    # Grava TAMBÉM a saída em Coleta_ram.json (fora do rotacionamento)
    if not is_ram:
        with open(FILE_RAM, "w", encoding="utf-8") as f:
            json.dump(conteudo_saida, f, indent=2, ensure_ascii=False)
        print(f"✅ Cópia independente gerada em: {FILE_RAM}")

    # Gera o arquivo DadosAtivosUnificados.json com dados reais
    gerar_arquivo_unificado(coletas)

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Coleta e Unificação concluídas com sucesso!"
    )
    print(
        f"Total de itens processados: {len(coletas)} | Arquivo: {os.path.basename(arquivo_destino)}\n"
    )


if __name__ == "__main__":
    print("============================================================")
    print(" FASE 1 & 2: MOTOR DE INGESTÃO E ROTAÇÃO DE DADOS (24 ATIVOS)")
    print("============================================================")
    executar_pipeline_coleta()