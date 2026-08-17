# ================================================================
# COLETOR MT5 v2.2
# Mercado B3 - WINFUT / WDO / DI1
#
# NÃO ALTERA OS COLETORES ANTERIORES
# ================================================================

import MetaTrader5 as mt5
import json
import os
from datetime import datetime


# ================================================================
# CONFIGURAÇÃO
# ================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
HISTORICO_DIR = os.path.join(COLETAS_DIR, "Historico_MT5")

ARQUIVO_ATUAL = os.path.join(
    COLETAS_DIR,
    "Dados_MT5_v2_2.json"
)

os.makedirs(COLETAS_DIR, exist_ok=True)
os.makedirs(HISTORICO_DIR, exist_ok=True)


# ================================================================
# ATIVOS
# ================================================================

ATIVOS = {
    "WIN": {
        "prefixo": "WIN",
        "descricao": "Mini Índice B3"
    },

    "WDO": {
        "prefixo": "WDO",
        "descricao": "Mini Dólar B3"
    },

    "DI1": {
        "prefixo": "DI1",
        "descricao": "DI Futuro B3"
    }
}


# ================================================================
# CONEXÃO MT5
# ================================================================

def conectar_mt5():

    print()
    print("=" * 70)
    print("🚀 INICIANDO COLETOR MT5 v2.2")
    print("=" * 70)

    if not mt5.initialize():

        print()
        print("❌ FALHA AO INICIALIZAR MT5")
        print("Erro:", mt5.last_error())

        return False

    versao = mt5.version()

    print()
    print("🔌 MT5")
    print("   Conectado: SIM")
    print("   Versão:", versao)

    return True


# ================================================================
# DATA/HORA
# ================================================================

def agora():

    return datetime.now().isoformat(timespec="milliseconds")


# ================================================================
# IDENTIFICAÇÃO DO CONTRATO
# ================================================================

def obter_contratos(prefixo):

    """
    Procura somente contratos reais do ativo.

    Exemplos aceitos:

        WINV26
        WINZ26

        WDOU26
        WDOV26

        DI1V26
        DI1F27

    Símbolos sintéticos como:

        WIN$
        WIN$D
        WIN$N
        WIN@
        WIN@D
        WIN@N

    são ignorados.
    """

    simbolos = mt5.symbols_get()

    if simbolos is None:
        return []

    contratos = []

    for s in simbolos:

        nome = s.name

        # --------------------------------------------------------
        # Prefixo
        # --------------------------------------------------------

        if not nome.startswith(prefixo):
            continue

        # --------------------------------------------------------
        # Ignora símbolos sintéticos
        # --------------------------------------------------------

        if "$" in nome:
            continue

        if "@" in nome:
            continue

        # --------------------------------------------------------
        # Ignora opções
        # --------------------------------------------------------

        if "C" in nome[len(prefixo):]:
            continue

        if "P" in nome[len(prefixo):]:
            continue

        # --------------------------------------------------------
        # Informações
        # --------------------------------------------------------

        info = {
            "nome": nome,
            "simbolo": s
        }

        # --------------------------------------------------------
        # Data de vencimento
        # --------------------------------------------------------

        data_expiracao = getattr(
            s,
            "expiration_time",
            0
        )

        if data_expiracao:

            try:

                data_expiracao = datetime.fromtimestamp(
                    data_expiracao
                )

            except Exception:

                data_expiracao = None

        else:

            data_expiracao = None

        info["expiracao"] = data_expiracao

        # --------------------------------------------------------
        # Tick
        # --------------------------------------------------------

        tick = mt5.symbol_info_tick(nome)

        if tick:

            info["volume"] = float(
                getattr(tick, "volume", 0) or 0
            )

            info["bid"] = float(
                getattr(tick, "bid", 0) or 0
            )

            info["ask"] = float(
                getattr(tick, "ask", 0) or 0
            )

            info["last"] = float(
                getattr(tick, "last", 0) or 0
            )

        else:

            info["volume"] = 0.0
            info["bid"] = 0.0
            info["ask"] = 0.0
            info["last"] = 0.0

        contratos.append(info)

    return contratos


# ================================================================
# SELECIONA CONTRATO PRINCIPAL
# ================================================================

