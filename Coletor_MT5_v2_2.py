# ================================================================
# COLETOR MT5 v2.2 (Atualizado com Open, High, Low, Close e Prev Close)
# Mercado B3 - WINFUT / DI1 / WDO
# ================================================================

import json
import os
from datetime import datetime

import MetaTrader5 as mt5

# ================================================================
# CONFIGURAÇÃO DE DIRETÓRIOS
# ================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
HISTORICO_DIR = os.path.join(COLETAS_DIR, "Historico_MT5")

ARQUIVO_ATUAL = os.path.join(COLETAS_DIR, "Dados_MT5_v2_2.json")

os.makedirs(COLETAS_DIR, exist_ok=True)
os.makedirs(HISTORICO_DIR, exist_ok=True)

# ================================================================
# ATIVOS SUPORTADOS
# ================================================================

ATIVOS = {
    "WIN": {
        "prefixo": "WIN",
        "descricao": "Mini Índice B3",
    },
    "DI1": {
        "prefixo": "DI1",
        "descricao": "DI Futuro B3",
    },
    "WDO": {
        "prefixo": "WDO",
        "descricao": "Mini Dólar Futuro B3",
    },
}

# ================================================================
# UTILITÁRIOS DE DATA/HORA
# ================================================================

def agora() -> str:
    """Retorna timestamp atual no formato ISO com milissegundos."""
    return datetime.now().isoformat(timespec="milliseconds")

# ================================================================
# CONEXÃO COM MT5
# ================================================================

def conectar_mt5() -> bool:
    """Inicializa a conexão com o MetaTrader 5."""
    print("\n" + "=" * 70)
    print("🚀 INICIANDO COLETOR MT5 v2.2 (OHLC Direct)")
    print("=" * 70)

    if not mt5.initialize():
        print("\n❌ FALHA AO INICIALIZAR MT5")
        print("Erro:", mt5.last_error())
        return False

    versao = mt5.version()
    print("\n🔌 MT5")
    print("   Conectado: SIM")
    print("   Versão:", versao)
    return True

# ================================================================
# OBTENÇÃO DE CONTRATOS VÁLIDOS
# ================================================================

def obter_contratos(prefixo: str) -> list:
    simbolos = mt5.symbols_get()
    if simbolos is None:
        return []

    contratos = []
    for s in simbolos:
        nome = s.name

        if not nome.startswith(prefixo):
            continue

        if "$" in nome or "@" in nome:
            continue
        if "C" in nome[len(prefixo):] or "P" in nome[len(prefixo):]:
            continue

        mt5.symbol_select(nome, True)

        tick = mt5.symbol_info_tick(nome)
        volume = float(tick.volume) if tick and tick.volume else 0.0
        bid = float(tick.bid) if tick and tick.bid else 0.0
        ask = float(tick.ask) if tick and tick.ask else 0.0
        last = float(tick.last) if tick and tick.last else 0.0

        expiracao = getattr(s, "expiration_time", 0)
        if expiracao:
            try:
                expiracao = datetime.fromtimestamp(expiracao)
            except Exception:
                expiracao = None
        else:
            expiracao = None

        contratos.append({
            "nome": nome,
            "simbolo": s,
            "expiracao": expiracao,
            "volume": volume,
            "bid": bid,
            "ask": ask,
            "last": last,
        })

    return contratos

# ================================================================
# SELEÇÃO DO CONTRATO PRINCIPAL
# ================================================================

def selecionar_contrato(prefixo: str) -> tuple:
    contratos = obter_contratos(prefixo)
    agora_dt = datetime.now()

    validos = [c for c in contratos if c["expiracao"] and c["expiracao"] > agora_dt]

    if not validos:
        return None, []

    validos.sort(key=lambda x: (x["expiracao"].timestamp(), -x["volume"]))

    return validos[0], validos

# ================================================================
# OBTENÇÃO DE PREÇO TEÓRICO
# ================================================================

def obter_preco_teorico(nome: str) -> float:
    info = mt5.symbol_info(nome)
    if info is None:
        return None
    try:
        valor = float(getattr(info, "price_theoretical", 0.0))
        return valor if valor > 0 else None
    except Exception:
        return None

# ================================================================
# OBTENÇÃO DO MARKET BOOK
# ================================================================

def obter_book(nome: str) -> dict:
    resultado = {
        "disponivel": False,
        "quantidade_niveis": 0,
        "bids": [],
        "asks": [],
    }

    try:
        if not mt5.market_book_add(nome):
            return resultado

        book = mt5.market_book_get(nome)
        if not book:
            mt5.market_book_release(nome)
            return resultado

        resultado["disponivel"] = True
        for nivel in book:
            tipo = getattr(nivel, "type", None)
            preco = float(getattr(nivel, "price", 0.0))
            volume = float(getattr(nivel, "volume", 0.0))
            item = {"preco": preco, "volume": volume}

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
# COLETA DE UM ATIVO (COM OHLC INTEGRADO)
# ================================================================

