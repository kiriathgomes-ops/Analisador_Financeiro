# -*- coding: utf-8 -*-
# pages/99_🗺️_Mapa_Mina.py — Navegador do mapa de dados + fluxo de arquivos.
#
# Le:
#   auditoria/mapa_mina.json   — campos + anomalias + aliases
#   auditoria/mapa_fluxo.json  — fluxo Script <-> JSON (lineage por arquivo)
#
# Abas:
#   1. Campos — busca + detalhes (origens, JSONs, uso por camada)
#   2. Anomalias — órfãos e fantasmas
#   3. Aliases — pares suspeitos
#   4. Fluxo — grafo Script <-> JSON + engenharia reversa

import json
from pathlib import Path
from collections import Counter

import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
MAPA_JSON = RAIZ / "auditoria" / "mapa_mina.json"
FLUXO_JSON = RAIZ / "auditoria" / "mapa_fluxo.json"
LIMITE_EXIBICAO = 100

st.set_page_config(page_title="Mapa da Mina", page_icon="🗺️", layout="wide")


@st.cache_data(ttl=60)
def _load_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_erro": str(e)}


mapa = _load_json(MAPA_JSON)
fluxo_data = _load_json(FLUXO_JSON)

st.title("🗺️ Mapa da Mina — Auditoria de Dados")
st.caption("Navegador do mapeamento de campos + anomalias + aliases + fluxo")

if mapa is None:
    st.error(f"Arquivo não encontrado: `{MAPA_JSON}`")
    st.info("Rode: `python ferramentas/minerador.py`")
    st.stop()

if "_erro" in mapa:
    st.error(f"Erro ao ler JSON: {mapa['_erro']}")
    st.stop()

campos = mapa.get("campos", {})
problemas = mapa.get("problemas", {})
aliases = mapa.get("aliases_estatisticos", [])

orfaos = problemas.get("orfaos", [])
fantasmas = problemas.get("fantasmas", [])

# === SIDEBAR: filtros ===
st.sidebar.header("🔍 Filtros")

todas_origens = Counter()
todas_camadas = Counter()
for info in campos.values():
    for o in info.get("origens", []):
        todas_origens[o] += 1
    for c in info.get("por_camada", {}).keys():
        todas_camadas[c] += 1

origens_sel = st.sidebar.multiselect(
    "Origem (fonte)",
    options=sorted(todas_origens.keys()),
    default=[],
    help="Ex: MT5, TRADINGVIEW, FINNHUB, BRAPI",
)

camadas_sel = st.sidebar.multiselect(
    "Camada",
    options=sorted(todas_camadas.keys()),
    default=[],
    help="Ex: coleta, calculo, consumo",
)

min_leituras = st.sidebar.number_input(
    "Mínimo de leituras",
    min_value=0, max_value=200, value=0, step=1,
)


def passa_filtros(info):
    if origens_sel:
        if not set(info.get("origens", [])) & set(origens_sel):
            return False
    if camadas_sel:
        if not any(c in info.get("por_camada", {}) for c in camadas_sel):
            return False
    if info.get("total_leituras", 0) < min_leituras:
        return False
    return True


campos_filtrados = {k: v for k, v in campos.items() if passa_filtros(v)}

# === MÉTRICAS ===
col1, col2, col3, col4 = st.columns(4)
col1.metric("Campos mapeados", len(campos))
col2.metric("Órfãos", len(orfaos))
col3.metric("Fantasmas", len(fantasmas))
col4.metric("Aliases suspeitos", len(aliases))

if len(campos_filtrados) != len(campos):
    st.info(f"Filtros ativos: **{len(campos_filtrados)}** de {len(campos)} campos")

st.markdown("---")

# === TABS ===
tab_campos, tab_anom, tab_aliases, tab_fluxo = st.tabs(
    ["📋 Campos", "⚠️ Anomalias", "🕵️ Aliases", "🔀 Fluxo"]
)

