# ============================================================
# ARQUIVO: Gerar_Resultado_Operacional.py (VERSÃO 3.0 - COMPLETA)
# MOTIVO: Processar Operacional com dados REAIS + FALLBACK + TENDÊNCIA
# ============================================================

import json
import os
from datetime import datetime
from pathlib import Path
import sys

# ============================================================
# CONFIGURAÇÃO DE CAMINHOS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
COLETAS_DIR = BASE_DIR / "Coletas"

# Arquivos de entrada do pipeline
FILE_METRICAS = COLETAS_DIR / "Metricas_Calculadas.json"
FILE_ESTIMATIVA = COLETAS_DIR / "EstimativaAbertura.json"
FILE_DECISAO = COLETAS_DIR / "Decisao_Core.json"
FILE_ATIVOS = COLETAS_DIR / "DadosAtivosUnificados.json"
FILE_TENDENCIAS = COLETAS_DIR / "Analise_Tendencias.json"
FILE_NOTICIAS = COLETAS_DIR / "Noticias_Calendario_0900.json"

# Arquivos de saída
FILE_OUTPUT = COLETAS_DIR / "Resultado_Calculadora_Operacional_Abertura.json"


# ============================================================
# FUNÇÃO PARA CARREGAR DADOS COM FALLBACK
# ============================================================

def carregar_com_fallback(caminho, default=None):
    """Carrega JSON com fallback silencioso."""
    if default is None:
        default = {}
    try:
        if caminho.exists():
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[AVISO] Erro ao carregar {caminho.name}: {e}")
    return default


# ============================================================
# FUNÇÃO PARA CARREGAR DADOS DO PIPELINE
# ============================================================

def carregar_dados_pipeline():
    """Carrega todos os dados gerados pelo pipeline com fallback."""
    dados = {}
    
    # 1. Métricas Calculadas
    metricas = carregar_com_fallback(FILE_METRICAS)
    dados["metricas"] = metricas
    indicadores = metricas.get("indicadores_compostos", {})
    
    # Extrai indicadores com fallback para None
    ind_mercado = indicadores.get("indicador_mercado_externo")
    ind_adrs = indicadores.get("indicador_adrs_brasileiras")
    
    # Se for None, tenta buscar de outras fontes
    if ind_mercado is None:
        # Tenta buscar do resumo macro ou performance relativa
        macro = metricas.get("indicadores_macro", {})
        perf = metricas.get("performance_relativa", {})
        # Calcula um indicador alternativo se possível
        vix_change = macro.get("vix_change_pct")
        if vix_change is not None:
            crude = macro.get("crude_oil_change_pct", 0)
            iron = macro.get("iron_ore", {}).get("change_percent", 0)
            ind_mercado = (-vix_change) + (crude or 0) + (iron or 0)
    
    dados["ind_mercado_externo"] = ind_mercado if ind_mercado is not None else 0.0
    
    if ind_adrs is None:
        # Tenta calcular a partir das ADRs individuais
        adrs = perf.get("adrs_brasileiras", {})
        if adrs:
            soma = 0
            count = 0
            for adr in adrs.values():
                pct = adr.get("change_percent")
                if pct is not None:
                    soma += pct
                    count += 1
            ind_adrs = soma if count > 0 else 0.0
    
    dados["ind_adrs_brasileiras"] = ind_adrs if ind_adrs is not None else 0.0
    
    # 2. Estimativa de Abertura
    dados["estimativas"] = carregar_com_fallback(FILE_ESTIMATIVA)
    
    # 3. Decisão Core
    dados["decisao"] = carregar_com_fallback(FILE_DECISAO)
    
    # 4. Dados dos Ativos
    dados["ativos"] = carregar_com_fallback(FILE_ATIVOS)
    
    # 5. Análise de Tendências (nova!)
    dados["tendencias"] = carregar_com_fallback(FILE_TENDENCIAS)
    
    return dados


# ============================================================
# FUNÇÃO PARA VERIFICAR NOTÍCIAS 09:00 COM FALLBACK
# ============================================================

