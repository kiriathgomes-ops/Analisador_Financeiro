# -*- coding: utf-8 -*-
"""
WINFUT - Previsão de Direção e Força da Abertura Pós-Leilão
Fontes: Genial MT5 + Yahoo Finance (yfinance) + pyield (DI real)
"""

import MetaTrader5 as mt5
import pyield as yd
import pandas as pd
import numpy as np
from datetime import datetime, date, time, timedelta
from bizdays import Calendar
import requests
import time as time_module
import warnings
import os
from dotenv import load_dotenv
import yfinance as yf

warnings.filterwarnings("ignore")

# Carrega as variáveis do arquivo .env
load_dotenv()

# ============================================================
# CONFIGURAÇÕES
# ============================================================

MT5_LOGIN      = int(os.getenv("MT5_LOGIN"))
MT5_PASSWORD   = os.getenv("MT5_PASSWORD")
MT5_SERVER     = os.getenv("MT5_SERVER")
MT5_PATH       = os.getenv("MT5_PATH")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT  = os.getenv("TELEGRAM_CHAT")

WIN_SYMBOL           = "WINV26"               # atualize todo mês
DIVIDENDOS_ESTIMADOS = 80                     # pontos aproximados

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def conectar_mt5():
    if not mt5.initialize(path=MT5_PATH, login=MT5_LOGIN,
                          password=MT5_PASSWORD, server=MT5_SERVER):
        print("Erro MT5:", mt5.last_error())
        return False
    print("✅ MT5 Genial conectado")
    return True

def enviar_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=8
        )
    except:
        pass

def get_last_tick(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return None
    return {"last": tick.last, "bid": tick.bid, "ask": tick.ask,
            "time": datetime.fromtimestamp(tick.time)}

def get_prev_close(symbol):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 5)
    if rates is None or len(rates) < 2:
        return None
    return float(pd.DataFrame(rates).iloc[-2]["close"])

def get_atr(symbol, period=14):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, period + 5)
    if rates is None:
        return None
    df = pd.DataFrame(rates)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs()
    ], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])

# ============================================================
# DI REAL (pyield)
# ============================================================

def obter_taxa_di_real(dias_uteis_alvo):
    """Puxa curva DI1 mais recente e interpola a taxa para o prazo do WIN"""
    try:
        cal = Calendar.load("B3")
        ref = cal.offset(date.today(), -1)

        df = yd.futuro.historico(ref.strftime("%d-%m-%Y"), "DI1")
        
        # Se não tiver dados, tenta o dia útil anterior
        if df is None or (hasattr(df, "is_empty") and df.is_empty()) or len(df) == 0:
            ref = cal.offset(ref, -1)
            df = yd.futuro.historico(ref.strftime("%d-%m-%Y"), "DI1")

        if df is None or (hasattr(df, "is_empty") and df.is_empty()) or len(df) == 0:
            print("⚠️ pyield não retornou curva DI – usando fallback 14.25%")
            return 0.1425

        # Converte para pandas se for Polars
        if hasattr(df, "to_pandas"):
            df = df.to_pandas()

        dus = df["dias_uteis"].tolist()
        taxas = df["taxa_ajuste"].tolist()

        # Garante que as taxas estejam em decimal
        if max(taxas) > 1:
            taxas = [t / 100 for t in taxas]

        # Interpolação
        try:
            interp = yd.Interpolador(dus, taxas, metodo="flat_forward")
            taxa = float(interp(dias_uteis_alvo))
        except:
            # Fallback linear
            taxa = float(np.interp(dias_uteis_alvo, dus, taxas))

        print(f"✅ Taxa DI interpolada ({dias_uteis_alvo} DU): {taxa*100:.2f}%")
        return taxa

    except Exception as e:
        print(f"Erro pyield: {e} – usando fallback")
        return 0.1425

def dias_uteis_ate_vencimento_win():
    """Aproximação boa do número de DU até o vencimento do contrato atual"""
    return 18  # ajuste manual se quiser precisão máxima

# ============================================================
# S&P + VIX (yfinance)
# ============================================================

def get_finnhub():
    """Busca gap do S&P 500 e VIX via Yahoo Finance (gratuito)"""
    try:
        # S&P 500
        spx = yf.Ticker("^GSPC")
        hist_spx = spx.history(period="5d")
        
        if hist_spx.empty or len(hist_spx) < 2:
            print("⚠️ Não foi possível obter histórico do S&P")
            return None
            
        prev_close = hist_spx["Close"].iloc[-2]
        last_close = hist_spx["Close"].iloc[-1]
        gap = (last_close - prev_close) / prev_close * 100

        # VIX
        vix_ticker = yf.Ticker("^VIX")
        hist_vix = vix_ticker.history(period="5d")
        vix = float(hist_vix["Close"].iloc[-1]) if not hist_vix.empty else 18.0

        return {
            "gap_pct": float(gap),
            "spx": float(last_close),
            "spx_prev": float(prev_close),
            "vix": vix
        }
    except Exception as e:
        print("Erro ao buscar dados (yfinance):", e)
        return None

# ============================================================
# PREÇO JUSTO + RANGE
# ============================================================

def preco_justo(spot, taxa, du, div=0):
    t = du / 252
    return spot * (1 + taxa * t) - div

def range_esperado(ref, atr, vix):
    fator = max(0.7, min(1.6, vix / 18))
    amp = atr * fator * 0.55
    return ref + amp, ref - amp, amp

# ============================================================
# SCORE DE DIREÇÃO + FORÇA
# ============================================================

