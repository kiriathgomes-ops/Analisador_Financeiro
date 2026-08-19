# ================================================================
# COLETOR MT5 v2.2
# Mercado B3 - WINFUT / DI1
# ================================================================
#
# Descrição:
#   Coleta dados dos contratos futuros da B3 (WIN e DI1) via MetaTrader 5.
#   Seleciona dinamicamente o contrato principal com base no vencimento
#   mais próximo e maior volume, gerando arquivos JSON atuais e históricos.
#
#   Esta versão é integrada ao pipeline principal (Coletor.py) e substitui
#   a coleta anterior baseada em TradingView para os ativos B3.
#
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
    "WDO": {                     # <-- NOVO
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
    """
    Inicializa a conexão com o MetaTrader 5.
    Exibe status no console.
    """
    print("\n" + "=" * 70)
    print("🚀 INICIANDO COLETOR MT5 v2.2")
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
    """
    Retorna lista de contratos reais para o prefixo informado.
    Filtra símbolos sintéticos ($/@) e opções (C/P).
    Cada contrato contém nome, expiração, tick (bid/ask/last) e volume.
    """
    simbolos = mt5.symbols_get()
    if simbolos is None:
        return []

    contratos = []
    for s in simbolos:
        nome = s.name

        # Filtro: deve começar com o prefixo
        if not nome.startswith(prefixo):
            continue

        # Ignora símbolos sintéticos e opções
        if "$" in nome or "@" in nome:
            continue
        if "C" in nome[len(prefixo):] or "P" in nome[len(prefixo):]:
            continue

        # Garante que o símbolo está visível no Market Watch
        mt5.symbol_select(nome, True)

        # Obtém tick atual
        tick = mt5.symbol_info_tick(nome)
        volume = float(tick.volume) if tick and tick.volume else 0.0
        bid = float(tick.bid) if tick and tick.bid else 0.0
        ask = float(tick.ask) if tick and tick.ask else 0.0
        last = float(tick.last) if tick and tick.last else 0.0

        # Data de vencimento
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
    """
    Seleciona o contrato principal com base no vencimento mais próximo
    e, em caso de empate, o de maior volume.
    Retorna (contrato_principal, lista_de_contratos_validos).
    """
    contratos = obter_contratos(prefixo)
    agora_dt = datetime.now()

    # Filtra apenas contratos com expiração futura
    validos = [c for c in contratos if c["expiracao"] and c["expiracao"] > agora_dt]

    if not validos:
        return None, []

    # Ordenação: expiração mais próxima (ascendente) e volume decrescente
    validos.sort(key=lambda x: (x["expiracao"].timestamp(), -x["volume"]))

    return validos[0], validos

# ================================================================
# OBTENÇÃO DE PREÇO TEÓRICO
# ================================================================

def obter_preco_teorico(nome: str) -> float:
    """Retorna o preço teórico do contrato (se disponível)."""
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
    """Retorna os níveis de Book (Bids e Asks) para o contrato."""
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
# COLETA DE UM ATIVO
# ================================================================

def coletar_ativo(nome_ativo: str, configuracao: dict) -> dict:
    """
    Executa a coleta completa para um ativo (WIN ou DI1).
    Retorna dicionário com todos os dados (contrato, preços, book, etc.).
    """
    prefixo = configuracao["prefixo"]
    principal, contratos_validos = selecionar_contrato(prefixo)

    if principal is None:
        print(f"\n📌 {nome_ativo}")
        print("   ❌ Nenhum contrato vigente encontrado")
        return {"ativo": nome_ativo, "status": "sem_contrato"}

    nome = principal["nome"]
    mt5.symbol_select(nome, True)

    tick = mt5.symbol_info_tick(nome)
    if tick is None:
        print(f"\n📌 {nome_ativo}")
        print(f"   Contrato: {nome}")
        print("   ❌ Não foi possível obter tick")
        return {"ativo": nome_ativo, "status": "sem_tick", "contrato": nome}

    # Extrai preços
    bid = float(tick.bid or 0.0)
    ask = float(tick.ask or 0.0)
    last = float(tick.last or 0.0)
    volume = float(tick.volume or 0.0)

    spread = ask - bid if (bid > 0 and ask > 0) else None
    teorico = obter_preco_teorico(nome)
    book = obter_book(nome)

    # Lista de contratos vigentes para saída
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

    # Monta o dicionário de saída
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
        "vencimento": principal["expiracao"].isoformat() if principal["expiracao"] else None,
        "market_book": book,
        "contratos_vigentes": contratos_saida,
        "status": "OK",
    }

    # Exibe resumo no console
    print(f"\n📌 {nome_ativo}")
    print(f"   Contrato principal: {nome} (Venc: {principal['expiracao'].strftime('%Y-%m-%d')})")
    print("   Contratos vigentes:")
    for c in contratos_saida:
        print(f"      • {c['contrato']} | Volume: {c['volume']} | Venc: {c['expiracao'][:10] if c['expiracao'] else 'N/A'}")
    print(f"   Bid:    {bid}")
    print(f"   Ask:    {ask}")
    print(f"   Last:   {last}")
    print(f"   Volume: {volume}")
    print(f"   Spread: {spread}")
    print(f"   Preço teórico: {teorico if teorico is not None else '⚠️ indisponível'}")
    print(f"   Market Book: {'✅ ' + str(book['quantidade_niveis']) + ' níveis' if book['disponivel'] else '⚠️ indisponível/vazio'}")

    return dados