def selecionar_contrato(prefixo):

    contratos = obter_contratos(prefixo)

    agora_dt = datetime.now()

    validos = []

    for c in contratos:

        expiracao = c["expiracao"]

        # --------------------------------------------------------
        # Sem data de vencimento
        # --------------------------------------------------------

        if expiracao is None:
            continue

        # --------------------------------------------------------
        # Contrato vencido
        # --------------------------------------------------------

        if expiracao <= agora_dt:
            continue

        # --------------------------------------------------------
        # Não considerar contratos sem mercado
        # --------------------------------------------------------

        if (
            c["bid"] <= 0
            and c["ask"] <= 0
            and c["last"] <= 0
        ):
            continue

        validos.append(c)

    # ------------------------------------------------------------
    # Ordenação
    #
    # Primeiro:
    #   contrato vigente
    #
    # Depois:
    #   maior volume
    #
    # ------------------------------------------------------------

    validos.sort(
        key=lambda x: (
            x["volume"],
            -x["expiracao"].timestamp()
        ),
        reverse=True
    )

    if not validos:

        return None, []

    principal = validos[0]

    return principal, validos


# ================================================================
# PREÇO TEÓRICO
# ================================================================

def obter_preco_teorico(nome):

    info = mt5.symbol_info(nome)

    if info is None:
        return None

    try:

        valor = getattr(
            info,
            "price_theoretical",
            None
        )

        if valor is None:
            return None

        valor = float(valor)

        if valor <= 0:
            return None

        return valor

    except Exception:

        return None


# ================================================================
# MARKET BOOK
# ================================================================

def obter_book(nome):

    resultado = {
        "disponivel": False,
        "quantidade_niveis": 0,
        "bids": [],
        "asks": []
    }

    try:

        # --------------------------------------------------------
        # Assina Market Book
        # --------------------------------------------------------

        if not mt5.market_book_add(nome):

            return resultado

        # --------------------------------------------------------
        # Obtém Book
        # --------------------------------------------------------

        book = mt5.market_book_get(nome)

        if not book:

            mt5.market_book_release(nome)

            return resultado

        resultado["disponivel"] = True

        for nivel in book:

            tipo = getattr(
                nivel,
                "type",
                None
            )

            preco = float(
                getattr(
                    nivel,
                    "price",
                    0
                ) or 0
            )

            volume = float(
                getattr(
                    nivel,
                    "volume",
                    0
                ) or 0
            )

            item = {
                "preco": preco,
                "volume": volume
            }

            # ----------------------------------------------------
            # Tipos do Market Book
            # ----------------------------------------------------

            if tipo == mt5.BOOK_TYPE_BUY:

                resultado["bids"].append(item)

            elif tipo == mt5.BOOK_TYPE_SELL:

                resultado["asks"].append(item)

        resultado["quantidade_niveis"] = len(book)

        mt5.market_book_release(nome)

    except Exception:

        try:
            mt5.market_book_release(nome)
        except Exception:
            pass

    return resultado


# ================================================================
# COLETA DE UM ATIVO
# ================================================================

