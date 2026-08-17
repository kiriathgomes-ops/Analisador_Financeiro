# ============================================================
# testar_mt5_vs_tradingview.py
# 
# OBJETIVO: Testar se os ativos atualmente coletados via 
#           TradingView estão disponíveis no MetaTrader 5 (MT5)
#           com dados em tempo real.
#
# USO: python testar_mt5_vs_tradingview.py
# ============================================================

import sys
import json
import csv
import time
from datetime import datetime
from pathlib import Path

# ============================================================
# FIX: FORÇA UTF-8 NO TERMINAL WINDOWS (SE POSSÍVEL)
# ============================================================
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# ============================================================
# TENTA IMPORTAR MT5
# ============================================================
try:
    import MetaTrader5 as mt5
    MT5_DISPONIVEL = True
except ImportError:
    MT5_DISPONIVEL = False
    print("[ERRO] Biblioteca MetaTrader5 não instalada.")
    print("       Execute: pip install MetaTrader5")
    sys.exit(1)

# ============================================================
# MAPEAMENTO: TradingView Ticker -> Possíveis nomes no MT5
# ============================================================
# A ordem importa: o script testa do primeiro ao último,
# e usa o primeiro que encontrar com dados válidos.
# 
# Adapte esta lista conforme os símbolos disponíveis na 
# sua corretora (XP, Clear, BTG, etc.)
# ============================================================

MAPEAMENTO = {
    # ---------- ADRs Brasileiras (US Stocks / OTC) ----------
    "VALE_ADR": {
        "tv_ticker": "NYSE:VALE",
        "mt5_candidatos": ["VALE", "VALE3", "VALE.US", "VALE.N", "VALE3.US", "VALE3.N"]
    },
    "PETR_ADR": {
        "tv_ticker": "NYSE:PBR",
        "mt5_candidatos": ["PETR", "PETR4", "PBR", "PETR.US", "PETR.N", "PETR4.US"]
    },
    "ITUB_ADR": {
        "tv_ticker": "NYSE:ITUB",
        "mt5_candidatos": ["ITUB", "ITUB4", "ITUB.US", "ITUB.N", "ITUB4.US"]
    },
    "BBD_ADR": {
        "tv_ticker": "NYSE:BBD",
        "mt5_candidatos": ["BBD", "BBDC4", "BBD.US", "BBD.N", "BBDC4.US"]
    },
    "BBAS_ADR": {
        "tv_ticker": "OTC:BDORY",
        "mt5_candidatos": ["BBAS", "BBAS3", "BDORY", "BBAS.US"]  # OTC raramente existe no MT5
    },
    "B3_ADR": {
        "tv_ticker": "OTC:BOLSY",
        "mt5_candidatos": ["B3", "B3SA3", "BOLSY", "B3.US"]      # OTC raramente existe no MT5
    },

    # ---------- ETFs & Índices ----------
    "EWZ": {
        "tv_ticker": "AMEX:EWZ",
        "mt5_candidatos": ["EWZ", "EWZ.US"]
    },
    "SP500_FUT": {
        "tv_ticker": "CME_MINI:ES1!",
        "mt5_candidatos": ["ES1!", "ES", "SPX", "US500", "SP500"]
    },
    "NASDAQ_FUT": {
        "tv_ticker": "CME_MINI:NQ1!",
        "mt5_candidatos": ["NQ1!", "NQ", "NAS100", "US100", "NASDAQ"]
    },
    "VIX": {
        "tv_ticker": "TVC:VIX",
        "mt5_candidatos": ["VIX", "VIX.US", "VIX.IND"]
    },

    # ---------- Commodities ----------
    "CRUDE_OIL": {
        "tv_ticker": "NYMEX:CL1!",
        "mt5_candidatos": ["CL1!", "CL", "WTI", "USOIL", "OIL"]
    },
    "GOLD": {
        "tv_ticker": "TVC:GOLD",
        "mt5_candidatos": ["XAUUSD", "GOLD", "XAU", "GOLD.USD"]
    },
    "IRON_ORE": {
        "tv_ticker": "SGX:FEF1!",
        "mt5_candidatos": ["FEF1!", "FEF", "FE", "SGX:FE"]  # MUITO difícil de ter no MT5 BR
    },
    "IRON_ORE_2M": {
        "tv_ticker": "SGX:FEF2!",
        "mt5_candidatos": ["FEF2!", "FEFU2026", "FE"]      # MUITO difícil de ter no MT5 BR
    },

    # ---------- Moedas (Forex / DXY) ----------
    "USD_BRL": {
        "tv_ticker": "FX_IDC:USDBRL",
        "mt5_candidatos": ["USDBRL", "USD/BRL", "USD.BRL", "BRL"]
    },
    "USD_MXN": {
        "tv_ticker": "FX_IDC:USDMXN",
        "mt5_candidatos": ["USDMXN", "USD/MXN", "USD.MXN"]
    },
    "DXY": {
        "tv_ticker": "TVC:DXY",
        "mt5_candidatos": ["DXY", "USDOLLAR", "USDX", "DX"]
    },

    # ---------- Juros (DI) - Já existem no MT5, mas vamos testar ----------
    "DI1_2027": {
        "tv_ticker": "BMFBOVESPA:DI1F2027",
        "mt5_candidatos": ["DI1F27", "DI1V26", "DI1Z26"]  # meses variam
    },
    "DI1_2029": {
        "tv_ticker": "BMFBOVESPA:DI1F2029",
        "mt5_candidatos": ["DI1F29", "DI1V28", "DI1Z28"]
    },
}

