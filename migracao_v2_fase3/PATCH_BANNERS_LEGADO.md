# Patches — Banner LEGADO nas páginas de decisão antiga

Colar **logo após** `st.set_page_config(...)` (ou no início do corpo da página, antes de qualquer título).

---

## 1. `pages/1.2_🔮_Previsao_Inteligente_Abertura.py`

```python
st.warning(
    "⚠️ **PÁGINA LEGADO** — A decisão oficial é a **V2** "
    "(`Coletas/Decisao_V2.json` e o menu **🎯 Decisão V2**). "
    "Use esta tela apenas para comparação histórica com o NOVO_MOTOR isolado."
)
```

---

## 2. `pages/1.3_🔮_Previsao_Inteligente_Abertura_Comparador.py`

```python
st.warning(
    "⚠️ **PÁGINA LEGADO** — A decisão oficial é a **V2** "
    "(`Coletas/Decisao_V2.json` e o menu **🎯 Decisão V2**). "
    "Para comparar V1 × V2 use a tela oficial **Comparador V1 × V2**."
)
```

---

## 3. `pages/2.0_📈_Previsao_Abertura_WINFUT.py`

```python
st.warning(
    "⚠️ **PÁGINA LEGADO** — A decisão oficial é a **V2** "
    "(`Coletas/Decisao_V2.json` e o menu **🎯 Decisão V2**). "
    "Esta tela não alimenta mais o fluxo operacional."
)
```

---

## Opcional — helper reutilizável

Se quiser padronizar, crie `utils/legado_ui.py`:

```python
import streamlit as st

def banner_legado(extra: str = "") -> None:
    msg = (
        "⚠️ **PÁGINA LEGADO** — A decisão oficial é a **V2** "
        "(`Coletas/Decisao_V2.json` e o menu **🎯 Decisão V2**)."
    )
    if extra:
        msg = f"{msg} {extra}"
    st.warning(msg)
```

Uso:

```python
from utils.legado_ui import banner_legado
banner_legado("Use apenas para referência histórica.")
```

---

## Checklist rápido após aplicar

- [ ] Menu mostra seção **🎯 Decisão V2 (oficial)** no topo (após Home)
- [ ] `5.3 Core Engine` e páginas `v2/` estão nessa seção
- [ ] `1.2`, `1.3` e `2.0` aparecem em **⚠️ Legado** com prefixo `[LEGADO]`
- [ ] Ao abrir cada legada, o banner amarelo aparece no topo
- [ ] App sobe sem erro (`streamlit run app_home.py`)
