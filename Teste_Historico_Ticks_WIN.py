import MetaTrader5 as mt5
from datetime import datetime, timedelta

print("=" * 70)
print("TESTE HISTÓRICO DE TICKS - WINFUT")
print("=" * 70)

if not mt5.initialize():
    print("❌ Falha ao inicializar MT5")
    print("Erro:", mt5.last_error())
    raise SystemExit

simbolo = "WINV26"

if not mt5.symbol_select(simbolo, True):
    print(f"❌ Não foi possível selecionar {simbolo}")
    mt5.shutdown()
    raise SystemExit

print(f"✅ MT5 conectado")
print(f"✅ Símbolo: {simbolo}")

# Últimos 7 dias
fim = datetime.now()
inicio = fim - timedelta(days=7)

print()
print(f"Buscando ticks:")
print(f"Início: {inicio}")
print(f"Fim:    {fim}")
print()

ticks = mt5.copy_ticks_range(
    simbolo,
    inicio,
    fim,
    mt5.COPY_TICKS_ALL
)

if ticks is None:
    print("❌ Nenhum dado retornado")
    print("Erro:", mt5.last_error())

elif len(ticks) == 0:
    print("⚠️ Nenhum tick encontrado")

else:
    print(f"✅ Ticks encontrados: {len(ticks):,}")

    primeiro = ticks[0]
    ultimo = ticks[-1]

    print()
    print("Primeiro tick:")
    print(primeiro)

    print()
    print("Último tick:")
    print(ultimo)

print()
print("=" * 70)

mt5.shutdown()