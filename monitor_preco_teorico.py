import MetaTrader5 as mt5
import time
from datetime import datetime, time as dt_time
import logging
from pathlib import Path
import sys

# ==================== CONFIGURAÇÕES ====================
SYMBOL = "WINV26"                    # Altere para o contrato vigente
INTERVALO_SEGUNDOS = 2
LOG_DIR = Path("logs")
HORARIO_INICIO_LEILAO = dt_time(8, 50)
HORARIO_FIM_LEILAO = dt_time(9, 15)

# Alerta
ALERTA_SONORO = True                 # True = ativa o bip
ALERTA_APENAS_PRIMEIRA_VEZ = True    # True = alerta só quando sai de 0 pela 1ª vez
# =======================================================

def configurar_logging():
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"preco_teorico_{SYMBOL}_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    logging.info(f"Log iniciado → {log_file}")
    return log_file

def tocar_alerta():
    """Emite um alerta sonoro (funciona no Windows e na maioria dos terminais)."""
    try:
        # Windows
        import winsound
        winsound.Beep(1000, 400)   # frequência 1000 Hz, duração 400 ms
        time.sleep(0.15)
        winsound.Beep(1400, 400)
    except ImportError:
        # Linux / Mac / fallback
        print("\a")                # bell character
        sys.stdout.write("\a")
        sys.stdout.flush()

def dentro_horario_leilao():
    agora = datetime.now().time()
    return HORARIO_INICIO_LEILAO <= agora <= HORARIO_FIM_LEILAO

def conectar_mt5():
    if not mt5.initialize():
        logging.error(f"Falha ao inicializar MT5: {mt5.last_error()}")
        return False

    conta = mt5.account_info()
    if conta:
        logging.info(f"Conectado | Conta: {conta.login} | Corretora: {conta.company}")
    else:
        logging.warning("Conectado, mas não foi possível obter dados da conta")

    if not mt5.symbol_select(SYMBOL, True):
        logging.error(f"Não foi possível selecionar o símbolo {SYMBOL}")
        return False

    return True

def coletar_preco_teorico():
    info = mt5.symbol_info(SYMBOL)
    if info is None:
        logging.error(f"Símbolo {SYMBOL} não encontrado")
        return None

    return {
        "timestamp": datetime.now(),
        "teorico": info.price_theoretical,
        "bid": info.bid,
        "ask": info.ask,
        "last": info.last,
        "spread": round(info.ask - info.bid, 2) if info.bid and info.ask else None
    }

def main():
    log_file = configurar_logging()
    logging.info("=" * 65)
    logging.info(f"Monitor de Preço Teórico iniciado | Símbolo: {SYMBOL}")
    logging.info(f"Intervalo: {INTERVALO_SEGUNDOS}s | Janela: {HORARIO_INICIO_LEILAO} → {HORARIO_FIM_LEILAO}")
    logging.info(f"Alerta sonoro: {'ATIVADO' if ALERTA_SONORO else 'DESATIVADO'}")
    logging.info("=" * 65)

    if not conectar_mt5():
        logging.error("Encerrando por falha de conexão")
        return

    ultimo_teorico = None
    ja_alertou = False
    contador = 0

    try:
        while True:
            agora = datetime.now()

            if not dentro_horario_leilao():
                logging.info(f"Fora do horário de leilão ({agora.strftime('%H:%M:%S')}). Aguardando...")
                time.sleep(30)
                continue

            dados = coletar_preco_teorico()
            contador += 1

            if dados is None:
                time.sleep(INTERVALO_SEGUNDOS)
                continue

            teorico = dados["teorico"]
            mudou = teorico != ultimo_teorico

            # ---- ALERTA ----
            if ALERTA_SONORO and teorico > 0:
                if ALERTA_APENAS_PRIMEIRA_VEZ:
                    if not ja_alertou:
                        tocar_alerta()
                        logging.info("🔔 ALERTA: Preço teórico detectado pela primeira vez!")
                        ja_alertou = True
                else:
                    # Alerta sempre que o valor mudar e for > 0
                    if mudou:
                        tocar_alerta()
                        logging.info(f"🔔 ALERTA: Preço teórico alterado → {teorico:.2f}")

            # Log (sempre que mudar ou a cada 10 ciclos)
            if mudou or contador % 10 == 0:
                status = "✅ TEÓRICO DISPONÍVEL" if teorico > 0 else "❌ TEÓRICO ZERADO"
                logging.info(
                    f"{status} | Teórico: {teorico:>10.2f} | "
                    f"Bid: {dados['bid']:>10.2f} | Ask: {dados['ask']:>10.2f} | "
                    f"Last: {dados['last']:>10.2f} | Spread: {dados['spread']}"
                )
                ultimo_teorico = teorico

            time.sleep(INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        logging.info("Monitor interrompido pelo usuário (Ctrl+C)")
    except Exception as e:
        logging.exception(f"Erro inesperado: {e}")
    finally:
        mt5.shutdown()
        logging.info("Conexão MT5 encerrada")
        logging.info(f"Log completo salvo em: {log_file}")

if __name__ == "__main__":
    main()