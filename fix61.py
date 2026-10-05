# -*- coding: utf-8 -*-
# fix61.py — Instrumentacao honesta do funil (fix61) + semantica do NM (fix62).
#
# PROBLEMA 1 (fix61 — instrumentacao):
#   Early returns em _verificar_confluencia nao preenchem _debug_confluencia.
#   Resultado: payload mostra nm_conf=100 e confianca_final=None, sugerindo
#   "NM aprovou com forca maxima e algo misterioso barrou". Na verdade a funcao
#   saiu por um return antes de calcular confianca_final (ex: divergencia
#   interna do NM em 05/10/2026).
#
# PROBLEMA 2 (fix62 — semantica):
#   nm_conf e magnitude (abs(score_signed) clipado em [0,100]), nao confianca.
#   Satura em 100 sem distinguir +101 de +500, e abs() apaga o sinal.
#   Payload deve expor "nm_magnitude" sem remover "nm_conf" (retrocompat).
#
# Uso:
#   python fix61.py --fase 1 --dry-run    # valida fix61
#   python fix61.py --fase 1              # aplica fix61
#   python fix61.py --fase 2 --dry-run    # valida fix62 (requer fase 1 aplicada)
#   python fix61.py --fase 2              # aplica fix62
#   python fix61.py --fase all            # aplica fix61 + fix62
#   python fix61.py --reverter            # restaura backup mais recente

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQUIVO = Path("v2/core/engines/v2_orchestrator.py")

# ============================================================
# FASE 1 — Instrumentacao honesta (fix61)
# ============================================================

