import json
import os
from datetime import datetime
from pathlib import Path
import MetaTrader5 as mt5

# Import para carregar o arquivo .env
from dotenv import load_dotenv
import pandas as pd
import requests

# ==============================================================================
# 1. CARREGAMENTO DAS VARIÁVEIS DE AMBIENTE (.env) E DIRETÓRIOS
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

COLETAS_DIR = BASE_DIR / "Coletas"
COLETAS_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# 2. MAPEAMENTO COM AS CHAVES FIXAS IDÊNTICAS AO COLETOR.PY
# ==============================================================================
ATIVOS_CONFIG = [
    # Volatilidade
    {
        "id_fixo": "VIX",
        "ativo_tradingview": "TVC:VIX",
        "ticker_coleta": "VXX",
        "fonte": "Finnhub",
        "categoria": "Volatilidade",
    },
    # Commodities
    {
        "id_fixo": "MINERIO_SLX",
        "ativo_tradingview": "SGX:FEF1!",
        "ticker_coleta": "SLX",
        "fonte": "Finnhub",
        "categoria": "Commodities",
    },
    {
        "id_fixo": "MINERIO_PICK",
        "ativo_tradingview": "SGX:FEF2!",
        "ticker_coleta": "PICK",
        "fonte": "Finnhub",
        "categoria": "Commodities",
    },
    {
        "id_fixo": "PETROLEO_USO",
        "ativo_tradingview": "NYMEX:CL1!",
        "ticker_coleta": "USO",
        "fonte": "Finnhub",
        "categoria": "Commodities",
    },
    {
        "id_fixo": "OURO_GLD",
        "ativo_tradingview": "TVC:GOLD",
        "ticker_coleta": "GLD",
        "fonte": "Finnhub",
        "categoria": "Commodities",
    },
    # ADRs B3
    {
        "id_fixo": "VALE_ADR",
        "ativo_tradingview": "NYSE:VALE",
        "ticker_coleta": "VALE",
        "fonte": "Finnhub",
        "categoria": "ADRs B3",
    },
    {
        "id_fixo": "PETR_ADR",
        "ativo_tradingview": "NYSE:PBR",
        "ticker_coleta": "PBR",
        "fonte": "Finnhub",
        "categoria": "ADRs B3",
    },
    {
        "id_fixo": "ITUB_ADR",
        "ativo_tradingview": "NYSE:ITUB",
        "ticker_coleta": "ITUB",
        "fonte": "Finnhub",
        "categoria": "ADRs B3",
    },
    {
        "id_fixo": "BDORY_ADR",
        "ativo_tradingview": "OTC:BDORY",
        "ticker_coleta": "BDORY",
        "fonte": "Finnhub",
        "categoria": "ADRs B3",
    },
    {
        "id_fixo": "BBD_ADR",
        "ativo_tradingview": "NYSE:BBD",
        "ticker_coleta": "BBD",
        "fonte": "Finnhub",
        "categoria": "ADRs B3",
    },
    {
        "id_fixo": "BOLSY_ADR",
        "ativo_tradingview": "OTC:BOLSY",
        "ticker_coleta": "BOLSY",
        "fonte": "Finnhub",
        "categoria": "ADRs B3",
    },
    # Índices Globais / Emergentes
    {
        "id_fixo": "EWZ",
        "ativo_tradingview": "AMEX:EWZ",
        "ticker_coleta": "EWZ",
        "fonte": "Finnhub",
        "categoria": "Índices Globais",
    },
    {
        "id_fixo": "SPY",
        "ativo_tradingview": "CME_MINI:ES1!",
        "ticker_coleta": "SPY",
        "fonte": "Finnhub",
        "categoria": "Índices Globais",
    },
    {
        "id_fixo": "QQQ",
        "ativo_tradingview": "CME_MINI:NQ1!",
        "ticker_coleta": "QQQ",
        "fonte": "Finnhub",
        "categoria": "Índices Globais",
    },
    {
        "id_fixo": "EWW",
        "ativo_tradingview": "FX_IDC:USDMXN",
        "ticker_coleta": "EWW",
        "fonte": "Finnhub",
        "categoria": "Emergentes",
    },
    # Câmbio
    {
        "id_fixo": "DXY_UUP",
        "ativo_tradingview": "TVC:DXY",
        "ticker_coleta": "UUP",
        "fonte": "Finnhub",
        "categoria": "Câmbio",
    },
    {
        "id_fixo": "DOLAR_SPOT",
        "ativo_tradingview": "FX_IDC:USDBRL",
        "ticker_coleta": "WDO$",
        "fonte": "MetaTrader5",
        "categoria": "Câmbio",
    },
    {
        "id_fixo": "USD_PTAX",
        "ativo_tradingview": "BCB:PTAX",
        "ticker_coleta": "10813",
        "fonte": "BCB",
        "categoria": "Câmbio",
    },
    # Futuros B3
    {
        "id_fixo": "INDICE_FUT",
        "ativo_tradingview": "BMFBOVESPA:WIN1!",
        "ticker_coleta": "WIN$",
        "fonte": "MetaTrader5",
        "categoria": "Futuros B3",
    },
    {
        "id_fixo": "DOLAR_FUT",
        "ativo_tradingview": "BMFBOVESPA:WDO1!",
        "ticker_coleta": "WDO$",
        "fonte": "MetaTrader5",
        "categoria": "Futuros B3",
    },
    # Juros DI
    {
        "id_fixo": "DI_2027",
        "ativo_tradingview": "BMFBOVESPA:DI1F2027",
        "ticker_coleta": "DI1F27",
        "fonte": "MetaTrader5",
        "categoria": "Juros DI",
    },
    {
        "id_fixo": "DI_2029",
        "ativo_tradingview": "BMFBOVESPA:DI1F2029",
        "ticker_coleta": "DI1F29",
        "fonte": "MetaTrader5",
        "categoria": "Juros DI",
    },
]