def calcular_score(gap_pct, desvio_justo, atr, vix):
    """
    Score de -100 a +100
    Positivo = comprador | Negativo = vendedor
    Absoluto = força
    """
    score = 0.0

    # 1. Gap externo (peso alto)
    if gap_pct > 0.40:
        score += 35
    elif gap_pct > 0.20:
        score += 22
    elif gap_pct < -0.40:
        score -= 35
    elif gap_pct < -0.20:
        score -= 22
    else:
        score += gap_pct * 40  # proporcional

    # 2. Desvio do preço justo (peso alto)
    if desvio_justo is not None:
        if desvio_justo > 120:
            score += 30
        elif desvio_justo > 60:
            score += 18
        elif desvio_justo < -120:
            score -= 30
        elif desvio_justo < -60:
            score -= 18
        else:
            score += desvio_justo * 0.18

    # 3. Regime de volatilidade (VIX)
    if vix > 25:
        score *= 0.85  # reduz confiança em dias de pânico
    elif vix < 14:
        score *= 1.05  # dias calmos tendem a seguir o gap

    # Limita
    score = max(-100, min(100, score))
    return score

def interpretar_score(score):
    forca = abs(score)
    if forca < 20:
        return "NEUTRO", "Fraca", "Mercado sem viés claro"
    elif forca < 45:
        direcao = "COMPRADOR" if score > 0 else "VENDEDOR"
        return direcao, "Moderada", f"Viés {direcao.lower()} com força moderada"
    else:
        direcao = "COMPRADOR" if score > 0 else "VENDEDOR"
        return direcao, "Forte", f"Viés {direcao.lower()} FORTE – boa probabilidade de seguir na abertura"

# ============================================================
# MONITORAMENTO TEÓRICO
# ============================================================

def monitorar_teorico(minutos=10):
    print("\n🔍 Monitorando teórico...")
    enviar_telegram("🔍 Monitoramento do leilão iniciado")
    inicio = datetime.now()
    ultimo = None
    hist = []

    while (datetime.now() - inicio).seconds < minutos * 60:
        tick = get_last_tick(WIN_SYMBOL)
        if tick and tick["last"]:
            t = tick["last"]
            if t != ultimo:
                agora = datetime.now().strftime("%H:%M:%S")
                print(f"[{agora}] Teórico → {t:.0f}")
                hist.append((agora, t))
                ultimo = t
                if len(hist) >= 2 and abs(t - hist[-2][1]) >= 150:
                    enviar_telegram(f"⚠️ Teórico moveu {t - hist[-2][1]:+.0f} → {t:.0f}")
        time_module.sleep(2.5)
    return hist

# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 72)
    print("WINFUT – PREVISÃO DE ABERTURA PÓS-LEILÃO")
    print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print("=" * 72)

    if not conectar_mt5():
        return

    # Dados base
    prev = get_prev_close(WIN_SYMBOL)
    tick = get_last_tick(WIN_SYMBOL)
    atr = get_atr(WIN_SYMBOL)
    du = dias_uteis_ate_vencimento_win()

    print(f"\nFechamento anterior : {prev}")
    print(f"ATR 14              : {atr:.0f}" if atr else "ATR indisponível")
    if tick:
        print(f"Último preço        : {tick['last']:.0f}")

    # DI real
    taxa_di = obter_taxa_di_real(du)

    # S&P + VIX
    fh = get_finnhub()
    if fh:
        print(f"\nGap S&P             : {fh['gap_pct']:+.2f}%")
        print(f"VIX                 : {fh['vix']:.1f}")
    else:
        fh = {"gap_pct": 0.0, "vix": 18.0}
        print("\n⚠️ Dados externos falharam – valores neutros")

    # Preço justo
    justo = None
    desvio = None
    if prev:
        justo = preco_justo(prev, taxa_di, du, DIVIDENDOS_ESTIMADOS)
        print(f"Preço Justo         : {justo:.0f}")
        if tick and tick["last"]:
            desvio = tick["last"] - justo
            print(f"Desvio atual        : {desvio:+.0f} pts")

    # Range esperado
    if prev and atr:
        max_e, min_e, amp = range_esperado(prev, atr, fh["vix"])
        print(f"Máx esperada        : {max_e:.0f}")
        print(f"Mín esperada        : {min_e:.0f}")
        print(f"Amplitude           : ±{amp:.0f} pts")

    # Score final
    score = calcular_score(fh["gap_pct"], desvio, atr, fh["vix"])
    direcao, forca, texto = interpretar_score(score)

    print("\n" + "=" * 72)
    print(f"🎯 DIREÇÃO          : {direcao}")
    print(f"💪 FORÇA            : {forca}")
    print(f"📊 SCORE            : {score:+.1f}")
    print(f"📝 {texto}")
    print("=" * 72)

    # Telegram
    msg = f"""
<b>WIN – Previsão de Abertura</b>
Direção: <b>{direcao}</b>
Força: <b>{forca}</b>
Score: {score:+.1f}

Gap S&P: {fh['gap_pct']:+.2f}%
VIX: {fh['vix']:.1f}
Preço Justo: {f'{justo:.0f}' if justo is not None else 'N/A'}
Desvio: {f'{desvio:+.0f}' if desvio is not None else 'N/A'} pts
"""
    enviar_telegram(msg)

    # Monitoramento se estiver no horário
    agora = datetime.now().time()
    if time(8, 50) <= agora <= time(9, 20):
        hist = monitorar_teorico(10)
        if hist:
            enviar_telegram(f"Leilão finalizado\nÚltimo teórico: {hist[-1][1]:.0f}")

    mt5.shutdown()
    print("\n✅ Finalizado")

if __name__ == "__main__":
    main()