# ---------- TAB 1: CAMPOS ----------
with tab_campos:
    st.subheader("Busca por campo")

    busca = st.text_input(
        "Filtrar por nome (substring)",
        value="",
        key="busca_campo",
        placeholder="ex: close, pivots, score, gap",
    )

    if busca.strip():
        resultados = {
            k: v for k, v in campos_filtrados.items()
            if busca.lower().strip() in k.lower()
        }
    else:
        resultados = campos_filtrados

    st.caption(f"**{len(resultados)}** campos correspondem")

    ordenados = sorted(
        resultados.items(),
        key=lambda x: -(
            x[1].get("total_leituras", 0) + x[1].get("total_escritas", 0)
        ),
    )

    if len(ordenados) > LIMITE_EXIBICAO:
        st.warning(
            f"Exibindo primeiros {LIMITE_EXIBICAO} de {len(ordenados)}. "
            "Refine a busca ou use os filtros laterais."
        )
        ordenados = ordenados[:LIMITE_EXIBICAO]

    for campo, info in ordenados:
        leituras = info.get("total_leituras", 0)
        escritas = info.get("total_escritas", 0)
        titulo = f"`{campo}` — {leituras} leituras / {escritas} escritas"

        with st.expander(titulo):
            c1, c2 = st.columns(2)

            with c1:
                st.markdown("**Origens**")
                origens = info.get("origens", [])
                if origens:
                    for o in origens:
                        st.markdown(f"- `{o}`")
                else:
                    st.caption("N/A")

                st.markdown("**JSONs onde aparece**")
                em_json = info.get("em_json", [])
                if em_json:
                    for j in em_json[:10]:
                        st.markdown(f"- `{j}`")
                    if len(em_json) > 10:
                        st.caption(f"... +{len(em_json) - 10}")
                else:
                    st.caption("Nenhum")

            with c2:
                st.markdown("**Uso por camada**")
                por_camada = info.get("por_camada", {})
                if not por_camada:
                    st.caption("Sem uso registrado (órfão)")
                else:
                    for camada, dados in por_camada.items():
                        st.markdown(f"**{camada.title()}**")
                        escritas_lista = dados.get("escrita", []) or []
                        leituras_lista = dados.get("leitura", []) or []

                        if escritas_lista:
                            st.caption(f"✍️ {len(escritas_lista)} escritas")
                            for e in escritas_lista[:3]:
                                if isinstance(e, (list, tuple)) and len(e) >= 2:
                                    st.caption(f"    `{e[0]}:{e[1]}`")
                        if leituras_lista:
                            st.caption(f"👁️ {len(leituras_lista)} leituras")
                            for l in leituras_lista[:3]:
                                if isinstance(l, (list, tuple)) and len(l) >= 2:
                                    st.caption(f"    `{l[0]}:{l[1]}`")

# ---------- TAB 2: ANOMALIAS ----------
with tab_anom:
    sub_orfaos, sub_fantasmas = st.tabs(["⚠️ Órfãos", "🚨 Fantasmas"])

    with sub_orfaos:
        st.markdown(
            f"### {len(orfaos)} campos órfãos\n"
            "Coletados em JSONs mas **sem leitura/escrita** no código. "
            "Candidatos a limpeza (ou a `feature inacabada`)."
        )
        if orfaos:
            st.dataframe(
                {"campo": orfaos},
                use_container_width=True,
                height=500,
            )
        else:
            st.success("Nenhum órfão 🎉")

    with sub_fantasmas:
        st.markdown(
            f"### {len(fantasmas)} campos fantasmas\n"
            "**Lidos no código mas nunca coletados/gravados.** "
            "Possíveis bugs silenciosos (leitura retorna `None`). "
            "Ver item 16 do `estado_atual.md` para ruído conhecido."
        )
        if fantasmas:
            st.dataframe(
                {"campo": fantasmas},
                use_container_width=True,
                height=500,
            )
        else:
            st.success("Nenhum fantasma 🎉")

# ---------- TAB 3: ALIASES ----------
with tab_aliases:
    st.markdown(
        f"### {len(aliases)} pares suspeitos de alias\n"
        "**Co-ocorrência ≥ 80% + nome similar.** Pode ser alias real ou "
        "co-ocorrência trivial (mesmo objeto com nomes diferentes). "
        "**Investigar manualmente** — não é bug por si só."
    )

    if aliases:
        df = [
            {"campo_a": a, "campo_b": b, "jaccard": j}
            for a, b, j in aliases
        ]
        st.dataframe(df, use_container_width=True, height=600)
    else:
        st.success("Nenhum alias suspeito 🎉")