# ==============================================================================
# 3. FUNÇÕES DE COLETA DE DADOS
# ==============================================================================
def coletar_finnhub(cfg):
    ticker = cfg["ticker_coleta"]

    if not FINNHUB_API_KEY:
        print("⚠️ [AVISO] Chave 'FINNHUB_API_KEY' não encontrada no arquivo .env")
        return None

    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        res = response.json()

        if "error" in res:
            print(f"⚠️ Erro de API Finnhub ({ticker}): {res['error']}")
            return None

        if "c" in res and res["c"] != 0:
            return (
                cfg["id_fixo"],
                {
                    "categoria": cfg["categoria"],
                    "ativo_tradingview": cfg["ativo_tradingview"],
                    "ticker_coleta": ticker,
                    "fonte": cfg["fonte"],
                    "preco": float(res["c"]),
                    "var_pct": round(float(res.get("dp", 0.0)), 2),
                    "var_abs": round(float(res.get("d", 0.0)), 2),
                    "fechamento_anterior": float(res.get("pc", 0.0)),
                    "status": "OK",
                },
            )
    except Exception as e:
        print(f"❌ Erro de requisição Finnhub ({ticker}): {e}")
    return None


def coletar_mt5(cfg):
    symbol = cfg["ticker_coleta"]
    mt5.symbol_select(symbol, True)
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)

    if info and tick:
        prev_close = float(getattr(info, "session_close", 0.0))
        preco = float(
            tick.last
            if tick.last > 0
            else float(tick.bid if tick.bid > 0 else tick.ask)
        )

        if preco > 0:
            var_pct = (
                round(((preco / prev_close) - 1) * 100, 2)
                if prev_close > 0
                else 0.0
            )
            return (
                cfg["id_fixo"],
                {
                    "categoria": cfg["categoria"],
                    "ativo_tradingview": cfg["ativo_tradingview"],
                    "ticker_coleta": symbol,
                    "fonte": cfg["fonte"],
                    "preco": preco,
                    "var_pct": var_pct,
                    "var_abs": (
                        round(preco - prev_close, 2) if prev_close > 0 else 0.0
                    ),
                    "fechamento_anterior": prev_close,
                    "status": "OK",
                },
            )
    return None


