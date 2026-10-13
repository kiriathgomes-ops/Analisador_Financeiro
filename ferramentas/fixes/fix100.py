# -*- coding: utf-8 -*-
"""
fix100 — Adiciona rotacao automatica ao Historico_MT5

Comportamento:
  - Mantem os ultimos DIAS_RETENCAO_RAW dias (default 7) em Historico_MT5/ como arquivos brutos
  - Arquivos mais antigos sao agrupados por mes em Historico_MT5/arquivo/YYYY-MM.zip
  - Chamada no fim de salvar_json() do Coletor_MT5_v2_2.py — idempotente, nao trava pipeline

Uso:
    python ferramentas/fixes/fix100.py              # dry-run
    python ferramentas/fixes/fix100.py --aplicar    # aplica
    python ferramentas/fixes/fix100.py --reverter   # restaura ultimo backup
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
ARQUIVO = BASE_DIR / "Coletor_MT5_v2_2.py"
BACKUP_DIR = BASE_DIR / "ferramentas" / "fixes" / "backups"


# ==============================================================================
# BLOCO DE ROTACAO — inserido antes de def salvar_json(dados):
# ==============================================================================
BLOCO_ROTACAO = '''# ================================================================
# ROTACAO DE HISTORICO (fix100)
# ================================================================

DIAS_RETENCAO_RAW = 7
HISTORICO_ARQUIVO_DIR = os.path.join(HISTORICO_DIR, "arquivo")


def _rotacionar_historico():
    """
    Mantem os ultimos DIAS_RETENCAO_RAW dias em Historico_MT5/ como arquivos brutos.
    Arquivos mais antigos sao agrupados por mes em Historico_MT5/arquivo/YYYY-MM.zip.

    - Idempotente: pode rodar multiplas vezes sem problema.
    - Nao trava: se falhar, loga warning e segue.
    - Nao deleta dados: tudo vai pro zip antes de ser removido.
    """
    import zipfile
    import glob
    from datetime import timedelta

    try:
        if not os.path.isdir(HISTORICO_DIR):
            return

        os.makedirs(HISTORICO_ARQUIVO_DIR, exist_ok=True)

        limite_dt = datetime.now() - timedelta(days=DIAS_RETENCAO_RAW)
        arquivos = glob.glob(os.path.join(HISTORICO_DIR, "MT5_v2_2_*.json"))

        antigos_por_mes = {}
        for arq in arquivos:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(arq))
            except OSError:
                continue
            if mtime >= limite_dt:
                continue
            mes = mtime.strftime("%Y-%m")
            antigos_por_mes.setdefault(mes, []).append(arq)

        for mes, lista in antigos_por_mes.items():
            zip_path = os.path.join(HISTORICO_ARQUIVO_DIR, f"{mes}.zip")
            try:
                with zipfile.ZipFile(zip_path, "a", zipfile.ZIP_DEFLATED) as zf:
                    nomes_existentes = set(zf.namelist())
                    for arq in lista:
                        nome = os.path.basename(arq)
                        if nome in nomes_existentes:
                            continue
                        zf.write(arq, nome)

                # So deleta originais se o zip foi criado/atualizado com sucesso
                for arq in lista:
                    try:
                        os.remove(arq)
                    except OSError as e:
                        print(f"[ROTACAO] Aviso: nao removi {arq}: {e}")
            except Exception as e:
                print(f"[ROTACAO] Aviso: falha zipando {mes}: {e}")

        if antigos_por_mes:
            total = sum(len(v) for v in antigos_por_mes.values())
            print(f"[ROTACAO] {total} arquivo(s) rotacionado(s) para {len(antigos_por_mes)} zip(s)")

    except Exception as e:
        print(f"[ROTACAO] Aviso: falha geral: {e}")


'''


# ==============================================================================
# PATCHES — pares (de, para)
# ==============================================================================
PATCHES = [
    # Patch 1: insere BLOCO_ROTACAO antes de "def salvar_json(dados):"
    (
        "def salvar_json(dados):",
        BLOCO_ROTACAO + "def salvar_json(dados):",
    ),
    # Patch 2: adiciona chamada de _rotacionar_historico antes de "return arquivo_historico"
    (
        "    with open(\n"
        "        arquivo_historico,\n"
        '        "w",\n'
        '        encoding="utf-8"\n'
        "    ) as arquivo:\n"
        "\n"
        "        json.dump(\n"
        "            dados,\n"
        "            arquivo,\n"
        "            ensure_ascii=False,\n"
        "            indent=4\n"
        "        )\n"
        "\n"
        "    return arquivo_historico\n",
        "    with open(\n"
        "        arquivo_historico,\n"
        '        "w",\n'
        '        encoding="utf-8"\n'
        "    ) as arquivo:\n"
        "\n"
        "        json.dump(\n"
        "            dados,\n"
        "            arquivo,\n"
        "            ensure_ascii=False,\n"
        "            indent=4\n"
        "        )\n"
        "\n"
        "    # fix100: rotacao automatica (mantem N dias brutos, zipa o resto por mes)\n"
        "    _rotacionar_historico()\n"
        "\n"
        "    return arquivo_historico\n",
    ),
]


# ==============================================================================
# HELPERS
# ==============================================================================
def _backup() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = BACKUP_DIR / f"coletor_mt5_pre_fix100_{ts}.bak"
    shutil.copy2(ARQUIVO, destino)
    return destino


def _reverter():
    backups = sorted(BACKUP_DIR.glob("coletor_mt5_pre_fix100_*.bak"))
    if not backups:
        print("❌ Nenhum backup encontrado em", BACKUP_DIR)
        sys.exit(1)
    ultimo = backups[-1]
    shutil.copy2(ultimo, ARQUIVO)
    print(f"✅ Revertido a partir de {ultimo.name}")


def _ja_aplicado(conteudo: str) -> bool:
    """Idempotencia: se ja tem _rotacionar_historico no arquivo, pula tudo."""
    return "fix100" in conteudo and "_rotacionar_historico" in conteudo


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="fix100 — rotacao automatica do Historico_MT5")
    parser.add_argument("--aplicar", action="store_true", help="aplica de verdade")
    parser.add_argument("--reverter", action="store_true", help="restaura ultimo backup")
    args = parser.parse_args()

    if args.reverter:
        _reverter()
        return

    if not ARQUIVO.exists():
        print(f"❌ {ARQUIVO} nao encontrado")
        sys.exit(1)

    conteudo = ARQUIVO.read_text(encoding="utf-8")

    if _ja_aplicado(conteudo):
        print("✅ fix100 ja aplicado (idempotente). Nada a fazer.")
        return

    dry_run = not args.aplicar
    modo = "🔴 APLICANDO" if args.aplicar else "🟡 DRY-RUN"

    print("=" * 70)
    print(f" fix100 — ROTACAO DE HISTORICO_MT5 — {modo}")
    print("=" * 70)
    print(f" Arquivo: {ARQUIVO.relative_to(BASE_DIR)}")
    print(f" Linhas antes: {len(conteudo.splitlines())}")
    print()

    # Backup
    if not dry_run:
        backup_path = _backup()
        print(f" 📦 Backup: {backup_path.relative_to(BASE_DIR)}")
        print()

    # Aplica patches em memoria
    atual = conteudo
    relatorio = []
    for idx, (de, para) in enumerate(PATCHES, start=1):
        if de not in atual:
            relatorio.append({"patch": idx, "status": "❌ NAO ENCONTRADO", "linhas_add": 0})
            continue
        ocorrencias = atual.count(de)
        if ocorrencias > 1:
            relatorio.append({"patch": idx, "status": f"⚠️ {ocorrencias} ocorrencias", "linhas_add": 0})
            continue

        linhas_add = para.count("\n") - de.count("\n")
        if not dry_run:
            atual = atual.replace(de, para, 1)
        relatorio.append({
            "patch": idx,
            "status": "✅ aplicado" if not dry_run else "🟡 aplicaria",
            "linhas_add": linhas_add,
        })

    linhas_depois = len(atual.splitlines())

    print(f"{'PATCH':<8} {'STATUS':<25} {'LINHAS ADD':>12}")
    print("-" * 70)
    for r in relatorio:
        print(f"#{r['patch']:<7} {r['status']:<25} {r['linhas_add']:>12}")

    print()
    print("=" * 70)
    print(f" Linhas antes:  {len(conteudo.splitlines())}")
    print(f" Linhas depois: {linhas_depois} (+{linhas_depois - len(conteudo.splitlines())})")
    print("=" * 70)

    if not dry_run:
        ARQUIVO.write_text(atual, encoding="utf-8")
        print()
        print(f" ✅ Arquivo salvo: {ARQUIVO.relative_to(BASE_DIR)}")
        print(f" 💡 Para reverter: python ferramentas/fixes/fix100.py --reverter")
    else:
        print()
        print(" 💡 Para aplicar de verdade:")
        print("    python ferramentas/fixes/fix100.py --aplicar")


if __name__ == "__main__":
    main()