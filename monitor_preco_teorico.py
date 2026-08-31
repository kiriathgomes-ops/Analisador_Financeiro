# -*- coding: utf-8 -*-
"""
Módulo: monitor_preco_teorico.py
Versão: 3.0 - Produção Otimizada V2
Objetivo: Monitorar a formação de preço teórico e spreads do leilão B3 em tempo real via MT5.
"""

import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import MetaTrader5 as mt5

# Ingestão de caminhos, limites temporais e flags estáveis do seu config.py
from config import (
    LOGS_DIR,
    FILE_MT5_V2,
    JANELA_AJUSTE_INICIO,
    JANELA_AJUSTE_FIM,
    MAX_TENTATIVAS_MT5
)

# Configuração local baseada nas regras de negócio da V2
INTERVALO_SEGUNDOS = 2
ALERTA_SONORO = True
ALERTA_APENAS_PRIMEIRA_VEZ = True

def tocar_alerta():
    """Emite um sinal sonoro de aviso institucional na mesa de operações."""
    try:
        if sys.platform == "win32":
            import winsound
            winsound.Beep(1000, 300)
            time.sleep(0.1)
            winsound.Beep(1300, 300)
        else:
            sys.stdout.write("\a")
            sys.stdout.flush()
    except:
        pass

def descobrir_contrato_ativo_v2() -> str:
    """
    Lê defensivamente o snapshot gerado pelo Coletor MT5 v2.2 para capturar 
    o contrato real vigente com maior volume ( WINV26, WINZ26, etc ).
    """
    if not FILE_MT5_V2.exists():
        return "WIN$"  # Fallback contínuo caso o pipeline inicial não tenha rodado
    try:
        with open(FILE_MT5_V2, "r", encoding="utf-8") as f:
            dados = json.load(f)
        contrato = dados.get("ativos", {}).get("WIN", {}).get("contrato_principal")
        if contrato:
            return str(contrato)
    except:
        pass
    return "WIN$"

def conectar_e_validar_mt5(symbol: str) -> bool:
    """Inicializa a conexão com o terminal MetaTrader 5 e ativa o ativo na grade."""
    if not mt5.initialize():
        logging.error(f"[LEILÃO] Falha ao conectar ao MT5: {mt5.last_error()}")
        return False
        
    # Garante que o contrato ativo esteja visível no Market Watch para receber ticks de leilão
    if not mt5.symbol_select(symbol, True):
        logging.error(f"[LEILÃO] Contrato '{symbol}' não pôde ser ativado no Market Watch.")
        mt5.shutdown()
        return False
        
    conta = mt5.account_info()
    if conta:
        logging.info(f"🔌 MT5 Conectado | Corretora: {conta.company} | Conta ID: {conta.login}")
    return True

def executar_monitoramento_leilao():
    # Inicializa os logs centralizados na pasta /logs do seu projeto
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"preco_teorico_WIN_V2.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()]
    )

    # Identificação dinâmica do contrato vigente para acabar com o hardcoding da V1
    symbol_alvo = descobrir_contrato_ativo_v2()
    
    logging.info("=" * 65)
    logging.info(f"🚀 MONITOR DE PREÇO TEÓRICO ATIVADO | CONTRATO: {symbol_alvo}")
    logging.info(f"🕒 Amostragem: {INTERVALO_SEGUNDOS}s | Alerta Sonoro: {'OK' if ALERTA_SONORO else 'OFF'}")
    logging.info("=" * 65)

    if not conectar_e_validar_mt5(symbol_alvo):
        return

    ultimo_teorico = None
    ja_alertou_leilao = False
    ciclos = 0

    try:
        while True:
            agora_time = datetime.now().time()
            ciclos += 1

            # Extrai as propriedades completas do ativo via chamadas estruturadas do MT5
            info_s = mt5.symbol_info(symbol_alvo)
            if info_s is None:
                logging.error(f"[ERRO] Falha crítica ao ler propriedades do ativo {symbol_alvo}")
                time.sleep(5)
                continue

            # Captura o preço teórico de leilão enviado pela B3
            teorico = getattr(info_s, "price_theoretical", 0.0) or 0.0
            bid = getattr(info_s, "bid", 0.0) or 0.0
            ask = getattr(info_s, "ask", 0.0) or 0.0
            last = getattr(info_s, "last", 0.0) or 0.0
            spread = round(ask - bid, 2) if (bid > 0 and ask > 0) else 0.0

            mudou = (teorico != ultimo_teorico)

            # ---- ENGINE DE ALERTA DE FORMAÇÃO DE GRADES ----
            if ALERTA_SONORO and teorico > 0:
                if ALERTA_APENAS_PRIMEIRA_VEZ:
                    if not ja_alertou_leilao:
                        tocar_alerta()
                        logging.info("🔔 [ALERTA] Início do Leilão Oficial! Primeiro preço teórico formado.")
                        ja_alertou_leilao = True
                else:
                    if mudou:
                        tocar_alerta()
                        logging.info(f"🔔 [MOVIMENTO] Preço Teórico Alterado ➔ {teorico:,.0f} pts")

            # Registro inteligente de logs no terminal para não inundar o console
            if mudou or (ciclos % 15 == 0):
                status_txt = "✅ LEILÃO ATIVO" if teorico > 0 else "⚖️ AGUARDANDO BOOK"
                logging.info(
                    f"{status_txt} | Teórico: {teorico:>8.0f} | "
                    f"Bid/Ask: {bid:.0f}/{ask:.0f} | Last: {last:.0f} | Spread: {spread}"
                )
                ultimo_teorico = teorico

            time.sleep(INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        logging.info("ℹ️ Monitoramento interrompido via teclado pelo operador (Ctrl+C).")
    except Exception as e:
        logging.error(f"❌ Falha inesperada na execução do monitor de leilão: {e}")
    finally:
        mt5.shutdown()
        logging.info("🔌 MetaTrader 5 desconectado de forma segura. Sessão encerrada.")

if __name__ == "__main__":
    # Força UTF-8 no terminal Windows para evitar quebras de caracteres nos emojis
    if sys.platform == "win32":
        try: sys.stdout.reconfigure(encoding="utf-8")
        except: pass
        
    executar_monitoramento_leilao()
