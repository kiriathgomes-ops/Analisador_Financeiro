"""
======================================================================
TESTE DE VENCIMENTO DOS CONTRATOS - MT5
======================================================================

Objetivo:
    Verificar se o MetaTrader 5 fornece corretamente a data de
    vencimento dos contratos futuros da B3.

IMPORTANTE:
    Este arquivo NÃO altera nenhum coletor.
    É apenas um teste/auditoria.

Data: 2026-08-16
======================================================================
"""

from datetime import datetime
import MetaTrader5 as mt5


# =====================================================================
# CONFIGURAÇÃO
# =====================================================================

PREFIXOS = [
    "WIN",
    "WDO",
    "DI1"
]


# =====================================================================
# FUNÇÕES
# =====================================================================

def formatar_data(timestamp):

    if not timestamp:
        return "NÃO INFORMADA"

    try:
        return datetime.fromtimestamp(
            timestamp
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    except Exception:
        return f"ERRO ({timestamp})"


def status_vencimento(timestamp):

    if not timestamp:
        return "⚠️ SEM DATA"

    try:

        data_expiracao = datetime.fromtimestamp(
            timestamp
        )

        agora = datetime.now()

        if data_expiracao < agora:

            return "❌ VENCIDO"

        return "✅ VIGENTE"

    except Exception:

        return "⚠️ ERRO"


# =====================================================================
# CONEXÃO
# =====================================================================

print()
print("=" * 70)
print("TESTE DE VENCIMENTO DOS CONTRATOS - MT5")
print("=" * 70)

print()

if not mt5.initialize():

    print("❌ FALHA AO INICIALIZAR MT5")
    print()
    print("Erro:")
    print(mt5.last_error())
    print()

    raise SystemExit


print("✅ MT5 conectado")

print(
    f"Versão: {mt5.version()}"
)

print()


# =====================================================================
# OBTÉM TODOS OS SÍMBOLOS
# =====================================================================

simbolos = mt5.symbols_get()

if simbolos is None:

    print("❌ Não foi possível obter os símbolos.")

    mt5.shutdown()

    raise SystemExit


print(
    f"Total de símbolos encontrados: "
    f"{len(simbolos)}"
)

print()


# =====================================================================
# ANALISA CADA PREFIXO
# =====================================================================

for prefixo in PREFIXOS:

    print()
    print("=" * 70)
    print(f"📌 {prefixo}")
    print("=" * 70)

    encontrados = []

    for simbolo in simbolos:

        nome = simbolo.name.upper()

        if not nome.startswith(prefixo):

            continue

        encontrados.append(
            simbolo
        )

    print(
        f"Símbolos encontrados: "
        f"{len(encontrados)}"
    )

    print()

    # ---------------------------------------------------------------
    # ORDENA POR NOME
    # ---------------------------------------------------------------

    encontrados.sort(
        key=lambda s: s.name
    )

    # ---------------------------------------------------------------
    # EXIBE
    # ---------------------------------------------------------------

    for simbolo in encontrados:

        nome = simbolo.name

        # -----------------------------------------------------------
        # Dados básicos
        # -----------------------------------------------------------

        try:

            info = mt5.symbol_info(
                nome
            )

        except Exception:

            info = None

        if info is None:

            print()
            print(
                f"❌ {nome}"
            )

            print(
                "   Não foi possível obter symbol_info."
            )

            continue

        # -----------------------------------------------------------
        # Vencimento
        # -----------------------------------------------------------

        expiration = getattr(
            info,
            "expiration_time",
            0
        )

        expiration_time = formatar_data(
            expiration
        )

        status = status_vencimento(
            expiration
        )

        # -----------------------------------------------------------
        # Volume
        # -----------------------------------------------------------

        try:

            volume = float(
                info.volume
            )

        except Exception:

            volume = 0.0

        # -----------------------------------------------------------
        # Bid / Ask / Last
        # -----------------------------------------------------------

        try:

            bid = float(
                info.bid
            )

        except Exception:

            bid = 0.0

        try:

            ask = float(
                info.ask
            )

        except Exception:

            ask = 0.0

        try:

            last = float(
                info.last
            )

        except Exception:

            last = 0.0

        # -----------------------------------------------------------
        # Selecionável
        # -----------------------------------------------------------

        selecionavel = getattr(
            info,
            "select",
            False
        )

        # -----------------------------------------------------------
        # Visível
        # -----------------------------------------------------------

        visivel = getattr(
            info,
            "visible",
            False
        )

        # -----------------------------------------------------------
        # Descrição
        # -----------------------------------------------------------

        descricao = getattr(
            info,
            "description",
            ""
        )

        # -----------------------------------------------------------
        # RESULTADO
        # -----------------------------------------------------------

        print()

        print(
            f"🔹 {nome}"
        )

        print(
            f"   Descrição: "
            f"{descricao}"
        )

        print(
            f"   Expiração: "
            f"{expiration_time}"
        )

        print(
            f"   Status: "
            f"{status}"
        )

        print(
            f"   Selecionável: "
            f"{selecionavel}"
        )

        print(
            f"   Visível: "
            f"{visivel}"
        )

        print(
            f"   Volume: "
            f"{volume}"
        )

        print(
            f"   Bid: "
            f"{bid}"
        )

        print(
            f"   Ask: "
            f"{ask}"
        )

        print(
            f"   Last: "
            f"{last}"
        )


# =====================================================================
# ENCERRAMENTO
# =====================================================================

print()
print("=" * 70)
print("TESTE FINALIZADO")
print("=" * 70)

mt5.shutdown()

print(
    "🔌 MT5 desconectado."
)

print()