# ---------- TAB 4: FLUXO ----------
with tab_fluxo:
    st.subheader("🔀 Fluxo de arquivos (Script ↔ JSON)")

    if fluxo_data is None:
        st.error(f"Arquivo não encontrado: `{FLUXO_JSON}`")
        st.info("Rode: `python ferramentas/mapear_fluxo.py`")
    elif "_erro" in fluxo_data:
        st.error(f"Erro ao ler fluxo: {fluxo_data['_erro']}")
    else:
        fluxo = fluxo_data.get("fluxo", {})

        # Métricas
        total_jsons = len(fluxo)
        total_p = sum(len(i.get("produtores", [])) for i in fluxo.values())
        total_c = sum(len(i.get("consumidores", [])) for i in fluxo.values())

        c1, c2, c3 = st.columns(3)
        c1.metric("JSONs mapeados", total_jsons)
        c2.metric("Produtores (escrita)", total_p)
        c3.metric("Consumidores (leitura)", total_c)

        st.markdown("---")

        # --- Filtro/busca ---
        c_busca, c_modo = st.columns([3, 1])
        with c_busca:
            busca_fluxo = st.text_input(
                "Buscar por JSON ou script",
                placeholder="ex: Dados_Validados, Coletor.py, Metricas",
                key="busca_fluxo",
            ).strip().lower()
        with c_modo:
            modo = st.radio(
                "Modo",
                ["Todos", "Só com produtor", "Só sem produtor"],
                horizontal=False,
                key="modo_fluxo",
            )

        # Filtra
        itens = []
        for json_path, info in fluxo.items():
            nome = json_path.split("/")[-1]
            n_p = len(info.get("produtores", []))
            n_c = len(info.get("consumidores", []))

            if modo == "Só com produtor" and n_p == 0:
                continue
            if modo == "Só sem produtor" and n_p > 0:
                continue

            if busca_fluxo:
                # Busca no nome do JSON ou em qualquer script mencionado
                scripts = set()
                for p in info.get("produtores", []):
                    scripts.add(p.get("arquivo", ""))
                for c in info.get("consumidores", []):
                    scripts.add(c.get("arquivo", ""))
                alvo = f"{json_path} {' '.join(scripts)}".lower()
                if busca_fluxo not in alvo:
                    continue

            itens.append((json_path, info, n_p, n_c))

        itens.sort(key=lambda x: (-x[2], -x[3]))
        st.caption(f"**{len(itens)}** JSONs correspondem")

        # --- Detalhes por JSON ---
        for json_path, info, n_p, n_c in itens[:LIMITE_EXIBICAO]:
            nome = json_path.split("/")[-1]
            flag = "✅" if n_p > 0 else "⚠️"
            titulo = f"{flag} `{nome}` — {n_p} produtores / {n_c} consumidores"

            with st.expander(titulo):
                # Timestamp do JSON no disco (se existir)
                path_fisico = RAIZ / json_path
                if path_fisico.exists():
                    try:
                        mtime = path_fisico.stat().st_mtime
                        from datetime import datetime as _dt
                        ts_str = _dt.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                        st.caption(f"📅 Última modificação no disco: `{ts_str}`")
                    except Exception:
                        pass
                else:
                    st.caption("📅 Arquivo não existe no disco (fantasma)")

                c_prod, c_cons = st.columns(2)

                with c_prod:
                    st.markdown(f"**✍️ Produtores ({n_p})**")
                    produtores = info.get("produtores", [])
                    if produtores:
                        for p in produtores:
                            arq = p.get("arquivo", "?")
                            linha = p.get("linha", 0)
                            texto = p.get("texto", "")[:100]
                            if linha > 0:
                                st.markdown(f"- `{arq}:{linha}`")
                            else:
                                st.markdown(f"- `{arq}` _(multi-linha)_")
                            st.caption(f"    {texto}")
                    else:
                        st.caption("Nenhum produtor detectado")

                with c_cons:
                    st.markdown(f"**👁️ Consumidores ({n_c})**")
                    consumidores = info.get("consumidores", [])
                    if consumidores:
                        for c in consumidores[:20]:
                            arq = c.get("arquivo", "?")
                            linha = c.get("linha", 0)
                            if linha > 0:
                                st.markdown(f"- `{arq}:{linha}`")
                            else:
                                st.markdown(f"- `{arq}` _(multi-linha)_")
                        if len(consumidores) > 20:
                            st.caption(f"... +{len(consumidores) - 20}")
                    else:
                        st.caption("Nenhum consumidor detectado")

        if len(itens) > LIMITE_EXIBICAO:
            st.warning(
                f"Exibindo primeiros {LIMITE_EXIBICAO} de {len(itens)} JSONs. "
                "Refine a busca."
            )

        # --- Grafo Mermaid ---
        st.markdown("---")
        with st.expander("📊 Diagrama completo (Mermaid)"):
            st.markdown(
                "Cole o conteúdo de `auditoria/mapa_fluxo.mmd` em "
                "[mermaid.live](https://mermaid.live) pra ver o grafo interativo."
            )
            mmd_path = RAIZ / "auditoria" / "mapa_fluxo.mmd"
            if mmd_path.exists():
                st.code(mmd_path.read_text(encoding="utf-8"), language="text")

# === RODAPÉ ===
st.markdown("---")
st.caption(
    f"Fontes: `auditoria/mapa_mina.json` + `auditoria/mapa_fluxo.json` | "
    f"Atualize com: `python ferramentas/minerador.py` + `python ferramentas/mapear_fluxo.py`"
)