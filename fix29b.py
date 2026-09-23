"""
fix29b.py — v2_orchestrator.py: aplica patch faltante do fix29
           (call site passa mtf_dados) + confirma que os 4 patches
           anteriores foram salvos.

O fix29 abortou em v2_orchestrator.py porque o padrao do call site
tinha indentacao de 12 espacos (errada) em vez de 8 (correta).
Este script:
    1. Reaplica TODOS os patches do fix29 em v2_orchestrator.py,
       com o padrao do call site corrigido.
    2. Faz verificacao pos-aplicacao dos 6 patches.
    3. Se ainda faltar algum, aborta sem salvar.

config.py ja foi atualizado pelo fix29 — nao mexemos nele aqui.

Uso:
    python fix29b.py --dry-run
    python fix29b.py
    python fix29b.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "v2" / "core" / "engines" / "v2_orchestrator.py"

# --- imports ---
ORQ_IMP_ANTIGO = '''from config import (
    FILE_DECISAO_V2,
    FILE_UNIFICADO,
    FILE_SMC_REGRAS,
    FILE_ESTIMATIVA_ABERTURA,
    FILE_NOTICIAS_IMPACTO,
    HISTORICO_DECISOES_V2_DIR,
)
'''

ORQ_IMP_NOVO = '''from config import (
    FILE_DECISAO_V2,
    FILE_UNIFICADO,
    FILE_SMC_REGRAS,
    FILE_SMC_MTF,
    MODIFICADOR_MTF,
    FILE_ESTIMATIVA_ABERTURA,
    FILE_NOTICIAS_IMPACTO,
    HISTORICO_DECISOES_V2_DIR,
)
'''

# --- _ler_smc assinatura ---
ORQ_LER_SIG_ANTIGO = (
    '    def _ler_smc(self, smc_dados: dict) -> Dict[str, Any]:\n'
)

ORQ_LER_SIG_NOVO = (
    '    def _ler_smc(self, smc_dados: dict, mtf_dados: Optional[dict] = None) -> Dict[str, Any]:\n'
)

# --- _ler_smc retorno ---
ORQ_LER_RET_ANTIGO = '''            "order_blocks": smc_dados.get("order_blocks", []) or [],
            "fvgs": smc_dados.get("fair_value_gaps", []) or [],
'''

ORQ_LER_RET_NOVO = '''            "order_blocks": smc_dados.get("order_blocks", []) or [],
            "fvgs": smc_dados.get("fair_value_gaps", []) or [],
            "veredito_mtf": (
                ((mtf_dados or {}).get("confluencia") or {}).get("veredito_mtf")
            ),
'''

# --- _verificar_confluencia: aplica delta ---
ORQ_CONF_ANTIGO = '''        smc_dir = smc["direcao"]
        smc_conf = smc["confianca"]
'''

ORQ_CONF_NOVO = '''        smc_dir = smc["direcao"]
        smc_conf_bruta = smc["confianca"]
        _delta_mtf = MODIFICADOR_MTF.get(smc.get("veredito_mtf") or "", 0)
        smc_conf = max(0.0, min(100.0, smc_conf_bruta + _delta_mtf))
        if _delta_mtf:
            motivos.append(
                f"MTF [{smc.get('veredito_mtf')}]: confianca SMC "
                f"{smc_conf_bruta:.0f}% -> {smc_conf:.0f}% ({_delta_mtf:+d})"
            )
'''

# --- call site: carrega MTF ---
ORQ_LOAD_ANTIGO = (
    '        smc_dados = self._carregar_json_defensivo(FILE_SMC_REGRAS)\n'
)

ORQ_LOAD_NOVO = (
    '        smc_dados = self._carregar_json_defensivo(FILE_SMC_REGRAS)\n'
    '        mtf_dados = self._carregar_json_defensivo(FILE_SMC_MTF)\n'
)

# --- call site: passa mtf_dados (INDENTACAO CORRIGIDA: 8 espacos) ---
ORQ_CALL_ANTIGO = (
    '        smc = self._ler_smc(smc_dados)\n'
)

ORQ_CALL_NOVO = (
    '        smc = self._ler_smc(smc_dados, mtf_dados)\n'
)

PATCHES = [
    ("importa FILE_SMC_MTF + MODIFICADOR_MTF", ORQ_IMP_ANTIGO, ORQ_IMP_NOVO),
    ("_ler_smc aceita mtf_dados", ORQ_LER_SIG_ANTIGO, ORQ_LER_SIG_NOVO),
    ("_ler_smc retorna veredito_mtf", ORQ_LER_RET_ANTIGO, ORQ_LER_RET_NOVO),
    ("_verificar_confluencia aplica delta MTF", ORQ_CONF_ANTIGO, ORQ_CONF_NOVO),
    ("call site carrega FILE_SMC_MTF", ORQ_LOAD_ANTIGO, ORQ_LOAD_NOVO),
    ("call site passa mtf_dados (8sp)", ORQ_CALL_ANTIGO, ORQ_CALL_NOVO),
]


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
        print(f"[ERRO] {ALVO.name} nao encontrado em {ALVO.parent}")
        return 1

    conteudo = ALVO.read_text(encoding="utf-8")
    novo = conteudo
    faltando = []
    for nome, old, new in PATCHES:
        if old not in novo:
            faltando.append(nome)
            continue
        novo = novo.replace(old, new, 1)
        print(f"  [PATCH OK] {nome}")

    if faltando:
        print(f"\n[ABORT] padroes nao encontrados:")
        for f in faltando:
            print(f"    - {f}")
        return 2

    # --- verificacao pos-aplicacao ---
    checks = [
        ("FILE_SMC_MTF", "FILE_SMC_MTF" in novo),
        ("MODIFICADOR_MTF importado", "MODIFICADOR_MTF" in novo),
        ("veredito_mtf no retorno", '"veredito_mtf"' in novo),
        ("delta MTF aplicado", "_delta_mtf" in novo),
        ("call site com mtf_dados", "self._ler_smc(smc_dados, mtf_dados)" in novo),
    ]
    print("\n[VERIFICACAO POS]")
    for nome, ok in checks:
        print(f"  [{'OK' if ok else 'FALHOU'}] {nome}")

    if not all(ok for _, ok in checks):
        print("\n[ABORT] verificacao pos falhou — nada salvo.")
        return 3

    if novo == conteudo:
        print("[INFO] nada mudou.")
        return 0

    if dry_run:
        print("\n[DRY-RUN] nada salvo.")
        return 0

    bak = _backup(ALVO)
    print(f"\n[BACKUP] {bak.name}")
    ALVO.write_text(novo, encoding="utf-8")
    print(f"[OK] {ALVO.name} atualizado.")
    return 0


def reverter() -> int:
    if not ALVO.exists():
        print(f"[ERRO] {ALVO.name} nao encontrado.")
        return 1
    bak = _ultimo_backup(ALVO)
    if not bak:
        print("[ERRO] nenhum backup.")
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