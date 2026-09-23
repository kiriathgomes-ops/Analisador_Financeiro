"""
fix21.py — analisar_rompimento_10h.py

Bugs corrigidos:
    1. SIMBOLOS_MT5 era hardcoded ["WINV26", "WINZ26", "WIN$"].
       Agora le Coletas/Dados_MT5_v2_2.json -> ativos.WIN.contrato_principal
       e cai nos contratos_vigentes como reserva.
    2. qtd=100 velas M5 (~8h) nao cobria 10:00 quando o dia ja avancou.
       Agora qtd=500 (~41h) com fallback de ate 7 dias uteis.
    3. Sem fallback de dia: se hoje fosse feriado/fim de semana, Bloco E
       saia como [NAO DISPONIVEL]. Agora busca o ultimo dia util.
    4. Sem log [DIAG]: nao se sabia o range obtido por simbolo.
       Agora imprime [DIAG] <simbolo> qtd=500: N barras, <ini> -> <fim>.

Uso:
    python fix21.py --dry-run
    python fix21.py
    python fix21.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "analisar_rompimento_10h.py"

# ---------------------------------------------------------------------------
# PATCHES
# ---------------------------------------------------------------------------

PATCH_IMPORT_ANTIGO = (
    "from datetime import datetime, time as dt_time\n"
)

PATCH_IMPORT_NOVO = (
    "from datetime import datetime, time as dt_time, timedelta\n"
)

PATCH_SIMBOLOS_ANTIGO = (
    "# Simbolos candidatos para buscar a vela M5 no MT5\n"
    'SIMBOLOS_MT5 = ["WINV26", "WINZ26", "WIN$"]\n'
)

PATCH_SIMBOLOS_NOVO = '''# Fallback estatico — a lista real vem de Coletas/Dados_MT5_v2_2.json
SIMBOLOS_MT5_FALLBACK = ["WINV26", "WINZ26", "WIN$"]
JSON_MT5 = COLETAS_DIR / "Dados_MT5_v2_2.json"


def _descobrir_contrato_vigente():
    """
    Le Coletas/Dados_MT5_v2_2.json e retorna a lista de simbolos a testar
    no MT5. Prioriza ativos.WIN.contrato_principal e completa com
    contratos_vigentes (na ordem). Se falhar, usa o fallback estatico.
    """
    try:
        if JSON_MT5.exists():
            with open(JSON_MT5, "r", encoding="utf-8") as f:
                data = json.load(f)
            win = ((data.get("ativos") or {}).get("WIN") or {})
            principal = win.get("contrato_principal")
            simbolos = []
            if principal:
                simbolos.append(principal)
            for c in (win.get("contratos_vigentes") or []):
                nome = c.get("contrato")
                if nome and nome not in simbolos:
                    simbolos.append(nome)
            if simbolos:
                print(f"[DIAG] Contrato vigente do JSON: {principal}")
                print(f"[DIAG] Simbolos a testar: {simbolos}")
                return simbolos
    except Exception as e:
        print(f"[DIAG] Falha ao ler {JSON_MT5}: {e}")
    print(f"[DIAG] Usando fallback estatico: {SIMBOLOS_MT5_FALLBACK}")
    return list(SIMBOLOS_MT5_FALLBACK)
'''

PATCH_VELA_ANTIGO = '''def obter_vela_10h():
    """Busca a vela M5 de 10:00 no MT5. Retorna dict ou None."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[AVISO] MetaTrader5 nao instalado. Use --vela-manual.")
        return None

    if not mt5.initialize():
        print(f"[AVISO] MT5 nao inicializou: {mt5.last_error()}")
        return None

    try:
        hoje = datetime.now().date()
        for simbolo in SIMBOLOS_MT5:
            info = mt5.symbol_info(simbolo)
            if info is None:
                continue
            if not info.visible:
                mt5.symbol_select(simbolo, True)

            rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M5, 0, 100)
            if rates is None or len(rates) == 0:
                continue

            # Procura a vela com hora 10:00 de hoje
            for r in rates:
                dt = datetime.fromtimestamp(r["time"])
                if dt.date() == hoje and dt.hour == 10 and dt.minute == 0:
                    agora = datetime.now()
                    # Se a vela esta em formacao (agora < 10:05)
                    em_formacao = agora.time() < dt_time(10, 5)
                    return {
                        "simbolo": simbolo,
                        "time": dt.isoformat(),
                        "open": float(r["open"]),
                        "high": float(r["high"]),
                        "low": float(r["low"]),
                        "close": float(r["close"]),
                        "volume": float(r["tick_volume"]),
                        "status": "EM_FORMACAO" if em_formacao else "FECHADA",
                    }

        print(f"[AVISO] Vela 10:00 de hoje nao encontrada no MT5.")
        return None
    finally:
        mt5.shutdown()
