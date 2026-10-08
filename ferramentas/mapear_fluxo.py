# -*- coding: utf-8 -*-
# mapear_fluxo.py — v8: guarda LISTA de atribuicoes por var.
#
# Mudancas v8 (sobre v7):
#   - atribuicoes[v] = [expr1, expr2, ...] em vez de sobrescrever
#   - BFS tenta cada atribuicao ate resolver
#   - Fix: 'caminho = caminho or ARQUIVO_SAIDA' nao e mais perdida

import json
import re
import sys
import glob
from pathlib import Path
from collections import defaultdict

RAIZ = Path(__file__).resolve().parent.parent
OUT_DIR = RAIZ / "auditoria"
OUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(RAIZ))
try:
    import config
except ImportError:
    config = None

MAPA_CONSTANTES = {}
if config:
    for nome in dir(config):
        if nome.startswith("_"):
            continue
        valor = getattr(config, nome)
        if isinstance(valor, Path):
            try:
                rel = str(valor.relative_to(RAIZ)).replace("\\", "/")
                if rel.endswith(".json"):
                    MAPA_CONSTANTES[nome] = rel
            except ValueError:
                pass
        elif isinstance(valor, str) and valor.endswith(".json"):
            v = valor.replace("\\", "/")
            if "Coletas/" in v:
                v = v[v.find("Coletas/"):]
            if v.endswith(".json"):
                MAPA_CONSTANTES[nome] = v

RE_JSON_LITERAL = re.compile(r'["\']([^"\']*Coletas/[^"\']*\.json)["\']')
RE_JSON_NAME = re.compile(r'["\']([A-Za-z0-9_\-]+\.json)["\']')

IGNORAR_ARQ = [
    "__pycache__", ".git", "/fix",
    "/_grep", "/_check", "/_valida", "/_investigar", "/_diag",
    "/ferramentas/", "/auditoria/",
    "/minerador.py", "/mapear_dados.py", "/mapear_fluxo.py",
    ".bak_",
]


def deve_ignorar(rel_path):
    if any(x in rel_path for x in IGNORAR_ARQ):
        return True
    if rel_path.startswith("fix") and rel_path.endswith(".py"):
        return True
    return False


def extrair_json_literal(linha):
    for m in RE_JSON_LITERAL.finditer(linha):
        return m.group(1).replace("\\", "/")
    m = RE_JSON_NAME.search(linha)
    if m:
        nome = m.group(1)
        if any(x in nome for x in ["%", "{", "}", "dummy", "test", "example"]):
            return None
        return f"Coletas/{nome}"
    return None


