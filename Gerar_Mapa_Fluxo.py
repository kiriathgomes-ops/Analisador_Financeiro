# ============================================================
# ARQUIVO: Gerar_Mapa_Fluxo.py (VERSÃO DINÂMICA)
#
# OBJETIVO:
#   Gerar Mapa_Fluxo.json automaticamente a partir da lista
#   'etapas' do main_pipeline.py.
#
# VANTAGENS:
#   - Sempre atualizado com o pipeline real.
#   - Novos scripts aparecem automaticamente.
#   - Mantém compatibilidade com a página Streamlit.
# ============================================================

import ast
import json
import os
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO DE CAMINHOS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_SAIDA = BASE_DIR / "Coletas" / "Mapa_Fluxo.json"
MAIN_PIPELINE = BASE_DIR / "main_pipeline.py"

# ============================================================
# METADADOS DOS SCRIPTS (entrada, saída, descrição)
# Para scripts não listados aqui, o sistema gera dados padrão.
# ============================================================
SCRIPT_METADATA = {
    "Limpar_Imagens_TradingView.py": {
        "descricao": "Gerencia imagens de gráficos baixadas (WIN 1min/5min)",
        "entrada": ["Pasta Downloads"],
        "saida": ["WIN_1min.png", "WIN_5min.png"]
    },
    "Coletor.py": {
        "descricao": "Aquisição de dados externos via TradingView, Finnhub, MT5 e BACEN",
        "entrada": ["TradingView", "Finnhub", "MetaTrader5", "BACEN"],
        "saida": ["Coleta_ram.json", "Coleta_rom-0.json", "DadosAtivosUnificados.json"]
    },
    "Coleta_Noticias_Calendario.py": {
        "descricao": "Coleta eventos econômicos do calendário (Brasil e EUA)",
        "entrada": ["TradingView API"],
        "saida": ["Noticias_Calendario.json", "Noticias_Calendario_0900.json"]
    },
    "Analise_Noticias.py": {
        "descricao": "Analisa impacto das notícias e gera alertas de risco",
        "entrada": ["Noticias_Calendario.json"],
        "saida": ["Noticias_Impacto_Dia.json"]
    },
    "Validador.py": {
        "descricao": "Sanitiza, valida e padroniza os dados brutos (32 ativos)",
        "entrada": ["Coleta_rom-0.json"],
        "saida": ["Dados_Validados.json"]
    },
    "Calculadora.py": {
        "descricao": "Calcula spreads, inclinação da curva DI, indicadores macro e compostos",
        "entrada": ["Dados_Validados.json"],
        "saida": ["Metricas_Calculadas.json"]
    },
    "CalculadoraEstimativaAbertura.py": {
        "descricao": "Estimativa teórica de abertura e pivôs (PP, R1, R2, S1, S2) para o WIN",
        "entrada": ["Dados_Validados.json"],
        "saida": ["EstimativaAbertura.json"]
    },
    "Gerar_Resultado_Operacional_Abertura.py": {
        "descricao": "Consolida métricas, estimativas, decisões e tendências em relatório operacional final",
        "entrada": ["Metricas_Calculadas.json", "EstimativaAbertura.json", "Decisao_V2.json", 
                    "DadosAtivosUnificados.json", "Analise_Tendencias.json", "Noticias_Calendario_0900.json"],
        "saida": ["Resultado_Calculadora_Operacional_Abertura.json"]
    },
    "Engine_Vies.py": {
        "descricao": "Core Engine V1 - Gera viés operacional (score e direção) para o WIN",
        "entrada": ["EstimativaAbertura.json", "Metricas_Calculadas.json", 
                    "Noticias_Impacto_Dia.json", "DadosAtivosUnificados.json"],
        "saida": ["Decisao_V2.json"]
    },
    "Rodar_SMC_Regras.py": {
        "descricao": "Motor de regras SMC/ICT (swings, BOS, FVG, Order Blocks, Liquidez)",
        "entrada": ["MetaTrader5 (dados de preço)"],
        "saida": ["AnaliseGraficaSMC_Regras.json"]
    },
    "Gerar_Relatorio_Mensagem.py": {
        "descricao": "Gera relatório resumido em Markdown com estimativas e pivôs",
        "entrada": ["EstimativaAbertura.json"],
        "saida": ["Relatorio_Executivo.md"]
    },
    "v2_gravar_sessao_win.py": {
        "descricao": "Grava sessão WINFUT (V2) no histórico de aberturas",
        "entrada": ["Dados do pipeline V2"],
        "saida": ["Historico_Aberturas/ (JSON)"]
    },
    "v2_rodar_decisao_completa.py": {
        "descricao": "Orquestrador V2 - Gera decisão completa com confluência e níveis operacionais",
        "entrada": ["Vários JSONs do pipeline"],
        "saida": ["Decisao_V2.json"]
    },
    "MapearTendencia15Min.py": {
        "descricao": "Analisa tendência de 15 minutos (comparativo 10min → 5min → atual)",
        "entrada": ["Coleta_rom-10.json", "Coleta_rom-5.json", "Coleta_rom-0.json"],
        "saida": ["Analise_Tendencias.json"]
    }
}


