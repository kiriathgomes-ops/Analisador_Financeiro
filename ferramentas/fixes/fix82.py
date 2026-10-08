# -*- coding: utf-8 -*-
# fix82.py — Adiciona retry + backoff ao coletar_bacen_ptax.
#
# DEBITO #4:
#   Bacen SGS timeout ocasional gera [AVISO] e cai pro TV fallback.
#   Sem retry, um pico de latencia de 10s derruba a coleta.
#
# FIX:
#   - Helper _fetch_url_com_retry(url, ctx=None, tentativas=3)
#   - Backoff exponencial: 1s, 2s, 4s entre tentativas
#   - Aplica em Bacen SGS E no fallback TV
#   - Loga cada tentativa pra debug
#
# Uso:
#   python fix82.py --dry-run
#   python fix82.py
#   python fix82.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("Coletor.py")

PATCHES = [
    # ---- 1. Adiciona import time no topo ----
    {
        "nome": "add_import_time",
        "ancora_antiga": (
            'import urllib.request'
        ),
        "ancora_nova": (
            'import time\n'
            'import urllib.request'
        ),
    },
    # ---- 2. Helper de retry + aplicar no Bacen SGS ----
    {
        "nome": "bacen_com_retry",
        "ancora_antiga": (
            'def coletar_bacen_ptax() -> dict:\n'
            '    timestamp = datetime.now().isoformat()\n'
            '    url_sgs = (\n'
            '        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.10813/dados/ultimos/5?formato=json"\n'
            '    )\n'
            '    ctx = ssl.create_default_context()\n'
            '    ctx.check_hostname = False\n'
            '    ctx.verify_mode = ssl.CERT_NONE\n'
            '\n'
            '    try:\n'
            '        req = urllib.request.Request(url_sgs, headers={"User-Agent": "Mozilla/5.0"})\n'
            '        with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT_BACEN or 10) as resp:\n'
            '            res = json.loads(resp.read().decode("utf-8"))\n'
            '            if res:\n'
            '                valor = float(res[-1]["valor"].replace(",", "."))\n'
            '                return {\n'
            '                    "ativo": "USD_PTAX",\n'
            '                    "fonte": "BACEN_SGS_10813",\n'
            '                    "timestamp": timestamp,\n'
            '                    "status": "OK",\n'
            '                    "dados_reais": {\n'
            '                        "close": valor,\n'
            '                        "open": None,\n'
            '                        "high": None,\n'
            '                        "low": None,\n'
            '                        "change_percent": None,\n'
            '                        "volume": None,\n'
            '                    },\n'
            '                }\n'
            '    except Exception as e:\n'
            '        print(f"[AVISO] Bacen SGS: {e}. Fallback TV...")'
        ),
        "ancora_nova": (
            'def _fetch_url_com_retry(\n'
            '    url: str,\n'
            '    ctx=None,\n'
            '    data: bytes = None,\n'
            '    tentativas: int = 3,\n'
            '    timeout: int = 10,\n'
            '    headers: dict = None,\n'
            ') -> bytes:\n'
            '    """\n'
            '    fix82: fetch URL com retry + backoff exponencial.\n'
            '\n'
            '    Backoff: 1s, 2s, 4s entre tentativas.\n'
            '    Retorna bytes do response. Levanta excecao se todas falharem.\n'
            '    """\n'
            '    headers = headers or {"User-Agent": "Mozilla/5.0"}\n'
            '    ultima_excecao = None\n'
            '    for tent in range(1, tentativas + 1):\n'
            '        try:\n'
            '            req = urllib.request.Request(url, data=data, headers=headers)\n'
            '            if ctx is not None:\n'
            '                with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:\n'
            '                    return resp.read()\n'
            '            else:\n'
            '                with urllib.request.urlopen(req, timeout=timeout) as resp:\n'
            '                    return resp.read()\n'
            '        except Exception as e:\n'
            '            ultima_excecao = e\n'
            '            if tent < tentativas:\n'
            '                espera = 2 ** (tent - 1)  # 1, 2, 4\n'
            '                print(f"   [RETRY] tentativa {tent}/{tentativas} falhou ({type(e).__name__}), "\n'
            '                      f"aguardando {espera}s...")\n'
            '                time.sleep(espera)\n'
            '    raise ultima_excecao\n'
            '\n'
            '\n'
            'def coletar_bacen_ptax() -> dict:\n'
            '    timestamp = datetime.now().isoformat()\n'
            '    url_sgs = (\n'
            '        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.10813/dados/ultimos/5?formato=json"\n'
            '    )\n'
            '    ctx = ssl.create_default_context()\n'
            '    ctx.check_hostname = False\n'
            '    ctx.verify_mode = ssl.CERT_NONE\n'
            '\n'
            '    try:\n'
            '        body = _fetch_url_com_retry(\n'
            '            url_sgs, ctx=ctx,\n'
            '            tentativas=3,\n'
            '            timeout=TIMEOUT_BACEN or 10,\n'
            '        )\n'
            '        res = json.loads(body.decode("utf-8"))\n'
            '        if res:\n'
            '            valor = float(res[-1]["valor"].replace(",", "."))\n'
            '            return {\n'
            '                "ativo": "USD_PTAX",\n'
            '                "fonte": "BACEN_SGS_10813",\n'
            '                "timestamp": timestamp,\n'
            '                "status": "OK",\n'
            '                "dados_reais": {\n'
            '                    "close": valor,\n'
            '                    "open": None,\n'
            '                    "high": None,\n'
            '                    "low": None,\n'
            '                    "change_percent": None,\n'
            '                    "volume": None,\n'
            '                },\n'
            '            }\n'
            '    except Exception as e:\n'
            '        print(f"[AVISO] Bacen SGS: {e} (apos retries). Fallback TV...")'
        ),
    },
    # ---- 3. Retry tambem no fallback TV (bloco inteiro) ----
    {
        "nome": "tv_fallback_com_retry",
        "ancora_antiga": (
            '        req = urllib.request.Request(\n'
            '            "https://scanner.tradingview.com/global/scan",\n'
            '            data=data,\n'
            '            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},\n'
            '        )\n'
            '        with urllib.request.urlopen(req, timeout=10) as resp:\n'
            '            res = json.loads(resp.read().decode("utf-8"))\n'
            '            vals = res.get("data", [])[0].get("d", [])\n'
            '            if vals and vals[0] is not None:\n'
            '                return {\n'
            '                    "ativo": "USD_PTAX",\n'
            '                    "fonte": "TRADINGVIEW_FALLBACK",\n'
            '                    "timestamp": timestamp,\n'
            '                    "status": "OK",\n'
            '                    "dados_reais": {\n'
            '                        "close": float(vals[0]),\n'
            '                        "open": None,\n'
            '                        "high": None,\n'
            '                        "low": None,\n'
            '                        "change_percent": None,\n'
            '                        "volume": None,\n'
            '                    },\n'
            '                }'
        ),
        "ancora_nova": (
            '        body = _fetch_url_com_retry(\n'
            '            "https://scanner.tradingview.com/global/scan",\n'
            '            data=data,\n'
            '            tentativas=2,\n'
            '            timeout=10,\n'
            '            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},\n'
            '        )\n'
            '        res = json.loads(body.decode("utf-8"))\n'
            '        vals = res.get("data", [])[0].get("d", [])\n'
            '        if vals and vals[0] is not None:\n'
            '            return {\n'
            '                "ativo": "USD_PTAX",\n'
            '                "fonte": "TRADINGVIEW_FALLBACK",\n'
            '                "timestamp": timestamp,\n'
            '                "status": "OK",\n'
            '                "dados_reais": {\n'
            '                    "close": float(vals[0]),\n'
            '                    "open": None,\n'
            '                    "high": None,\n'
            '                    "low": None,\n'
            '                    "change_percent": None,\n'
            '                    "volume": None,\n'
            '                },\n'
            '            }'
        ),
    },
]