def coletar_ativo(nome_ativo, configuracao):

    prefixo = configuracao["prefixo"]

    principal, contratos = selecionar_contrato(prefixo)

    if principal is None:

        print()
        print(f"📌 {nome_ativo}")
        print("   ❌ Nenhum contrato vigente encontrado")

        return {
            "ativo": nome_ativo,
            "status": "sem_contrato"
        }

    nome = principal["nome"]

    # ------------------------------------------------------------
    # Garantir símbolo selecionado
    # ------------------------------------------------------------

    mt5.symbol_select(nome, True)

    tick = mt5.symbol_info_tick(nome)

    if tick is None:

        print()
        print(f"📌 {nome_ativo}")
        print(f"   Contrato: {nome}")
        print("   ❌ Não foi possível obter tick")

        return {
            "ativo": nome_ativo,
            "status": "sem_tick",
            "contrato": nome
        }

    # ------------------------------------------------------------
    # Preços
    # ------------------------------------------------------------

    bid = float(
        getattr(tick, "bid", 0) or 0
    )

    ask = float(
        getattr(tick, "ask", 0) or 0
    )

    last = float(
        getattr(tick, "last", 0) or 0
    )

    volume = float(
        getattr(tick, "volume", 0) or 0
    )

    spread = None

    if bid > 0 and ask > 0:

        spread = ask - bid

    # ------------------------------------------------------------
    # Preço teórico
    # ------------------------------------------------------------

    teorico = obter_preco_teorico(nome)

    # ------------------------------------------------------------
    # Book
    # ------------------------------------------------------------

    book = obter_book(nome)

    # ------------------------------------------------------------
    # Contratos vigentes
    # ------------------------------------------------------------

    contratos_saida = []

    for c in contratos:

        contratos_saida.append({
            "contrato": c["nome"],
            "expiracao": (
                c["expiracao"].isoformat()
                if c["expiracao"]
                else None
            ),
            "volume": c["volume"],
            "bid": c["bid"],
            "ask": c["ask"],
            "last": c["last"]
        })

    # ------------------------------------------------------------
    # Resultado
    # ------------------------------------------------------------

    dados = {

        "ativo": nome_ativo,

        "descricao": configuracao["descricao"],

        "contrato_principal": nome,

        "timestamp": agora(),

        "bid": bid,

        "ask": ask,

        "last": last,

        "volume": volume,

        "spread": spread,

        "preco_teorico": teorico,

        "vencimento": (
            principal["expiracao"].isoformat()
            if principal["expiracao"]
            else None
        ),

        "market_book": book,

        "contratos_vigentes": contratos_saida,

        "status": "OK"
    }

    # ------------------------------------------------------------
    # Console
    # ------------------------------------------------------------

    print()
    print(f"📌 {nome_ativo}")
    print(f"   Contrato principal: {nome}")

    print()
    print("   Contratos vigentes:")

    for c in contratos_saida:

        print(
            f"      • {c['contrato']} | "
            f"Volume: {c['volume']}"
        )

    print()
    print(f"   Bid:    {bid}")
    print(f"   Ask:    {ask}")
    print(f"   Last:   {last}")
    print(f"   Volume: {volume}")
    print(f"   Spread: {spread}")

    if teorico is not None:

        print(
            f"   Preço teórico: {teorico}"
        )

    else:

        print(
            "   Preço teórico: "
            "⚠️ indisponível"
        )

    # ------------------------------------------------------------
    # Book
    # ------------------------------------------------------------

    if book["disponivel"]:

        print(
            "   Market Book: "
            f"✅ {book['quantidade_niveis']} níveis"
        )

    else:

        print(
            "   Market Book: "
            "⚠️ indisponível/vazio"
        )

    return dados


# ================================================================
# SALVAR JSON
# ================================================================

def salvar_json(dados):

    # ------------------------------------------------------------
    # Arquivo atual
    # ------------------------------------------------------------

    with open(
        ARQUIVO_ATUAL,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

    # ------------------------------------------------------------
    # Histórico
    # ------------------------------------------------------------

    agora_dt = datetime.now()

    nome_historico = (
        f"MT5_v2_2_"
        f"{agora_dt.strftime('%Y%m%d_%H%M%S_%f')}.json"
    )

    arquivo_historico = os.path.join(
        HISTORICO_DIR,
        nome_historico
    )

    with open(
        arquivo_historico,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

    return arquivo_historico


# ================================================================
# FUNÇÃO PARA INTEGRAÇÃO COM O PIPELINE (Coletor.py)
# ================================================================

def executar_coleta_mt5_v2():
    """
    Função principal para ser chamada pelo Coletor.py / pipeline.
    Retorna o dicionário completo dos dados coletados ou None em caso de falha.
    Também grava Dados_MT5_v2_2.json e o histórico.
    """
    if not conectar_mt5():
        return None

    try:
        timestamp = agora()

        print()
        print("=" * 70)
        print("📊 COLETOR MT5 v2.2 (integração pipeline)")
        print("=" * 70)
        print(f"🕒 Coleta: {timestamp}")

        dados = {
            "versao_coletor": "2.2",
            "timestamp": timestamp,
            "mt5": {
                "conectado": True,
                "versao": mt5.version()
            },
            "ativos": {},
            "status": "OK"
        }

        for nome_ativo, configuracao in ATIVOS.items():
            dados["ativos"][nome_ativo] = coletar_ativo(
                nome_ativo,
                configuracao
            )

        print()
        print("=" * 70)

        arquivo_historico = salvar_json(dados)

        print()
        print("💾 Arquivo atual:")
        print(f"   {ARQUIVO_ATUAL}")
        print()
        print("📚 Histórico:")
        print(f"   {arquivo_historico}")

        return dados

    except Exception as erro:
        print()
        print("❌ ERRO DURANTE A COLETA v2.2")
        print(f"   {erro}")
        return None

    finally:
        mt5.shutdown()
        print()
        print("🔌 MT5 desconectado.")
        print()


# ================================================================
# MAIN (execução direta)
# ================================================================

def main():
    executar_coleta_mt5_v2()


# ================================================================
# EXECUÇÃO
# ================================================================

if __name__ == "__main__":
    main()