# ================================================================
# SALVAMENTO EM ARQUIVOS
# ================================================================

def salvar_json(dados: dict) -> str:
    """
    Salva os dados no arquivo atual (Dados_MT5_v2_2.json) e também
    em um arquivo histórico com timestamp no nome.
    Retorna o caminho do arquivo histórico.
    """
    # Arquivo atual (sobrescreve)
    with open(ARQUIVO_ATUAL, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

    # Arquivo histórico
    agora_dt = datetime.now()
    nome_historico = f"MT5_v2_2_{agora_dt.strftime('%Y%m%d_%H%M%S_%f')}.json"
    caminho_historico = os.path.join(HISTORICO_DIR, nome_historico)
    with open(caminho_historico, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

    return caminho_historico

# ================================================================
# FUNÇÃO PRINCIPAL (INTEGRAÇÃO COM PIPELINE)
# ================================================================

def executar_coleta_mt5_v2() -> dict:
    """Função chamada pelo pipeline principal (Coletor.py). Retorna os dados coletados."""
    if not conectar_mt5():
        return None

    try:
        timestamp = agora()
        print("\n" + "=" * 70)
        print("📊 COLETOR MT5 v2.2 (integração pipeline)")
        print("=" * 70)
        print(f"🕒 Coleta: {timestamp}")

        dados = {
            "versao_coletor": "2.2",
            "timestamp": timestamp,
            "mt5": {"conectado": True, "versao": mt5.version()},
            "ativos": {},
            "status": "OK",
        }

        for nome_ativo, config in ATIVOS.items():
            dados["ativos"][nome_ativo] = coletar_ativo(nome_ativo, config)

        print("\n" + "=" * 70)

        caminho_historico = salvar_json(dados)
        print("\n💾 Arquivo atual:", ARQUIVO_ATUAL)
        print("\n📚 Histórico:", caminho_historico)

        return dados

    except Exception as erro:
        print("\n❌ ERRO DURANTE A COLETA v2.2")
        print(f"   {erro}")
        return None

    finally:
        mt5.shutdown()
        print("\n🔌 MT5 desconectado.\n")

# ================================================================
# EXECUÇÃO DIRETA (TESTE)
# ================================================================

def main():
    executar_coleta_mt5_v2()

if __name__ == "__main__":
    main()