def verificar_noticias_0900():
    """Verifica notícias de 3 estrelas às 09:00 com fallback."""
    
    # Tenta ler do arquivo
    noticias_data = carregar_com_fallback(FILE_NOTICIAS)
    alerta = noticias_data.get("alerta_noticia_0900", {})
    
    # Se não tiver dados ou estiver vazio, retorna padrão
    if not alerta:
        print("[AVISO] Nenhuma notícia encontrada. Usando dados padrão.")
        return {
            "tem_evento_3_estrelas": False,
            "alerta": "🟢 Leilão sem notícias de alto impacto às 09:00",
            "quantidade_eventos": 0,
            "eventos": [],
            "fonte": "Dados padrão (arquivo não encontrado)"
        }
    
    # Adiciona fonte
    alerta["fonte"] = "Noticias_Calendario_0900.json"
    return alerta


# ============================================================
# CLASSIFICAÇÃO OPERACIONAL (melhorada)
# ============================================================

def classificar_operacional(valor_pct, nome_indicador="", limiar_ruido=0.05):
    """
    Classifica o sinal operacional com validação robusta.
    """
    # Validação de entrada
    if valor_pct is None:
        print(f"[AVISO] Valor None para {nome_indicador}. Usando 0.0")
        valor_pct = 0.0
    
    if not isinstance(valor_pct, (int, float)):
        print(f"[AVISO] Tipo inválido para {nome_indicador}: {type(valor_pct)}")
        return {
            "valor_pct": 0.0,
            "classificacao": "INDISPONIVEL",
            "sinal_operacional": "NEUTRO",
            "rotulo_completo": "INDISPONIVEL_NEUTRO",
            "valido": False,
            "observacao": f"Valor inválido: {valor_pct}"
        }
    
    abs_valor = abs(valor_pct)
    
    # Classificação de intensidade (mais granular)
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
    
    # Sinal com margem para ruído
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


# ============================================================
# EXTRAIR TENDÊNCIA DOS ATIVOS PRINCIPAIS
# ============================================================