PATCHES_FASE1 = [
    {
        "nome": "f1_debug_inicial_motivo_saida",
        "ancora_antiga": (
            '            "confianca_final": None,\n'
            '            "passou_gate_confluencia": ('
        ),
        "ancora_nova": (
            '            "confianca_final": None,\n'
            '            "motivo_saida": None,\n'
            '            "passou_gate_confluencia": ('
        ),
    },
    {
        "nome": "f1_smc_neutro",
        "ancora_antiga": (
            '        if smc_dir == "NEUTRO":\n'
            '            motivos.append("SMC sem direção definida (LATERAL/NEUTRO)")\n'
            '            return False, "NEUTRO", None, 0.0, motivos, riscos'
        ),
        "ancora_nova": (
            '        if smc_dir == "NEUTRO":\n'
            '            motivos.append("SMC sem direção definida (LATERAL/NEUTRO)")\n'
            '            self._debug_confluencia["motivo_saida"] = "smc_neutro"\n'
            '            self._debug_confluencia["confianca_final"] = 0.0\n'
            '            return False, "NEUTRO", None, 0.0, motivos, riscos'
        ),
    },
    {
        "nome": "f1_smc_conf_baixa",
        "ancora_antiga": (
            '            motivos.append(\n'
            '                f"SMC com confiança baixa ({smc_conf:.0f}% < {CONFIANCA_MINIMA_CONFLUENCIA:.0f}%)"\n'
            '            )\n'
            '            return False, "NEUTRO", None, smc_conf, motivos, riscos'
        ),
        "ancora_nova": (
            '            motivos.append(\n'
            '                f"SMC com confiança baixa ({smc_conf:.0f}% < {CONFIANCA_MINIMA_CONFLUENCIA:.0f}%)"\n'
            '            )\n'
            '            self._debug_confluencia["motivo_saida"] = "smc_conf_baixa"\n'
            '            self._debug_confluencia["confianca_final"] = float(smc_conf)\n'
            '            return False, "NEUTRO", None, smc_conf, motivos, riscos'
        ),
    },
    {
        "nome": "f1_nm_indisponivel",
        "ancora_antiga": (
            '            motivos.append("NOVO_MOTOR indisponível — sem confluência")\n'
            '            riscos.append("NOVO_MOTOR não retornou previsão")\n'
            '            return False, "NEUTRO", None, smc_conf * 0.5, motivos, riscos'
        ),
        "ancora_nova": (
            '            motivos.append("NOVO_MOTOR indisponível — sem confluência")\n'
            '            riscos.append("NOVO_MOTOR não retornou previsão")\n'
            '            self._debug_confluencia["motivo_saida"] = "nm_indisponivel"\n'
            '            self._debug_confluencia["confianca_final"] = float(smc_conf * 0.5)\n'
            '            return False, "NEUTRO", None, smc_conf * 0.5, motivos, riscos'
        ),
    },
    {
        "nome": "f1_nm_divergencia_interna",
        "ancora_antiga": (
            '                "Sem convicção — não operar."\n'
            '            )\n'
            '            return False, "NEUTRO", None, 0.0, motivos, riscos'
        ),
        "ancora_nova": (
            '                "Sem convicção — não operar."\n'
            '            )\n'
            '            self._debug_confluencia["motivo_saida"] = "nm_divergencia_interna"\n'
            '            self._debug_confluencia["confianca_final"] = 0.0\n'
            '            return False, "NEUTRO", None, 0.0, motivos, riscos'
        ),
    },
    {
        "nome": "f1_confianca_final_abaixo_minimo",
        "ancora_antiga": (
            '                motivos.append(\n'
            '                    f"⚠️ Confiança final {confianca_final:.1f}% < "\n'
            '                    f"mínimo {CONFIANCA_MINIMA_FINAL:.0f}% — não opera"\n'
            '                )\n'
            '                return False, "NEUTRO", None, confianca_final, motivos, riscos'
        ),
        "ancora_nova": (
            '                motivos.append(\n'
            '                    f"⚠️ Confiança final {confianca_final:.1f}% < "\n'
            '                    f"mínimo {CONFIANCA_MINIMA_FINAL:.0f}% — não opera"\n'
            '                )\n'
            '                self._debug_confluencia["motivo_saida"] = "confianca_final_abaixo_minimo"\n'
            '                return False, "NEUTRO", None, confianca_final, motivos, riscos'
        ),
    },
    {
        "nome": "f1_ok",
        "ancora_antiga": (
            '            motivos.append(f"✅ Confluência confirmada em {smc_dir}")\n'
            '            return True, smc_dir, smc_dir, confianca_final, motivos, riscos'
        ),
        "ancora_nova": (
            '            motivos.append(f"✅ Confluência confirmada em {smc_dir}")\n'
            '            self._debug_confluencia["motivo_saida"] = "ok"\n'
            '            return True, smc_dir, smc_dir, confianca_final, motivos, riscos'
        ),
    },
    {
        "nome": "f1_divergencia_smc_nm",
        "ancora_antiga": (
            '            "Aguardar alinhamento antes de operar."\n'
            '        )\n'
            '        return False, "NEUTRO", None, 0.0, motivos, riscos'
        ),
        "ancora_nova": (
            '            "Aguardar alinhamento antes de operar."\n'
            '        )\n'
            '        self._debug_confluencia["motivo_saida"] = "divergencia_smc_nm"\n'
            '        self._debug_confluencia["confianca_final"] = 0.0\n'
            '        return False, "NEUTRO", None, 0.0, motivos, riscos'
        ),
    },
]

# ============================================================
# FASE 2 — Semantica do NM (fix62) — requer fase 1 aplicada
# ============================================================

