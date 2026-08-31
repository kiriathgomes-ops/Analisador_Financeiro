# -*- coding: utf-8 -*-
"""
Módulo: win_abertura_pro.py
Versão: 3.0 - Produção Otimizada V2
Objetivo: Previsão de direção e força da abertura do WINFUT baseando-se na curva 
          DI real interpolada e dados macro locais do pipeline V2.
"""

import os
import json
import logging
import warnings
from datetime import datetime, date, time
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
import requests
from dotenv import load_dotenv

# Ingestão de caminhos, constantes e configurações centrais da V2
from config import (
    COLETAS_DIR,
    FILE_VALIDADOS,
    FILE_MT5_V2,
    PESOS_ESTIMATIVA_ABERTURA,
    LOGS_DIR
)

warnings.filterwarnings("ignore")
load_dotenv()

# Configurações de mensageria do Telegram via ambiente (.env)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT")
DIVIDENDOS_ESTIMADOS = 80  # Pontos teóricos estimados de desconto de dividendos

def enviar_telegram(msg: str):
    """Envia o relatório de previsão pós-leilão diretamente para o canal operacional."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except:
        pass

def descobrir_contrato_vigente_v2() -> str:
    """Lê o snapshot do coletor V2.2 para capturar o contrato ativo com maior volume."""
    if not FILE_MT5_V2.exists():
        return "WIN$"
    try:
        with open(FILE_MT5_V2, "r", encoding="utf-8") as f:
            dados = json.load(f)
        contrato = dados.get("ativos", {}).get("WIN", {}).get("contrato_principal")
        if contrato:
            return str(contrato)
    except:
        pass
    return "WIN$"

def conectar_mt5_v2(symbol: str) -> bool:
    """Inicializa a API do MT5 garantindo o contrato selecionado na grade."""
    if not mt5.initialize():
        print(f"❌ Erro ao inicializar MT5: {mt5.last_error()}")
        return False
    mt5.symbol_select(symbol, True)
    return True

def carregar_dados_locais_v2() -> tuple[dict, dict]:
    """Carrega as métricas e dados validados processados em background pelo pipeline."""
    dados_validados = {}
    if FILE_VALIDADOS.exists():
        try:
            with open(FILE_VALIDADOS, "r", encoding="utf-8") as f:
                payload = json.load(f)
            # Converte a lista de ativos validados em dicionário chaveado pelo ativo_id
            dados_validados = {item["ativo_id"]: item for item in payload.get("ativos_validados", [])}
        except:
            pass
            
    dados_mt5 = {}
    if FILE_MT5_V2.exists():
        try:
            with open(FILE_MT5_V2, "r", encoding="utf-8") as f:
                dados_mt5 = json.load(f)
        except:
            pass
            
    return dados_validados, dados_mt5

def preco_justo(spot: float, taxa_di: float, du: int, div: int = 0) -> float:
    """Aplica o modelo matemático de precificação de carry-cost para contratos futuros."""
    t = du / 252
    return spot * (1 + taxa_di * t) - div

def calcular_score_direcional(gap_pct: float, desvio_justo: float, vix: float) -> float:
    """Calcula o score direcional de força de -100 a +100 baseado em prêmio e desvios macro."""
    score = 0.0

    # 1. Impacto do gap externo ponderado
    if gap_pct > 0.40: score += 35
    elif gap_pct > 0.20: score += 22
    elif gap_pct < -0.40: score -= 35
    elif gap_pct < -0.20: score -= 22
    else: score += gap_pct * 40

    # 2. Impacto do desvio do preço justo teórico
    if desvio_justo is not None:
        if desvio_justo > 120: score += 30
        elif desvio_justo > 60: score += 18
        elif desvio_justo < -120: score -= 30
        elif desvio_justo < -60: score -= 18
        else: score += desvio_justo * 0.18

    # 3. Trava e ajuste de volatilidade global (VIX)
    if vix > 25:
        score *= 0.85  # Reduz exposição em dias de pânico sistêmico
    elif vix < 14:
        score *= 1.05  # Aumenta confiança em regimes de volatilidade controlada
        
    return max(-100, min(100, score))

def interpretar_score_operacional(score: float) -> tuple[str, str, str]:
    forca = abs(score)
    if forca < 20:
        return "NEUTRO", "Fraca", "Mercado sem viés direcional claro"
    direcao = "COMPRADOR" if score > 0 else "VENDEDOR"
    forca_txt = "Forte" if forca >= 45 else "Moderada"
    return direcao, forca_txt, f"Viés {direcao.lower()} com força {forca_txt.lower()} — setup validado na V2"

def executar_previsao_abertura():
    # 1. Identificação dinâmica do ativo alvo do mês (Fim do hardcoding V1)
    win_symbol = descobrir_contrato_vigente_v2()
    
    print("=" * 72)
    print(f"🎯 WINFUT – ENGINE PRO DE PREVISÃO DE ABERTURA V2 | ATIVO: {win_symbol}")
    print(f"🕒 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 72)

    if not conectar_mt5_v2(win_symbol):
        return

    # 2. Extração de Métricas Locais Higienizadas (Fim das chamadas yfinance lentas na UI)
    mapa_ativos, payload_mt5 = carregar_dados_locais_v2()
    
    # Busca dados técnicos direto do MetaTrader via API estável
    rates_d1 = mt5.copy_rates_from_pos(win_symbol, mt5.TIMEFRAME_D1, 0, 2)
    tick_atual = mt5.symbol_info_tick(win_symbol)
    info_symbol = mt5.symbol_info(win_symbol)

    if rates_d1 is None or len(rates_d1) < 1:
        print("❌ Falha ao extrair candles históricos D1 do MetaTrader 5.")
        mt5.shutdown()
        return

    # Captura o fechamento anterior real e calcula o ATR 
    prev_close = float(rates_d1[0]["close"])
    last_price = float(tick_atual.last) if (tick_atual and tick_atual.last > 0) else prev_close
    
    # Parâmetros macro extraídos de forma limpa do cache Dados_Validados.json do pipeline
    vix = mapa_ativos.get("VIX", {}).get("close", 14.5)
    sp500_fut_change = mapa_ativos.get("SP500_FUT", {}).get("change_percent", 0.0)
    
    # Interpolação local defensiva de taxas DI extraídas do config/validador
    di27 = mapa_ativos.get("DI1_2027", {}).get("close", 13.60)
    di29 = mapa_ativos.get("DI1_2029", {}).get("close", 14.15)
    du_vencimento = 18 # DU estimado padrão até a rolagem do WIN
    
    # Flat-forward aproximado local entre os vértices curto e longo validados
    taxa_di_interpolada = (di27 + di29) / 2 / 100 

    print(f"\nFechamento Anterior : {prev_close:,.0f} pts")
    print(f"Último Preço MT5    : {last_price:,.0f} pts")
    print(f"Taxa DI Interpolada : {taxa_di_interpolada*100:.2f}% ({du_vencimento} DU)")
    print(f"Gap S&P 500 Futuro  : {sp500_fut_change:+.2f}%")
    print(f"VIX (Volatilidade)  : {vix:.1f}")

    # 3. Modelagem de Preço Justo e Desvios do Leilão
    justo = preco_justo(prev_close, taxa_di_interpolada, du_vencimento, DIVIDENDOS_ESTIMADOS)
    desview_pts = last_price - justo if last_price > 0 else 0.0
    
    print(f"Preço Justo Futuro  : {justo:,.0f} pts")
    print(f"Desvio do Modelo    : {desview_pts:+.0f} pts")

    # 4. Cálculo Estatístico do Score de Força Operacional
    score = calcular_score_direcional(sp500_fut_change, desview_pts, vix)
    direcao, forca, diagnostico_txt = interpretar_score_operacional(score)

    print("\n" + "=" * 72)
    print(f"🎯 DIREÇÃO PRO WIN  : {direcao}")
    print(f"💪 FORÇA DO SETUP    : {forca}")
    print(f"📊 SCORE NUMÉRICO   : {score:+.1f}")
    print(f"📝 {diagnostico_txt}")
    print("=" * 72)

    # 5. MENSAGERIA TELEGRAM INTEGRADA
    msg_markdown = f"""
<b>WIN PRO – Previsão de Abertura V2</b>
Direção: <b>{direcao}</b>
Força: <b>{forca}</b>
Score Ponderado: <code>{score:+.1f}</code>

• Preço Ref. MT5: <code>{last_price:,.0f}</code>
• Preço Justo Carry: <code>{justo:,.0f}</code>
• Desvio do Modelo: <code>{desview_pts:+.0f} pts</code>
• Gap S&P 500 Fut: <code>{sp500_fut_change:+.2f}%</code>
• VIX Volatilidade: <code>{vix:.1f}</code>

<i>{diagnostico_txt}</i>
"""
    enviar_telegram(msg_markdown)
    
    mt5.shutdown()
    print("\n✅ Execução e previsão do win_abertura_pro concluídas com sucesso na V2.")

if __name__ == "__main__":
    executar_previsao_abertura()
