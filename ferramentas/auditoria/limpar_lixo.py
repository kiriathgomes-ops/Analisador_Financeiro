# -*- coding: utf-8 -*-
"""
Script de limpeza de lixo acumulado no projeto.

Uso:
    python ferramentas/auditoria/limpar_lixo.py              # dry-run (padrão)
    python ferramentas/auditoria/limpar_lixo.py --aplicar    # executa

Alvos:
  1. docs/dump_completo/            → deletar (regenerável via gerar_dump_completo.py)
  2. Coletas/ArquivosApp.py         → deletar (regenerável)
  3. Coletas/monitor_2_completo*.png → deletar (3 cópias antigas)
  4. auditoria/*.json                → zipar em arquivo_morto/
  5. Coletas/Historico_Decisoes_V2_PRE_FIX66/ → zipar em arquivo_morto/
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


BASE_DIR = Path(__file__).resolve().parents[2]
ARQUIVO_MORTO = BASE_DIR / "ferramentas" / "auditoria" / "arquivo_morto"


def _human(kb: float) -> str:
    if kb < 1024:
        return f"{kb:.1f} KB"
    return f"{kb/1024:.2f} MB"


def _tamanho_pasta(p: Path) -> int:
    if not p.exists():
        return 0
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def _deletar(caminho: Path, aplicar: bool) -> dict:
    if not caminho.exists():
        return {"alvo": str(caminho), "acao": "SKIP (não existe)", "bytes": 0}
    if caminho.is_dir():
        tam = _tamanho_pasta(caminho)
    else:
        tam = caminho.stat().st_size
    if aplicar:
        if caminho.is_dir():
            shutil.rmtree(caminho)
        else:
            caminho.unlink()
        return {"alvo": str(caminho.relative_to(BASE_DIR)), "acao": "DELETADO", "bytes": tam}
    return {"alvo": str(caminho.relative_to(BASE_DIR)), "acao": "DELETARIA", "bytes": tam}


def _zipar(caminho: Path, nome_zip: str, aplicar: bool) -> dict:
    if not caminho.exists():
        return {"alvo": str(caminho), "acao": "SKIP (não existe)", "bytes": 0}

    tam_orig = _tamanho_pasta(caminho) if caminho.is_dir() else caminho.stat().st_size
    ARQUIVO_MORTO.mkdir(parents=True, exist_ok=True)
    destino = ARQUIVO_MORTO / nome_zip

    if aplicar:
        with ZipFile(destino, "w", ZIP_DEFLATED) as zf:
            if caminho.is_dir():
                for f in caminho.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(caminho.parent))
            else:
                zf.write(caminho, caminho.name)

        # Após zipar, deleta o original
        if caminho.is_dir():
            shutil.rmtree(caminho)
        else:
            caminho.unlink()

        tam_zip = destino.stat().st_size
        return {
            "alvo": str(caminho.relative_to(BASE_DIR)),
            "acao": f"ZIPADO → {destino.name} ({_human(tam_zip/1024)})",
            "bytes": tam_orig,
        }
    return {
        "alvo": str(caminho.relative_to(BASE_DIR)),
        "acao": f"ZIPARIA em {nome_zip}",
        "bytes": tam_orig,
    }


def main():
    parser = argparse.ArgumentParser(description="Limpeza de lixo acumulado")
    parser.add_argument("--aplicar", action="store_true", help="executa de verdade (padrão: dry-run)")
    args = parser.parse_args()

    aplicar = args.aplicar
    modo = "🔴 APLICANDO" if aplicar else "🟡 DRY-RUN (nada será deletado)"

    print("=" * 70)
    print(f" LIMPEZA DE LIXO — {modo}")
    print("=" * 70)
    print()

    data_hoje = datetime.now().strftime("%Y-%m-%d")
    resultados = []

    # 1. docs/dump_completo/
    resultados.append(_deletar(BASE_DIR / "docs" / "dump_completo", aplicar))

    # 2. Coletas/ArquivosApp.py
    resultados.append(_deletar(BASE_DIR / "Coletas" / "ArquivosApp.py", aplicar))

    # 3. PNGs antigos
    for png in (BASE_DIR / "Coletas").glob("monitor_2_completo*.png"):
        resultados.append(_deletar(png, aplicar))

    # 4. auditoria/*.json → zipar
    for js in (BASE_DIR / "auditoria").glob("*.json") if (BASE_DIR / "auditoria").exists() else []:
        resultados.append(
            _zipar(js, f"auditoria_{js.stem}_{data_hoje}.zip", aplicar)
        )

    # 5. Historico_Decisoes_V2_PRE_FIX66 → zipar (grande)
    resultados.append(
        _zipar(
            BASE_DIR / "Coletas" / "Historico_Decisoes_V2_PRE_FIX66",
            f"Historico_Decisoes_V2_PRE_FIX66_{data_hoje}.zip",
            aplicar,
        )
    )

    # Relatório
    total_bytes = 0
    print(f"{'AÇÃO':<45} {'TAMANHO':>12}")
    print("-" * 70)
    for r in resultados:
        tam_str = _human(r["bytes"] / 1024) if r["bytes"] else "—"
        print(f"{r['acao']:<45} {tam_str:>12}")
        print(f"   ↳ {r['alvo']}")
        total_bytes += r["bytes"]

    print()
    print("=" * 70)
    print(f" TOTAL LIBERÁVEL: {_human(total_bytes / 1024)}")
    print("=" * 70)
    if not aplicar:
        print()
        print("💡 Para aplicar de verdade:")
        print("   python ferramentas/auditoria/limpar_lixo.py --aplicar")


if __name__ == "__main__":
    main()