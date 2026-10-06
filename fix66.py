# -*- coding: utf-8 -*-
# fix66.py — Corrige ADRs OTC stale do Finnhub + fallback TradingView.
#
# BUG:
#   Finnhub retorna change_percent (dp) correto pros 4 NYSEs (VALE/PBR/ITUB/BBD)
#   mas ERRADO pros 2 OTCs (BDORY/BOLSY). Causa: Finnhub deixa o prev_close
#   desatualizado pra OTC iliquido. Ex (06/10/2026):
#     BDORY: c=5.29 pc=4.60 -> dp=+15.00% (real: -2.65%)
#     BOLSY: c=13.98 pc=10.75 -> dp=+30.05% (real: -2.15%)
#   O campo t revela: BDORY e BOLSY tem t=1791158400 (meia-noite UTC de 05/10)
#   enquanto VALE tem t=1791314023 (intraday de 06/10 19:13 UTC). Diferenca
#   de ~43h confirma dado stale.
#
# FIX (defesa em profundidade):
#   1. Coletor: valida 4 sanidades pos-Finnhub
#      - idade do t < 24h
#      - abs(dp) < 15%
#      - pc > 0, c > 0
#   2. Coletor: fallback TradingView (endpoint /symbol) se Finnhub falhar
#      - valida close > 0, change != None, abs(change) < 15%
#   3. Coletor: se TV tambem falhar, marca STALE_FINNHUB_SEM_TV (descartado)
#   4. Calculadora: guarda final abs(pct_val) > 15 = ignora (defesa extra)
#
# Uso:
#   python fix66.py --dry-run
#   python fix66.py
#   python fix66.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ_COLETOR = Path("Coletor.py")
ARQ_CALC = Path("Calculadora.py")

# ============================================================
# PATCHES — Coletor.py
# ============================================================

