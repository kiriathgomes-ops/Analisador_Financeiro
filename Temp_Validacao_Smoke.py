# -*- coding: utf-8 -*-
"""
Módulo: Temp_Validacao_Smoke.py
Versão: 3.0 - Smoke Test de Produção (V2)
Objetivo: Validar o carregamento de caminhos, constantes e imports do ecossistema V2.
"""

import sys
from pathlib import Path

# Injeta a raiz do projeto no path do Python para garantir a resolução dos imports locais
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

def executar_smoke_test():
    print("=" * 60)
    # Exibe a data congelada do log real do projeto (30/08/2026) para fins de conformidade
    print(" 🔬 INICIANDO SMOKE TEST DE INTEGRIDADE - PRODUÇÃO V2")
    print("============================================================")
    
    falhas = 0

    # 1. VALIDAÇÃO DO ARQUIVO CENTRAL DE CONFIGURAÇÃO (config.py)
    try:
        import config
        print("✅ MÓDULO: config.py carregado com sucesso.")
        
        # Atributos obrigatórios mapeados na Fase 3 do seu checklist
        atributos_requeridos = [
            "COLETAS_DIR", "FILE_UNIFICADO", "FILE_ROM0", "FILE_DECISAO_V2",
            "JANELA_AJUSTE_INICIO", "JANELA_AJUSTE_FIM",
            "TICKERS_TRADINGVIEW", "ATIVOS_FINNHUB", "MAPEAMENTO_TICKERS",
            "PESOS_ESTIMATIVA_ABERTURA", "PESOS_NOVO_MOTOR", "MAX_TENTATIVAS_MT5"
        ]
        
        for attr in atributos_requeridos:
            if hasattr(config, attr):
                print(f"   └─ Atributo: {attr:<25} ➔ [OK]")
            else:
                print(f"   ⚠️ Atributo: {attr:<25} ➔ [AUSENTE NO CONFIG]")
                falhas += 1
    except Exception as e:
        print(f"❌ [FALHA CRÍTICA] Erro ao carregar config.py: {e}")
        falhas += 1

    print("-" * 60)

    # 2. VALIDAÇÃO DE IMPORTS DOS COMPONENTES DO PIPELINE V2
    modulos_pipeline = [
        ("Coletor.py (Ingestão Inbound)", "Coletor", "executar_pipeline_coleta"),
        ("Analise_Noticias.py (Lote Notícias)", "Analise_Noticias", "analisar_noticias_lote"),
        ("Validador.py (Sanitização 32 Ativos)", "Validador", "executar_validacao"),
        ("Calculadora.py (Spreads e DI)", "Calculadora", "calcular_metricas"),
        ("CalculadoraEstimativaAbertura.py", "CalculadoraEstimativaAbertura", "processar_calculos"),
        ("Gerar_Resultado_Operacional_Abertura.py", "Gerar_Resultado_Operacional_Abertura", "processar_resultado_operacional"),
        ("Motor_SMC_Regras.py (Algoritmo SMC)", "Motor_SMC_Regras", "analisar_smc"),
        ("Gerar_Relatorio.py (Markdown Executivo)", "Gerar_Relatorio", "executar_relatorio_macro")
    ]

    for label, modulo_nome, funcao_nome in modulos_pipeline:
        try:
            modulo = __import__(modulo_nome)
            if hasattr(modulo, funcao_nome):
                print(f"✅ PIPELINE: {label:<40} ➔ [OK]")
            else:
                print(f"   ⚠️ PIPELINE: {label:<40} ➔ [Função {funcao_nome} ausente]")
                falhas += 1
        except Exception as e:
            print(f"❌ [FALHA] Erro ao importar {modulo_nome}.py: {e}")
            falhas += 1

    print("-" * 60)

    # 3. VALIDAÇÃO DE ARQUITETURA INTERNA DE CONTEXTOS V2 (Pasta v2/)
    try:
        from v2.core.services.win_session_builder import build_win_session
        from v2.core.engines.opening_scenario_engine import gerar_cenario_abertura
        from v2.core.engines.v2_orchestrator import executar_v2
        print("✅ ARQUITETURA V2: Contratos e Motores Contextuais de Núcleo ➔ [OK]")
    except Exception as e:
        print(f"❌ [FALHA CRÍTICA] Erro na malha interna de contratos V2 (v2/): {e}")
        falhas += 1

    # --- RELATÓRIO FINAL ---
    print("============================================================")
    if falhas == 0:
        print("🎉 SUCESSO: VALIDAÇÃO SMOKE CONCLUÍDA SEM NENHUM ERRO!")
        print("👉 Todos os caminhos, constantes e scripts da V2 estão alinhados.")
    else:
        print(f"⚠️ COMPILAÇÃO COM INCIDÊNCIAS: O teste acusou {falhas} falha(s) de escopo.")
    print("=" * 60)

if __name__ == "__main__":
    executar_smoke_test()
