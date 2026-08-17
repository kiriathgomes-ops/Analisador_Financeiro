import MetaTrader5 as mt5
import time
import csv
from datetime import datetime
from pathlib import Path


# ============================================================
# CONFIGURAÇÃO
# ============================================================

SIMBOLO = "WINV26"

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO = BASE_DIR / "Coletas" / "Monitor_Leilao_WIN.csv"

ARQUIVO.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# INICIALIZAÇÃO
# ============================================================

print("=" * 80)
print("MONITOR DE LEILÃO - WINFUT")
print("=" * 80)

if not mt5.initialize():
    print("❌ Falha ao inicializar MT5")
    print("Erro:", mt5.last_error())
    raise SystemExit

print("✅ MT5 conectado")

if not mt5.symbol_select(SIMBOLO, True):
    print(f"❌ Não foi possível selecionar {SIMBOLO}")
    print("Erro:", mt5.last_error())
    mt5.shutdown()
    raise SystemExit

print(f"✅ Símbolo: {SIMBOLO}")
print()
print("Monitorando...")
print("Pressione CTRL+C para encerrar.")
print()


# ============================================================
# CSV
# ============================================================

novo_arquivo = not ARQUIVO.exists()

arquivo_csv = open(
    ARQUIVO,
    "a",
    newline="",
    encoding="utf-8"
)

writer = csv.writer(arquivo_csv)

if novo_arquivo:
    writer.writerow([
        "timestamp",
        "symbol",
        "bid",
        "ask",
        "last",
        "volume",
        "price_theoretical"
    ])


# ============================================================
# MONITORAMENTO
# ============================================================

try:

    while True:

        info = mt5.symbol_info(SIMBOLO)

        if info is None:
            print("⚠️ symbol_info retornou None")
            time.sleep(1)
            continue

        agora = datetime.now().isoformat()

        bid = info.bid
        ask = info.ask
        last = info.last
        volume = info.volume

        try:
            teorico = info.price_theoretical
        except AttributeError:
            teorico = None

        writer.writerow([
            agora,
            SIMBOLO,
            bid,
            ask,
            last,
            volume,
            teorico
        ])

        arquivo_csv.flush()

        print(
            f"{agora} | "
            f"Last={last:.0f} | "
            f"Bid={bid:.0f} | "
            f"Ask={ask:.0f} | "
            f"Vol={volume} | "
            f"Teórico={teorico}"
        )

        time.sleep(1)

except KeyboardInterrupt:

    print()
    print("🛑 Monitor encerrado pelo usuário.")

finally:

    arquivo_csv.close()
    mt5.shutdown()

    print()
    print(f"📁 Dados salvos em:")
    print(ARQUIVO)

    print("=" * 80)