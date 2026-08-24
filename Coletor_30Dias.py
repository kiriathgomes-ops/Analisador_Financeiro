#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, time, timedelta
import json
import os
import MetaTrader5 as mt5
import pandas as pd
import yfinance as yf

# CONFIGURAÇÕES
DIAS_UTEIS_ALVO = 30
ARQUIVO_SAIDA = "Historico_Janela_Abertura_30Dias.json"

# Ativos da B3 (MT5) e Globais (yfinance)
ATIVOS_MT5 = ["WIN$", "WDO$", "VALE3", "PETR4", "ITUB4"]
ATIVOS_YFINANCE = {
    "EWZ": "EWZ",
    "SP500_FUT": "ES=F",
    "DXY": "DX-Y.NYB",
    "VALE_ADR": "VALE",
    "PETR_ADR": "PBR",
}


def obter_dias_uteis(quantidade):
    """Gera uma lista com os últimos N dias úteis ignorando finais de semana."""
    dias = []
    atual = datetime.now().date() - timedelta(days=1)  # Começa de ontem

    while len(dias) < quantidade:
        # 0 = Segunda, 4 = Sexta, 5 = Sábado, 6 = Domingo
        if atual.weekday() < 5:
            dias.append(atual)
        atual -= timedelta(days=1)

    return sorted(dias)


def extrair_mt5_janela(simbolo, data_alvo):
    """Puxa candles de 5m do MT5 entre 09:50 e 10:30."""
    inicio = datetime.combine(data_alvo, time(9, 50))
    fim = datetime.combine(data_alvo, time(10, 30))

    mt5.symbol_select(simbolo, True)
    rates = mt5.copy_rates_range(simbolo, mt5.TIMEFRAME_M5, inicio, fim)

    if rates is None or len(rates) == 0:
        return []

    dados = []
    for r in rates:
        dados.append(
            {
                "time": datetime.fromtimestamp(r["time"]).strftime(
                    "%H:%M:%S"
                ),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": int(r["tick_volume"]),
            }
        )
    return dados


def extrair_yfinance_janela(ticker, data_alvo):
    """Puxa candles de 5m do Yahoo Finance para o dia específico."""
    inicio_str = data_alvo.strftime("%Y-%m-%d")
    fim_str = (data_alvo + timedelta(days=1)).strftime("%Y-%m-%d")

    df = yf.download(
        ticker, start=inicio_str, end=fim_str, interval="5m", progress=False
    )

    if df.empty:
        return []

    # Achata MultiIndex das colunas caso exista
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Filtra a janela das 09:50 às 10:30
    df = df.between_time("09:50", "10:30")

    dados = []
    for idx, row in df.iterrows():
        dados.append(
            {
                "time": idx.strftime("%H:%M:%S"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
            }
        )
    return dados


def executar_coleta_30_dias():
    if not mt5.initialize():
        print("❌ Erro ao inicializar o MetaTrader 5.")
        return

    dias_uteis = obter_dias_uteis(DIAS_UTEIS_ALVO)
    print(
        f"📅 Coletando dados de {len(dias_uteis)} dias úteis (de {dias_uteis[0]} até {dias_uteis[-1]})..."
    )

    base_historica = {}

    for dia in dias_uteis:
        data_str = dia.strftime("%Y-%m-%d")
        print(f"⏳ Processando: {data_str}...")

        base_historica[data_str] = {"b3": {}, "global": {}}

        # 1. Coleta Ativos B3 via MT5
        for ativo in ATIVOS_MT5:
            base_historica[data_str]["b3"][ativo] = extrair_mt5_janela(
                ativo, dia
            )

        # 2. Coleta Ativos Internacionais via yfinance
        for nome_chave, ticker in ATIVOS_YFINANCE.items():
            base_historica[data_str]["global"][nome_chave] = (
                extrair_yfinance_janela(ticker, dia)
            )

    # Salva o arquivo JSON final
    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(base_historica, f, indent=2, ensure_ascii=False)

    mt5.shutdown()
    print(f"\n✅ Coleta concluída com sucesso! Arquivo salvo em: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    executar_coleta_30_dias()