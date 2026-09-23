"""
fix30.py — Gerar_Relatorio_Mensagem.py: carrega JSONs DENTRO do executar()

Bug:
    Os carregamentos de JSON estao no nivel de modulo (linhas 34-42).
    Como o main_pipeline faz `import Gerar_Relatorio_Mensagem` no topo,
    os JSONs sao lidos ANTES de qualquer fase rodar. Resultado: o
    relatorio sempre mostra o estado do ciclo ANTERIOR.

Fix:
    Move os carregamentos para dentro de executar(). Assim cada chamada
    le o estado fresco do disco.

Uso:
    python fix30.py --dry-run
    python fix30.py
    python fix30.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Gerar_Relatorio_Mensagem.py"

# ---------------------------------------------------------------------------
# PATCH 1: transforma carregamento em nivel-modulo em funcao
# ---------------------------------------------------------------------------

P_CARGA_ANTIGO = '''unificados = carregar_json("DadosAtivosUnificados.json")
decisao_v2 = carregar_json("Decisao_V2.json")
resultado_operacional = carregar_json("Resultado_Calculadora_Operacional_Abertura.json")
estimativas = carregar_json("EstimativaAbertura.json") or carregar_json("Resultado_Calculadora.json")
smc_dados = carregar_json("AnaliseGraficaSMC_Regras.json")

ativos = unificados.get("ativos", {})
obj_decisao = decisao_v2.get("decisao", {})
meta_decisao = obj_decisao.get("metadados", {})
'''

P_CARGA_NOVO = '''# ATENCAO: os JSONs eram carregados no nivel de modulo (bug).
# Como o main_pipeline importa este modulo no topo, os carregamentos
# rodavam ANTES de qualquer fase executar — o relatorio mostrava sempre
# o estado do ciclo ANTERIOR.
# Agora sao carregados em _carregar_estado(), chamada dentro de executar().

def _carregar_estado():
    """Carrega todos os JSONs frescos e retorna dict com as variaveis."""
    unificados = carregar_json("DadosAtivosUnificados.json")
    decisao_v2 = carregar_json("Decisao_V2.json")
    resultado_operacional = carregar_json("Resultado_Calculadora_Operacional_Abertura.json")
    estimativas = carregar_json("EstimativaAbertura.json") or carregar_json("Resultado_Calculadora.json")
    smc_dados = carregar_json("AnaliseGraficaSMC_Regras.json")

    ativos = unificados.get("ativos", {})
    obj_decisao = decisao_v2.get("decisao", {})
    meta_decisao = obj_decisao.get("metadados", {})

    return {
        "ativos": ativos,
        "obj_decisao": obj_decisao,
        "meta_decisao": meta_decisao,
        "estimativas": estimativas,
        "resultado_operacional": resultado_operacional,
        "smc_dados": smc_dados,
    }

# Placeholders para compatibilidade com funcoes que usam essas vars no
# nivel de modulo (get_preco_str, get_var_str, etc). Serao preenchidos
# por executar() antes de formatar o relatorio.
ativos = {}
obj_decisao = {}
meta_decisao = {}
estimativas = {}
resultado_operacional = {}
smc_dados = {}
'''

# ---------------------------------------------------------------------------
# PATCH 2: preenche as variaveis dentro de executar()
# ---------------------------------------------------------------------------

P_EXEC_ANTIGO = '''def executar():
    print("=" * 60)
    print("🚀 INICIANDO GERADOR DE RELATÓRIO OPERACIONAL EXECUTIVO (V2)")
    print("=" * 60)
    
    agora_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
'''

P_EXEC_NOVO = '''def executar():
    print("=" * 60)
    print("🚀 INICIANDO GERADOR DE RELATÓRIO OPERACIONAL EXECUTIVO (V2)")
    print("=" * 60)

    # --- FIX: carrega JSONs frescos AGORA (nao mais no import) ---
    global ativos, obj_decisao, meta_decisao
    global estimativas, resultado_operacional, smc_dados

    estado = _carregar_estado()
    ativos = estado["ativos"]
    obj_decisao = estado["obj_decisao"]
    meta_decisao = estado["meta_decisao"]
    estimativas = estado["estimativas"]
    resultado_operacional = estado["resultado_operacional"]
    smc_dados = estado["smc_dados"]

    # Recalcula os campos derivados (eram calculados no nivel modulo)
    vies_final = obj_decisao.get("vies_final") or "NEUTRO"
    confianca = obj_decisao.get("confianca", 0)

    agora_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
'''

PATCHES = [
    ("move carga para _carregar_estado()", P_CARGA_ANTIGO, P_CARGA_NOVO),
    ("executar() recarrega estado fresco", P_EXEC_ANTIGO, P_EXEC_NOVO),
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
        print(f"[ERRO] {ALVO.name} nao encontrado")
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