import MetaTrader5 as mt5

print("=" * 60)
print("TESTE DE CONEXÃO META TRADER 5")
print("=" * 60)

print("\nVersão do módulo:")
print(mt5.version())

print("\nTentando inicializar...")

if not mt5.initialize():
    print("❌ FALHA AO INICIALIZAR")
    print("Erro retornado pelo MT5:")
    print(mt5.last_error())
else:
    print("✅ MT5 INICIALIZADO COM SUCESSO")

    print("\nInformações do terminal:")
    print(mt5.terminal_info())

    print("\nInformações da conta:")
    print(mt5.account_info())

    mt5.shutdown()

print("=" * 60)