PATCHES_COLETOR = [
    # ---- 1. Adiciona helper de fallback TV antes de coletar_finnhub ----
    {
        "nome": "helper_tv_adr_fallback",
        "ancora_antiga": (
            '# ------------------------------------------------------------\n'
            '# Finnhub (paralelo)\n'
            '# ------------------------------------------------------------\n'
            'def coletar_finnhub() -> List[Dict[str, Any]]:'
        ),
        "ancora_nova": (
            '# ------------------------------------------------------------\n'
            '# Fallback TradingView para ADRs (fix66)\n'
            '# ------------------------------------------------------------\n'
            'def _coletar_tv_adr(ticker_tv: str) -> Dict[str, Any]:\n'
            '    """\n'
            '    fix66: fallback TV para ADR quando Finnhub retorna dado stale/absurdo.\n'
            '\n'
            '    Usa o endpoint /symbol do TradingView (nao /global/scan).\n'
            '    Valida 3 sanidades antes de retornar:\n'
            '      - close > 0\n'
            '      - change nao-nulo\n'
            '      - abs(change) < 15 (circuit breaker B3)\n'
            '\n'
            '    Retorna dict no mesmo formato de coletar_finnhub,\n'
            '    ou None se TV tambem falhar.\n'
            '    """\n'
            '    url = (\n'
            '        f"https://scanner.tradingview.com/symbol?"\n'
            '        f"symbol={ticker_tv}&fields=close,change,change|1"\n'
            '    )\n'
            '    try:\n'
            '        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})\n'
            '        with urllib.request.urlopen(req, timeout=8) as resp:\n'
            '            res = json.loads(resp.read().decode("utf-8"))\n'
            '        close_val = res.get("close")\n'
            '        change_val = res.get("change")\n'
            '\n'
            '        # Sanidade 1: close valido\n'
            '        if close_val is None or float(close_val) <= 0:\n'
            '            print(f"      [TV fallback] {ticker_tv}: close invalido ({close_val})")\n'
            '            return None\n'
            '\n'
            '        # Sanidade 2: change presente\n'
            '        if change_val is None:\n'
            '            print(f"      [TV fallback] {ticker_tv}: change ausente")\n'
            '            return None\n'
            '\n'
            '        change_f = float(change_val)\n'
            '\n'
            '        # Sanidade 3: variacao dentro do razoavel\n'
            '        if abs(change_f) > 15.0:\n'
            '            print(f"      [TV fallback] {ticker_tv}: variacao absurda ({change_f:.2f}%)")\n'
            '            return None\n'
            '\n'
            '        return {\n'
            '            "c": float(close_val),\n'
            '            "d": 0.0,\n'
            '            "dp": change_f,\n'
            '            "pc": 0.0,\n'
            '            "t": 0,\n'
            '        }\n'
            '    except Exception as e:\n'
            '        print(f"      [TV fallback] {ticker_tv}: erro {e}")\n'
            '        return None\n'
            '\n'
            '\n'
            '# ------------------------------------------------------------\n'
            '# Finnhub (paralelo)\n'
            '# ------------------------------------------------------------\n'
            'def coletar_finnhub() -> List[Dict[str, Any]]:'
        ),
    },
    # ---- 2. Substitui o bloco de validação/retorno dentro de _um ----
    {
        "nome": "validacao_finnhub_com_tv_fallback",
        "ancora_antiga": (
            '            if "c" in res and res["c"] != 0:\n'
            '                return {\n'
            '                    "ativo": cfg["ativo"],\n'
            '                    "fonte": "FINNHUB",\n'
            '                    "timestamp": timestamp,\n'
            '                    "status": "OK",\n'
            '                    "dados_reais": {\n'
            '                        "close": float(res["c"]),\n'
            '                        "open": None,\n'
            '                        "high": None,\n'
            '                        "low": None,\n'
            '                        "change_percent": round(float(res.get("dp", 0.0)), 2),\n'
            '                        "volume": None,\n'
            '                        "var_abs": round(float(res.get("d", 0.0)), 2),\n'
            '                        "fechamento_anterior": float(res.get("pc", 0.0)),\n'
            '                    },\n'
            '                }'
        ),
        "ancora_nova": (
            '            if "c" in res and res["c"] != 0:\n'
            '                # fix66: valida sanidade antes de aceitar Finnhub\n'
            '                import time as _time\n'
            '                _c = float(res.get("c", 0) or 0)\n'
            '                _pc = float(res.get("pc", 0) or 0)\n'
            '                _dp = float(res.get("dp", 0) or 0)\n'
            '                _t = float(res.get("t", 0) or 0)\n'
            '                _idade_h = (_time.time() - _t) / 3600 if _t > 0 else 9999\n'
            '\n'
            '                _falhas = []\n'
            '                if _idade_h > 24:\n'
            '                    _falhas.append(f"stale({_idade_h:.1f}h)")\n'
            '                if abs(_dp) > 15.0:\n'
            '                    _falhas.append(f"dp_absurdo({_dp:+.2f}%)")\n'
            '                if _pc <= 0:\n'
            '                    _falhas.append("pc_invalido")\n'
            '                if _c <= 0:\n'
            '                    _falhas.append("c_invalido")\n'
            '\n'
            '                if _falhas:\n'
            '                    print(f"   ⚠️ Finnhub {cfg[\'ticker_coleta\']} descartado: {\', \'.join(_falhas)} — tentando TV...")\n'
            '                    _tv = _coletar_tv_adr(cfg["ativo"])\n'
            '                    if _tv is not None:\n'
            '                        print(f"   ✅ TV fallback OK para {cfg[\'ticker_coleta\']}: {_tv[\'dp\']:+.2f}%")\n'
            '                        return {\n'
            '                            "ativo": cfg["ativo"],\n'
            '                            "fonte": "TRADINGVIEW_FALLBACK",\n'
            '                            "timestamp": timestamp,\n'
            '                            "status": "OK_TV_FALLBACK",\n'
            '                            "dados_reais": {\n'
            '                                "close": _tv["c"],\n'
            '                                "open": None,\n'
            '                                "high": None,\n'
            '                                "low": None,\n'
            '                                "change_percent": round(_tv["dp"], 2),\n'
            '                                "volume": None,\n'
            '                                "var_abs": 0.0,\n'
            '                                "fechamento_anterior": 0.0,\n'
            '                            },\n'
            '                        }\n'
            '                    print(f"   ❌ TV fallback falhou para {cfg[\'ticker_coleta\']} — descartado")\n'
            '                    return {\n'
            '                        "ativo": cfg["ativo"],\n'
            '                        "fonte": "FINNHUB_STALE_SEM_TV",\n'
            '                        "timestamp": timestamp,\n'
            '                        "status": "STALE",\n'
            '                        "dados_reais": None,\n'
            '                    }\n'
            '\n'
            '                # Sanidade OK — Finnhub aceito\n'
            '                return {\n'
            '                    "ativo": cfg["ativo"],\n'
            '                    "fonte": "FINNHUB",\n'
            '                    "timestamp": timestamp,\n'
            '                    "status": "OK",\n'
            '                    "dados_reais": {\n'
            '                        "close": _c,\n'
            '                        "open": None,\n'
            '                        "high": None,\n'
            '                        "low": None,\n'
            '                        "change_percent": round(_dp, 2),\n'
            '                        "volume": None,\n'
            '                        "var_abs": round(float(res.get("d", 0.0)), 2),\n'
            '                        "fechamento_anterior": _pc,\n'
            '                    },\n'
            '                }'
        ),
    },
]

# ============================================================
# PATCHES — Calculadora.py
# ============================================================

