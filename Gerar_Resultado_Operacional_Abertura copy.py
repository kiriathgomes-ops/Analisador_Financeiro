# ============================================================
# ARQUIVO: Gerar_Resultado_Operacional_Abertura.py (VERSÃO V2)
# DATA: 27/08/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Processar resultado operacional com dados REAIS + FALLBACK + TENDÊNCIA.
# DESCRICAO:
#   Consolida métricas, estimativa de abertura do WIN, análise de tendências,
#   notícias das 09:00 e decisões da Core Engine V2 em um relatório operacional final.
#   AGORA: Fonte oficial de decisão é Decisao_V2.json (V2).
# ============================================================

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO DE CAMINHOS E DIRETÓRIOS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
COLETAS_DIR = BASE_DIR / "Coletas"

# Arquivos de entrada do pipeline (agora todos V2)
FILE_METRICAS = COLETAS_DIR / "Metricas_Calculadas.json"
FILE_ESTIMATIVA = COLETAS_DIR / "EstimativaAbertura.json"
FILE_DECISAO = COLETAS_DIR / "Decisao_V2.json"          # <-- ALTERADO para V2
FILE_ATIVOS = COLETAS_DIR / "DadosAtivosUnificados.json"
FILE_TENDENCIAS = COLETAS_DIR / "Analise_Tendencias.json"
FILE_NOTICIAS = COLETAS_DIR / "Noticias_Calendario_0900.json"

# Arquivo de saída consolidado
FILE_OUTPUT = COLETAS_DIR / "Resultado_Calculadora_Operacional_Abertura.json"


# ============================================================
# FUNÇÕES DE CARREGAMENTO DEFENSIVO (FALLBACK)
# ============================================================

def carregar_com_fallback(caminho: Path, default=None):
    """
    Carrega arquivo JSON com tratamento defensivo de exceções.
    Evita a interrupção do pipeline em caso de corrupção ou ausência do arquivo.
    """
    if default is None:
        default = {}
    try:
        if caminho.exists():
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            print(f"[AVISO] Arquivo não encontrado: {caminho.name}. Usando fallback.")
    except Exception as e:
        print(f"[ERRO] Falha ao carregar {caminho.name}: {str(e)}. Usando fallback.")
    return default


def carregar_dados_pipeline() -> dict:
    """Carrega e consolida todas as saídas do pipeline com tratamento de nulos."""
    dados = {}

    # 1. MÉTRICAS CALCULADAS
    metricas = carregar_com_fallback(FILE_METRICAS)
    dados["metricas"] = metricas
    indicadores = metricas.get("indicadores_compostos", {})

    ind_mercado = indicadores.get("indicador_mercado_externo")
    ind_adrs = indicadores.get("indicador_adrs_brasileiras")

    # Fallback para indicador de Mercado Externo caso nulo
    if ind_mercado is None:
        macro = metricas.get("indicadores_macro", {})
        perf = metricas.get("performance_relativa", {})

        vix_change = macro.get("vix_change_pct")
        if isinstance(vix_change, (int, float)):
            crude = macro.get("crude_oil_change_pct", 0) or 0
            iron = macro.get("iron_ore", {}).get("change_percent", 0) or 0
            # VIX alto reflete aversão ao risco (-), commodities refletem alta (+)
            ind_mercado = (-1 * vix_change) + (crude * 0.5) + (iron * 0.5)

    dados["ind_mercado_externo"] = float(ind_mercado) if isinstance(ind_mercado, (int, float)) else 0.0

    # Fallback para indicador de ADRs caso nulo
    if ind_adrs is None:
        adrs = metricas.get("performance_relativa", {}).get("adrs_brasileiras", {})
        if isinstance(adrs, dict) and adrs:
            valores = [adr.get("change_percent") for adr in adrs.values() if isinstance(adr.get("change_percent"), (int, float))]
            ind_adrs = (sum(valores) / len(valores)) if valores else 0.0

    dados["ind_adrs_brasileiras"] = float(ind_adrs) if isinstance(ind_adrs, (int, float)) else 0.0

    # 2. OUTROS ARQUIVOS DE SUPORTE
    dados["estimativas"] = carregar_com_fallback(FILE_ESTIMATIVA)
    dados["ativos"] = carregar_com_fallback(FILE_ATIVOS)
    dados["tendencias"] = carregar_com_fallback(FILE_TENDENCIAS)

    # 3. DECISÃO V2 (OFICIAL)
    dados["decisao"] = carregar_com_fallback(FILE_DECISAO)   # Agora carrega Decisao_V2.json

    return dados


def verificar_noticias_0900() -> dict:
    """Verifica alertas de eventos macroeconômicos de 3 estrelas às 09:00."""
    noticias_data = carregar_com_fallback(FILE_NOTICIAS)
    alerta = noticias_data.get("alerta_noticia_0900", {})

    if not alerta:
        return {
            "tem_evento_3_estrelas": False,
            "alerta": "🟢 Leilão sem notícias de alto impacto às 09:00",
            "quantidade_eventos": 0,
            "eventos": [],
            "fonte": "Dados padrão (sem notícias registradas)"
        }

    alerta["fonte"] = FILE_NOTICIAS.name
    return alerta


