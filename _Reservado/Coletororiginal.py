# ============================================================
# ARQUIVO: Coletor.py
# DATA: 30/07/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Ingestão de Dados (BACEN SGS 10813 + TV + B3 WIN/WDO Separados)
#         Engine de Rotação Temporal de Memória e
#         Geração do Arquivo Unificado dos 24 Ativos Mapeados.
# MODIFICAÇÃO FINAL: Integração com MT5 para capturar o LAST TICK (WIN/WDO)
#                    apenas dentro da janela de ajuste (19:00 - 08:50).
#
# ATUALIZAÇÃO 16/08/2026:
#   - Integração prioritária com Coletor_MT5_v2_2 (seleção dinâmica de contrato)
#   - Fallback automático para o coletor antigo (Coletor_MT5.py)
#   - Preservação total da V1 (nenhum arquivo antigo foi removido)
#   - ROTAÇÃO EXPANDIDA PARA 12 ARQUIVOS (0, 5, 10, ..., 55 min) → 60 min de histórico
# ============================================================


import json
import os
import shutil
import ssl
import sys
import urllib.request
from datetime import datetime, time
from pathlib import Path

# ------------------------------------------------------------
# CONFIGURAÇÃO DE DIRETÓRIOS E ARQUIVOS
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")

# Garante que a pasta 'Coletas' existe
os.makedirs(COLETAS_DIR, exist_ok=True)

# Definição dos caminhos para Rotação Temporal (Janela Móvel) - 12 arquivos
# 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55 minutos atrás
ARQUIVOS_ROM = [
    os.path.join(COLETAS_DIR, "Coleta_rom-0.json"),
    os.path.join(COLETAS_DIR, "Coleta_rom-5.json"),
    os.path.join(COLETAS_DIR, "Coleta_rom-10.json"),
    os.path.join(COLETAS_DIR, "Coleta_rom-15.json"),
    os.path.join(COLETAS_DIR, "Coleta_rom-20.json"),
    os.path.join(COLETAS_DIR, "Coleta_rom-25.json"),
    os.path.join(COLETAS_DIR, "Coleta_rom-30.json"),
    os.path.join(COLETAS_DIR, "Coleta_rom-35.json"),
    os.path.join(COLETAS_DIR, "Coleta_rom-40.json"),
    os.path.join(COLETAS_DIR, "Coleta_rom-45.json"),
    os.path.join(COLETAS_DIR, "Coleta_rom-50.json"),
    os.path.join(COLETAS_DIR, "Coleta_rom-55.json"),
]

# Referência para o arquivo mais recente (usado pelo Validador e demais módulos)
FILE_ROM0 = ARQUIVOS_ROM[0]

FILE_RAM = os.path.join(COLETAS_DIR, "Coleta_ram.json")
FILE_UNIFICADO = os.path.join(COLETAS_DIR, "DadosAtivosUnificados.json")

# Arquivos gerados pelos coletores MT5
FILE_MT5 = os.path.join(COLETAS_DIR, "Dados_MT5.json")          # formato antigo (v1)
FILE_MT5_V2 = os.path.join(COLETAS_DIR, "Dados_MT5_v2_2.json")  # formato novo (v2.2)

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
    # NOVOS ATIVOS PARA O LAST TICK (serão adicionados via MT5)
    "WIN_LAST_TICK": "WIN_LAST_TICK",
    "WDO_LAST_TICK": "WDO_LAST_TICK",
}


# ------------------------------------------------------------
# FUNÇÃO AUXILIAR: VERIFICAÇÃO DA JANELA DE AJUSTE (19:00 - 08:50)
# ------------------------------------------------------------
def esta_na_janela_ajuste() -> bool:
    """
    Retorna True se o horário atual estiver dentro da janela de ajuste oficial.
    Janela: das 19:00 até as 08:50 do dia seguinte (considerando virada de dia).
    """
    agora = datetime.now().time()
    hora_inicio = time(19, 0, 0)
    hora_fim = time(8, 50, 0)
    return agora >= hora_inicio or agora <= hora_fim