def resolver_expr_path(expr, tabela_atual=None):
    """v8: resolve expr com 'or', defaults, constantes e cadeias."""
    if tabela_atual is None:
        tabela_atual = {}

    expr = expr.strip()
    while expr.startswith("(") and expr.endswith(")"):
        expr = expr[1:-1].strip()

    # 1. Literal direto
    jp = extrair_json_literal(expr)
    if jp:
        return jp

    # 2. Var pai + literal .json
    m = re.search(
        r'([A-Za-z_][A-Za-z0-9_]*)\s*/\s*["\']([A-Za-z0-9_\-]+\.json)["\']',
        expr,
    )
    if m:
        pai_var = m.group(1)
        nome_json = m.group(2)
        if pai_var == "COLETAS_DIR" or "COLETAS" in pai_var.upper():
            return f"Coletas/{nome_json}"
        if pai_var in tabela_atual:
            base = tabela_atual[pai_var]
            if base.endswith("/"):
                return f"{base}{nome_json}"
            return f"{base}/{nome_json}"
        return f"Coletas/{nome_json}"

    # 3. Constante direta
    for const, path in MAPA_CONSTANTES.items():
        if re.search(rf'\b{re.escape(const)}\b', expr):
            return path

    # 4. Expr com "or"
    if " or " in expr:
        for parte in expr.split(" or "):
            parte = parte.strip()
            if re.match(r'^[A-Za-z_]\w*$', parte):
                p = resolver_expr_path(parte, tabela_atual)
                if p:
                    return p

    # 5. Var ja resolvida
    for m in re.finditer(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', expr):
        nome = m.group(1)
        if nome != "self" and nome in tabela_atual:
            return tabela_atual[nome]

    return None


def colapsar_parenteses_multilinea(texto):
    resultado = []
    i = 0
    n = len(texto)
    while i < n:
        c = texto[i]
        if c == "(":
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if texto[j] == "(":
                    depth += 1
                elif texto[j] == ")":
                    depth -= 1
                j += 1
            if depth == 0:
                conteudo = texto[i:j]
                resultado.append(re.sub(r'\s+', ' ', conteudo))
                i = j
                continue
        resultado.append(c)
        i += 1
    return "".join(resultado)


RE_DEF_PARAM = re.compile(r'def\s+\w+\s*\(([^)]+)\)')
RE_PARAM_DEFAULT = re.compile(r'(\w+)\s*(?::\s*[\w\[\]\s\.]+)?\s*=\s*([^,=]+)')


def construir_tabela_simbolos(linhas):
    """v8: guarda LISTA de atribuicoes por var."""
    tabela = {}
    atribuicoes = defaultdict(list)

    for linha in linhas:
        sem = linha.split("#", 1)[0].strip()
        if not sem:
            continue

        for m in re.finditer(r'\bimport\s+(\w+)\s+as\s+(\w+)', sem):
            orig, alias = m.group(1), m.group(2)
            if orig in MAPA_CONSTANTES:
                tabela[alias] = MAPA_CONSTANTES[orig]

        for m in re.finditer(r'(\w+)\s+as\s+(\w+)', sem):
            orig, alias = m.group(1), m.group(2)
            if orig in MAPA_CONSTANTES:
                tabela[alias] = MAPA_CONSTANTES[orig]

        for m_def in RE_DEF_PARAM.finditer(sem):
            params = m_def.group(1)
            for m_pd in RE_PARAM_DEFAULT.finditer(params):
                var, default = m_pd.group(1), m_pd.group(2).strip()
                if var in ("self", "cls"):
                    continue
                if re.match(r'^[A-Za-z_]\w*$', default) or extrair_json_literal(default):
                    atribuicoes[var].append(default)

        m = re.match(r'(\w+)\s*=\s*(.+)', sem)
        if m:
            var, expr = m.group(1), m.group(2)
            atribuicoes[var].append(expr)

    for _ in range(10):
        mudou = False
        for var, exprs in atribuicoes.items():
            if var in tabela:
                continue
            for expr in exprs:
                p = resolver_expr_path(expr, tabela)
                if p:
                    tabela[var] = p
                    mudou = True
                    break
        if not mudou:
            break

    return tabela


RE_WITH_OPEN = re.compile(r'with\s+open\s*\(([^)]+)\)\s+as\s+\w+')


def escanear_codigo():
    resultado = defaultdict(lambda: {"produtores": [], "consumidores": []})

    for arq in glob.glob(f"{RAIZ}/**/*.py", recursive=True):
        arq_p = Path(arq)
        try:
            rel = str(arq_p.relative_to(RAIZ)).replace("\\", "/")
        except ValueError:
            continue

        if deve_ignorar(rel):
            continue

        try:
            texto_original = arq_p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        linhas = texto_original.splitlines()
        texto_colapsado = colapsar_parenteses_multilinea(texto_original)
        linhas_colapsadas = texto_colapsado.splitlines()

        tabela = construir_tabela_simbolos(linhas_colapsadas)
        cache_vars = dict(tabela)
        for const, path in MAPA_CONSTANTES.items():
            if const not in cache_vars:
                cache_vars[const] = path

        for i, linha in enumerate(linhas, 1):
            sem = linha.split("#", 1)[0]
            if not sem.strip():
                continue

            jsons_aqui = set()
            for m in RE_JSON_LITERAL.finditer(sem):
                jsons_aqui.add(m.group(1).replace("\\", "/"))
            for m in re.finditer(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', sem):
                nome = m.group(1)
                if nome in cache_vars:
                    jsons_aqui.add(cache_vars[nome])

            if not jsons_aqui:
                continue

            tipo = None
            if re.search(r'open\s*\([^)]*,\s*["\']w', sem) or \
               re.search(r'\.write_text\s*\(', sem) or \
               re.search(r'json\.dump\s*\(', sem):
                tipo = "escrita"
            elif re.search(r'open\s*\([^)]*,\s*["\']r', sem) or \
                 re.search(r'\.read_text\s*\(', sem) or \
                 re.search(r'json\.load\s*\(', sem) or \
                 re.search(r'carregar_json', sem):
                tipo = "leitura"

            if not tipo:
                continue

            for jp in jsons_aqui:
                entrada = {"arquivo": rel, "linha": i,
                           "texto": sem.strip()[:130]}
                chave = "produtores" if tipo == "escrita" else "consumidores"
                resultado[jp][chave].append(entrada)

        for i_c, linha_c in enumerate(linhas_colapsadas, 1):
            sem = linha_c.split("#", 1)[0]
            if "with open" not in sem:
                continue

            m = RE_WITH_OPEN.search(sem)
            if not m:
                continue

            args = m.group(1)
            modo_escrita = bool(re.search(r',\s*["\']w', args))
            modo_leitura = bool(re.search(r',\s*["\']r', args))

            if not (modo_escrita or modo_leitura):
                continue

            jsons_open = set()
            for mm in RE_JSON_LITERAL.finditer(args):
                jsons_open.add(mm.group(1).replace("\\", "/"))
            for mm in re.finditer(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', args):
                nome = mm.group(1)
                if nome in cache_vars:
                    jsons_open.add(cache_vars[nome])

            if not jsons_open:
                continue

            tipo = "escrita" if modo_escrita else "leitura"
            chave = "produtores" if tipo == "escrita" else "consumidores"
            for jp in jsons_open:
                ja_tem = any(e["arquivo"] == rel for e in resultado[jp][chave])
                if not ja_tem:
                    resultado[jp][chave].append({
                        "arquivo": rel,
                        "linha": 0,
                        "texto": f"[colapsado] {args.strip()[:100]}",
                    })

    for jp in resultado:
        for kind in ("produtores", "consumidores"):
            visto = set()
            unico = []
            for item in resultado[jp][kind]:
                chave = (item["arquivo"], item["linha"] if item["linha"] > 0 else item["texto"])
                if chave not in visto:
                    visto.add(chave)
                    unico.append(item)
            resultado[jp][kind] = unico

    return dict(resultado)


def gerar_mermaid(fluxo):
    linhas = ["```mermaid", "graph LR"]
    scripts = set()
    jsons = set()
    for path, info in fluxo.items():
        jsons.add(path)
        for p in info["produtores"]:
            scripts.add(p["arquivo"])
        for c in info["consumidores"]:
            scripts.add(c["arquivo"])

    def safe(s):
        return re.sub(r'[^a-zA-Z0-9_]', '_', s)[:50]

    for s in sorted(scripts):
        linhas.append(f'  {safe(s)}["{s}"]')
    for j in sorted(jsons):
        name = j.split("/")[-1]
        linhas.append(f'  {safe(j)}[("{name}")]')
    for j, info in fluxo.items():
        for p in info["produtores"]:
            linhas.append(f'  {safe(p["arquivo"])} --> {safe(j)}')
        for c in info["consumidores"]:
            linhas.append(f'  {safe(j)} --> {safe(c["arquivo"])}')
    linhas.append("```")
    return "\n".join(linhas)


def main():
    print("=" * 70)
    print(" MAPEAMENTO DE FLUXO — JSONs do projeto (v8)")
    print("=" * 70)

    print(f"\nConstantes .json mapeadas no config: {len(MAPA_CONSTANTES)}")
    print(f"\nEscanenado codigo (lista de atribuicoes + or + defaults)...")
    fluxo = escanear_codigo()

    total_p = sum(len(i["produtores"]) for i in fluxo.values())
    total_c = sum(len(i["consumidores"]) for i in fluxo.values())

    print(f"  {len(fluxo)} JSONs com uso detectado")
    print(f"  {total_p} produtores, {total_c} consumidores\n")

    print("=" * 70)
    print(" SUMARIO (P=produtores, C=consumidores)")
    print("=" * 70)

    ordenado = sorted(
        fluxo.keys(),
        key=lambda x: -len(fluxo[x]["produtores"]) - len(fluxo[x]["consumidores"]),
    )

    for path in ordenado:
        info = fluxo[path]
        n_p = len(info["produtores"])
        n_c = len(info["consumidores"])
        nome = path.split("/")[-1]
        flag = "OK" if n_p > 0 else "sem P"
        print(f"  {nome:<48} | {n_p:>3}P | {n_c:>3}C | {flag}")

    (OUT_DIR / "mapa_fluxo.json").write_text(
        json.dumps({
            "fluxo": fluxo,
            "mapa_constantes": MAPA_CONSTANTES,
        }, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )
    (OUT_DIR / "mapa_fluxo.mmd").write_text(
        gerar_mermaid(fluxo), encoding="utf-8"
    )

    print(f"\nGerados:")
    print(f"  auditoria/mapa_fluxo.json")
    print(f"  auditoria/mapa_fluxo.mmd")


if __name__ == "__main__":
    main()