PATCHES_CALC = [
    {
        "nome": "guarda_sanidade_adrs",
        "ancora_antiga": (
            '            if isinstance(pct_val, (int, float)):\n'
            '                soma_variacoes_adrs += pct_val\n'
            '                qtd_adrs_validas += 1'
        ),
        "ancora_nova": (
            '            if isinstance(pct_val, (int, float)):\n'
            '                # fix66: defesa em profundidade — descarta variacao absurda\n'
            '                # (circuit breaker B3 e 10-15%; nada legitimo passa disso num dia)\n'
            '                if abs(pct_val) > 15.0:\n'
            '                    print(f"   ⚠️ {adr_id} com variacao absurda ({pct_val:+.2f}%) — ignorado do indicador")\n'
            '                    continue\n'
            '                soma_variacoes_adrs += pct_val\n'
            '                qtd_adrs_validas += 1'
        ),
    },
    {
        "nome": "log_qtd_adrs_usados",
        "ancora_antiga": (
            '    # Indicador ADRs Brasileiras = soma das variações\n'
            '    ind_adrs_brasileiras = round(soma_variacoes_adrs, 4) if qtd_adrs_validas > 0 else None'
        ),
        "ancora_nova": (
            '    # Indicador ADRs Brasileiras = soma das variações\n'
            '    # fix66: log quantos ADRs entraram (transparencia quando algum foi descartado)\n'
            '    print(f"   📊 ADRs usados no indicador: {qtd_adrs_validas}/{len(adrs_chaves)}")\n'
            '    ind_adrs_brasileiras = round(soma_variacoes_adrs, 4) if qtd_adrs_validas > 0 else None'
        ),
    },
]


# ============================================================
# Infra
# ============================================================

def pre_validar(arquivo, patches):
    if not arquivo.exists():
        print(f"ABORTADO: {arquivo} nao encontrado")
        return False
    conteudo = arquivo.read_text(encoding="utf-8")
    for patch in patches:
        antiga = patch["ancora_antiga"]
        n = conteudo.count(antiga)
        if n == 0:
            print(f"ABORTADO [{arquivo.name}]: ancora nao encontrada: {patch['nome']}")
            print("---"); print(antiga); print("---")
            return False
        if n > 1:
            print(f"ABORTADO [{arquivo.name}]: ancora ambigua ({n}x): {patch['nome']}")
            return False
    return True


def aplicar(arquivo, patches):
    conteudo = arquivo.read_text(encoding="utf-8")
    for patch in patches:
        conteudo = conteudo.replace(patch["ancora_antiga"], patch["ancora_nova"], 1)
        print(f"OK [{arquivo.name}]: {patch['nome']}")
    return conteudo


def validar_sintaxe(conteudo, nome):
    try:
        compile(conteudo, nome, "exec")
    except SyntaxError as e:
        print(f"ABORTADO: sintaxe invalida em {nome}: {e}")
        return False
    print(f"OK [{nome}]: sintaxe validada")
    return True


def mostrar_diff(antes, depois, nome):
    print(f"\n--- DRY-RUN: diff {nome} ---")
    for linha in difflib.unified_diff(
        antes.splitlines(), depois.splitlines(),
        lineterm="", fromfile="antes", tofile="depois",
    ):
        print(linha)
    print(f"--- DRY-RUN {nome}: nada foi salvo ---")


def processar(arquivo, patches, dry_run):
    if not pre_validar(arquivo, patches):
        sys.exit(1)
    antes = arquivo.read_text(encoding="utf-8")
    depois = aplicar(arquivo, patches)
    if not validar_sintaxe(depois, arquivo.name):
        sys.exit(1)
    if dry_run:
        mostrar_diff(antes, depois, arquivo.name)
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = arquivo.parent / f"{arquivo.name}.bak_{ts}"
    shutil.copy(arquivo, backup)
    arquivo.write_text(depois, encoding="utf-8")
    print(f"OK [{arquivo.name}]: backup={backup.name}")


def reverter():
    for arq in [ARQ_COLETOR, ARQ_CALC]:
        backups = sorted(arq.parent.glob(f"{arq.name}.bak_*"))
        if not backups:
            print(f"AVISO: sem backup para {arq.name}")
            continue
        ultimo = backups[-1]
        shutil.copy(ultimo, arq)
        print(f"OK: revertido {arq.name} de {ultimo.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        reverter()
        return

    print("===== fix66: ADRs stale + TV fallback + guarda sanidade =====")
    processar(ARQ_COLETOR, PATCHES_COLETOR, args.dry_run)
    processar(ARQ_CALC, PATCHES_CALC, args.dry_run)

    if not args.dry_run:
        print("\nOK: fix66 aplicado nos 2 arquivos")
    else:
        print("\n--- DRY-RUN concluido: nada foi salvo ---")


if __name__ == "__main__":
    main()