# ------------------------------------------------------------
# FUNÇÃO PARA CAPTURAR LAST DO MT5
# ------------------------------------------------------------
def capturar_last_do_mt5() -> dict:
    """
    Extrai o 'last' dos contratos principais de WIN e WDO.

    Prioridade de leitura:
      1. Dados_MT5_v2_2.json  (formato novo - seleção dinâmica por volume/vencimento)
      2. Dados_MT5.json       (formato antigo - lista fixa)

    Retorna dict no formato:
      {
        "WIN": {"contrato": "WINV26", "last": 128450.0, "timestamp": "..."},
        "WDO": {"contrato": "WDOV26", "last": 5.432, "timestamp": "..."}
      }
    """
    resultado = {}

    # ----------------------------------------------------------
    # 1. Tenta o formato novo (v2.2) — preferencial
    # ----------------------------------------------------------
    if os.path.exists(FILE_MT5_V2):
        try:
            with open(FILE_MT5_V2, "r", encoding="utf-8") as f:
                dados = json.load(f)

            timestamp = dados.get("timestamp", datetime.now().isoformat())
            ativos = dados.get("ativos", {})

            for prefixo in ("WIN", "WDO"):
                info_ativo = ativos.get(prefixo, {})
                if info_ativo.get("status") == "OK" or info_ativo.get("last") is not None:
                    last = info_ativo.get("last")
                    contrato = info_ativo.get("contrato_principal")
                    if last is not None and last > 0 and contrato:
                        resultado[prefixo] = {
                            "contrato": contrato,
                            "last": float(last),
                            "timestamp": timestamp,
                            "fonte": "MT5_v2.2",
                        }

            if resultado:
                if "WIN" in resultado:
                    print(f"   ✅ Last WIN via MT5 v2.2: {resultado['WIN']['last']} ({resultado['WIN']['contrato']})")
                if "WDO" in resultado:
                    print(f"   ✅ Last WDO via MT5 v2.2: {resultado['WDO']['last']} ({resultado['WDO']['contrato']})")
                return resultado

        except Exception as e:
            print(f"[AVISO] Falha ao ler Dados_MT5_v2_2.json: {e}. Tentando formato antigo...")

    # ----------------------------------------------------------
    # 2. Fallback: formato antigo (Dados_MT5.json)
    # ----------------------------------------------------------
    if not os.path.exists(FILE_MT5):
        print("[AVISO] Nenhum arquivo MT5 encontrado (v2.2 nem v1). Não será possível capturar o last.")
        return resultado

    try:
        with open(FILE_MT5, "r", encoding="utf-8") as f:
            dados = json.load(f)

        contratos = dados.get("contratos", {})
        timestamp = dados.get("timestamp", datetime.now().isoformat())

        # Lista de prioridade do formato antigo (mantida por compatibilidade)
        mapeamento_contratos = {
            "WIN": ["WINQ26", "WINV26", "WINZ26"],
            "WDO": ["WDOQ26", "WDOV26", "WDOZ26"],
        }

        for ativo, lista in mapeamento_contratos.items():
            for contrato in lista:
                if contrato in contratos:
                    info = contratos[contrato]
                    last = info.get("last")
                    if last is not None and last > 0:
                        resultado[ativo] = {
                            "contrato": contrato,
                            "last": float(last),
                            "timestamp": timestamp,
                            "fonte": "MT5_v1",
                        }
                        break

        if "WIN" in resultado:
            print(f"   ✅ Last WIN via MT5 v1: {resultado['WIN']['last']} ({resultado['WIN']['contrato']})")
        if "WDO" in resultado:
            print(f"   ✅ Last WDO via MT5 v1: {resultado['WDO']['last']} ({resultado['WDO']['contrato']})")

        return resultado

    except Exception as e:
        print(f"[ERRO] Falha ao ler Dados_MT5.json (formato antigo): {e}")
        return {}


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
                item["timestamp"] = timestamp
            return cache_encontrado
        else:
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
    """
    Coleta os ativos mapeados via Scanner API Oculta do TradingView.
    Não tenta mais capturar 'last' porque a API não retorna esse campo fora do pregão.
    """
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
                    change_pct = float(vals[4]) if vals[4] is not None else 0.0

                    resultados.append(
                        {
                            "ativo": ticker_chave,
                            "fonte": "TRADINGVIEW_SCANNER",
                            "timestamp": timestamp,
                            "status": "OK",
                            "dados_reais": {
                                "close": close,
                                "open": float(vals[1]) if vals[1] is not None else None,
                                "high": float(vals[2]) if vals[2] is not None else None,
                                "low": float(vals[3]) if vals[3] is not None else None,
                                "change_percent": change_pct,
                                "volume": float(vals[5]) if len(vals) > 5 and vals[5] is not None else None,
                            },
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
    """
    Executa a rotação temporal dos 12 arquivos (0, 5, 10, ..., 55 min).
    - Se is_ram_mode for True, apenas retorna o caminho do RAM (sem rotação).
    - Caso contrário, desloca os arquivos: rom-55 ← rom-50, rom-50 ← rom-45, ..., rom-0 ← rom-5? 
      Na verdade, a lógica é: o arquivo mais antigo (rom-55) é sobrescrito pelo anterior (rom-50),
      e assim sucessivamente, até que o rom-5 seja sobrescrito pelo rom-0 (que contém a coleta anterior),
      e então o rom-0 será sobrescrito pela nova coleta.
    """
    if is_ram_mode:
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] Modo RAM ativado. Ignorando rotação temporal."
        )
        return FILE_RAM

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Executando rotação de memória física (Janela Móvel - 12 arquivos)..."
    )

    # Percorre de trás para frente (do mais antigo para o mais recente)
    # Exemplo: rom-50 -> rom-55, rom-45 -> rom-50, ..., rom-0 -> rom-5
    # O índice 0 é o mais recente (rom-0), índice 11 é o mais antigo (rom-55)
    for i in range(len(ARQUIVOS_ROM) - 1, 0, -1):
        origem = ARQUIVOS_ROM[i - 1]
        destino = ARQUIVOS_ROM[i]
        if os.path.exists(origem):
            shutil.copy2(origem, destino)
            print(f"  └─ Rotação: {os.path.basename(origem)} ──> {os.path.basename(destino)}")
        else:
            # Se o arquivo de origem não existe, apenas registra (não copia)
            print(f"  └─ Aviso: {os.path.basename(origem)} não encontrado, pulando.")

    # Retorna o caminho do arquivo mais recente (rom-0) onde a nova coleta será gravada
    return ARQUIVOS_ROM[0]


