# Fase 3 — Migração de interface (páginas)

**Data:** 27/08/2026  
**Objetivo:** usuário vê **uma** decisão principal (V2); legados marcados ou arquivados.

---

## Status por página

| Página | Status | Ação |
|--------|--------|------|
| `v2/pages/1.1_dashboard_v2.py` | Oficial | Manter |
| `v2/pages/1.2_comparador.py` | Oficial | Manter (já avisa V1 descontinuada) |
| `v2/pages/1.3_analise_detalhada.py` | Oficial | Manter |
| `pages/5.3_⚙️_Core_Engine.py` | Oficial (V2) | **Já migrada** — prioriza `Decisao_V2.json` |
| `pages/1.2_🔮_Previsao_Inteligente_Abertura.py` | Legado | Banner LEGADO + preferir Decisao_V2 se possível |
| `pages/1.3_🔮_Previsao_Inteligente_Abertura_Comparador.py` | Legado | Idem |
| `pages/2.0_📈_Previsao_Abertura_WINFUT.py` | Legado | Migrar para contratos V2 ou redirecionar |
| `pages/1.1_🎯_Setup_Abertura.py` | Operacional | UX: sub-abas (item 3.4) — não bloqueia decisão |

---

## 1. Organização do menu (`app_home.py`)

Hoje o menu mapeia automaticamente **toda** a pasta `pages/` e `v2/pages/`.  
Sugestão: agrupar explicitamente e marcar legados.

### Trecho sugerido (substituir o bloco `estrutura_menu`)

```python
# --- Páginas V2 oficiais (decisão) ---
paginas_decisao_v2 = []
if PASTA_V2.exists():
    for arq in sorted(PASTA_V2.glob("*.py")):
        if arq.name.startswith("__"):
            continue
        rel = arq.relative_to(BASE_DIR).as_posix()
        nome = arq.stem.split("_", 1)[-1].replace("_", " ").strip()
        paginas_decisao_v2.append(
            st.Page(rel, title=nome, icon="🚀")
        )

# --- Core Engine (já V2, pasta pages) ---
core_engine = None
core_path = PASTA_PAGES / "5.3_⚙️_Core_Engine.py"
if core_path.exists():
    core_engine = st.Page(
        core_path.relative_to(BASE_DIR).as_posix(),
        title="Core Engine (V2)",
        icon="⚙️",
    )

# --- Páginas legadas de decisão (banner LEGADO) ---
LEGADO_DECISAO = {
    "1.2_🔮_Previsao_Inteligente_Abertura.py",
    "1.3_🔮_Previsao_Inteligente_Abertura_Comparador.py",
    "2.0_📈_Previsao_Abertura_WINFUT.py",
}

paginas_legado = []
paginas_outras = []
if PASTA_PAGES.exists():
    for arq in sorted(PASTA_PAGES.glob("*.py")):
        if arq.name.startswith("__") or arq.name == "5.3_⚙️_Core_Engine.py":
            continue
        rel = arq.relative_to(BASE_DIR).as_posix()
        nome = arq.stem.replace("_", " ").strip()
        page = st.Page(rel, title=nome, icon="📌")
        if arq.name in LEGADO_DECISAO:
            page = st.Page(rel, title=f"[LEGADO] {nome}", icon="⚠️")
            paginas_legado.append(page)
        else:
            paginas_outras.append(page)

estrutura_menu = {
    "Navegação Principal": [page_home],
}

if paginas_decisao_v2 or core_engine:
    bloco = list(paginas_decisao_v2)
    if core_engine:
        bloco.insert(0, core_engine)
    estrutura_menu["🎯 Decisão V2 (oficial)"] = bloco

if paginas_outras:
    estrutura_menu["Operacional"] = paginas_outras

if paginas_legado:
    estrutura_menu["⚠️ Legado (somente referência)"] = paginas_legado
```

---

## 2. Banner LEGADO (colar no topo das páginas legadas)

```python
st.warning(
    "⚠️ **PÁGINA LEGADO** — A decisão oficial é a **V2** "
    "(`Coletas/Decisao_V2.json` e menu **Decisão V2**). "
    "Use esta tela apenas para comparação histórica."
)
```

Arquivos prioritários para o banner:

- `pages/1.2_🔮_Previsao_Inteligente_Abertura.py`
- `pages/1.3_🔮_Previsao_Inteligente_Abertura_Comparador.py`
- `pages/2.0_📈_Previsao_Abertura_WINFUT.py`

---

## 3. `5.3_Core_Engine` — já OK

Confirmação do código atual:

- Prioriza `Coletas/Decisao_V2.json`
- Mantém `Decisao_Core.json` só como referência
- Exibe auditoria dos contextos V2 (`market_ok`, `prediction_ok`, etc.)

**Nenhuma alteração obrigatória.** Opcional: importar caminhos de `config` em vez de `os.path.join` local.

```python
from config import COLETAS_DIR, FILE_DECISAO_V2  # se existir FILE_DECISAO_V2
# ou
from config import COLETAS_DIR
ARQUIVOS = {
    "decisao_v2": str(COLETAS_DIR / "Decisao_V2.json"),
    ...
}
```

---

## 4. Próximos passos concretos (ordem)

1. Aplicar o **menu agrupado** em `app_home.py` (ganho imediato de clareza).
2. Colar o **banner LEGADO** nas 3 páginas de decisão antiga.
3. (Opcional) Fazer `2.0_Previsao_Abertura_WINFUT` ler `Decisao_V2` / contratos V2 em vez de Engine_Vies.
4. Item 3.4 (sub-abas no Setup Abertura) — UX, pode ficar para depois.

---

## 5. Critério de saída da Fase 3

- [ ] Menu com seção **Decisão V2 (oficial)** em destaque  
- [ ] Páginas legadas com banner e/ou prefixo `[LEGADO]` no título  
- [ ] Usuário não confunde mais 3 “verdades” na UI  
- [x] `5.3` e `v2/pages` já consomem V2  

---

*Guia gerado na continuação da migração — 27/08/2026.*
