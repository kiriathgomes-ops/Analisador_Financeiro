# -*- coding: utf-8 -*-
"""
Módulo: Gerar_Resultado_Operacional_Abertura.py
Versão: 2.5 - Produção Consolidada V2
Objetivo: Consolidação final de métricas, estimativas, tendências e decisões no payload operacional.
"""

import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Ingestão de caminhos estáveis e centralizados do seu config.py
from config import (
    COLETAS_DIR,
    FILE_METRICAS,
    FILE_ESTIMATIVA_ABERTURA,
    FILE_DECISAO_V2,
    FILE_UNIFICADO,
    FILE_TENDENCIAS,
    FILE_NOTICIAS_CALENDARIO_0900,
    FILE_RESULTADO_OPERACIONAL
)

def carregar_json_defensivo(caminho_path, default=None) -> dict:
    """Carrega arquivos JSON com isolamento de falhas para proteger a esteira."""
    if default is None:
        default = {}
    if not caminho_path.exists():
        return default
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def classificar_intensidade_sinal(valor_pct: float, limiar_ruido: float = 0.05) -> dict:
    """Classifica a força direcional do indicador com base na variação percentual."""
    if valor_pct is None or not isinstance(valor_pct, (int, float)):
        return {
            "valor_pct": 0.0,
            "classificacao": "INDISPONIVEL",
            "sinal_operacional": "NEUTRO",
            "rotulo_completo": "INDISPONIVEL_NEUTRO"
        }

    abs_valor = abs(valor_pct)

    if abs_valor < 0.3:
        intensidade = "LATERAL"
    elif 0.3 <= abs_valor < 0.8:
        intensidade = "MUITO_FRACA"
    elif 0.8 <= abs_valor < 1.5:
        intensidade = "FRACA"
    elif 1.5 <= abs_valor < 2.5:
        intensidade = "MODERADA"
    else:
        intensidade = "FORTE"

    sinal = "COMPRA" if valor_pct > limiar_ruido else ("VENDA" if valor_pct < -limiar_ruido else "NEUTRO")

    return {
        "valor_pct": round(valor_pct, 4),
        "classificacao": intensidade,
        "sinal_operacional": sinal,
        "rotulo_completo": f"{intensidade}_{sinal}"
    }

def processar_resultado_operacional():
    print("=" * 70)
    print(" 📊 COMPILADOR E CONSOLIDADOR OPERACIONAL DE ABERTURA — V2")
    print("=" * 70)
    print(f"🕒 Execução: {datetime.now().strftime('%H:%M:%S')}")

    # 1. Carga defensiva de todos os componentes gerados no pipeline
    metricas = carregar_json_defensivo(FILE_METRICAS)
    estimativa_dict = carregar_json_defensivo(FILE_ESTIMATIVA_ABERTURA)
    decisao_v2 = carregar_json_defensivo(FILE_DECISAO_V2)
    tendencias = carregar_json_defensivo(FILE_TENDENCIAS)
    noticias_0900 = carregar_json_defensivo(FILE_NOTICIAS_CALENDARIO_0900)

    # 2. Processamento e Higienização de Indicadores Compostos
    indicadores = metricas.get("indicadores_compostos", {})
    ind_mercado_externo = indicadores.get("indicador_mercado_externo", 0.0)
    ind_adrs_brasileiras = indicadores.get("indicador_adrs_brasileiras", 0.0)

    res_externo = classificar_intensidade_sinal(ind_mercado_externo)
    res_adrs = classificar_intensidade_sinal(ind_adrs_brasileiras)

    # 3. Mapeamento Estrito dos Contratos da Decisão V2 (Oficial)
    decisao_data = decisao_v2.get("decisao", {})
    vies_final = decisao_data.get("vies_final", "NEUTRO")
    confianca = decisao_data.get("confianca", 0)

    # Converte o nível de confiança (0-100) para score numérico adaptativo (-10 a +10)
    # Mantém compatibilidade com blocos legados e estatísticas de backtest
    if "COMPRA" in vies_final.upper() or vies_final.upper() == "ALTA":
        score_calculado = (confianca / 100) * 10
    elif "VENDA" in vies_final.upper() or vies_final.upper() == "BAIXA":
        score_calculado = -((confianca / 100) * 10)
    else:
        score_calculado = 0.0

    win_core_consolidado = {
        "vies_final": vies_final,
        "score_numeric": round(score_calculado, 2),
        "fatores_relevantes": decisao_data.get("motivos", []),
        "confianca": confianca,
        "entrada": decisao_data.get("entrada"),
        "stop": decisao_data.get("stop_loss"),
        "alvo_1": decisao_data.get("alvo_1"),
        "alvo_2": decisao_data.get("alvo_2"),
    }

    # 4. Captura das estimativas teóricas (Compatível com singular e plural)
    abertura_win = estimativa_dict.get("estimativa_abertura", {}).get("WIN_INDICE") or \
                   estimativa_dict.get("estimativas_abertura", {}).get("WIN_INDICE", {})

    # 5. MONTAGEM DA CARGA ÚTIL DO ARQUIVO OPERACIONAL FINAL
    payload_resultado = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "origem": "Pipeline_Completo_V2",
            "versao": "2.0_V2",
            "integridade_fontes": {
                "metricas": FILE_METRICAS.exists(),
                "estimativa": FILE_ESTIMATIVA_ABERTURA.exists(),
                "decisao": FILE_DECISAO_V2.exists(),
                "tendencias": FILE_TENDENCIAS.exists(),
                "noticias_0900": FILE_NOTICIAS_CALENDARIO_0900.exists()
            }
        },
        "alerta_calendario_0900": noticias_0900.get("alerta_noticia_0900", {
            "tem_evento_3_estrelas": False,
            "alerta": "🟢 Leilão livre de notícias de alto impacto às 09:00h",
            "quantidade_eventos": 0,
            "eventos": []
        }),
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
            "win": win_core_consolidado
        }
    }

    # 6. PERSISTÊNCIA FÍSICA NO DISCO DE PRODUÇÃO
    try:
        COLETAS_DIR.mkdir(parents=True, exist_ok=True)
        with open(FILE_RESULTADO_OPERACIONAL, "w", encoding="utf-8") as f:
            json.dump(payload_resultado, f, indent=2, ensure_ascii=False)
            
        print("\n📊 Resumo Consolidado com Sucesso:")
        print(f"  • Viés Core V2 : {win_core_consolidado['vies_final']} (Confiança: {win_core_consolidado['confianca']}%)")
        print(f"  • Teórico WIN  : {abertura_win.get('abertura_teorica_pontos', 0.0):,.0f} pts")
        print(f"  • Ext. Driver  : {res_externo['valor_pct']:+.2f}% → [{res_externo['rotulo_completo']}]")
        print(f"  • ADRs Driver  : {res_adrs['valor_pct']:+.2f}% → [{res_adrs['rotulo_completo']}]")
        print(f"\n✅ Arquivo operacional gravado com sucesso: {FILE_RESULTADO_OPERACIONAL.name}\n")
        
    except Exception as e:
        print(f"❌ [ERRO CRÍTICO AO SALVAR RESULTADO OPERACIONAL]: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    processar_resultado_operacional()
