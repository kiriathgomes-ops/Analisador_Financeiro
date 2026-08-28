# ============================================================
# PATCH — app_home.py
# Substituir o bloco de navegação (desde "# 1. Página Principal"
# até "estrutura_menu[...]" inclusive) pelo código abaixo.
#
# Localização aproximada: final do arquivo, antes de
# st.set_page_config / st.navigation / pg.run()
# ============================================================

# 1. Página Principal (Home) declarada como função
page_home = st.Page(
    render_home_page,
    title="Home / Dashboard",
    icon="🏠",
    default=True,
)

# ------------------------------------------------------------
# Páginas legadas de DECISÃO (mostrar com aviso no menu)
# ------------------------------------------------------------
LEGADO_DECISAO = {
    "1.2_🔮_Previsao_Inteligente_Abertura.py",
    "1.3_🔮_Previsao_Inteligente_Abertura_Comparador.py",
    "2.0_📈_Previsao_Abertura_WINFUT.py",
}

# 2. Core Engine (já migrado para V2 — destaque)
core_engine = None
core_path = PASTA_PAGES / "5.3_⚙️_Core_Engine.py"
if core_path.exists():
    core_engine = st.Page(
        core_path.relative_to(BASE_DIR).as_posix(),
        title="Core Engine (V2)",
        icon="⚙️",
    )

# 3. Pasta pages/ — separar operacional vs legado de decisão
paginas_operacional = []
paginas_legado = []
if PASTA_PAGES.exists():
    for arq in sorted(PASTA_PAGES.glob("*.py")):
        if arq.name.startswith("__"):
            continue
        # Core Engine já tratado acima
        if arq.name == "5.3_⚙️_Core_Engine.py":
            continue

        rel_path = arq.relative_to(BASE_DIR).as_posix()
        nome_limpo = arq.stem
        for prefixo in [
            "10_", "4_", "5_", "6_", "7_", "8_", "21_",
            "🎯_", "🔢_", "⚙️_", "🔬_", "📡_", "📊_", "📅_",
            "🤖_", "📥_", "🗺️_", "🔑_", "⚡_", "📈_", "🔮_",
        ]:
            nome_limpo = nome_limpo.replace(prefixo, "")

        titulo = nome_limpo.replace("_", " ").strip()

        if arq.name in LEGADO_DECISAO:
            paginas_legado.append(
                st.Page(rel_path, title=f"[LEGADO] {titulo}", icon="⚠️")
            )
        else:
            paginas_operacional.append(
                st.Page(rel_path, title=titulo, icon="📌")
            )

# 4. Pasta v2/pages/ — decisão oficial
paginas_v2 = []
if PASTA_V2.exists():
    for arq in sorted(PASTA_V2.glob("*.py")):
        if arq.name.startswith("__"):
            continue
        rel_path = arq.relative_to(BASE_DIR).as_posix()
        # títulos mais legíveis
        mapa_titulo = {
            "1.1_dashboard_v2": "Dashboard V2",
            "1.2_comparador": "Comparador V1 × V2",
            "1.3_analise_detalhada": "Análise Detalhada",
        }
        chave = arq.stem
        titulo = mapa_titulo.get(chave, chave.replace("_", " ").title())
        paginas_v2.append(
            st.Page(rel_path, title=titulo, icon="🚀")
        )

# ------------------------------------------------------------
# Estrutura do Menu (ordem de exibição)
# ------------------------------------------------------------
estrutura_menu = {
    "Navegação Principal": [page_home],
}

# Decisão oficial em destaque
bloco_decisao = []
if core_engine is not None:
    bloco_decisao.append(core_engine)
bloco_decisao.extend(paginas_v2)
if bloco_decisao:
    estrutura_menu["🎯 Decisão V2 (oficial)"] = bloco_decisao

# Demais módulos operacionais
if paginas_operacional:
    estrutura_menu["Operacional"] = paginas_operacional

# Legado por último
if paginas_legado:
    estrutura_menu["⚠️ Legado (somente referência)"] = paginas_legado