# ============================================================
# FUNÇÃO PARA TESTAR UM SÍMBOLO NO MT5
# ============================================================

def testar_simbolo_mt5(simbolo: str) -> dict:
    """
    Tenta selecionar um símbolo no MT5 e obter o último tick.
    Retorna: {
        "encontrado": bool,
        "selecionado": bool,
        "preco": float or None,
        "bid": float or None,
        "ask": float or None,
        "volume": float or None,
        "time": str or None,
        "erro": str or None
    }
    """
    resultado = {
        "encontrado": False,
        "selecionado": False,
        "preco": None,
        "bid": None,
        "ask": None,
        "volume": None,
        "time": None,
        "erro": None
    }

    try:
        # Verifica se o símbolo existe
        info = mt5.symbol_info(simbolo)
        if info is None:
            resultado["encontrado"] = False
            resultado["erro"] = "Símbolo não encontrado"
            return resultado

        resultado["encontrado"] = True

        # Tenta selecionar o símbolo (adicionar ao Market Watch)
        if not mt5.symbol_select(simbolo, True):
            resultado["selecionado"] = False
            resultado["erro"] = "Não foi possível selecionar (Market Watch)"
            # Mesmo assim, tenta pegar o tick
        else:
            resultado["selecionado"] = True

        # Obtém o tick
        tick = mt5.symbol_info_tick(simbolo)
        if tick is None:
            resultado["preco"] = None
            resultado["erro"] = "Tick indisponível (pode estar fora do pregão)"
            return resultado

        # Preenche os dados
        resultado["bid"] = tick.bid
        resultado["ask"] = tick.ask
        resultado["preco"] = tick.last if tick.last > 0 else tick.bid if tick.bid > 0 else tick.ask
        resultado["volume"] = tick.volume
        if tick.time:
            resultado["time"] = datetime.fromtimestamp(tick.time).strftime("%Y-%m-%d %H:%M:%S")

        return resultado

    except Exception as e:
        resultado["encontrado"] = False
        resultado["erro"] = f"Exceção: {str(e)}"
        return resultado


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():
    print("=" * 70)
    print(" TESTE: MT5 vs TRADINGVIEW - DISPONIBILIDADE DE ATIVOS")
    print("=" * 70)
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not MT5_DISPONIVEL:
        print("[ERRO] MetaTrader5 não instalado.")
        return

    # Inicializa MT5
    print("[INFO] Conectando ao MetaTrader 5...")
    if not mt5.initialize():
        print(f"[ERRO] Falha ao inicializar MT5. Código: {mt5.last_error()}")
        print("       Verifique se o MetaTrader 5 está aberto e logado.")
        return

    print("[INFO] MT5 conectado com sucesso!")
    versao = mt5.version()
    print(f"[INFO] Versão MT5: {versao}")
    print()

    # Dicionário para armazenar os resultados
    resultados = {}
    total_encontrados = 0
    total_com_preco = 0
    total_nao_encontrados = 0

    # Testa cada ativo
    for ativo_id, config in MAPEAMENTO.items():
        tv_ticker = config["tv_ticker"]
        candidatos = config["mt5_candidatos"]

        print(f"📌 Testando: {ativo_id} (TV: {tv_ticker})")
        print(f"   Candidatos MT5: {', '.join(candidatos)}")

        melhor_resultado = None
        simbolo_usado = None

        for candidato in candidatos:
            res = testar_simbolo_mt5(candidato)

            # Critério de aceitação: encontrado E tem preço > 0
            if res["encontrado"] and res["preco"] is not None and res["preco"] > 0:
                melhor_resultado = res
                simbolo_usado = candidato
                break  # usa o primeiro com preço válido

            # Fallback: se não achou com preço, mas achou o símbolo, guarda
            if res["encontrado"] and melhor_resultado is None:
                melhor_resultado = res
                simbolo_usado = candidato

        # Se ainda não achou nada, pega o primeiro erro (ou None)
        if melhor_resultado is None:
            melhor_resultado = {"encontrado": False, "erro": "Nenhum candidato funcionou"}
            simbolo_usado = "N/A"

        # Classifica o resultado
        status = "❌ NAO_ENCONTRADO"
        if melhor_resultado.get("encontrado"):
            if melhor_resultado.get("preco") and melhor_resultado["preco"] > 0:
                status = f"✅ ENCONTRADO (preço: {melhor_resultado['preco']:.2f})"
                total_com_preco += 1
            else:
                status = "⚠️ ENCONTRADO_SEM_PRECO"
            total_encontrados += 1
        else:
            total_nao_encontrados += 1

        # Exibe o resultado
        print(f"   -> {status} | Símbolo usado: {simbolo_usado}")
        if melhor_resultado.get("erro") and melhor_resultado["erro"] != "Nenhum candidato funcionou":
            print(f"      Obs: {melhor_resultado['erro']}")
        if melhor_resultado.get("time"):
            print(f"      Último tick: {melhor_resultado['time']}")
        print()

        # Salva no dicionário de resultados
        resultados[ativo_id] = {
            "tv_ticker": tv_ticker,
            "mt5_simbolo_usado": simbolo_usado,
            "candidatos_testados": candidatos,
            "status": status,
            "preco": melhor_resultado.get("preco"),
            "bid": melhor_resultado.get("bid"),
            "ask": melhor_resultado.get("ask"),
            "volume": melhor_resultado.get("volume"),
            "time": melhor_resultado.get("time"),
            "erro": melhor_resultado.get("erro"),
        }

    # Desconecta MT5
    mt5.shutdown()
    print("[INFO] MT5 desconectado.")

    # ============================================================
    # RESUMO FINAL
    # ============================================================
    print("=" * 70)
    print(" RESUMO")
    print("=" * 70)
    print(f"Total de ativos testados : {len(resultados)}")
    print(f"✅ Encontrados com preço   : {total_com_preco}")
    print(f"⚠️ Encontrados sem preço   : {total_encontrados - total_com_preco}")
    print(f"❌ Não encontrados         : {total_nao_encontrados}")
    print()

    # ============================================================
    # SALVA RELATÓRIO EM JSON
    # ============================================================
    output_dir = Path(__file__).resolve().parent / "Coletas"
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / "Diagnostico_MT5_vs_TradingView.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_ativos": len(resultados),
            "encontrados_com_preco": total_com_preco,
            "encontrados_sem_preco": total_encontrados - total_com_preco,
            "nao_encontrados": total_nao_encontrados,
            "detalhes": resultados
        }, f, indent=2, ensure_ascii=False)

    print(f"[INFO] Relatório JSON salvo em: {json_path}")

    # ============================================================
    # SALVA RELATÓRIO EM CSV (para abrir no Excel)
    # ============================================================
    csv_path = output_dir / "Diagnostico_MT5_vs_TradingView.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Ativo", "TV_Ticker", "MT5_Simbolo_Usado", "Status", 
            "Preco", "Bid", "Ask", "Volume", "Ultimo_Tick", "Erro"
        ])
        for ativo_id, dados in resultados.items():
            writer.writerow([
                ativo_id,
                dados["tv_ticker"],
                dados["mt5_simbolo_usado"],
                dados["status"],
                dados["preco"],
                dados["bid"],
                dados["ask"],
                dados["volume"],
                dados["time"],
                dados["erro"]
            ])

    print(f"[INFO] Relatório CSV salvo em: {csv_path}")
    print("=" * 70)
    print(" FIM DO DIAGNÓSTICO")
    print("=" * 70)


if __name__ == "__main__":
    main()