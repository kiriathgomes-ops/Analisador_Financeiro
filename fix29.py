"""
fix29.py — V2 Orchestrator consome AnaliseGraficaSMC_MTF.json

Opcao 2 (modificador de confianca):
    O V2 continua lendo o SMC M5 como fonte de DIRECAO.
    O MTF entra como MODIFICADOR DE CONFIANCA antes do teste de
    CONFIANCA_MINIMA_CONFLUENCIA (55).

Mudancas:
    A) config.py
       - Adiciona FILE_SMC_MTF
       - Adiciona MODIFICADOR_MTF (dict veredito -> delta)

    B) v2/core/engines/v2_orchestrator.py
       - Importa FILE_SMC_MTF + MODIFICADOR_MTF
       - _ler_smc aceita mtf_dados opcional -> retorna veredito_mtf
       - _verificar_confluencia aplica delta antes do teste de confianca
       - Call site carrega MTF e passa pra _ler_smc

Uso:
    python fix29.py --dry-run
    python fix29.py
    python fix29.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO_CONFIG = ROOT / "config.py"
ALVO_ORQ = ROOT / "v2" / "core" / "engines" / "v2_orchestrator.py"

# ---------------------------------------------------------------------------
# PATCHES config.py
# ---------------------------------------------------------------------------
CFG_ANTIGO = (
    'FILE_SMC_REGRAS = COLETAS_DIR / "AnaliseGraficaSMC_Regras.json"\n'
)

CFG_NOVO = '''FILE_SMC_REGRAS = COLETAS_DIR / "AnaliseGraficaSMC_Regras.json"
FILE_SMC_MTF = COLETAS_DIR / "AnaliseGraficaSMC_MTF.json"

# Modificador de confianca SMC por veredito multi-timeframe.
# Aplicado ANTES de comparar com CONFIANCA_MINIMA_CONFLUENCIA (55).
# Opcao 2: o MTF refina a confianca, nao sobrescreve a direcao.
MODIFICADOR_MTF = {
    "ALINHADO_FORTE": +10,
    "PULLBACK": 0,
    "REVERSAO_MICRO_MEDIO": -10,
    "CONFLITO_MACRO": -25,
    "DIVERGENTE": -40,
    "NEUTRO": -15,
}
'''

PATCHES_CONFIG = [
    ("adiciona FILE_SMC_MTF + MODIFICADOR_MTF", CFG_ANTIGO, CFG_NOVO),
]

# ---------------------------------------------------------------------------
# PATCHES v2_orchestrator.py
# ---------------------------------------------------------------------------

# 1) Imports
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

# 2) Assinatura de _ler_smc
ORQ_LER_SIG_ANTIGO = (
    '    def _ler_smc(self, smc_dados: dict) -> Dict[str, Any]:\n'
)

ORQ_LER_SIG_NOVO = (
    '    def _ler_smc(self, smc_dados: dict, mtf_dados: Optional[dict] = None) -> Dict[str, Any]:\n'
)

# 3) Adiciona veredito_mtf no retorno de _ler_smc
ORQ_LER_RET_ANTIGO = '''            "order_blocks": smc_dados.get("order_blocks", []) or [],
            "fvgs": smc_dados.get("fair_value_gaps", []) or [],
'''

ORQ_LER_RET_NOVO = '''            "order_blocks": smc_dados.get("order_blocks", []) or [],
            "fvgs": smc_dados.get("fair_value_gaps", []) or [],
            "veredito_mtf": (
                ((mtf_dados or {}).get("confluencia") or {}).get("veredito_mtf")
            ),
'''

# 4) Aplica delta de confianca em _verificar_confluencia
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

# 5) Call site: carrega MTF
ORQ_LOAD_ANTIGO = (
    '        smc_dados = self._carregar_json_defensivo(FILE_SMC_REGRAS)\n'
)

ORQ_LOAD_NOVO = (
    '        smc_dados = self._carregar_json_defensivo(FILE_SMC_REGRAS)\n'
    '        mtf_dados = self._carregar_json_defensivo(FILE_SMC_MTF)\n'
)

# 6) Call site: passa MTF pra _ler_smc
ORQ_CALL_ANTIGO = (
    '            smc = self._ler_smc(smc_dados)\n'
)

ORQ_CALL_NOVO = (
    '            smc = self._ler_smc(smc_dados, mtf_dados)\n'
)

PATCHES_ORQ = [
    ("importa FILE_SMC_MTF + MODIFICADOR_MTF", ORQ_IMP_ANTIGO, ORQ_IMP_NOVO),
    ("_ler_smc aceita mtf_dados", ORQ_LER_SIG_ANTIGO, ORQ_LER_SIG_NOVO),
    ("_ler_smc retorna veredito_mtf", ORQ_LER_RET_ANTIGO, ORQ_LER_RET_NOVO),
    ("_verificar_confluencia aplica delta MTF", ORQ_CONF_ANTIGO, ORQ_CONF_NOVO),
    ("call site carrega FILE_SMC_MTF", ORQ_LOAD_ANTIGO, ORQ_LOAD_NOVO),
    ("call site passa mtf_dados", ORQ_CALL_ANTIGO, ORQ_CALL_NOVO),
]

# ---------------------------------------------------------------------------


def _backup(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p: Path):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def _aplicar(alvo: Path, patches, dry_run: bool) -> int:
    if not alvo.exists():
        print(f"[ERRO] {alvo} nao encontrado")
        return 1

    conteudo = alvo.read_text(encoding="utf-8")
    novo = conteudo
    faltando = []
    for nome, old, new in patches:
        if old not in novo:
            faltando.append(nome)
            continue
        novo = novo.replace(old, new, 1)
        print(f"  [PATCH OK] {nome}")

    if faltando:
        print(f"\n[ABORT] {alvo.name} — padroes nao encontrados:")
        for f in faltando:
            print(f"    - {f}")
        return 2

    if novo == conteudo:
        print(f"  [INFO] {alvo.name}: nada mudou.")
        return 0

    if dry_run:
        print(f"  [DRY-RUN] {alvo.name}: nao salvo.")
        return 0

    bak = _backup(alvo)
    print(f"  [BACKUP] {bak.name}")
    alvo.write_text(novo, encoding="utf-8")
    print(f"  [OK] {alvo.name} atualizado.")
    return 0


def aplicar(dry_run: bool) -> int:
    print(f"\n[ALVO 1] {ALVO_CONFIG.name}")
    r1 = _aplicar(ALVO_CONFIG, PATCHES_CONFIG, dry_run)

    print(f"\n[ALVO 2] {ALVO_ORQ.name}")
    r2 = _aplicar(ALVO_ORQ, PATCHES_ORQ, dry_run)

    if r1 == 0 and r2 == 0:
        print("\n[SUCESSO] fix29 aplicado.")
        return 0
    return max(r1, r2)


def reverter() -> int:
    for alvo in (ALVO_CONFIG, ALVO_ORQ):
        if not alvo.exists():
            print(f"[ERRO] {alvo.name} nao encontrado.")
            continue
        bak = _ultimo_backup(alvo)
        if not bak:
            print(f"[ERRO] {alvo.name}: nenhum backup.")
            continue
        shutil.copy2(bak, alvo)
        print(f"[REVERTER] {alvo.name} restaurado de {bak.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    return reverter() if args.reverter else aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())