PATCHES_FASE2 = [
    {
        "nome": "f2_debug_inicial_nm_campos",
        "ancora_antiga": (
            '            "confianca_final": None,\n'
            '            "motivo_saida": None,\n'
            '            "passou_gate_confluencia": ('
        ),
        "ancora_nova": (
            '            "confianca_final": None,\n'
            '            "motivo_saida": None,\n'
            '            "nm_magnitude": None,\n'
            '            "nm_direcao_score": None,\n'
            '            "nm_divergencia_interna": None,\n'
            '            "passou_gate_confluencia": ('
        ),
    },
    {
        "nome": "f2_preencher_nm_campos",
        "ancora_antiga": (
            '        nm_conf = novo_motor["confianca"]\n'
            '        # fix57: guarda nm_conf pro payload\n'
            '        self._debug_confluencia["nm_conf"] = float(nm_conf)'
        ),
        "ancora_nova": (
            '        nm_conf = novo_motor["confianca"]\n'
            '        # fix57: guarda nm_conf pro payload\n'
            '        self._debug_confluencia["nm_conf"] = float(nm_conf)\n'
            '        # fix62: nm_conf e magnitude (|score| clipado), nao confianca direcional.\n'
            '        # Mantido "nm_conf" por retrocompat de backtest; "nm_magnitude" e o nome honesto.\n'
            '        self._debug_confluencia["nm_magnitude"] = float(nm_conf)\n'
            '        self._debug_confluencia["nm_direcao_score"] = nm_score_dir\n'
            '        self._debug_confluencia["nm_divergencia_interna"] = bool(\n'
            '            novo_motor.get("divergencia_direcao")\n'
            '        )'
        ),
    },
]


# ============================================================
# Infra
# ============================================================

def pre_validar(conteudo, patches):
    for patch in patches:
        antiga = patch["ancora_antiga"]
        n = conteudo.count(antiga)
        if n == 0:
            print(f"ABORTADO: ancora nao encontrada: {patch['nome']}")
            print("---")
            print(antiga)
            print("---")
            return False
        if n > 1:
            print(f"ABORTADO: ancora ambigua ({n}x): {patch['nome']}")
            return False
    return True


def aplicar(conteudo, patches):
    for patch in patches:
        conteudo = conteudo.replace(patch["ancora_antiga"], patch["ancora_nova"], 1)
        print(f"OK: patch aplicado: {patch['nome']}")
    return conteudo


def validar_sintaxe(conteudo):
    try:
        compile(conteudo, str(ARQUIVO), "exec")
    except SyntaxError as e:
        print(f"ABORTADO: sintaxe invalida apos patch: {e}")
        return False
    print("OK: sintaxe validada")
    return True


def mostrar_diff(antes, depois):
    print("\n--- DRY-RUN: diff ---")
    diff = difflib.unified_diff(
        antes.splitlines(),
        depois.splitlines(),
        lineterm="",
        fromfile="antes",
        tofile="depois",
    )
    for linha in diff:
        print(linha)
    print("--- DRY-RUN: nada foi salvo ---")


def reverter():
    backups = sorted(ARQUIVO.parent.glob(f"{ARQUIVO.name}.bak_*"))
    if not backups:
        print("ERRO: nenhum backup encontrado")
        sys.exit(1)
    ultimo = backups[-1]
    shutil.copy(ultimo, ARQUIVO)
    print(f"OK: revertido de {ultimo.name}")


def aplicar_fase(numero, patches, dry_run):
    print(f"\n===== FASE {numero} =====")
    if not ARQUIVO.exists():
        print(f"ERRO: {ARQUIVO} nao encontrado")
        sys.exit(1)

    original = ARQUIVO.read_text(encoding="utf-8")

    if not pre_validar(original, patches):
        sys.exit(1)

    novo = aplicar(original, patches)

    if not validar_sintaxe(novo):
        sys.exit(1)

    if dry_run:
        mostrar_diff(original, novo)
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ARQUIVO.parent / f"{ARQUIVO.name}.bak_{ts}"
    shutil.copy(ARQUIVO, backup)
    print(f"OK: backup criado: {backup.name}")

    ARQUIVO.write_text(novo, encoding="utf-8")
    print(f"OK: {ARQUIVO} atualizado (fase {numero})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fase", choices=["1", "2", "all"], default="1")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        reverter()
        return

    if args.fase in ("1", "all"):
        aplicar_fase(1, PATCHES_FASE1, args.dry_run)

    if args.fase in ("2", "all"):
        aplicar_fase(2, PATCHES_FASE2, args.dry_run)


if __name__ == "__main__":
    main()