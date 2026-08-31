# ARQUIVO: pages/7_🤖_IA_SpikeImagem.py

import json
import os
import re
from pathlib import Path
import PIL.Image
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from google.generativeai.types import HarmBlockThreshold, HarmCategory

# 1. Configuração da Página do Streamlit
st.set_page_config(
    page_title="Analisador SMC/ICT - Spike IA",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Analisador SMT / ICT - Spike IA")
st.write(
    "Gere análises SMC/ICT e scripts NTSL do ProfitChart utilizando as imagens coletadas ou enviando novos prints."
)

# 2. Carregar variáveis de ambiente (.env)
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error(
        "⚠️ Chave 'GEMINI_API_KEY' não encontrada no arquivo .env. Obtenha uma grátis em aistudio.google.com"
    )
    st.stop()

# Configurar chave do Gemini
genai.configure(api_key=api_key)

# Caminho da pasta Coletas
BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_COLETAS = BASE_DIR / "Coletas"


def obter_modelos_disponiveis():
    """Consulta a API do Google e traz APENAS modelos Gemini com suporte a visão."""
    try:
        modelos_validos = []
        for m in genai.list_models():
            nome_modelo = m.name.lower()
            if (
                "generateContent" in m.supported_generation_methods
                and "gemini" in nome_modelo
                and "gemma" not in nome_modelo
                and "2.5" not in nome_modelo
            ):
                modelos_validos.append(m.name)

        if modelos_validos:
            modelos_validos.sort(
                key=lambda x: 0 if "1.5-flash" in x else (1 if "1.5-pro" in x else 2)
            )
            return modelos_validos

        return ["models/gemini-1.5-flash", "models/gemini-1.5-pro"]
    except Exception:
        return ["models/gemini-1.5-flash", "models/gemini-1.5-pro"]


def listar_imagens_coletas():
    """Busca todas as imagens disponíveis na pasta Coletas."""
    if not PASTA_COLETAS.exists():
        return []
    extensoes = ("*.png", "*.jpg", "*.jpeg")
    arquivos = []
    for ext in extensoes:
        arquivos.extend(list(PASTA_COLETAS.glob(ext)))
    
    # Ordena pelos arquivos mais recentes primeiro
    arquivos.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return [arq.name for arq in arquivos]


def selecionar_imagem_por_timeframe(imagens, preferência="htf"):
    """Seleciona dinamicamente a imagem com base nos sufixos e timeframes do nome do arquivo."""
    if not imagens:
        return 0
    
    palavras_htf = ["5min", "15min", "60min", "daily", "diario", "htf", "5m", "15m"]
    palavras_ltf = ["1min", "2min", "3min", "ltf", "1m", "2m", "3m"]

    alvo = palavras_htf if preferência == "htf" else palavras_ltf

    for idx, arq in enumerate(imagens):
        arq_lower = arq.lower()
        if any(p in arq_lower for p in alvo):
            return idx + 1  # +1 por causa da opção "Nenhuma" no dropdown

    return 1 if len(imagens) > 0 else 0


def redimensionar_imagem(img_pil, max_largura=1280):
    """Redimensiona ligeiramente a imagem mantendo alta resolução para leitura de textos minúsculos."""
    largura, altura = img_pil.size
    if largura > max_largura:
        proporcao = max_largura / float(largura)
        nova_altura = int((float(altura) * float(proporcao)))
        return img_pil.resize((max_largura, nova_altura), PIL.Image.Resampling.LANCZOS)
    return img_pil


def extrair_json_puro(texto):
    """Extrai com precisão o bloco JSON da resposta do Gemini."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())

    match_solto = re.search(r"(\{.*\})", texto, re.DOTALL)
    if match_solto:
        return json.loads(match_solto.group(1).strip())

    raise ValueError(
        "Não foi possível localizar uma estrutura JSON válida na resposta do Gemini."
    )


def gerar_script_ntsl_do_json(dados_json):
    """Gera o script NTSL (ProfitChart) dinamicamente a partir dos preços no JSON."""
    linhas_var = []
    linhas_atrib = []
    linhas_plot = []

    for i, item in enumerate(dados_json.get("estruturas_coletadas", [])):
        match = re.match(r"^([\d\.]+)\s*:\s*(.*)$", item)
        if match:
            preco_str = match.group(1).replace(".", "")
            descricao = match.group(2).replace('"', "'")

            var_nome = f"L_Nivel_{i+1}"
            linhas_var.append(f"  {var_nome} : float;")
            linhas_atrib.append(f"  {var_nome} := {preco_str};")

            cor = "clGray"
            if "Supply" in descricao or "Bearish" in descricao or "High" in descricao:
                cor = "clRed"
            elif "Demand" in descricao or "Bullish" in descricao or "Low" in descricao:
                cor = "clGreen"
            elif "EQL" in descricao or "EQH" in descricao or "BSL" in descricao or "SSL" in descricao:
                cor = "clAqua"

            label_curto = (descricao[:20] + "..") if len(descricao) > 20 else descricao
            linhas_plot.append(
                f'  HorizontalLineCustom({var_nome}, {cor}, 1, 0, "{label_curto}", 9, tpTopRight, Date, 0, MinPriceIncrement);'
            )

    script_ntsl = f"""// ==========================================
// SCRIPT GERADO AUTOMATICAMENTE - PROFITCHART (NTSL)
// ==========================================
var
{chr(10).join(linhas_var)}
inicio
{chr(10).join(linhas_atrib)}

{chr(10).join(linhas_plot)}
fim;
"""
    return script_ntsl


def exibir_relatorio_formatado(dados_json):
    """Renderiza na tela do Streamlit o relatório formatado em Markdown bonito."""
    st.markdown("### 1. Relatório de Análise SMT/ICT")
    st.markdown(
        f"**Timeframes Identificados:** {dados_json.get('timeframes_identificados', 'N/A')}"
    )
    st.markdown(
        f"**Bias Direcional (HTF):** {dados_json.get('bias_direcional', 'N/A')}"
    )

    st.markdown("#### Estruturas Coletadas:")
    for est in dados_json.get("estruturas_coletadas", []):
        st.markdown(f"- **{est}**")

    st.markdown("#### Liquidez Relevante:")
    for liq in dados_json.get("liquidez_relevante", []):
        st.markdown(f"- {liq}")

    st.markdown("#### Zonas de Interesse Principais & Cenários Operacionais:")
    for cen in dados_json.get("zonas_de_interesse_e_cenarios", []):
        st.markdown(f"- {cen}")

    st.divider()

    script_ntsl = gerar_script_ntsl_do_json(dados_json)
    st.markdown("### 2. Script de Níveis (ProfitChart / NTSL)")
    st.code(script_ntsl, language="pascal")


def analisar_graficos(image_htf_pil, image_ltf_pil, modelo_nome):
    """Envia os gráficos solicitando estritamente o formato JSON padrão."""

    prompt_smc = """
    Você é um especialista em Smart Money Concepts (SMC) e Inner Circle Trader (ICT).

    SEU OBJETIVO: Mapear TODOS os níveis e preços visíveis nos eixos dos gráficos fornecidos.

    Sua resposta DEVE SER EXCLUSIVAMENTE um bloco JSON válido no seguinte formato exato (sem texto antes ou depois):

    ```json
    {
      "timeframes_identificados": "HTF (5 Minutos) e LTF (1 Minuto)",
      "bias_direcional": "Bearish (Baixista)",
      "estruturas_coletadas": [
        "178.000: HTF Extreme Supply Zone (Topo do Range / Bloco de Venda Majoritário)",
        "177.650: Equilibrium HTF (Ponto Médio do Range Principal)"
      ],
      "liquidez_relevante": [
        "BSL: 178.000 (Topo do Mercado)",
        "SSL: 170.915 (PDL)"
      ],
      "zonas_de_interesse_e_cenarios": [
        "Cenário Vendedor: Retração até o Bearish OB em 171.850."
      ]
    }
    ```

    IMPORTANTE: Sempre inclua o valor numérico da cotação/preço no início de cada item da lista "estruturas_coletadas" e nas descrições de "liquidez_relevante".
    """

    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    model = genai.GenerativeModel(
        modelo_nome,
        safety_settings=safety_settings,
    )

    response = model.generate_content(
        [prompt_smc, image_htf_pil, image_ltf_pil],
        request_options={"timeout": 120},
    )

    return response.text


# 3. Interface e Seleção de Origem das Imagens
modelos_disponiveis = obter_modelos_disponiveis()

col_modelo, col_empty = st.columns([1, 2])
with col_modelo:
    modelo_selecionado = st.selectbox(
        "Selecione o Modelo Ativo na sua API Key:",
        modelos_disponiveis,
        index=0,
    )

st.markdown("---")
st.subheader("🖼️ Seleção das Imagens")

# Obtém lista de arquivos salvos na pasta Coletas
imagens_coletadas = listar_imagens_coletas()

# Identificação automática inteligente por nome
index_htf = selecionar_imagem_por_timeframe(imagens_coletadas, preferência="htf")
index_ltf = selecionar_imagem_por_timeframe(imagens_coletadas, preferência="ltf")

img_htf_pil = None
img_ltf_pil = None

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Gráfico HTF (Timeframe Maior)")
    
    arq_htf_sel = st.selectbox(
        "Imagem Automática da Pasta 'Coletas':",
        options=["Nenhuma / Fazer Upload Manual"] + imagens_coletadas,
        index=index_htf,
        key="sel_htf"
    )
    
    uploaded_htf = st.file_uploader(
        "Ou faça Upload Manual HTF:", type=["png", "jpg", "jpeg"], key="up_htf"
    )

    if uploaded_htf:
        img_htf_pil = PIL.Image.open(uploaded_htf).convert("RGB")
        st.image(img_htf_pil, caption="Upload Manual (HTF)", use_container_width=True)
    elif arq_htf_sel != "Nenhuma / Fazer Upload Manual":
        caminho_img = PASTA_COLETAS / arq_htf_sel
        img_htf_pil = PIL.Image.open(caminho_img).convert("RGB")
        st.image(img_htf_pil, caption=f"Coletas: {arq_htf_sel}", use_container_width=True)

with col2:
    st.markdown("#### Gráfico LTF (Timeframe Menor)")
    
    arq_ltf_sel = st.selectbox(
        "Imagem Automática da Pasta 'Coletas':",
        options=["Nenhuma / Fazer Upload Manual"] + imagens_coletadas,
        index=index_ltf,
        key="sel_ltf"
    )
    
    uploaded_ltf = st.file_uploader(
        "Ou faça Upload Manual LTF:", type=["png", "jpg", "jpeg"], key="up_ltf"
    )

    if uploaded_ltf:
        img_ltf_pil = PIL.Image.open(uploaded_ltf).convert("RGB")
        st.image(img_ltf_pil, caption="Upload Manual (LTF)", use_container_width=True)
    elif arq_ltf_sel != "Nenhuma / Fazer Upload Manual":
        caminho_img = PASTA_COLETAS / arq_ltf_sel
        img_ltf_pil = PIL.Image.open(caminho_img).convert("RGB")
        st.image(img_ltf_pil, caption=f"Coletas: {arq_ltf_sel}", use_container_width=True)

st.divider()

# 4. Execução, Salvamento e Renderização
if img_htf_pil and img_ltf_pil:
    if st.button("🚀 Gerar Análise SMC/ICT e Script Profit", type="primary"):
        status = st.empty()
        status.info("⏳ Processando imagens e extraindo cotações exatas...")

        try:
            img_htf_pil = redimensionar_imagem(img_htf_pil)
            img_ltf_pil = redimensionar_imagem(img_ltf_pil)

            status.info(
                f"📡 Analisando gráficos com {modelo_selecionado}... Aguarde."
            )

            texto_resposta = analisar_graficos(
                img_htf_pil, img_ltf_pil, modelo_nome=modelo_selecionado
            )

            # 1. Converte e Salva no arquivo JSON
            dados_json = extrair_json_puro(texto_resposta)

            os.makedirs(PASTA_COLETAS, exist_ok=True)
            caminho_arquivo = PASTA_COLETAS / "AnaliseGraficaSMC.json"

            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                json.dump(dados_json, f, ensure_ascii=False, indent=2)

            status.empty()
            st.success(f"✅ JSON salvo em `{caminho_arquivo}`!")

            # 2. Exibe o relatório formatado em texto + Script NTSL na tela
            exibir_relatorio_formatado(dados_json)

            # 3. Exibe o JSON expandível
            with st.expander("🔍 Inspecionar Arquivo JSON Estruturado"):
                st.json(dados_json)

        except Exception as e:
            status.empty()
            st.error(f"❌ Erro ao processar a análise: {str(e)}")
else:
    st.info(
        "Selecione as imagens da pasta 'Coletas' ou faça o upload manual de ambos os gráficos para habilitar a análise."
    )