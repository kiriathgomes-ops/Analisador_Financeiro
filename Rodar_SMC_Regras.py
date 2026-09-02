#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rodar_SMC_Regras.py
===================
Script executor para rodar a análise SMC com Filtro de Volume e Deslocamento.

Fluxo:
1. Conecta ao MT5 e obtém os dados recentes de M5.
2. Executa a análise SMC (via Motor_SMC_Regras.py).
3. Salva o resultado em 'Coletas/AnaliseGraficaSMC_Regras.json'.
4. Imprime no terminal o resumo e os METADADOS contendo as métricas de volume.
"""

import json
import sys
from pathlib import Path

# Garante que o diretório atual está no path para importar o motor
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Importa as funções do Motor SMC
try:
    from Motor_SMC_Regras import analisar_smc, carregar_mt5, salvar_resultado, CONFIG
except ImportError as e:
    print(f"Erro ao importar Motor_SMC_Regras.py: {e}")
    sys.exit(1)

# Força codificação UTF-8 no terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def executar():
    print("=" * 60)
    print(" Executando Análise SMC (Com Filtro de Volume e Expansão)")
    print("=" * 60)

    ATIVO = "WIN$"
    TIMEFRAME_MIN = 5
    QTD_CANDLES = 300

    try:
        # 1. Carrega dados do MetaTrader 5
        print(f"-> Conectando ao MT5 para buscar {QTD_CANDLES} candles de {ATIVO} (M{TIMEFRAME_MIN})...")
        candles, simbolo_real = carregar_mt5(symbol=ATIVO, timeframe_min=TIMEFRAME_MIN, qtd=QTD_CANDLES)
        print(f"   [OK] Sucesso! Símbolo retornado: '{simbolo_real}' | Candles obtidos: {len(candles)}")

        # 2. Executa o algoritmo de análise
        print("-> Processando regras SMC (Swings, BOS/CHoCH, FVG, OB e Liquidez)...")
        resultado = analisar_smc(
            dados_candles=candles,
            ativo=simbolo_real,
            timeframe=f"{TIMEFRAME_MIN}m",
            config=CONFIG
        )

        # 3. Salva no arquivo JSON padrão do pipeline
        caminho_json = salvar_resultado(resultado)
        print(f"   [OK] Análise salva em: {caminho_json}")

        # 4. Exibe os resultados principais no terminal
        print("\n" + "-" * 60)
        print(" RESUMO DO PROCESSAMENTO")
        print("-" * 60)
        print(f" Ativo / Timeframe    : {resultado.get('ativo')} | {resultado.get('timeframe')}")
        print(f" Preço Atual          : {resultado.get('preco_atual')}")
        print(f" Viés Direcional      : {resultado.get('bias_direcional')}")
        print(f" Confiança Visual     : {resultado.get('confianca_visual')}%")
        print(f" Entrada Sugerida     : {resultado.get('entrada_sugerida')}")
        print(f" Stop Sugerido        : {resultado.get('stop_sugerido')}")
        print(f" Alvos                : {resultado.get('alvos')}")
        print(f" Order Blocks Válidos : {len(resultado.get('order_blocks', []))}")
        print(f" FVGs Abertos Válidos : {len(resultado.get('fair_value_gaps', []))}")

        # 5. EXIBE OS METADADOS (Onde você confirma se o filtro de volume rodou)
        print("\n" + "-" * 60)
        print(" METADADOS DA ANÁLISE (FILTROS DE VOLUME E CONFIGURAÇÕES)")
        print("-" * 60)
        metadados = resultado.get("metadados", {})
        print(json.dumps(metadados, indent=2, ensure_ascii=False))
        print("=" * 60)

    except Exception as err:
        print(f"\n[ERRO] Falha ao rodar pipeline SMC: {err}")
        sys.exit(1)


if __name__ == "__main__":
    executar()