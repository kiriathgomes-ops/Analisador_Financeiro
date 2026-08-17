import MetaTrader5 as mt5

print("=" * 70)
print("TESTE DE DADOS DO LEILÃO - WINFUT")
print("=" * 70)

if not mt5.initialize():
    print("❌ Falha ao inicializar MT5")
    print("Erro:", mt5.last_error())
    raise SystemExit

print("✅ MT5 conectado")
print("Versão:", mt5.version())

# ------------------------------------------------------------
# Procurar símbolos relacionados ao WIN
# ------------------------------------------------------------

simbolos = mt5.symbols_get()

if simbolos is None:
    print("❌ Não foi possível obter os símbolos")
    print("Erro:", mt5.last_error())
    mt5.shutdown()
    raise SystemExit

wins = []

for simbolo in simbolos:
    nome = simbolo.name.upper()

    if "WIN" in nome:
        wins.append(simbolo)

print()
print(f"🔎 Símbolos contendo WIN encontrados: {len(wins)}")

for simbolo in wins:
    print()
    print("-" * 70)
    print("Símbolo:", simbolo.name)
    print("Descrição:", simbolo.description)
    print("Visível:", simbolo.visible)
    print("Selecionável:", simbolo.select)

    # Seleciona o símbolo
    if mt5.symbol_select(simbolo.name, True):

        info = mt5.symbol_info(simbolo.name)

        if info:
            print("Bid:", info.bid)
            print("Ask:", info.ask)
            print("Last:", info.last)
            print("Volume:", info.volume)

            # Tenta obter preço teórico
            try:
                print("Preço teórico:", info.price_theoretical)
            except AttributeError:
                print("Preço teórico: propriedade não disponível")

        tick = mt5.symbol_info_tick(simbolo.name)

        if tick:
            print("Tick:")
            print("  Bid:", tick.bid)
            print("  Ask:", tick.ask)
            print("  Last:", tick.last)
            print("  Volume:", tick.volume)

print()
print("=" * 70)

mt5.shutdown()