'''

PATCH_VELA_NOVO = '''def obter_vela_10h():
    """Busca a vela M5 de 10:00 no MT5. Retorna dict ou None."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[AVISO] MetaTrader5 nao instalado. Use --vela-manual.")
        return None

    if not mt5.initialize():
        print(f"[AVISO] MT5 nao inicializou: {mt5.last_error()}")
        return None

    try:
        simbolos = _descobrir_contrato_vigente()
        hoje = datetime.now().date()

        # Tenta hoje e cai para ate 7 dias uteis anteriores se nao achar
        # (fim de semana, feriado, ou rodada fora da janela do pregao).
        for offset_dias in range(0, 7):
            alvo = hoje - timedelta(days=offset_dias)
            for simbolo in simbolos:
                info = mt5.symbol_info(simbolo)
                if info is None:
                    print(f"[DIAG] {simbolo}: symbol_info=None (nao existe)")
                    continue
                if not info.visible:
                    mt5.symbol_select(simbolo, True)

                rates = mt5.copy_rates_from_pos(
                    simbolo, mt5.TIMEFRAME_M5, 0, 500
                )
                if rates is None or len(rates) == 0:
                    print(
                        f"[DIAG] {simbolo}: copy_rates_from_pos "
                        f"retornou vazio (last_error={mt5.last_error()})"
                    )
                    continue

                dt_first = datetime.fromtimestamp(rates[0]["time"])
                dt_last = datetime.fromtimestamp(rates[-1]["time"])
                print(
                    f"[DIAG] {simbolo} qtd=500: {len(rates)} barras, "
                    f"{dt_first.isoformat()} -> {dt_last.isoformat()} "
                    f"(alvo={alvo.isoformat()})"
                )

                for r in rates:
                    dt = datetime.fromtimestamp(r["time"])
                    if (
                        dt.date() == alvo
                        and dt.hour == 10
                        and dt.minute == 0
                    ):
                        agora = datetime.now()
                        em_formacao = agora.time() < dt_time(10, 5)
                        if alvo != hoje:
                            print(
                                f"[DIAG] Vela 10:00 de hoje nao achada; "
                                f"usando ultimo dia util: {alvo.isoformat()}"
                            )
                        return {
                            "simbolo": simbolo,
                            "time": dt.isoformat(),
                            "open": float(r["open"]),
                            "high": float(r["high"]),
                            "low": float(r["low"]),
                            "close": float(r["close"]),
                            "volume": float(r["tick_volume"]),
                            "status": (
                                "EM_FORMACAO" if em_formacao else "FECHADA"
                            ),
                        }

        print(
            "[AVISO] Vela 10:00 nao encontrada nos ultimos 7 dias "
            "em nenhum simbolo testado."
        )
        return None
    finally:
        mt5.shutdown()
'''

PATCHES = [
    ("importa timedelta", PATCH_IMPORT_ANTIGO, PATCH_IMPORT_NOVO),
    (
        "substitui SIMBOLOS_MT5 hardcoded por leitura do JSON",
        PATCH_SIMBOLOS_ANTIGO,
        PATCH_SIMBOLOS_NOVO,
    ),
    (
        "obter_vela_10h: qtd 100->500, fallback ultimo dia util, logs DIAG",
        PATCH_VELA_ANTIGO,
        PATCH_VELA_NOVO,
    ),
]

IGNORAR = {"fix21.py"}

# ---------------------------------------------------------------------------


def _backup(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p: Path):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def aplicar(dry_run: bool) -> int:
    if not ALVO.exists():
        print(f"[ERRO] {ALVO.name} nao encontrado em {ROOT}")
        return 1

    conteudo = ALVO.read_text(encoding="utf-8")
    novo = conteudo

    faltando = []
    for nome, old, new in PATCHES:
        if old not in novo:
            faltando.append(nome)
            continue
        novo = novo.replace(old, new, 1)
        print(f"[PATCH OK] {nome}")

    if faltando:
        print("\n[ABORT] Padroes nao encontrados:")
        for f in faltando:
            print(f"  - {f}")
        print("\nNada foi salvo.")
        return 2

    if novo == conteudo:
        print("[INFO] Nada mudou.")
        return 0

    if dry_run:
        print("\n[DRY-RUN] Nada salvo.")
        return 0

    bak = _backup(ALVO)
    print(f"[BACKUP] {bak.name}")
    ALVO.write_text(novo, encoding="utf-8")
    print(f"[OK] {ALVO.name} atualizado.")
    return 0


def reverter() -> int:
    if not ALVO.exists():
        print(f"[ERRO] {ALVO.name} nao encontrado.")
        return 1
    bak = _ultimo_backup(ALVO)
    if not bak:
        print("[ERRO] Nenhum backup encontrado.")
        return 1
    shutil.copy2(bak, ALVO)
    print(f"[REVERTER] {ALVO.name} restaurado de {bak.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    return reverter() if args.reverter else aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())