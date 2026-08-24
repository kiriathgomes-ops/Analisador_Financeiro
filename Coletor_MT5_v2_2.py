# ================================================================
# COLETOR MT5 v2.3
# Mercado B3 - WIN / WDO / DI1
#
# Melhorias vs 2.2:
#   - 1 conexão reutilizável (Coletor.py não reconecta para ações)
#   - retry de initialize (terminal ocupado)
#   - login opcional via .env (MT5_LOGIN / MT5_PASSWORD / MT5_SERVER)
#   - contrato: liquidez (volume) no vencimento da frente; fallback PREFIXO$
#   - last: last > mid(bid,ask) > teórico
#   - prev_close: session_close ou D1[-2]
#   - idade do tick (stale)
#   - book opcional (MT5_COLETAR_BOOK=1)
#   - histórico rotativo (máx. 288 arquivos ≈ 24h @ 5 min)
#   - status PARCIAL se um ativo falhar (não zera o JSON inteiro)
# ================================================================

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Optional

try:
    import MetaTrader5 as mt5
    MT5_OK = True
except ImportError:
    mt5 = None
    MT5_OK = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
HISTORICO_DIR = os.path.join(COLETAS_DIR, "Historico_MT5")
ARQUIVO_ATUAL = os.path.join(COLETAS_DIR, "Dados_MT5_v2_2.json")

os.makedirs(COLETAS_DIR, exist_ok=True)
os.makedirs(HISTORICO_DIR, exist_ok=True)

VERSAO = "2.3"
MAX_HISTORICO = 288  # 24h se o pipeline roda a cada 5 min
TICK_STALE_SEG = 120  # tick com mais de 2 min = aviso

ATIVOS = {
    "WIN": {"prefixo": "WIN", "descricao": "Mini Índice B3"},
    "WDO": {"prefixo": "WDO", "descricao": "Mini Dólar Futuro B3"},
    "DI1": {"prefixo": "DI1", "descricao": "DI Futuro B3"},
}

# Letras de vencimento B3 (evita filtrar C/P de forma ingênua)
MESES_B3 = set("FGHJKMNQUVXZ")