def coletar_bcb(cfg):
    """Coleta a cotação PTAX mais recente enviada pelo Banco Central."""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.10813/dados/ultimos/2?formato=json"
        res = requests.get(url, timeout=5).json()

        if isinstance(res, list) and len(res) >= 2:
            prev_val = float(res[0]["valor"])
            curr_val = float(res[1]["valor"])

            if prev_val > 0 and curr_val > 0:
                var_pct = round(((curr_val / prev_val) - 1) * 100, 2)
                var_abs = round(curr_val - prev_val, 4)

                return (
                    cfg["id_fixo"],
                    {
                        "categoria": cfg["categoria"],
                        "ativo_tradingview": cfg["ativo_tradingview"],
                        "ticker_coleta": "PTAX_BCB",
                        "fonte": "Banco Central",
                        "preco": curr_val,
                        "var_pct": var_pct,
                        "var_abs": var_abs,
                        "fechamento_anterior": prev_val,
                        "status": "OK",
                    },
                )
    except Exception as e:
        print(f"❌ Erro ao coletar PTAX do BCB: {e}")
    return None


# ==============================================================================
# 4. EXECUÇÃO PRINCIPAL
# ==============================================================================
def main():
    print("🚀 Coletando ativos via Finnhub, MetaTrader 5 e Banco Central...")

    mt5_ok = mt5.initialize()
    resultados_dict = {}
    resultados_lista = []

    for cfg in ATIVOS_CONFIG:
        dado = None
        if cfg["fonte"] == "Finnhub":
            dado = coletar_finnhub(cfg)
        elif cfg["fonte"] == "MetaTrader5" and mt5_ok:
            dado = coletar_mt5(cfg)
        elif cfg["fonte"] == "BCB":
            dado = coletar_bcb(cfg)

        if dado:
            id_fixo, dados_ativo = dado
            resultados_dict[id_fixo] = dados_ativo
            resultados_lista.append({"id_fixo": id_fixo, **dados_ativo})

    if mt5_ok:
        mt5.shutdown()

    total = len(resultados_dict)
    print(f"\n✅ Total de ativos coletados: {total}/{len(ATIVOS_CONFIG)}\n")

    if resultados_dict:
        # Exibição organizada no Terminal
        df = pd.DataFrame(resultados_lista)
        colunas = [
            "id_fixo",
            "categoria",
            "ticker_coleta",
            "fonte",
            "preco",
            "var_pct",
            "var_abs",
            "fechamento_anterior",
        ]
        df = df[colunas]

        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", 1000)
        print(df.to_string(index=False))

        agora = datetime.now()
        timestamp_str = agora.strftime("%Y-%m-%d %H:%M:%S")

        # ----------------------------------------------------------------------
        # A) Atualiza o ARQUIVO UNIFICADO PRINCIPAL
        # ----------------------------------------------------------------------
        path_unificado = COLETAS_DIR / "DadosAtivosUnificados.json"
        json_unificado = {
            "metadata": {
                "timestamp": timestamp_str,
                "total_ativos": total,
            },
            "ativos": resultados_dict,
        }
        with open(path_unificado, "w", encoding="utf-8") as f:
            json.dump(json_unificado, f, indent=4, ensure_ascii=False)
        print(f"\n💾 [UNIFICADO] Atualizado com sucesso: {path_unificado}")

        # ----------------------------------------------------------------------
        # B) Grava a ROTAÇÃO MÓVEL (Coleta_rom-X.json e Coleta_ram.json)
        # ----------------------------------------------------------------------
        slot_minuto = (agora.minute // 5) * 5
        path_rotativo = COLETAS_DIR / f"Coleta_rom-{slot_minuto}.json"
        path_ram = COLETAS_DIR / "Coleta_ram.json"

        json_rotativo = {
            "metadata_coleta": {
                "timestamp_coleta": agora.isoformat(),
                "total_ativos": total,
                "slot_minuto": slot_minuto,
            },
            "ativos": resultados_dict,
        }

        for path in [path_rotativo, path_ram]:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(json_rotativo, f, indent=4, ensure_ascii=False)
        print(f"🔄 [ROTAÇÃO] Gravado slot {slot_minuto} min: {path_rotativo.name} e Coleta_ram.json")


if __name__ == "__main__":
    main()