def pre_validar(conteudo):
    for patch in PATCHES:
        n = conteudo.count(patch["ancora_antiga"])
        if n == 0:
            print(f"ABORTADO: ancora nao encontrada: {patch['nome']}")
            print("---primeiras 200 chars---")
            print(patch["ancora_antiga"][:200])
            print("---")
            return False
        if n > 1:
            print(f"ABORTADO: ancora ambigua ({n}x): {patch['nome']}")
            return False
    return True


def aplicar(conteudo):
    for patch in PATCHES:
        conteudo = conteudo.replace(patch["ancora_antiga"], patch["ancora_nova"], 1)
        print(f"OK: patch aplicado: {patch['nome']}")
    return conteudo


def validar_sintaxe(conteudo):
    try:
        compile(conteudo, str(ARQ), "exec")
    except SyntaxError as e:
        print(f"ABORTADO: sintaxe invalida: {e}")
        return False
    print("OK: sintaxe validada")
    return True


def mostrar_diff(antes, depois):
    print("\n--- DRY-RUN: diff ---")
    for linha in difflib.unified_diff(
        antes.splitlines(), depois.splitlines(),
        lineterm="", fromfile="antes", tofile="depois",
    ):
        print(linha)
    print("--- DRY-RUN: nada foi salvo ---")


def reverter():
    backups = sorted(ARQ.parent.glob(f"{ARQ.name}.bak_*"))
    if not backups:
        print("ERRO: nenhum backup encontrado")
        sys.exit(1)
    ultimo = backups[-1]
    shutil.copy(ultimo, ARQ)
    print(f"OK: revertido de {ultimo.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        reverter()
        return

    if not ARQ.exists():
        print(f"ERRO: {ARQ} nao encontrado")
        sys.exit(1)

    original = ARQ.read_text(encoding="utf-8")
    if not pre_validar(original):
        sys.exit(1)

    novo = aplicar(original)
    if not validar_sintaxe(novo):
        sys.exit(1)

    if args.dry_run:
        mostrar_diff(original, novo)
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ARQ.parent / f"{ARQ.name}.bak_{ts}"
    shutil.copy(ARQ, backup)
    print(f"OK: backup={backup.name}")
    ARQ.write_text(novo, encoding="utf-8")
    print(f"OK: {ARQ} atualizado")


if __name__ == "__main__":
    main()