"""
cache_candles.py — Cache incremental de candles do MT5

Objetivo: reduzir o custo de puxar centenas de candles a cada chamada.
Mantém cache em disco por (contrato, timeframe) e só faz fetch dos
candles novos (incremental).

Formato: JSON em Coletas/cache/candles_{CONTRATO}_{TF}m.json

Rollover: cache é keyed no contrato real (WINV26). Quando muda, o cache
antigo é movido para Coletas/cache/_arquivo/ e um novo é criado.

fix88: fetch incremental dinâmico baseado em gap + sanity check pós-merge.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "Coletas" / "cache"
ARQUIVO_DIR = CACHE_DIR / "_arquivo"

BRT = timezone(timedelta(hours=-3))
MAX_CACHE_POR_TF = 1500
QTD_REFRESH_INCREMENTAL = 60
DIAS_RETENCAO = 30

# fix88: thresholds de deteccao de gap
GAP_MIN_PERMITIDO_MIN = 5     # gap > 5 min = suspeito (1 candle faltando)
GAP_ALERTA_MIN = 30           # gap > 30 min = forca refresh maior

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def _rate_para_dict(rate) -> Dict[str, Any]:
    try:
        dt_brt = datetime.fromtimestamp(rate["time"], tz=timezone.utc).replace(tzinfo=BRT)
    except Exception:
        dt_brt = datetime.now(BRT)

    v_real = 0.0
    try:
        if "real_volume" in rate.dtype.names:
            v_real = float(rate["real_volume"])
    except Exception:
        pass
    if v_real <= 0:
        try:
            if "tick_volume" in rate.dtype.names:
                v_real = float(rate["tick_volume"])
        except Exception:
            pass

    return {
        "time": dt_brt.isoformat(),
        "open": float(rate["open"]),
        "high": float(rate["high"]),
        "low": float(rate["low"]),
        "close": float(rate["close"]),
        "volume": v_real,
    }


def _resolver_contrato_real(symbol: str) -> str:
    import MetaTrader5 as mt5
    info = mt5.symbol_info(symbol)
    if info is None:
        return symbol
    basis = (getattr(info, "basis", "") or "").strip()
    return basis if basis else symbol


def _base_symbol(contrato: str) -> str:
    m = re.match(r"^([A-Z]+)", contrato)
    return m.group(1) if m else contrato


def _cache_path(contrato: str, tf_min: int) -> Path:
    return CACHE_DIR / f"candles_{contrato}_{tf_min}m.json"


def _ler_cache(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[CACHE] Erro lendo {path.name}: {e}")
        return None


def _salvar_cache(path: Path, contrato: str, tf_min: int, candles: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "versao": 1,
        "simbolo": contrato,
        "tf_min": tf_min,
        "atualizado_em": datetime.now(BRT).isoformat(timespec="seconds"),
        "total_candles": len(candles),
        "candles": candles,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    tmp.replace(path)


def _merge_candles(antigos: List[Dict], novos: List[Dict]) -> List[Dict]:
    mapa = {c["time"]: c for c in antigos if "time" in c}
    for c in novos:
        if "time" in c:
            mapa[c["time"]] = c
    return sorted(mapa.values(), key=lambda c: c["time"])


def _detectar_gaps(candles: List[Dict], tf_min: int) -> List[float]:
    """
    fix88: retorna lista de gaps em minutos entre candles consecutivos.
    Considera gap valido (overnight + fim de semana) como ignorado.
    """
    if len(candles) < 2:
        return []

    gaps = []
    # Tolerancia: 2x o TF (pega faltando 1 candle)
    tol = max(tf_min * 2, GAP_MIN_PERMITIDO_MIN)

    for i in range(1, len(candles)):
        try:
            t1 = datetime.fromisoformat(candles[i - 1]["time"])
            t2 = datetime.fromisoformat(candles[i]["time"])
        except Exception:
            continue

        delta_min = (t2 - t1).total_seconds() / 60

        if delta_min <= tol:
            continue

        # Ignora gaps de overnight (>= 12h) e fim de semana (>= 24h)
        if delta_min >= 12 * 60:
            continue

        gaps.append(delta_min)

    return gaps


def _arquivar_contratos_antigos(contrato_atual: str, tf_min: int) -> int:
    base = _base_symbol(contrato_atual)
    if not CACHE_DIR.exists():
        return 0

    movidos = 0
    for arq in CACHE_DIR.glob(f"candles_{base}*_{tf_min}m.json"):
        if contrato_atual in arq.name:
            continue
        try:
            ARQUIVO_DIR.mkdir(parents=True, exist_ok=True)
            destino = ARQUIVO_DIR / arq.name
            shutil.move(str(arq), str(destino))
            movidos += 1
            print(f"[CACHE] Arquivado: {arq.name}")
        except Exception as e:
            print(f"[CACHE] Erro arquivando {arq.name}: {e}")
    return movidos


def _limpar_arquivo_antigo(dias: int = DIAS_RETENCAO) -> int:
    if not ARQUIVO_DIR.exists():
        return 0
    corte = datetime.now() - timedelta(days=dias)
    removidos = 0
    for arq in ARQUIVO_DIR.glob("*.json"):
        try:
            if datetime.fromtimestamp(arq.stat().st_mtime) < corte:
                arq.unlink()
                removidos += 1
        except Exception:
            continue
    return removidos


def _fetch_mt5(
    simbolo_mt5: str, tf_min: int, qtd: int
) -> List[Dict[str, Any]]:
    """Busca candles do MT5. Assume que MT5 já está inicializado."""
    import MetaTrader5 as mt5

    tf_map = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15}
    tf = tf_map.get(tf_min)
    if tf is None:
        raise ValueError(f"TF nao suportado: {tf_min}")

    rates = mt5.copy_rates_from_pos(simbolo_mt5, tf, 0, qtd)
    if rates is None or len(rates) == 0:
        return []
    return [_rate_para_dict(r) for r in rates]


def _obter_com_mt5_aberto(
    simbolo_mt5: str, tf_min: int, qtd: int
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Retorna (candles, contrato_real).
    Assume MT5 já inicializado pelo caller.

    fix88: fetch incremental dinamico baseado em gap + sanity check pos-merge.
    """
    import MetaTrader5 as mt5

    info = mt5.symbol_info(simbolo_mt5)
    if info is None:
        raise RuntimeError(f"Simbolo nao encontrado no MT5: {simbolo_mt5}")
    if not info.visible:
        mt5.symbol_select(simbolo_mt5, True)

    contrato_real = _resolver_contrato_real(simbolo_mt5)

    # Rollover: arquiva caches antigos de outros contratos da mesma familia
    _arquivar_contratos_antigos(contrato_real, tf_min)

    path = _cache_path(contrato_real, tf_min)
    cache = _ler_cache(path)

    # Cache vazio ou corrompido: puxa tudo do MT5
    if cache is None or "candles" not in cache:
        candles = _fetch_mt5(simbolo_mt5, tf_min, qtd)
        if candles:
            _salvar_cache(path, contrato_real, tf_min, candles)
        return candles[-qtd:] if len(candles) > qtd else candles, contrato_real

    antigos = cache.get("candles") or []
    if not antigos:
        candles = _fetch_mt5(simbolo_mt5, tf_min, qtd)
        if candles:
            _salvar_cache(path, contrato_real, tf_min, candles)
        return candles[-qtd:] if len(candles) > qtd else candles, contrato_real

    # Verifica se o cache esta obsoleto (mais de 1 dia)
    try:
        ultimo_ts = datetime.fromisoformat(antigos[-1]["time"])
        agora = datetime.now(BRT)
        if (agora - ultimo_ts).days >= 1:
            print(f"[CACHE] Cache obsoleto ({contrato_real} {tf_min}m) — refresh total")
            candles = _fetch_mt5(simbolo_mt5, tf_min, qtd)
            if candles:
                _salvar_cache(path, contrato_real, tf_min, candles)
            return candles[-qtd:] if len(candles) > qtd else candles, contrato_real
    except Exception:
        pass

    # fix41b: se cache tem menos candles que o caller pediu,
    # faz refresh TOTAL em vez de incremental.
    if len(antigos) < qtd:
        print(f"[CACHE] Cache insuficiente ({len(antigos)} < {qtd}) — refresh total")
        candles = _fetch_mt5(simbolo_mt5, tf_min, qtd)
        if candles:
            _salvar_cache(path, contrato_real, tf_min, candles)
        return candles, contrato_real

    # fix88: fetch incremental DINAMICO baseado no gap entre ultimo candle e agora
    try:
        ultimo_cache = datetime.fromisoformat(antigos[-1]["time"])
        gap_min = max(0.0, (datetime.now(BRT) - ultimo_cache).total_seconds() / 60.0)
    except Exception:
        gap_min = 0.0

    # Se gap > QTD_REFRESH_INCREMENTAL, aumenta o fetch pra cobrir
    qtd_incr = max(QTD_REFRESH_INCREMENTAL, int(gap_min) + 10)
    qtd_incr = min(qtd_incr, MAX_CACHE_POR_TF)

    if qtd_incr > QTD_REFRESH_INCREMENTAL:
        print(f"[CACHE] Gap detectado ({gap_min:.0f} min) — fetch {qtd_incr} candles")

    novos = _fetch_mt5(simbolo_mt5, tf_min, qtd_incr)
    if not novos:
        return antigos[-qtd:] if len(antigos) > qtd else antigos, contrato_real

    merged = _merge_candles(antigos, novos)

    # fix88: sanity check pos-merge — se ainda tem gaps internos anomalos,
    # forca refresh total pra limpar o cache.
    gaps_detectados = _detectar_gaps(merged, tf_min)
    if gaps_detectados:
        total_gap = sum(gaps_detectados)
        print(f"[CACHE] Pós-merge: {len(gaps_detectados)} gaps internos ({total_gap:.0f} min total) — refresh total")
        candles = _fetch_mt5(simbolo_mt5, tf_min, qtd)
        if candles:
            _salvar_cache(path, contrato_real, tf_min, candles)
            return candles[-qtd:] if len(candles) > qtd else candles, contrato_real

    if len(merged) > MAX_CACHE_POR_TF:
        merged = merged[-MAX_CACHE_POR_TF:]

    _salvar_cache(path, contrato_real, tf_min, merged)

    return merged[-qtd:] if len(merged) > qtd else merged, contrato_real


