import MetaTrader5 as mt5
import time

print("=" * 70)
print("TESTE BOOK WINFUT - MONITORAMENTO")
print("=" * 70)

if not mt5.initialize():
    print("❌ Falha ao inicializar")
    print("Erro:", mt5.last_error())
    raise SystemExit

simbolo = "WINV26"

if not mt5.symbol_select(simbolo, True):
    print("❌ Falha ao selecionar", simbolo)
    mt5.shutdown()
    raise SystemExit

print("✅ MT5 conectado")
print("✅ Símbolo:", simbolo)

if not mt5.market_book_add(simbolo):
    print("❌ Falha ao assinar Market Book")
    print("Erro:", mt5.last_error())
    mt5.shutdown()
    raise SystemExit

print("✅ Market Book assinado")
print()
print("Aguardando dados...")
print()

for tentativa in range(10):

    time.sleep(1)

    book = mt5.market_book_get(simbolo)

    print(f"[{tentativa + 1}/10] ", end="")

    if book is None:
        print("None | erro:", mt5.last_error())

    elif len(book) == 0:
        print("Book vazio")

    else:

        print(f"{len(book)} registros")

        for item in book:

            print(
                f"   type={item.type} | "
                f"price={item.price:.2f} | "
                f"volume={item.volume}"
            )

        print()
        break

print()
print("=" * 70)

mt5.market_book_release(simbolo)
mt5.shutdown()