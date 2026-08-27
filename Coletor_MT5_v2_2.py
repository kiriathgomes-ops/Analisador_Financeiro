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

    # Confirma se o terminal está de fato ligado à corretora
    terminal = mt5.terminal_info()
    conta = mt5.account_info()
    versao = mt5.version()

    conectado = bool(terminal and getattr(terminal, "connected", False))
    empresa = getattr(terminal, "company", None) if terminal else None

    print()
    print("🔌 MT5")
    print(f"   Versão: {versao}")
    print(f"   Empresa: {empresa}")
    print(f"   Conectado à corretora: {conectado}")
    if conta:
        print(f"   Conta: {getattr(conta, 'login', '?')}")

    if not conectado:
        print()
        print("⚠️ MT5 abriu, mas NÃO está conectado à corretora.")
        print("   Abra o terminal, faça login e tente de novo.")
        print("   Pipeline seguirá com cache, se houver.")
        try:
            mt5.shutdown()
        except Exception:
            pass
        return False

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
    Procura somente contratos reais do ativo (rápido).

    Estratégia (evita symbols_get() de toda a corretora, que trava no Windows):
      1) symbols_get(group="PREFIX*") se o broker suportar
      2) Candidatos por código de mês B3 (ex: WINV26, WDOU26, DI1F27)
      3) Fallback: varrer symbols_get() completo só se 1 e 2 falharem
    """

    terminal = mt5.terminal_info()
    if terminal is None or not getattr(terminal, "connected", False):
        print(f"   ⚠️ obter_contratos({prefixo}): MT5 sem conexão — abortando busca.")
        return []

    def _eh_contrato_valido(nome: str) -> bool:
        if not nome.startswith(prefixo):
            return False
        if "$" in nome or "@" in nome:
            return False
        # opções: C/P após o prefixo (heurística)
        resto = nome[len(prefixo):]
        if "C" in resto or "P" in resto:
            # DI1 e WIN usam letras de mês; letras de opção costumam vir no meio
            # Mantém filtro leve: se terminar com C/P + dígitos de strike, ignora
            if any(ch.isdigit() for ch in resto) and (resto.endswith("C") or resto.endswith("P")):
                return False
        return True

    def _monta_info(s) -> dict:
        nome = s.name
        data_expiracao = getattr(s, "expiration_time", 0) or 0
        if data_expiracao:
            try:
                data_expiracao = datetime.fromtimestamp(data_expiracao)
            except Exception:
                data_expiracao = None
        else:
            data_expiracao = None

        tick = mt5.symbol_info_tick(nome)
        if tick:
            volume = float(getattr(tick, "volume", 0) or 0)
            bid = float(getattr(tick, "bid", 0) or 0)
            ask = float(getattr(tick, "ask", 0) or 0)
            last = float(getattr(tick, "last", 0) or 0)
        else:
            volume = bid = ask = last = 0.0

        return {
            "nome": nome,
            "simbolo": s,
            "expiracao": data_expiracao,
            "volume": volume,
            "bid": bid,
            "ask": ask,
            "last": last,
        }

    contratos = []
    vistos = set()

    # ---- 1) Filtro por grupo (rápido) ----
    for group in (f"{prefixo}*", f"*{prefixo}*"):
        try:
            simbolos = mt5.symbols_get(group=group)
        except Exception:
            simbolos = None
        if not simbolos:
            continue
        print(f"   🔎 {prefixo}: {len(simbolos)} símbolos via group='{group}'")
        for s in simbolos:
            nome = s.name
            if nome in vistos or not _eh_contrato_valido(nome):
                continue
            vistos.add(nome)
            mt5.symbol_select(nome, True)
            contratos.append(_monta_info(s))
        if contratos:
            return contratos

    # ---- 2) Candidatos explícitos (mês B3 + ano) ----
    # Códigos de mês B3: F G H J K M N Q U V X Z
    meses = list("FGHJKMNQUVXZ")
    agora_dt = datetime.now()
    anos = [agora_dt.year % 100, (agora_dt.year + 1) % 100]
    candidatos = []
    for aa in anos:
        for m in meses:
            candidatos.append(f"{prefixo}{m}{aa:02d}")
    # Contínuos / genéricos comuns na Genial
    if prefixo == "WIN":
        candidatos.extend(["WIN$", "WINV26", "WINZ26"])
    elif prefixo == "WDO":
        candidatos.extend(["WDO$", "WDOU26", "WDOV26"])
    elif prefixo == "DI1":
        candidatos.extend(["DI1F27", "DI1F28", "DI1F29"])

    print(f"   🔎 {prefixo}: testando {len(candidatos)} candidatos diretos...")
    for nome in candidatos:
        if nome in vistos:
            continue
        info_s = mt5.symbol_info(nome)
        if info_s is None:
            continue
        if not _eh_contrato_valido(nome):
            continue
        vistos.add(nome)
        mt5.symbol_select(nome, True)
        contratos.append(_monta_info(info_s))

    if contratos:
        print(f"   ✅ {prefixo}: {len(contratos)} contratos via candidatos")
        return contratos

    # ---- 3) Fallback completo (pode ser lento) ----
    print(f"   ⏳ {prefixo}: fallback symbols_get() completo (pode demorar)...")
    simbolos = mt5.symbols_get()
    if simbolos is None:
        print(f"   ⚠️ symbols_get() retornou None (prefixo={prefixo})")
        return []

    for s in simbolos:
        nome = s.name
        if nome in vistos or not _eh_contrato_valido(nome):
            continue
        vistos.add(nome)
        mt5.symbol_select(nome, True)
        contratos.append(_monta_info(s))

    print(f"   ✅ {prefixo}: {len(contratos)} contratos via varredura completa")
    return contratos


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
    # OHLC D1 + fechamento anterior (para pivots / WIN_FUT / WDO_FUT)
    # ------------------------------------------------------------

    open_d1 = None
    high_d1 = None
    low_d1 = None
    close_d1 = None
    volume_d1 = None
    prev_close = None
    change_percent = None

    try:
        info = mt5.symbol_info(nome)
        if info is not None:
            prev_close = float(getattr(info, "session_close", 0) or 0) or None

        # copy_rates_from_pos: array ordenado do mais ANTIGO → mais RECENTE
        # rates[-1] = barra atual (hoje) | rates[-2] = dia anterior
        rates = mt5.copy_rates_from_pos(nome, mt5.TIMEFRAME_D1, 0, 3)
        if rates is not None and len(rates) > 0:
            r_atual = rates[-1]
            try:
                open_d1 = float(r_atual["open"])
                high_d1 = float(r_atual["high"])
                low_d1 = float(r_atual["low"])
                close_d1 = float(r_atual["close"])
                volume_d1 = (
                    float(r_atual["tick_volume"])
                    if "tick_volume" in r_atual.dtype.names
                    else None
                )
            except Exception:
                open_d1 = float(r_atual[1])
                high_d1 = float(r_atual[2])
                low_d1 = float(r_atual[3])
                close_d1 = float(r_atual[4])
                volume_d1 = float(r_atual[5]) if len(r_atual) > 5 else None

            # Fechamento anterior: session_close ou close da barra D1 anterior
            if (prev_close is None or prev_close <= 0) and len(rates) >= 2:
                r_ant = rates[-2]
                try:
                    prev_close = float(r_ant["close"])
                except Exception:
                    prev_close = float(r_ant[4])

        preco_ref = last if last > 0 else (close_d1 or 0)
        if prev_close and prev_close > 0 and preco_ref > 0:
            change_percent = round(((preco_ref / prev_close) - 1) * 100, 4)
    except Exception as e:
        print(f"   ⚠️ OHLC D1 ({nome}): {e}")

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

        # OHLC diário (pivots / WIN_FUT / WDO_FUT)
        "open": open_d1,
        "high": high_d1,
        "low": low_d1,
        "close": close_d1 if close_d1 else (last if last > 0 else None),
        "volume_d1": volume_d1,
        "prev_close": prev_close,
        "change_percent": change_percent,
        "session_close": prev_close,

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
    if high_d1 is not None:
        print(f"   D1 O/H/L/C: {open_d1} / {high_d1} / {low_d1} / {close_d1}")
    if prev_close:
        print(f"   Prev close: {prev_close} | var: {change_percent}%")

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
    Nunca deve travar o pipeline: se MT5 estiver offline, retorna None cedo.
    """
    if not conectar_mt5():
        return {
            "versao_coletor": "2.2",
            "timestamp": agora(),
            "mt5": {"conectado": False},
            "ativos": {},
            "status": "OFFLINE",
        }

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
            print(f"\n➡️  Coletando {nome_ativo} ({configuracao['descricao']})...")
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