def obter_candles(
    symbol: str = "WIN$",
    tf_min: int = 5,
    qtd: int = 200,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    API publica. Retorna (candles, contrato_real).

    Gerencia init/shutdown do MT5 se necessario. Se MT5 ja esta
    inicializado por outro caller, usa a conexao existente.

    Args:
        symbol: simbolo MT5 (ex: "WIN$", "WDO$")
        tf_min: 1, 5 ou 15
        qtd: numero de candles desejados

    Returns:
        (lista de candles ordenados por tempo, contrato real ex: "WINV26")
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[CACHE] MT5 nao instalado — retornando lista vazia")
        return [], symbol

    ja_inicializado = mt5.terminal_info() is not None
    if not ja_inicializado:
        if not mt5.initialize():
            print(f"[CACHE] mt5.initialize falhou: {mt5.last_error()}")
            return [], symbol

    try:
        return _obter_com_mt5_aberto(symbol, tf_min, qtd)
    except Exception as e:
        print(f"[CACHE] Erro em obter_candles: {e}")
        return [], symbol
    finally:
        if not ja_inicializado:
            try:
                mt5.shutdown()
            except Exception:
                pass


def obter_candles_multi_tf(
    symbol: str = "WIN$",
    tf_qtd: Optional[Dict[int, int]] = None,
) -> Dict[int, Tuple[List[Dict[str, Any]], str]]:
    """
    Puxa varios TFs numa unica conexao MT5.

    Args:
        tf_qtd: dict {tf_min: qtd}, ex {1: 600, 5: 300, 15: 300}

    Returns:
        {tf_min: (candles, contrato_real)}
    """
    if tf_qtd is None:
        tf_qtd = {1: 600, 5: 300, 15: 300}

    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {tf: ([], symbol) for tf in tf_qtd}

    ja_inicializado = mt5.terminal_info() is not None
    if not ja_inicializado:
        if not mt5.initialize():
            return {tf: ([], symbol) for tf in tf_qtd}

    resultado: Dict[int, Tuple[List[Dict[str, Any]], str]] = {}
    try:
        for tf_min, qtd in tf_qtd.items():
            try:
                resultado[tf_min] = _obter_com_mt5_aberto(symbol, tf_min, qtd)
            except Exception as e:
                print(f"[CACHE] Erro em TF {tf_min}: {e}")
                resultado[tf_min] = ([], symbol)
    finally:
        if not ja_inicializado:
            try:
                mt5.shutdown()
            except Exception:
                pass

    return resultado


def invalidar_cache(symbol: str = "WIN$", tf_min: Optional[int] = None) -> int:
    """
    Apaga caches. Se tf_min=None, apaga todos os TFs do contrato.
    Retorna numero de arquivos removidos.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return 0

    ja_inicializado = mt5.terminal_info() is not None
    if not ja_inicializado:
        if not mt5.initialize():
            return 0

    removidos = 0
    try:
        contrato = _resolver_contrato_real(symbol)
        tfs = [tf_min] if tf_min else [1, 5, 15]
        for tf in tfs:
            p = _cache_path(contrato, tf)
            if p.exists():
                p.unlink()
                removidos += 1
                print(f"[CACHE] Invalidado: {p.name}")
    except Exception as e:
        print(f"[CACHE] Erro ao invalidar: {e}")
    finally:
        if not ja_inicializado:
            try:
                mt5.shutdown()
            except Exception:
                pass

    return removidos


def limpar_arquivo_antigo() -> int:
    """Remove caches arquivados com mais de DIAS_RETENCAO dias."""
    return _limpar_arquivo_antigo()


if __name__ == "__main__":
    import argparse as _argparse

    ap = _argparse.ArgumentParser(description="Debug do cache de candles")
    ap.add_argument("--symbol", default="WIN$")
    ap.add_argument("--tf", type=int, default=5)
    ap.add_argument("--qtd", type=int, default=200)
    ap.add_argument("--invalidar", action="store_true")
    ap.add_argument("--limpar-arquivo", action="store_true")
    args = ap.parse_args()

    if args.invalidar:
        n = invalidar_cache(args.symbol, args.tf)
        print(f"[OK] {n} arquivos invalidados")
    elif args.limpar_arquivo:
        n = limpar_arquivo_antigo()
        print(f"[OK] {n} arquivos antigos removidos de _arquivo/")
    else:
        candles, contrato = obter_candles(args.symbol, args.tf, args.qtd)
        print(f"Contrato: {contrato}")
        print(f"Candles: {len(candles)}")
        if candles:
            print(f"Primeiro: {candles[0]['time']}")
            print(f"Ultimo:   {candles[-1]['time']}")
            print(f"Ultimo close: {candles[-1]['close']}")