def gerar_arquivo_unificado(coletas):
    """Gera o arquivo DadosAtivosUnificados.json com as chaves tratadas dos ativos."""
    ativos_map = {}

    for item in coletas:
        ativo_raw = item.get("ativo")
        dados_reais = item.get("dados_reais") or {}

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

    print(f"✅ Arquivo unificado salvo em: {FILE_UNIFICADO}")


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

    # 3. Extração TradingView Scanner (sem last)
    tv_dados = coletar_tradingview()
    coletas.extend(tv_dados)

    # ------------------------------------------------------------
    # 4. Se estiver na janela de ajuste, capturar LAST via MT5
    #    Prioridade: Coletor_MT5_v2_2 → fallback Coletor_MT5 (v1)
    # ------------------------------------------------------------
    if esta_na_janela_ajuste():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Capturando LAST TICK via MT5...")

        # 4.1 Tenta o coletor v2.2 (seleção dinâmica de contrato)
        mt5_ok = False
        try:
            from Coletor_MT5_v2_2 import executar_coleta_mt5_v2
            dados_mt5 = executar_coleta_mt5_v2()
            if dados_mt5 and dados_mt5.get("status") == "OK":
                print("   ✅ MT5 v2.2 coletado com sucesso.")
                mt5_ok = True
            else:
                print("   ⚠️ Coleta MT5 v2.2 retornou status não-OK.")
        except ImportError:
            print("   ⚠️ Módulo Coletor_MT5_v2_2 não encontrado.")
        except Exception as e:
            print(f"   ⚠️ Erro ao executar Coletor_MT5_v2_2: {e}")

        # 4.2 Fallback para o coletor antigo (v1) se o v2.2 falhou
        if not mt5_ok:
            try:
                from Coletor_MT5 import executar_coleta_mt5
                dados_mt5 = executar_coleta_mt5()
                if dados_mt5 and dados_mt5.get("status") == "OK":
                    print("   ✅ MT5 v1 (fallback) coletado com sucesso.")
                else:
                    print("   ⚠️ Falha também no coletor MT5 v1. Tentando ler arquivo existente.")
            except ImportError:
                print("   ⚠️ Módulo Coletor_MT5 (v1) também não encontrado. Tentando ler arquivo existente.")
            except Exception as e:
                print(f"   ⚠️ Erro ao executar Coletor_MT5 (v1): {e}")

        # 4.3 Extrai os lasts (lê preferencialmente o v2.2, com fallback automático)
        lasts = capturar_last_do_mt5()
        if lasts:
            timestamp_atual = datetime.now().isoformat()
            if "WIN" in lasts:
                fonte_usada = lasts["WIN"].get("fonte", "MT5")
                coletas.append({
                    "ativo": "WIN_LAST_TICK",
                    "fonte": fonte_usada,
                    "timestamp": timestamp_atual,
                    "status": "OK",
                    "dados_reais": {
                        "close": lasts["WIN"]["last"],
                        "open": None,
                        "high": None,
                        "low": None,
                        "change_percent": None,
                        "volume": None,
                    },
                })
            if "WDO" in lasts:
                fonte_usada = lasts["WDO"].get("fonte", "MT5")
                coletas.append({
                    "ativo": "WDO_LAST_TICK",
                    "fonte": fonte_usada,
                    "timestamp": timestamp_atual,
                    "status": "OK",
                    "dados_reais": {
                        "close": lasts["WDO"]["last"],
                        "open": None,
                        "high": None,
                        "low": None,
                        "change_percent": None,
                        "volume": None,
                    },
                })
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fora da janela de ajuste. LAST TICK NÃO coletado.")

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

    # Grava Coleta de Rotação
    with open(arquivo_destino, "w", encoding="utf-8") as f:
        json.dump(conteudo_saida, f, indent=2, ensure_ascii=False)

    # Grava RAM (cópia independente da mais recente)
    if not is_ram:
        with open(FILE_RAM, "w", encoding="utf-8") as f:
            json.dump(conteudo_saida, f, indent=2, ensure_ascii=False)
        print(f"✅ Cópia independente gerada em: {FILE_RAM}")

    # Gera unificado
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