# ============================================================
# CLASSIFICAÇÃO E REGRAS OPERACIONAIS
# ============================================================

def classificar_operacional(valor_pct: float, nome_indicador: str = "", limiar_ruido: float = 0.05) -> dict:
    """
    Classifica a intensidade e a direção da força de mercado.
    Garante sanitização rigorosa contra dados inválidos.
    """
    if valor_pct is None or not isinstance(valor_pct, (int, float)):
        print(f"[AVISO] Valor inválido recebido em '{nome_indicador}': {valor_pct}")
        return {
            "valor_pct": 0.0,
            "classificacao": "INDISPONIVEL",
            "sinal_operacional": "NEUTRO",
            "rotulo_completo": "INDISPONIVEL_NEUTRO",
            "valido": False,
            "observacao": "Dado ausente ou não numérico"
        }

    abs_valor = abs(valor_pct)

    # Escala de intensidade
    if abs_valor < 0.3:
        intensidade = "LATERAL"
    elif 0.3 <= abs_valor < 0.8:
        intensidade = "MUITO_FRACA"
    elif 0.8 <= abs_valor < 1.5:
        intensidade = "FRACA"
    elif 1.5 <= abs_valor < 2.5:
        intensidade = "MODERADA"
    elif 2.5 <= abs_valor < 4.5:
        intensidade = "FORTE"
    else:
        intensidade = "MUITO_FORTE"

    # Direcionamento do sinal com filtro de ruído
    if valor_pct > limiar_ruido:
        sinal = "COMPRA"
    elif valor_pct < -limiar_ruido:
        sinal = "VENDA"
    else:
        sinal = "NEUTRO"

    return {
        "valor_pct": round(valor_pct, 4),
        "classificacao": intensidade,
        "sinal_operacional": sinal,
        "rotulo_completo": f"{intensidade}_{sinal}",
        "valido": True,
        "observacao": "OK"
    }


def extrair_tendencias_principais(dados_tendencias: dict) -> dict:
    """Extrai tendências apenas dos ativos relevantes para a abertura do Mini Índice."""
    tendencias = {}
    if not isinstance(dados_tendencias, dict):
        return tendencias

    # Ativos focados estritamente na precificação do WIN
    ativos_chave = [
        "WIN_FUT", "SP500_FUT", "NASDAQ_FUT",
        "VIX", "EWZ", "VALE_ADR", "PETR_ADR"
    ]

    for ativo in ativos_chave:
        if ativo in dados_tendencias:
            info = dados_tendencias[ativo]
            intervalo = info.get("intervalo_5_para_0", {})
            tendencias[ativo] = {
                "padrao": info.get("padrao_comportamento", "N/A"),
                "ultima_variacao": intervalo.get("variacao_pct", 0.0),
                "tendencia_ultimo": intervalo.get("tendencia", "N/A")
            }

    return tendencias


# ============================================================
# FUNÇÃO PRINCIPAL – GERADOR DE RESULTADO OPERACIONAL
# ============================================================

