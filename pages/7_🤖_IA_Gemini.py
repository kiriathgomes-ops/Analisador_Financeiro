import json
import os
import re
import PIL.Image
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from google.generativeai.types import HarmBlockThreshold, HarmCategory

# 1. Configuração da Página do Streamlit
st.set_page_config(
    page_title="Analisador SMC/ICT - Google Gemini",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Analisador SMT / ICT - Google Gemini (Exhaustivo)")
st.write(
    "Envie os prints dos seus gráficos para receber a análise detalhada e o script NTSL COMPLETO do ProfitChart."
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
        # Extrai o preço (ex: 178.000 ou 178000) e a descrição
        match = re.match(r"^([\d\.]+)\s*:\s*(.*)$", item)
        if match:
            preco_str = match.group(1).replace(".", "")
            descricao = match.group(2).replace('"', "'")

            var_nome = f"L_Nivel_{i+1}"
            linhas_var.append(f"  {var_nome} : float;")
            linhas_atrib.append(f"  {var_nome} := {preco_str};")

            # Escolhe cor com base na descrição
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

    # Gera e exibe o Script NTSL do ProfitChart
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
        "177.650: Equilibrium HTF (Ponto Médio do Range Principal)",
        "177.200: HTF Swing High (Ponto de Refúgio com Liquidez de 5.821K)",
        "176.750: LTF 2x EQH (3K Liquidez)",
        "176.500: Supply Zone 5m / EQH (4.2K BSL)",
        "176.350: LTF 2x EQH (3.4K BSL)",
        "176.250: PDH (Previous Day High) / EQH (9.8K BSL) / EQH (888)",
        "175.800: LTF EQH (4.1K BSL)",
        "175.550: LTF EQH (5K BSL)",
        "175.150: Bearish Order Block 5m / FVG Unfilled",
        "174.300: Bearish Order Block 5m / Zona de Oferta Intermediária",
        "173.850: Bearish Order Block 1m/5m",
        "173.350: Bearish Order Block Principal da Pernada de Baixa",
        "172.450: Nível Rápido de CHoCH / Resistência Estrutural",
        "172.250: Strong High 1m (HH do Dia de Hoje - Aug 12)",
        "172.000: 2x EQH com forte piscina de liquidez comprador (277.9K / 115.8K / 46.5K BSL)",
        "171.850: Bearish Order Block 1m / Zona de Oferta Local",
        "171.250: Equilibrium Range 1m / Ponto Neutro",
        "170.915: PDL (Previous Day Low)",
        "170.780: 2x EQL (292.9K SSL) - Piscina Massiva de Liquidez Vendedora",
        "170.600: Bullish Demand Zone / Discount Zone High",
        "170.450: Weak Low 1m / Fundo Extremo de Discount"
      ],
      "liquidez_relevante": [
        "BSL: 178.000 (Topo do Mercado)",
        "BSL: 177.200 (5.821K)",
        "BSL: 176.750 (2x EQH 3K)",
        "BSL: 176.350 (2x EQH 3.4K)",
        "BSL: 176.250 (PDH + EQH 9.8K)",
        "BSL: 175.800 (EQH 4.1K)",
        "BSL: 175.550 (EQH 5K)",
        "BSL: 172.000 (2x EQH 277.9K / 115.8K BSL)",
        "SSL: 170.915 (PDL)",
        "SSL: 170.780 (2x EQL 292.9K SSL - Ponto crítico de indução)",
        "SSL: 170.450 (Weak Low)"
      ],
      "zonas_de_interesse_e_cenarios": [
        "Cenário Vendedor (Região 1): Retração até o Bearish OB em 171.850 / 172.000. Varredura da liquidez do EQH (277.9K) com confirmação por CHoCH em 1m para entrada vendida visando 170.780.",
        "Cenário Vendedor (Região 2): Teste do Strong High em 172.250 ou bloco em 173.350.",
        "Cenário Comprador (Reversão / Scalp de Discount): Entrada de compra válida após captura total da liquidez em 170.780 (2x EQL) com rejeição forte (Pavio/SFP) e CHoCH em 1m subindo acima de 171.250, visando 171.850 e 172.000."
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


# 3. Interface e Upload
modelos_disponiveis = obter_modelos_disponiveis()

col_modelo, col_empty = st.columns([1, 2])
with col_modelo:
    modelo_selecionado = st.selectbox(
        "Selecione o Modelo Ativo na sua API Key:",
        modelos_disponiveis,
        index=0,
    )

col1, col2 = st.columns(2)

with col1:
    uploaded_htf = st.file_uploader(
        "Gráfico HTF (ex: 5min)", type=["png", "jpg", "jpeg"]
    )
    if uploaded_htf:
        st.image(
            uploaded_htf, caption="Timeframe Maior (HTF)", use_container_width=True
        )

with col2:
    uploaded_ltf = st.file_uploader(
        "Gráfico LTF (ex: 1min)", type=["png", "jpg", "jpeg"]
    )
    if uploaded_ltf:
        st.image(
            uploaded_ltf, caption="Timeframe Menor (LTF)", use_container_width=True
        )

st.divider()

# 4. Execução, Salvamento e Renderização no Streamlit
if uploaded_htf and uploaded_ltf:
    if st.button("🚀 Gerar Análise SMC/ICT e Script Profit", type="primary"):
        status = st.empty()
        status.info("⏳ Processando imagens e extraindo cotações exatas...")

        try:
            img_htf_pil = PIL.Image.open(uploaded_htf).convert("RGB")
            img_ltf_pil = PIL.Image.open(uploaded_ltf).convert("RGB")

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

            os.makedirs("./Coletas", exist_ok=True)
            caminho_arquivo = "./Coletas/AnaliseGraficaSMC.json"

            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                json.dump(dados_json, f, ensure_ascii=False, indent=2)

            status.empty()
            st.success(f"✅ JSON salvo em `{caminho_arquivo}`!")

            # 2. Exibe o relatório formatado em texto + Script NTSL na tela
            exibir_relatorio_formatado(dados_json)

            # 3. Exibe o JSON expandível no final caso queira inspecionar
            with st.expander("🔍 Inspecionar Arquivo JSON Estruturado"):
                st.json(dados_json)

        except Exception as e:
            status.empty()
            st.error(f"❌ Erro ao processar a análise: {str(e)}")
else:
    st.info(
        "Por favor, faça o upload de ambos os gráficos para liberar a análise."
    )