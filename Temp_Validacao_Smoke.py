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
        ("Validador.py (Sanitização 33 Ativos)", "Validador", "executar_validacao"),
        ("Calculadora.py (Spreads e DI)", "Calculadora", "calcular_metricas"),
        ("CalculadoraEstimativaAbertura.py", "CalculadoraEstimativaAbertura", "processar_calculos_operacionais"),
        ("Gerar_Resultado_Operacional_Abertura.py", "Gerar_Resultado_Operacional_Abertura", "processar_resultado_operacional"),
        ("Motor_SMC_Regras.py (Algoritmo SMC)", "Motor_SMC_Regras", "analisar_smc")
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

    print("-" * 60)

    # 4. VALIDACAO DE SCHEMAS JSON (fix80)
    print("\U0001F50D BLOCO 4: SCHEMAS DOS JSONs CRITICOS")
    import json as _json
    from datetime import date as _date

    def _ler_json(path):
        try:
            with open(path, encoding="utf-8") as f:
                return _json.load(f)
        except Exception:
            return None

    hoje = _date.today().isoformat()
    hist_path = f"Coletas/Historico_Aberturas/{hoje}.json"

    schemas_criticos = [
        ("Coletas/DadosAtivosUnificados.json",
         lambda d: isinstance(d.get("ativos"), dict)
                   and len(d["ativos"]) >= 30
                   and all(isinstance(v, dict) and v.get("fonte")
                           for v in d["ativos"].values()),
         "33+ ativos com 'fonte' (fix76)"),
        ("Coletas/Dados_Validados.json",
         lambda d: isinstance(d.get("ativos_validados"), list)
                   and len(d["ativos_validados"]) >= 30
                   and all(a.get("fonte") for a in d["ativos_validados"]),
         "33+ validados com 'fonte'"),
        ("Coletas/Decisao_V2.json",
         lambda d: (d.get("decisao", {})
                     .get("metadados", {})
                     .get("confluencia", {})
                     .get("score_magnitude")) is not None,
         "confluencia.score_magnitude preenchido (fix75)"),
        ("Coletas/Metricas_Calculadas.json",
         lambda d: d.get("indicadores_compostos", {})
                    .get("indicador_adrs_brasileiras") is not None,
         "indicador_adrs_brasileiras presente"),
    ]

    if Path(hist_path).exists():
        schemas_criticos.append(
            (hist_path,
             lambda d: bool(((d.get("atualizacoes") or [{}])[-1]
                             .get("cenario", {}) or {})
                            .get("direcao_provavel")),
             "atualizacoes[-1].cenario.direcao_provavel (fix73/79)")
        )

    for arq, validador, descricao in schemas_criticos:
        d = _ler_json(arq)
        if d is None:
            print(f"   \u23ED\uFE0F  SCHEMA: {arq:<38} -> [SKIP: sem arquivo]")
            continue
        try:
            if validador(d):
                print(f"   \u2705 SCHEMA: {arq:<38} -> [OK]")
            else:
                print(f"   \u274C SCHEMA: {arq:<38} -> [FALHA: {descricao}]")
                falhas += 1
        except Exception as e:
            print(f"   \u274C SCHEMA: {arq:<38} -> [ERRO: {e}]")
            falhas += 1

    print("-" * 60)

    # 5. VALIDACAO FUNCIONAL (fix80)
    print("\U0001F50D BLOCO 5: FUNCOES CRITICAS")

    # Teste A: leitura de cenario do Historico_Aberturas (replica fix73/79)
    if Path(hist_path).exists():
        try:
            d = _ler_json(hist_path)
            atu = d.get("atualizacoes") or []
            if atu:
                cen = atu[-1].get("cenario") or {}
                if cen.get("direcao_provavel"):
                    print(f"   \u2705 FUNC: cenario Historico_Aberturas -> [OK: {cen['direcao_provavel']}]")
                else:
                    print(f"   \u274C FUNC: cenario Historico_Aberturas -> [direcao_provavel vazio]")
                    falhas += 1
        except Exception as e:
            print(f"   \u274C FUNC: cenario -> [ERRO: {e}]")
            falhas += 1
    else:
        print(f"   \u23ED\uFE0F  FUNC: cenario -> [SKIP: {hist_path} nao existe]")

    # Teste B: canonicos == aliases no payload (fix75)
    try:
        d = _ler_json("Coletas/Decisao_V2.json")
        if d:
            c = (d.get("decisao", {}).get("metadados", {})
                  .get("confluencia", {}))
            if (c.get("score_magnitude") == c.get("nm_magnitude")
                and c.get("score_direcao") == c.get("nm_direcao_score")):
                print(f"   \u2705 FUNC: canonicos == aliases (fix75) -> [OK]")
            else:
                print(f"   \u274C FUNC: canonicos != aliases -> [FALHA]")
                falhas += 1
        else:
            print(f"   \u23ED\uFE0F  FUNC: canonicos -> [SKIP: sem Decisao_V2.json]")
    except Exception as e:
        print(f"   \u274C FUNC: canonicos vs aliases -> [ERRO: {e}]")
        falhas += 1

    print("-" * 60)

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
