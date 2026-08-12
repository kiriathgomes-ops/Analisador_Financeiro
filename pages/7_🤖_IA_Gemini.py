import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import PIL.Image
import streamlit as st

# 1. Configuração da Página do Streamlit
st.set_page_config(
    page_title="Analisador SMC/ICT - Google Gemini",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Analisador SMT / ICT - Google Gemini (Exaustivo)")
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
    except Exception as e:
        return ["models/gemini-1.5-flash", "models/gemini-1.5-pro"]


def redimensionar_imagem(img_pil, max_largura=1280):
    """Redimensiona ligeiramente a imagem mantendo alta resolução para leitura de textos minúsculos."""
    largura, altura = img_pil.size
    if largura > max_largura:
        proporcao = max_largura / float(largura)
        nova_altura = int((float(altura) * float(proporcao)))
        return img_pil.resize((max_largura, nova_altura), PIL.Image.Resampling.LANCZOS)
    return img_pil


def analisar_graficos(image_htf_pil, image_ltf_pil, modelo_nome):
    """Envia as duas imagens para o Gemini exigindo mapeamento exaustivo de NÍVEIS e NTSL sem simplificações."""

    prompt_smc = """
    Você é um especialista em Smart Money Concepts (SMC) e Inner Circle Trader (ICT) e um programador sênior em NTSL (ProfitChart).

    SEU OBJETIVO PRINCIPAL: Mapear TODOS os níveis e linhas visíveis nos gráficos e gerar o script NTSL completo sem omitir nem agrupar preços.

    REGRAS DE COLETA EXAUSTIVA:
    - NÃO RESUMA. Se houver 20, 25 ou 30 níveis no gráfico, liste TODOS ELES.
    - Mapeie todas as piscinas de liquidez (EQH, EQL, BSL, SSL), máximas e mínimas anteriores (PDH, PDL), blocos de ordem (Order Blocks HTF e LTF), Fair Value Gaps (FVGs), pontos de equilíbrio (Equilibrium), topos e fundos fracos/fortes (Strong High, Weak Low).
    - Para níveis repetidos ou muito próximos entre os timeframes, dê prioridade ao valor exato do Timeframe Menor (1m).

    SUA RESPOSTA DEVE CONTER OBRIGATORIAMENTE:

    ### 1. Relatório de Análise SMT/ICT
    - **Timeframes Identificados:** HTF e LTF
    - **Bias Direcional (HTF):** Bullish, Bearish ou Neutro com justificativa detalhada.
    - **Estruturas Coletadas (Exaustivo):**
      Liste absolutamente TODOS os preços encontrados organizados por Timeframe (HTF e LTF).
    - **Liquidez Relevante:** BSL e SSL identificadas.
    - **Zonas de Interesse Principais & Cenários Operacionais.**

    ---

    ### 2. Script de Níveis (ProfitChart / NTSL)

    REGRAS DE CÓDIGO NTSL:
    1. O código NTSL DEVE estar dentro de um bloco de código Markdown ```pascal ... ``` com quebras de linha normais para cada comando.
    2. Declare UMA VARIÁVEL DEDICADA para CADA NÍVEL mapeado (ex: L_WeakLow, L_EQL_1, L_EQL_2, L_PDL, L_OB_1, L_OB_2, L_EQH_1, L_EQH_2, L_PDH, L_Supply_1, L_Equil, etc.).
    3. Atribua os preços aproximados correspondentes para cada variável.
    4. Plote CADA UMA das linhas no gráfico com `HorizontalLineCustom`:
       `HorizontalLineCustom(Variavel, Cor, Espessura, Estilo, "Rotulo", TamanhoFonte, Posicao, Data, Hora, Incremento);`
    5. Cores padrão NTSL:
       - clRed / clMaroon : Oferta, Order Blocks de Venda, Strong High
       - clAqua / clBlue  : Liquidez (BSL / SSL / EQH / EQL)
       - clFuchsia        : Máximas e Mínimas do Dia Anterior (PDH / PDL)
       - clGray           : Níveis de Equilíbrio (Equilibrium Range)

    Exemplo de saída de código esperada:

    ```pascal
    // ==========================================
    // SCRIPT GERADO PELA IA SPIKE - NÍVEIS SMC/ICT
    // ==========================================
    var
      L_WeakLow   : float;
      L_EQL_1m    : float;
      L_PDL_1m    : float;
      L_EqRange   : float;
      L_OB_1m     : float;
      L_StrongHigh: float;
      L_OB_5m_1   : float;
      L_OB_5m_2   : float;
      L_EQH_1m_1  : float;
      L_EQH_1m_2  : float;
      L_PDH       : float;
      L_Supply_5m : float;
      L_Equil_5m  : float;
    inicio
      L_WeakLow    := 170500;
      L_EQL_1m     := 170780;
      L_PDL_1m     := 170890;
      L_EqRange    := 171250;
      L_OB_1m      := 171850;
      L_StrongHigh := 172250;
      L_OB_5m_1    := 173300;
      L_OB_5m_2    := 174200;
      L_EQH_1m_1   := 175100;
      L_EQH_1m_2   := 175750;
      L_PDH        := 176250;
      L_Supply_5m  := 176500;
      L_Equil_5m   := 177500;

      HorizontalLineCustom(L_WeakLow, clRed, 2, 0, "Weak Low 1m", 9, tpTopRight, Date, 0, MinPriceIncrement);
      HorizontalLineCustom(L_EQL_1m, clAqua, 2, 0, "2x EQL (292K SSL)", 9, tpTopRight, Date, 0, MinPriceIncrement);
      HorizontalLineCustom(L_PDL_1m, clFuchsia, 1, 0, "PDL 1m", 9, tpTopRight, Date, 0, MinPriceIncrement);
      HorizontalLineCustom(L_EqRange, clGray, 1, 2, "Equilibrium Range 1m", 9, tpTopRight, Date, 0, MinPriceIncrement);
      HorizontalLineCustom(L_OB_1m, clMaroon, 2, 0, "Bearish OB 1m", 9, tpTopRight, Date, 0, MinPriceIncrement);
      HorizontalLineCustom(L_StrongHigh, clRed, 2, 0, "Strong High 1m", 9, tpTopRight, Date, 0, MinPriceIncrement);
      HorizontalLineCustom(L_OB_5m_1, clMaroon, 1, 0, "Bearish OB 5m", 9, tpTopRight, Date, 0, MinPriceIncrement);
      HorizontalLineCustom(L_OB_5m_2, clMaroon, 1, 0, "Bearish OB 5m", 9, tpTopRight, Date, 0, MinPriceIncrement);
      HorizontalLineCustom(L_EQH_1m_1, clBlue, 1, 0, "EQH 1m", 9, tpTopRight, Date, 0, MinPriceIncrement);
      HorizontalLineCustom(L_EQH_1m_2, clBlue, 1, 0, "EQH 4.1K 1m", 9, tpTopRight, Date, 0, MinPriceIncrement);
      HorizontalLineCustom(L_PDH, clFuchsia, 2, 0, "PDH / EQH 9.8K BSL", 9, tpTopRight, Date, 0, MinPriceIncrement);
      HorizontalLineCustom(L_Supply_5m, clRed, 2, 0, "Supply Zone 5m", 9, tpTopRight, Date, 0, MinPriceIncrement);
      HorizontalLineCustom(L_Equil_5m, clGray, 2, 2, "Equilibrium HTF", 9, tpTopRight, Date, 0, MinPriceIncrement);
    fim;
    ```
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

    # Timeout expandido para 120s para permitir respostas exaustivas e scripts longos
    response = model.generate_content(
        [prompt_smc, image_htf_pil, image_ltf_pil],
        request_options={"timeout": 120},
    )

    if not response.text or response.text.strip() == ".":
        return "⚠️ O modelo retornou uma resposta vazia. Tente alternar para o modelo `models/gemini-1.5-pro` no menu suspenso."

    return response.text


# 3. Interface de Seleção de Modelo e Upload
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

# 4. Botão de Execução
if uploaded_htf and uploaded_ltf:
    if st.button("🚀 Gerar Análise SMC/ICT e Script", type="primary"):
        status = st.empty()
        status.info("⏳ Otimizando imagens em alta resolução...")

        try:
            # Converte e redimensiona mantendo alta resolução (1280px)
            img_htf_pil = PIL.Image.open(uploaded_htf).convert("RGB")
            img_ltf_pil = PIL.Image.open(uploaded_ltf).convert("RGB")

            img_htf_pil = redimensionar_imagem(img_htf_pil)
            img_ltf_pil = redimensionar_imagem(img_ltf_pil)

            status.info(
                f"📡 Mapeando exaustivamente todos os níveis com {modelo_selecionado}... Aguarde."
            )

            # Executa a análise
            resultado = analisar_graficos(
                img_htf_pil, img_ltf_pil, modelo_nome=modelo_selecionado
            )

            # Salva o arquivo diretamente no diretório ./Coletas/
            if resultado and not resultado.startswith("⚠️"):
                with open("./Coletas/AnaliseGraficaSMC.txt", "w", encoding="utf-8") as f:
                    f.write(resultado)

            status.empty()
            st.success(" Análise concluída com sucesso!")
            st.markdown(resultado)

        except Exception as e:
            status.empty()
            st.error(f"❌ Erro ao processar a análise: {str(e)}")
else:
    st.info("Por favor, faça o upload de ambos os gráficos para liberar o botão de análise.")