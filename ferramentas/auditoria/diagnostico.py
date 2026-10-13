# -*- coding: utf-8 -*-
"""
diagnostico.py — Auditoria recorrente do Analisador Financeiro.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = BASE_DIR / "docs"

IGNORAR_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".pytest_cache", ".idea", ".vscode", "arquivo_morto",
    "backups", "_legado", "lixeira_analise",
}

FRESHNESS_MAP = {
    "Decisao_V2.json":                          (10,  "CRITICO"),
    "DadosAtivosUnificados.json":               (10,  "CRITICO"),
    "Dados_Validados.json":                     (10,  "CRITICO"),
    "Dados_MT5_v2_2.json":                      (10,  "CRITICO"),
    "Coleta_rom-0.json":                        (10,  "CRITICO"),
    "Coleta_ram.json":                          (10,  "CRITICO"),
    "Metricas_Calculadas.json":                 (10,  "CRITICO"),
    "Analise_Tendencias.json":                  (10,  "ALTO"),
    "AnaliseGraficaSMC_Regras.json":            (15,  "ALTO"),
    "AnaliseGraficaSMC_MTF.json":               (15,  "ALTO"),
    "EstimativaAbertura.json":                  (10,  "ALTO"),
    "Resultado_Calculadora_Operacional_Abertura.json": (10, "ALTO"),
    "Noticias_Calendario.json":                 (24*60, "BAIXO"),
    "Noticias_Impacto_Dia.json":                (24*60, "BAIXO"),
    "config_regiao.json":                       (365*24*60, "ESTATICO"),
    "LastTick_Congelado.json":                  (365*24*60, "ESTATICO"),
    "EstimativaAbertura_Cache.json":            (24*60, "BAIXO"),
}


# ==============================================================================
# HELPERS
# ==============================================================================
def _iter_arquivos(skip_ignorados: bool = True):
    for p in BASE_DIR.rglob("*"):
        if not p.is_file():
            continue
        if skip_ignorados and any(part in IGNORAR_DIRS for part in p.parts):
            continue
        yield p


def _human_kb(kb: float) -> str:
    if kb < 1024:
        return f"{kb:.1f} KB"
    return f"{kb/1024:.2f} MB"


def _sep(titulo: str):
    print()
    print("=" * 78)
    print(f" {titulo}")
    print("=" * 78)


# ==============================================================================
# SUBCOMANDO: INVENTARIO
# ==============================================================================
def cmd_inventario() -> str:
    linhas = []
    linhas.append("## 1. Inventário\n")

    por_pasta: dict[str, dict] = {}
    for p in _iter_arquivos():
        pasta = p.parent.name or "(raiz)"
        info = por_pasta.setdefault(pasta, {"count": 0, "bytes": 0})
        info["count"] += 1
        try:
            info["bytes"] += p.stat().st_size
        except OSError:
            pass

    ordenado = sorted(por_pasta.items(), key=lambda kv: kv[1]["count"], reverse=True)

    print(f"{'PASTA':<45} {'ARQS':>6} {'TAMANHO':>12}")
    print("-" * 78)
    linhas.append("| Pasta | Arquivos | Tamanho |")
    linhas.append("|---|---:|---:|")

    for pasta, info in ordenado[:30]:
        tam = _human_kb(info["bytes"] / 1024)
        print(f"{pasta:<45} {info['count']:>6} {tam:>12}")
        linhas.append(f"| `{pasta}` | {info['count']} | {tam} |")

    print()
    print(f"{'TOP 30 MAIORES ARQUIVOS':<45} {'KB':>10} {'MODIFICADO':>18}")
    print("-" * 78)
    linhas.append("\n### Top 30 maiores arquivos\n")
    linhas.append("| Arquivo | KB | Modificado |")
    linhas.append("|---|---:|---|")

    todos = []
    for p in _iter_arquivos():
        try:
            st = p.stat()
            todos.append((p, st.st_size, st.st_mtime))
        except OSError:
            continue
    todos.sort(key=lambda x: x[1], reverse=True)

    for p, tam, mtime in todos[:30]:
        rel = str(p.relative_to(BASE_DIR))
        kb = tam / 1024
        dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        print(f"{rel:<45} {kb:>10.1f} {dt:>18}")
        linhas.append(f"| `{rel}` | {kb:.1f} | {dt} |")

    return "\n".join(linhas)


# ==============================================================================
# SUBCOMANDO: INTEGRIDADE
# ==============================================================================
def cmd_integridade() -> str:
    linhas = []
    linhas.append("## 2. Integridade\n")

    # --- Python: compila em memória (não escreve .pyc) ---
    print("### Compilando .py (em memória)")
    print("-" * 78)
    pys = [p for p in _iter_arquivos() if p.suffix == ".py"]
    erros_py = []
    for p in pys:
        try:
            source = p.read_text(encoding="utf-8")
            compile(source, str(p), "exec")
        except SyntaxError as e:
            erros_py.append((p.relative_to(BASE_DIR), f"linha {e.lineno}: {e.msg}"[:120]))
        except UnicodeDecodeError as e:
            erros_py.append((p.relative_to(BASE_DIR), f"encoding: {e}"[:120]))
        except Exception as e:
            erros_py.append((p.relative_to(BASE_DIR), f"{type(e).__name__}: {e}"[:120]))

    if erros_py:
        print(f"❌ {len(erros_py)} de {len(pys)} arquivos .py com erro:")
        linhas.append(f"\n❌ **{len(erros_py)} de {len(pys)} arquivos .py com erro:**\n")
        for rel, err in erros_py:
            print(f"   {rel}: {err}")
            linhas.append(f"- `{rel}`: {err}")
    else:
        print(f"✅ {len(pys)} arquivos .py compilam OK")
        linhas.append(f"\n✅ **{len(pys)} arquivos .py compilam OK**")

    # --- JSON: parseia ---
    print()
    print("### Parseando .json")
    print("-" * 78)
    jsons = [p for p in _iter_arquivos() if p.suffix == ".json"]
    erros_json = []
    total_bytes = 0
    for p in jsons:
        try:
            with open(p, "r", encoding="utf-8") as f:
                json.load(f)
            total_bytes += p.stat().st_size
        except json.JSONDecodeError as e:
            erros_json.append((p.relative_to(BASE_DIR), f"linha {e.lineno}: {e.msg}"[:120]))
        except Exception as e:
            erros_json.append((p.relative_to(BASE_DIR), f"{type(e).__name__}: {e}"[:120]))

    if erros_json:
        print(f"❌ {len(erros_json)} de {len(jsons)} arquivos .json com erro:")
        linhas.append(f"\n❌ **{len(erros_json)} de {len(jsons)} arquivos .json com erro:**\n")
        for rel, err in erros_json:
            print(f"   {rel}: {err}")
            linhas.append(f"- `{rel}`: {err}")
    else:
        print(f"✅ {len(jsons)} arquivos .json parseiam OK ({_human_kb(total_bytes/1024)} no total)")
        linhas.append(f"\n✅ **{len(jsons)} arquivos .json parseiam OK** ({_human_kb(total_bytes/1024)})")

    return "\n".join(linhas)


# ==============================================================================
# SUBCOMANDO: FRESHNESS
# ==============================================================================
def cmd_freshness() -> str:
    linhas = []
    linhas.append("## 3. Freshness dos JSONs de produção\n")

    coletas = BASE_DIR / "Coletas"
    agora = datetime.now()

    print(f"{'ARQUIVO':<50} {'IDADE':>10} {'LIMITE':>10} {'STATUS':>10}")
    print("-" * 78)
    linhas.append("| Arquivo | Idade | Limite | Status |")
    linhas.append("|---|---:|---:|---|")

    problemas = []

    for nome, (limite_min, criticidade) in FRESHNESS_MAP.items():
        caminho = coletas / nome
        if not caminho.exists():
            print(f"{nome:<50} {'—':>10} {f'{limite_min}m':>10} {'AUSENTE':>10}")
            linhas.append(f"| `{nome}` | — | {limite_min}m | 🔴 AUSENTE |")
            problemas.append((nome, "AUSENTE", criticidade))
            continue

        idade = (agora - datetime.fromtimestamp(caminho.stat().st_mtime)).total_seconds() / 60

        if criticidade == "ESTATICO":
            status = "✅ OK"
        elif idade > limite_min * 3:
            status = "🔴 STALE"
            problemas.append((nome, f"{idade:.0f}m", criticidade))
        elif idade > limite_min:
            status = "🟡 ATRASADO"
            problemas.append((nome, f"{idade:.0f}m", criticidade))
        else:
            status = "✅ OK"

        if idade < 60:
            idade_str = f"{idade:.0f}m"
        elif idade < 60 * 24:
            idade_str = f"{idade/60:.1f}h"
        else:
            idade_str = f"{idade/60/24:.1f}d"

        print(f"{nome:<50} {idade_str:>10} {f'{limite_min}m':>10} {status:>10}")
        linhas.append(f"| `{nome}` | {idade_str} | {limite_min}m | {status} |")

    if problemas:
        linhas.append(f"\n⚠️ **{len(problemas)} arquivo(s) com problema:**\n")
        for nome, idade, crit in problemas:
            linhas.append(f"- `{nome}` ({crit}) — {idade}")

    return "\n".join(linhas)


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Diagnóstico do Analisador Financeiro")
    parser.add_argument("--inventario", action="store_true")
    parser.add_argument("--integridade", action="store_true")
    parser.add_argument("--freshness", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    if not any([args.inventario, args.integridade, args.freshness, args.full]):
        parser.print_help()
        sys.exit(0)

    inicio = datetime.now()
    partes = []
    partes.append(f"# Diagnóstico — {inicio.strftime('%Y-%m-%d %H:%M')}\n")
    partes.append(f"Gerado por `ferramentas/auditoria/diagnostico.py`\n")

    if args.inventario or args.full:
        _sep("1. INVENTÁRIO")
        partes.append(cmd_inventario())

    if args.integridade or args.full:
        _sep("2. INTEGRIDADE")
        partes.append(cmd_integridade())

    if args.freshness or args.full:
        _sep("3. FRESHNESS")
        partes.append(cmd_freshness())

    dur = (datetime.now() - inicio).total_seconds()
    _sep(f"CONCLUÍDO EM {dur:.1f}s")

    if args.full:
        DOCS_DIR.mkdir(exist_ok=True)
        destino = DOCS_DIR / f"diagnostico_{inicio.strftime('%Y-%m-%d')}.md"
        destino.write_text("\n\n".join(partes), encoding="utf-8")
        print(f"\n📄 Relatório salvo: {destino.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()