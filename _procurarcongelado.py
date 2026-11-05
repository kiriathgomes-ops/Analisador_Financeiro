# _scan_congelados.py — acha JSONs em Coletas/ com OHLC D1
import json
from datetime import datetime
from pathlib import Path

COLETAS = Path("Coletas")
CANDIDATOS_CHAVES = {"WIN", "WIN_AJUSTE", "WIN_FUT"}

def _tem_ohlc(d):
    if not isinstance(d, dict):
        return False
    return all(k in d for k in ("open", "high", "low", "close"))

def _procurar(d, path=""):
    hits = []
    if isinstance(d, dict):
        if _tem_ohlc(d) and any(c in path for c in CANDIDATOS_CHAVES):
            hits.append((path or "<root>", {k: d.get(k) for k in ("open","high","low","close")}))
        for k, v in d.items():
            hits.extend(_procurar(v, f"{path}.{k}" if path else k))
    elif isinstance(d, list):
        for i, v in enumerate(d[:5]):  # amostra 5
            hits.extend(_procurar(v, f"{path}[{i}]"))
    return hits

for p in sorted(COLETAS.rglob("*.json")):
    try:
        mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    hits = _procurar(d)
    if hits:
        print(f"\n{p}  (mtime={mtime})")
        for path, ohlc in hits[:3]:
            print(f"   {path}: {ohlc}")