# ============================================================
# FUNÇÃO PARA EXTRAIR A LISTA 'etapas' DO main_pipeline.py
# ============================================================
def extrair_etapas_do_pipeline() -> list:
    """
    Lê o arquivo main_pipeline.py e extrai a variável 'etapas'
    usando a AST (Abstract Syntax Tree) do Python.
    Retorna a lista de tuplas (nome_etapa, script) ou lista vazia.
    """
    if not MAIN_PIPELINE.exists():
        print(f"[ERRO] Arquivo {MAIN_PIPELINE} não encontrado!")
        return []

    try:
        with open(MAIN_PIPELINE, "r", encoding="utf-8") as f:
            codigo = f.read()

        # Parseia o código-fonte para árvore sintática
        arvore = ast.parse(codigo)

        # Procura por atribuições à variável 'etapas'
        for node in ast.walk(arvore):
            if isinstance(node, ast.Assign):
                for alvo in node.targets:
                    if isinstance(alvo, ast.Name) and alvo.id == "etapas":
                        # Converte o nó da lista para objeto Python
                        try:
                            etapas = ast.literal_eval(node.value)
                            # Verifica se é uma lista de tuplas
                            if isinstance(etapas, list) and all(isinstance(item, tuple) and len(item) == 2 for item in etapas):
                                return etapas
                            else:
                                print("[AVISO] A variável 'etapas' não está no formato esperado (lista de tuplas).")
                                return []
                        except Exception as e:
                            print(f"[ERRO] Falha ao interpretar a lista 'etapas': {e}")
                            return []
        print("[AVISO] Variável 'etapas' não encontrada no main_pipeline.py")
        return []

    except Exception as e:
        print(f"[ERRO] Falha ao processar {MAIN_PIPELINE}: {e}")
        return []


# ============================================================
# FUNÇÃO PARA GERAR O MAPA DE FLUXO DINÂMICAMENTE
# ============================================================
def gerar_mapa_dinamico():
    """
    Orquestra a geração do Mapa_Fluxo.json:
      1. Extrai etapas do main_pipeline.py
      2. Mapeia metadados para cada script
      3. Cria a estrutura JSON
      4. Salva na pasta Coletas/
    """
    print("=" * 60)
    print(" GERADOR DINÂMICO DE MAPA DE FLUXO ")
    print("=" * 60)

    # 1. Extrai as etapas do pipeline
    etapas_extraidas = extrair_etapas_do_pipeline()
    if not etapas_extraidas:
        print("❌ Nenhuma etapa encontrada. Verifique o main_pipeline.py.")
        return

    print(f"✅ {len(etapas_extraidas)} etapas encontradas no pipeline.")

    # 2. Constrói o dicionário do fluxo
    pipeline_estrutura = []
    for idx, (nome_etapa, script) in enumerate(etapas_extraidas, start=1):
        # Busca metadados para o script específico
        meta = SCRIPT_METADATA.get(script, {})
        
        # Se não houver metadados, gera valores genéricos
        if not meta:
            descricao = f"Executa o script {script}"
            entrada = ["Arquivos gerados por etapas anteriores"]
            saida = ["Arquivo(s) gerado(s) pelo script"]
            print(f"⚠️ Script '{script}' não tem metadados mapeados. Usando valores genéricos.")
        else:
            descricao = meta.get("descricao", f"Executa {script}")
            entrada = meta.get("entrada", ["Dados de entrada"])
            saida = meta.get("saida", ["Arquivo(s) de saída"])

        pipeline_estrutura.append({
            "etapa": idx,
            "nome": nome_etapa,
            "descricao": descricao,
            "arquivos": [script],
            "entrada": entrada,
            "saida": saida
        })

    # 3. Monta o JSON final
    fluxo_aplicacao = {
        "metadata": {
            "projeto": "Analisador_Financeiro",
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tipo": "Mapa de fluxo de dados (gerado dinamicamente)"
        },
        "pipeline": pipeline_estrutura
    }

    # 4. Salva no arquivo JSON
    os.makedirs(ARQUIVO_SAIDA.parent, exist_ok=True)
    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(fluxo_aplicacao, f, indent=4, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("✅ MAPA DE FLUXO GERADO COM SUCESSO!")
    print("=" * 60)
    print(f"📂 Arquivo: {ARQUIVO_SAIDA}")
    print(f"📊 Etapas processadas: {len(pipeline_estrutura)}")
    print("=" * 60)


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================
if __name__ == "__main__":
    gerar_mapa_dinamico()