def coletar_ativo(nome_ativo: str, configuracao: dict) -> dict:
    prefixo = configuracao["prefixo"]
    principal, contratos_validos = selecionar_contrato(prefixo)

    if principal is None:
        print(f"\n📌 {nome_ativo}")
        print("   ❌ Nenhum contrato vigente encontrado")
        return {"ativo": nome_ativo, "status": "sem_contrato"}

    nome = principal["nome"]
    mt5.symbol_select(nome, True)

    tick = mt5.symbol_info_tick(nome)
    info_symbol = mt5.symbol_info(nome)

    if tick is None or info_symbol is None:
        print(f"\n📌 {nome_ativo}")
        print(f"   Contrato: {nome}")
        print("   ❌ Não foi possível obter tick ou informações do símbolo")
        return {"ativo": nome_ativo, "status": "sem_tick", "contrato": nome}

    # Preços de book/tick
    bid = float(tick.bid or 0.0)
    ask = float(tick.ask or 0.0)
    last = float(tick.last or 0.0)
    volume = float(tick.volume or 0.0)

    # Extração das barras diárias para Abertura, Máxima, Mínima e Volume do dia
    rates = mt5.copy_rates_from_pos(nome, mt5.TIMEFRAME_D1, 0, 1)
    
    open_val = float(rates[0][1]) if rates is not None and len(rates) > 0 else None
    high_val = float(rates[0][2]) if rates is not None and len(rates) > 0 else None
    low_val = float(rates[0][3]) if rates is not None and len(rates) > 0 else None
    
    # Preço do fechamento anterior
    prev_close = float(getattr(info_symbol, "session_close", 0.0))
    
    # Variações
    spread = ask - bid if (bid > 0 and ask > 0) else None
    var_abs = round(last - prev_close, 2) if prev_close > 0 else 0.0
    var_pct = round(((last / prev_close) - 1) * 100, 2) if prev_close > 0 else 0.0

    teorico = obter_preco_teorico(nome)
    book = obter_book(nome)

    contratos_saida = []
    for c in contratos_validos:
        contratos_saida.append({
            "contrato": c["nome"],
            "expiracao": c["expiracao"].isoformat() if c["expiracao"] else None,
            "volume": c["volume"],
            "bid": c["bid"],
            "ask": c["ask"],
            "last": c["last"],
        })

    # Monta o dicionário de saída expandido
    dados = {
        "ativo": nome_ativo,
        "descricao": configuracao["descricao"],
        "contrato_principal": nome,
        "timestamp": agora(),
        "bid": bid,
        "ask": ask,
        "last": last,
        "open": open_val,
        "high": high_val,
        "low": low_val,
        "session_close": prev_close,
        "change_percent": var_pct,
        "change_abs": var_abs,
        "volume": volume,
        "spread": spread,
        "preco_teorico": teorico,
        "vencimento": principal["expiracao"].isoformat() if principal["expiracao"] else None,
        "market_book": book,
        "contratos_vigentes": contratos_saida,
        "status": "OK",
    }

    # Console output
    print(f"\n📌 {nome_ativo} ({nome})")
    print(f"   Open:   {open_val}")
    print(f"   High:   {high_val}")
    print(f"   Low:    {low_val}")
    print(f"   Last:   {last}")
    print(f"   Prev C: {prev_close}")
    print(f"   Var %:  {var_pct}%")

    return dados

# ================================================================
# SALVAMENTO EM ARQUIVOS
# ================================================================

def salvar_json(dados: dict) -> str:
    with open(ARQUIVO_ATUAL, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

    agora_dt = datetime.now()
    nome_historico = f"MT5_v2_2_{agora_dt.strftime('%Y%m%d_%H%M%S_%f')}.json"
    caminho_historico = os.path.join(HISTORICO_DIR, nome_historico)
    with open(caminho_historico, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

    return caminho_historico

# ================================================================
# FUNÇÃO PRINCIPAL
# ================================================================

def executar_coleta_mt5_v2() -> dict:
    if not conectar_mt5():
        return None

    try:
        timestamp = agora()
        dados = {
            "versao_coletor": "2.2",
            "timestamp": timestamp,
            "mt5": {"conectado": True, "versao": mt5.version()},
            "ativos": {},
            "status": "OK",
        }

        for nome_ativo, config in ATIVOS.items():
            dados["ativos"][nome_ativo] = coletar_ativo(nome_ativo, config)

        caminho_historico = salvar_json(dados)
        return dados

    except Exception as erro:
        print(f"\n❌ ERRO DURANTE A COLETA v2.2: {erro}")
        return None

    finally:
        mt5.shutdown()
        print("\n🔌 MT5 desconectado.\n")

if __name__ == "__main__":
    executar_coleta_mt5_v2()