def agora() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def _f(v, default=0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


# ----------------------------------------------------------------
# Conexão
# ----------------------------------------------------------------

_CONECTADO = False


def conectar_mt5(tentativas: int = 3) -> bool:
    """Anexa ao terminal já aberto, ou faz login se houver credenciais no env."""
    global _CONECTADO
    if not MT5_OK:
        print("❌ MetaTrader5 não instalado (pip install MetaTrader5)")
        return False

    if _CONECTADO:
        info = mt5.terminal_info()
        if info is not None:
            return True

    print("\n" + "=" * 70)
    print(f"INICIANDO COLETOR MT5 v{VERSAO}")
    print("=" * 70)

    login = os.getenv("MT5_LOGIN")
    password = os.getenv("MT5_PASSWORD")
    server = os.getenv("MT5_SERVER")
    path = os.getenv("MT5_PATH")  # opcional: caminho do terminal64.exe

    kwargs: dict[str, Any] = {}
    if path:
        kwargs["path"] = path
    if login and password and server:
        try:
            kwargs["login"] = int(login)
        except ValueError:
            print("⚠️ MT5_LOGIN inválido — tentando anexar ao terminal aberto")
        else:
            kwargs["password"] = password
            kwargs["server"] = server

    ultimo_erro = None
    for i in range(1, tentativas + 1):
        ok = mt5.initialize(**kwargs) if kwargs else mt5.initialize()
        if ok:
            _CONECTADO = True
            versao = mt5.version()
            term = mt5.terminal_info()
            print(f"MT5 conectado (tentativa {i}/{tentativas})")
            print(f"   Versão: {versao}")
            if term:
                print(f"   Empresa: {getattr(term, 'company', '')}")
                print(f"   Conectado à corretora: {getattr(term, 'connected', None)}")
            return True
        ultimo_erro = mt5.last_error()
        print(f"⚠️ initialize falhou ({i}/{tentativas}): {ultimo_erro}")
        try:
            mt5.shutdown()
        except Exception:
            pass

    print(f"❌ FALHA AO INICIALIZAR MT5: {ultimo_erro}")
    _CONECTADO = False
    return False


def desconectar_mt5() -> None:
    global _CONECTADO
    if not MT5_OK:
        return
    try:
        mt5.shutdown()
    except Exception:
        pass
    _CONECTADO = False
    print("\nMT5 desconectado.\n")


# ----------------------------------------------------------------
# Contratos
# ----------------------------------------------------------------

def _eh_opcao(nome: str, prefixo: str) -> bool:
    resto = nome[len(prefixo):]
    if "C" in resto and any(ch.isdigit() for ch in resto):
        # WINQ26C... opções; WINQ26 não
        # Heurística: C ou P seguido de strike (dígitos depois de C/P no meio)
        if "C" in resto[1:] or "P" in resto[1:]:
            return True
    return False


def _eh_futuro_datado(nome: str, prefixo: str) -> bool:
    """WINQ26, WDOV26, DI1F27 — prefixo + mês B3 + ano."""
    if not nome.startswith(prefixo):
        return False
    if "$" in nome or "@" in nome:
        return False
    resto = nome[len(prefixo):]
    if not resto:
        return False
    if _eh_opcao(nome, prefixo):
        return False
    # DI1F27 / WINQ26
    letra = resto[0]
    return letra in MESES_B3 or resto[:1].isalpha()


def obter_contratos(prefixo: str) -> list:
    if not MT5_OK:
        return []
    grupo = f"{prefixo}*"
    simbolos = mt5.symbols_get(group=grupo)
    if not simbolos:
        simbolos = mt5.symbols_get()
    if not simbolos:
        return []

    contratos = []
    agora_dt = datetime.now()
    for s in simbolos:
        nome = s.name
        if not nome.startswith(prefixo):
            continue
        if "$" in nome or "@" in nome:
            continue
        if not _eh_futuro_datado(nome, prefixo):
            continue

        mt5.symbol_select(nome, True)
        tick = mt5.symbol_info_tick(nome)
        volume = _f(tick.volume) if tick else 0.0
        bid = _f(tick.bid) if tick else 0.0
        ask = _f(tick.ask) if tick else 0.0
        last = _f(tick.last) if tick else 0.0

        expiracao = getattr(s, "expiration_time", 0) or 0
        exp_dt = None
        if expiracao:
            try:
                exp_dt = datetime.fromtimestamp(expiracao)
            except Exception:
                exp_dt = None

        if exp_dt and exp_dt <= agora_dt:
            continue

        contratos.append({
            "nome": nome,
            "expiracao": exp_dt,
            "volume": volume,
            "bid": bid,
            "ask": ask,
            "last": last,
            "liquidez": volume + (1.0 if last > 0 else 0.0) + (1.0 if bid > 0 and ask > 0 else 0.0),
        })
    return contratos


def _tentar_continuo(prefixo: str) -> Optional[dict]:
    """Fallback WIN$ / WDO$ quando a corretora não lista o datado."""
    nome = f"{prefixo}$"
    if not mt5.symbol_select(nome, True):
        return None
    tick = mt5.symbol_info_tick(nome)
    if tick is None:
        return None
    last = _f(tick.last)
    bid = _f(tick.bid)
    ask = _f(tick.ask)
    if last <= 0 and bid <= 0 and ask <= 0:
        return None
    return {
        "nome": nome,
        "expiracao": None,
        "volume": _f(tick.volume),
        "bid": bid,
        "ask": ask,
        "last": last,
        "liquidez": 0,
    }


def selecionar_contrato(prefixo: str) -> tuple:
    """
    Frente líquida: entre os 2 vencimentos mais próximos, pega o de maior volume.
    Se não houver datado, tenta PREFIXO$.
    """
    contratos = obter_contratos(prefixo)
    if not contratos:
        cont = _tentar_continuo(prefixo)
        return (cont, []) if cont else (None, [])

    com_exp = [c for c in contratos if c["expiracao"]]
    com_exp.sort(key=lambda x: x["expiracao"].timestamp())
    frente = com_exp[:2] if com_exp else contratos[:2]
    frente.sort(key=lambda x: -x["liquidez"])
    principal = frente[0]
    # lista vigente ordenada por vencimento
    vigentes = com_exp if com_exp else contratos
    vigentes.sort(key=lambda x: (x["expiracao"].timestamp() if x["expiracao"] else 9e18, -x["volume"]))
    return principal, vigentes


def obter_preco_teorico(nome: str) -> Optional[float]:
    info = mt5.symbol_info(nome)
    if info is None:
        return None
    try:
        valor = float(getattr(info, "price_theoretical", 0.0) or 0.0)
        return valor if valor > 0 else None
    except Exception:
        return None


def obter_book(nome: str) -> dict:
    resultado = {
        "disponivel": False,
        "quantidade_niveis": 0,
        "bids": [],
        "asks": [],
    }
    if os.getenv("MT5_COLETAR_BOOK", "0") not in ("1", "true", "True", "yes"):
        return resultado
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
            item = {
                "preco": _f(getattr(nivel, "price", 0.0)),
                "volume": _f(getattr(nivel, "volume", 0.0)),
            }
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


def _ohlc_d1(nome: str) -> dict:
    out = {"open": None, "high": None, "low": None, "close": None, "prev_close_d1": None}
    rates = mt5.copy_rates_from_pos(nome, mt5.TIMEFRAME_D1, 0, 2)
    if rates is None or len(rates) == 0:
        return out
    r0 = rates[0]
    try:
        out["open"] = float(r0["open"])
        out["high"] = float(r0["high"])
        out["low"] = float(r0["low"])
        out["close"] = float(r0["close"])
    except Exception:
        out["open"] = float(r0[1])
        out["high"] = float(r0[2])
        out["low"] = float(r0[3])
        out["close"] = float(r0[4])
    if len(rates) > 1:
        r1 = rates[1]
        try:
            out["prev_close_d1"] = float(r1["close"])
        except Exception:
            out["prev_close_d1"] = float(r1[4])
    return out


def _preco_last(tick, teorico: Optional[float]) -> tuple[float, str]:
    last = _f(tick.last)
    if last > 0:
        return last, "last"
    bid, ask = _f(tick.bid), _f(tick.ask)
    if bid > 0 and ask > 0:
        return round((bid + ask) / 2.0, 2), "mid_bid_ask"
    if bid > 0:
        return bid, "bid"
    if ask > 0:
        return ask, "ask"
    if teorico and teorico > 0:
        return float(teorico), "teorico"
    return 0.0, "vazio"


def coletar_ativo(nome_ativo: str, configuracao: dict) -> dict:
    prefixo = configuracao["prefixo"]
    principal, contratos_validos = selecionar_contrato(prefixo)

    if principal is None:
        print(f"\n{nome_ativo}: nenhum contrato vigente")
        return {"ativo": nome_ativo, "status": "sem_contrato"}

    nome = principal["nome"]
    mt5.symbol_select(nome, True)
    tick = mt5.symbol_info_tick(nome)
    info_symbol = mt5.symbol_info(nome)

    if tick is None or info_symbol is None:
        print(f"\n{nome_ativo} ({nome}): sem tick")
        return {"ativo": nome_ativo, "status": "sem_tick", "contrato": nome}

    teorico = obter_preco_teorico(nome)
    last, fonte_last = _preco_last(tick, teorico)
    bid = _f(tick.bid)
    ask = _f(tick.ask)
    volume = _f(tick.volume)

    ohlc = _ohlc_d1(nome)
    session_close = _f(getattr(info_symbol, "session_close", 0.0))
    prev_close = session_close if session_close > 0 else (ohlc["prev_close_d1"] or 0.0)

    spread = round(ask - bid, 2) if bid > 0 and ask > 0 else None
    var_abs = round(last - prev_close, 2) if prev_close > 0 and last > 0 else 0.0
    var_pct = round(((last / prev_close) - 1) * 100, 2) if prev_close > 0 and last > 0 else 0.0

    tick_time = getattr(tick, "time", 0) or 0
    idade = None
    stale = False
    if tick_time:
        try:
            idade = int((datetime.now() - datetime.fromtimestamp(tick_time)).total_seconds())
            stale = idade > TICK_STALE_SEG
        except Exception:
            idade = None

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

    status = "OK" if last > 0 else "SEM_LAST"
    if stale:
        status = "STALE" if last > 0 else "SEM_LAST_STALE"

    dados = {
        "ativo": nome_ativo,
        "descricao": configuracao["descricao"],
        "contrato_principal": nome,
        "timestamp": agora(),
        "bid": bid,
        "ask": ask,
        "last": last,
        "fonte_last": fonte_last,
        "open": ohlc["open"],
        "high": ohlc["high"],
        "low": ohlc["low"],
        "session_close": session_close,
        "prev_close": prev_close,
        "change_percent": var_pct,
        "change_abs": var_abs,
        "volume": volume,
        "spread": spread,
        "preco_teorico": teorico,
        "tick_time": datetime.fromtimestamp(tick_time).isoformat() if tick_time else None,
        "tick_idade_seg": idade,
        "tick_stale": stale,
        "vencimento": principal["expiracao"].isoformat() if principal.get("expiracao") else None,
        "market_book": book,
        "contratos_vigentes": contratos_saida,
        "status": status,
    }

    print(f"\n{nome_ativo} ({nome}) [{status}] last={last} via {fonte_last} prev={prev_close} var={var_pct}%")
    if stale:
        print(f"   ⚠️ tick stale ({idade}s)")
    return dados


def _podar_historico() -> None:
    try:
        arquivos = [
            os.path.join(HISTORICO_DIR, n)
            for n in os.listdir(HISTORICO_DIR)
            if n.endswith(".json")
        ]
        arquivos.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for velho in arquivos[MAX_HISTORICO:]:
            try:
                os.remove(velho)
            except OSError:
                pass
    except OSError:
        pass


def salvar_json(dados: dict) -> str:
    with open(ARQUIVO_ATUAL, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

    agora_dt = datetime.now()
    nome_historico = f"MT5_v2_3_{agora_dt.strftime('%Y%m%d_%H%M%S')}.json"
    caminho_historico = os.path.join(HISTORICO_DIR, nome_historico)
    with open(caminho_historico, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)
    _podar_historico()
    return caminho_historico


def executar_coleta_mt5_v2(desconectar: bool = True) -> Optional[dict]:
    """
    deso:
      desconectar=False  → deixa o MT5 aberto para o Coletor.py coletar ações B3
                           no mesmo ciclo (depois chame desconectar_mt5()).
    """
    if not conectar_mt5():
        return {
            "versao_coletor": VERSAO,
            "timestamp": agora(),
            "mt5": {"conectado": False},
            "ativos": {},
            "status": "ERRO_CONEXAO",
        }

    try:
        dados = {
            "versao_coletor": VERSAO,
            "timestamp": agora(),
            "mt5": {"conectado": True, "versao": list(mt5.version()) if mt5.version() else None},
            "ativos": {},
            "status": "OK",
        }
        falhas = 0
        for nome_ativo, config in ATIVOS.items():
            item = coletar_ativo(nome_ativo, config)
            dados["ativos"][nome_ativo] = item
            if item.get("status") not in ("OK", "STALE"):
                falhas += 1
        if falhas:
            dados["status"] = "PARCIAL"
        salvar_json(dados)
        return dados
    except Exception as erro:
        print(f"\n❌ ERRO DURANTE A COLETA v{VERSAO}: {erro}")
        return {
            "versao_coletor": VERSAO,
            "timestamp": agora(),
            "mt5": {"conectado": True},
            "ativos": {},
            "status": "ERRO",
            "erro": str(erro),
        }
    finally:
        if desconectar:
            desconectar_mt5()


if __name__ == "__main__":
    executar_coleta_mt5_v2(desconectar=True)