def extrair_tendencias_principais(dados_tendencias):
    """Extrai a tendência dos ativos mais relevantes."""
    tendencias = {}
    
    if not dados_tendencias:
        return tendencias
    
    # Ativos que mais importam para a abertura
    ativos_chave = [
        "WIN_FUT", "WDO_FUT", "SP500_FUT", "NASDAQ_FUT",
        "VIX", "EWZ", "VALE_ADR", "PETR_ADR"
    ]
    
    for ativo in ativos_chave:
        if ativo in dados_tendencias:
            info = dados_tendencias[ativo]
            tendencias[ativo] = {
                "padrao": info.get("padrao_comportamento", "N/A"),
                "ultima_variacao": info.get("intervalo_5_para_0", {}).get("variacao_pct", 0),
                "tendencia_ultimo": info.get("intervalo_5_para_0", {}).get("tendencia", "N/A")
            }
    
    return tendencias


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def gerar_resultado_operacional():
    """Gera o resultado operacional usando dados REAIS do pipeline."""
    
    print("=" * 70)
    print(" GERADOR DE RESULTADO OPERACIONAL (DADOS REAIS DO PIPELINE)")
    print("=" * 70)
    
    # 1. Carrega dados do pipeline
    print("\n📊 Carregando dados do pipeline...")
    dados_pipeline = carregar_dados_pipeline()
    
    # 2. Verifica notícias das 09:00
    print("📰 Verificando notícias das 09:00...")
    alerta_noticias = verificar_noticias_0900()
    
    # 3. Extrai indicadores REAIS
    ind_mercado_externo = dados_pipeline.get("ind_mercado_externo", 0.0)
    ind_adrs_brasileiras = dados_pipeline.get("ind_adrs_brasileiras", 0.0)
    
    print(f"\n📈 Indicadores extraídos do pipeline:")
    print(f"   • Mercado Externo: {ind_mercado_externo:.4f}%")
    print(f"   • ADRs Brasileiras: {ind_adrs_brasileiras:.4f}%")
    
    # 4. Extrai tendências
    print("\n📉 Extraindo tendências dos ativos principais...")
    tendencias = extrair_tendencias_principais(dados_pipeline.get("tendencias", {}))
    if tendencias:
        for ativo, info in tendencias.items():
            print(f"   • {ativo}: {info['padrao']} (var: {info['ultima_variacao']:+.2f}%)")
    
    # 5. Classifica os indicadores
    res_externo = classificar_operacional(ind_mercado_externo, "Mercado Externo")
    res_adrs = classificar_operacional(ind_adrs_brasileiras, "ADRs Brasileiras")
    
    # 6. Obtém dados adicionais do Core Engine
    decisao_core = dados_pipeline.get("decisao", {})
    analise_operacional = decisao_core.get("analise_operacional", {})
    
    # 7. Monta resultado consolidado
    resultado = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "origem": "Pipeline_Completo_V3",
            "versao": "3.0",
            "dados_carregados": {
                "metricas": FILE_METRICAS.exists(),
                "estimativa": FILE_ESTIMATIVA.exists(),
                "decisao": FILE_DECISAO.exists(),
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
        "estimativas_abertura": dados_pipeline.get("estimativas", {}).get("estimativas_abertura", {}),
        "pivot_points": dados_pipeline.get("estimativas", {}).get("pivot_points", {}),
        "resumo_macro": dados_pipeline.get("estimativas", {}).get("resumo_macro", {}),
        "decisao_core": {
            "win": analise_operacional.get("WIN_INDICE", {}),
            "wdo": analise_operacional.get("WDO_DOLAR", {}),
        }
    }
    
    # 8. Salva resultado
    os.makedirs(COLETAS_DIR, exist_ok=True)
    with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    
    # 9. Exibe resumo detalhado
    print("\n" + "=" * 70)
    print(" RESULTADO OPERACIONAL CALCULADO ")
    print("=" * 70)
    
    # Alerta de Notícias
    print(f"\n📰 ALERTA NOTÍCIA 09:00 : {alerta_noticias.get('alerta', 'N/A')}")
    if alerta_noticias.get("tem_evento_3_estrelas", False):
        for ev in alerta_noticias.get("eventos", []):
            print(f"  └─ 📌 [{ev.get('hora', '')}] {ev.get('evento', '')}")
    
    # Indicadores
    print("\n📊 INDICADORES COMPOSTOS:")
    print(f"   • Mercado Externo  : {res_externo['valor_pct']:+.4f}% → [{res_externo['rotulo_completo']}]")
    print(f"   • ADRs Brasileiras : {res_adrs['valor_pct']:+.4f}% → [{res_adrs['rotulo_completo']}]")
    
    # Tendências
    if tendencias:
        print("\n📉 TENDÊNCIAS DOS ATIVOS PRINCIPAIS:")
        for ativo, info in list(tendencias.items())[:5]:
            emoji = "🟢" if info['ultima_variacao'] > 0 else "🔴" if info['ultima_variacao'] < 0 else "🟡"
            print(f"   • {emoji} {ativo}: {info['padrao']} ({info['ultima_variacao']:+.2f}%)")
    
    # Core Engine
    win_core = analise_operacional.get("WIN_INDICE", {})
    wdo_core = analise_operacional.get("WDO_DOLAR", {})
    if win_core or wdo_core:
        print("\n⚙️ CORE ENGINE:")
        if win_core:
            print(f"   • WIN: {win_core.get('vies_final', 'N/A')} (Score: {win_core.get('score_numeric', 0):.2f})")
        if wdo_core:
            print(f"   • WDO: {wdo_core.get('vies_final', 'N/A')} (Score: {wdo_core.get('score_numeric', 0):.2f})")
    
    print("\n" + "=" * 70)
    print(f"✅ Arquivo gerado: {FILE_OUTPUT}")
    print("=" * 70)
    
    return resultado


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

if __name__ == "__main__":
    gerar_resultado_operacional()