def gerar_resultado_operacional() -> dict:
    """Orquestra o carregamento, processamento e geração do relatório operacional."""
    print("=" * 70)
    print(" GERADOR DE RESULTADO OPERACIONAL (FOCO EXCLUSIVO: MINI ÍNDICE) – V2")
    print("=" * 70)

    # 1. Carregamento dos dados
    print("\n📊 Carregando dados do pipeline...")
    dados_pipeline = carregar_dados_pipeline()

    # 2. Verificação de eventos do calendário
    print("📰 Verificando calendário de notícias às 09:00...")
    alerta_noticias = verificar_noticias_0900()

    # 3. Extração dos indicadores
    ind_mercado_externo = dados_pipeline.get("ind_mercado_externo", 0.0)
    ind_adrs_brasileiras = dados_pipeline.get("ind_adrs_brasileiras", 0.0)

    print(f"\n📈 Indicadores Consolidados:")
    print(f"   • Mercado Externo  : {ind_mercado_externo:+.4f}%")
    print(f"   • ADRs Brasileiras : {ind_adrs_brasileiras:+.4f}%")

    # 4. Tendências
    print("\n📉 Mapeando tendências dos ativos de suporte...")
    tendencias = extrair_tendencias_principais(dados_pipeline.get("tendencias", {}))
    for ativo, info in tendencias.items():
        print(f"   • {ativo}: {info['padrao']} (Var: {info['ultima_variacao']:+.2f}%)")

    # 5. Classificação dos indicadores
    res_externo = classificar_operacional(ind_mercado_externo, "Mercado Externo")
    res_adrs = classificar_operacional(ind_adrs_brasileiras, "ADRs Brasileiras")

    # 6. MAPEAMENTO DA DECISÃO V2 (OFICIAL)
    decisao_v2 = dados_pipeline.get("decisao", {})          # Decisao_V2.json
    decisao_data = decisao_v2.get("decisao", {})            # campo "decisao" dentro do JSON

    # Extrai os campos do V2
    vies_v2 = decisao_data.get("vies_final", "NEUTRO")
    confianca_v2 = decisao_data.get("confianca", 0)         # 0-100
    motivos_v2 = decisao_data.get("motivos", [])
    entrada_v2 = decisao_data.get("entrada")
    stop_v2 = decisao_data.get("stop_loss")
    alvo1_v2 = decisao_data.get("alvo_1")
    alvo2_v2 = decisao_data.get("alvo_2")

    # Converte confiança (0-100) para score numérico compatível com V1 (-10 a +10)
    # Isso mantém compatibilidade com dashboards que esperam "score_numeric"
    if "COMPRA" in vies_v2.upper() or vies_v2.upper() in ("ALTA", "BULL"):
        score_calculado = (confianca_v2 / 100) * 10   # 95% -> 9.5
    elif "VENDA" in vies_v2.upper() or vies_v2.upper() in ("BAIXA", "BEAR"):
        score_calculado = - (confianca_v2 / 100) * 10 # 80% -> -8.0
    else:
        score_calculado = 0.0

    # Monta o dicionário no formato esperado (compatível com a estrutura antiga)
    win_core_v2 = {
        "vies_final": vies_v2,
        "score_numeric": round(score_calculado, 2),
        "fatores_relevantes": motivos_v2,          # V2 chama de "motivos", mas mantemos "fatores_relevantes"
        "confianca": confianca_v2,                 # adicional, para referência
        "entrada": entrada_v2,
        "stop": stop_v2,
        "alvo_1": alvo1_v2,
        "alvo_2": alvo2_v2,
    }

    # 7. Estimativa de abertura (compatível com singular/plural)
    estimativa_dict = dados_pipeline.get("estimativas", {})
    abertura_win = estimativa_dict.get("estimativa_abertura", {}).get("WIN_INDICE") or \
                   estimativa_dict.get("estimativas_abertura", {}).get("WIN_INDICE", {})

    # 8. Construção da Estrutura Final do JSON
    resultado = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "origem": "Pipeline_Completo_V2",
            "versao": "2.0_V2",
            "arquivos_presentes": {
                "metricas": FILE_METRICAS.exists(),
                "estimativa": FILE_ESTIMATIVA.exists(),
                "decisao": FILE_DECISAO.exists(),          # agora aponta para V2
                "ativos": FILE_ATIVOS.exists(),
                "tendencias": FILE_TENDENCIAS.exists(),
                "noticias": FILE_NOTICIAS.exists(),
            }
        },
        "alerta_calendario_0900": alerta_noticias,
        "indicadores_compostos": {
            "indicador_mercado_externo": res_externo,
            "indicador_adrs_brasileiras": res_adrs,
        },
        "analise_tendencias": tendencias,
        "estimativa_abertura": {
            "WIN_INDICE": abertura_win
        },
        "pivot_points": {
            "WIN_FUT": estimativa_dict.get("pivot_points", {}).get("WIN_FUT", {})
        },
        "resumo_macro": estimativa_dict.get("resumo_macro", {}),
        "decisao_core": {
            "win": win_core_v2       # <-- agora alimentado pela V2
        }
    }

    # 9. Gravação do arquivo de saída
    try:
        os.makedirs(COLETAS_DIR, exist_ok=True)
        with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Relatório gravado com sucesso em: {FILE_OUTPUT.name}")
    except Exception as e:
        print(f"\n[ERRO CRÍTICO] Falha ao gravar arquivo de saída: {str(e)}")

    # 10. Exibição do Resumo
    print("\n" + "=" * 70)
    print(" RESUMO OPERACIONAL DE ABERTURA (MINI ÍNDICE) – V2")
    print("=" * 70)

    print(f"\n📰 NOTÍCIAS (09:00): {alerta_noticias.get('alerta', 'N/A')}")
    print("\n📊 SINAIS DOS INDICADORES:")
    print(f"   • Mercado Externo  : {res_externo['valor_pct']:+.4f}% → [{res_externo['rotulo_completo']}]")
    print(f"   • ADRs Brasileiras : {res_adrs['valor_pct']:+.4f}% → [{res_adrs['rotulo_completo']}]")

    print("\n⚙️ DECISÃO CORE ENGINE V2:")
    print(f"   • Viés Final : {win_core_v2['vies_final']}")
    print(f"   • Confiança  : {win_core_v2.get('confianca', 0)}%")
    print(f"   • Score      : {win_core_v2['score_numeric']:.2f}")
    print(f"   • Entrada    : {win_core_v2.get('entrada', '—')}")
    print(f"   • Stop       : {win_core_v2.get('stop', '—')}")
    print(f"   • Alvo 1/2   : {win_core_v2.get('alvo_1', '—')} / {win_core_v2.get('alvo_2', '—')}")
    if win_core_v2.get("fatores_relevantes"):
        print("   • Fatores:")
        for f in win_core_v2["fatores_relevantes"][:3]:
            print(f"      - {f}")

    print("=" * 70)
    return resultado


if __name__ == "__main__":
    gerar_resultado_operacional()