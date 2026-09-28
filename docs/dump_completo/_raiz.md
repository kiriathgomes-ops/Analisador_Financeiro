# Dump completo - _raiz

Gerado em: 2026-09-27 22:07:53
Total de arquivos: 42

## Arvore

```
.
|-- Agendador.py
|-- Analise_Noticias.py
|-- Calculadora.py
|-- CalculadoraEstimativaAbertura.py
|-- Coleta_Noticias_Calendario.py
|-- Coletor.py
|-- Coletor_MT5_v2_2.py
|-- Gerar_Mapa_Fluxo.py
|-- Gerar_Mapa_Inventario_Tecnico.py
|-- Gerar_Mapa_Projeto.py
|-- Gerar_Relatorio_Mensagem.py
|-- Gerar_Resultado_Operacional_Abertura.py
|-- Limpar_Imagens_TradingView.py
|-- MapearTendencia15Min.py
|-- Motor_SMC_Regras.py
|-- README.md
|-- Rodar_SMC_Regras.py
|-- Temp_Validacao_Smoke.py
|-- Validador.py
|-- abertura 25set.txt
|-- analisar_divergencia.py
|-- analisar_historico.py
|-- analisar_historico_v2.py
|-- analisar_rompimento_10h.py
|-- app_home.py
|-- backtest_bias_estabilidade.py
|-- cache_candles.py
|-- comçarNovotrab.txt
|-- config.py
|-- diag_orb_10h.py
|-- fix01.py
|-- fix02.py
|-- fix03.py
|-- fix04.py
|-- gerar_docs.py
|-- gerar_dump_completo.py
|-- gerar_snapshot_mtf_ia.py
|-- main_pipeline.py
|-- requirements.txt
|-- v2_gravar_sessao_win.py
|-- v2_rodar_decisao_completa.py
`-- win_abertura_sniper.py
```

## Conteudo dos arquivos

### `Agendador.py`

```python
# ============================================================
# ARQUIVO: Agendador.py
#
# AGENDADOR SINCRONIZADO COM RELÓGIO (A CADA 5 MIN EM :04, :09, :14...)
# ============================================================

import os
import subprocess
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PIPELINE = os.path.join(BASE_DIR, "main_pipeline.py")


def calcular_segundos_ate_proximo_ciclo():
    """Calcula quantos segundos faltam até o próximo minuto terminado em 4 ou 9."""
    agora = datetime.now()
    minuto_atual = agora.minute
    segundo_atual = agora.second
    microsegundo_atual = agora.microsecond

    # Calcula os minutos necessários até o próximo múltiplo de 5 vindo do :04
    # Os minutos de disparo são: 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59
    minutos_para_esperar = (4 - (minuto_atual % 5)) % 5

    # Se já passou do segundo 0 do minuto exato de execução, espera o próximo ciclo de 5 min
    if minutos_para_esperar == 0 and (
        segundo_atual > 0 or microsegundo_atual > 0
    ):
        minutos_para_esperar = 5

    # Converte tudo para segundos exatos
    segundos_restantes = (
        (minutos_para_esperar * 60)
        - segundo_atual
        - (microsegundo_atual / 1_000_000.0)
    )
    return max(0.0, segundos_restantes)


def iniciar_agendador():
    print("============================================================")
    print("⏰ AGENDADOR SINCRONIZADO INICIADO")
    print("🎯 PONTOS DE EXECUÇÃO: :04 | :09 | :14 | :19 | :24 | :29 ...")
    print("============================================================")

    while True:
        segundos_espera = calcular_segundos_ate_proximo_ciclo()
        proximo_disparo = time.strftime(
            "%H:%M:%S", time.localtime(time.time() + segundos_espera)
        )

        print(
            f"\n[⏳ STATUS] Aguardando {int(segundos_espera)}s até a próxima janela ({proximo_disparo})..."
        )
        time.sleep(segundos_espera)

        print(
            f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 Disparando Main Pipeline..."
        )
        try:
            subprocess.run([sys.executable, SCRIPT_PIPELINE], check=True)
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Ciclo concluído com sucesso."
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro na execução do pipeline: {e}")
        except Exception as e:
            print(f"⚠️ Falha inesperada no agendador: {e}")


if __name__ == "__main__":
    iniciar_agendador()

```

### `Analise_Noticias.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: Analise_Noticias.py
Versão: 2.5 - Produção Pipeline V2
Objetivo: Processar o impacto das notícias macro em lote e gerar travas de volatilidade.
"""

import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Ingestão de caminhos, pesos e constantes unificadas do seu config.py
from config import (
    FILE_NOTICIAS_CALENDARIO,
    FILE_NOTICIAS_IMPACTO,
    PESO_ESTRELAS,
    COLETAS_DIR
)

def classificar_risco(pontos: int) -> str:
    """Classifica a intensidade do risco com base no somatório de pesos das notícias."""
    if pontos >= 15:
        return "EXTREMO"
    elif pontos >= 9:
        return "ALTO"
    elif pontos >= 4:
        return "ATENÇÃO"
    return "BAIXO"

def analisar_noticias_lote() -> dict:
    print("=" * 60)
    print(" 📰 INICIANDO COMPILADOR QUANTITATIVO DE IMPACTO MACRO (V2)")
    print("=" * 60)
    print(f"🕒 Horário do Processamento: {datetime.now().strftime('%H:%M:%S')}")
    
    timestamp_iso = datetime.now().isoformat()
    
    # Estrutura defensiva padrão (Fallback Neutro) caso o JSON de entrada falhe
    resultado_padrao = {
        "metadata": {
            "timestamp": timestamp_iso,
            "fonte": "Analise Noticias TV API V2 (Fallback)",
        },
        "resumo": {
            "impacto_total": 0,
            "classificacao": "BAIXO",
        },
        "alertas": {
            "tem_3_estrelas_brasil_0900": False,
            "tem_3_estrelas_outros_horarios": False,
            "noticias_3_estrelas_outros_horarios": [],
            "tem_multiplas_2_estrelas_mesmo_horario": False,
            "horarios_multiplas_2_estrelas": [],
            "risco_abertura_WIN": False,
        },
        "horarios": [],
    }

    # 1. VALIDAÇÃO DEFENSIVA DE ENTRADA DO ARQUIVO BRUTO
    if not FILE_NOTICIAS_CALENDARIO.exists():
        print(f"⚠️ [AVISO] Calendário econômico bruto ausente: {FILE_NOTICIAS_CALENDARIO.name}")
        print("   -> Gerando payload padrão com risco BAIXO para liberar o pipeline.")
        with open(FILE_NOTICIAS_IMPACTO, "w", encoding="utf-8") as arquivo:
            json.dump(resultado_padrao, arquivo, indent=4, ensure_ascii=False)
        return resultado_padrao

    try:
        # 2. LEITURA DOS DADOS COLETADOS PELO PIPELINE
        with open(FILE_NOTICIAS_CALENDARIO, "r", encoding="utf-8") as arquivo:
            dados_brutos = json.load(arquivo)

        # Ajuste adaptativo para aceitar os dois schemas possíveis do seu coletor
        eventos = dados_brutos.get("calendario_eventos", {}).get("eventos", []) or dados_brutos.get("eventos", [])

        agrupados = {}
        impacto_total = 0

        # Estruturas de controle para os alertas institucionais de risco
        alerta_3_estrelas_brasil_0900 = False
        noticias_3_estrelas_outros_horarios = []
        horarios_com_multiplas_2_estrelas = []

        # 3. PROCESSAMENTO MATEMÁTICO DOS PESOS EM LOTE
        for evento in eventos:
            hora = evento.get("hora", "")
            importancia = int(evento.get("importancia", 0))
            pais = evento.get("pais", "")
            moeda = evento.get("moeda", "")
            nome_evento = evento.get("evento", "")

            # Captura o peso configurado centralizadamente no config.py (A2)
            peso = PESO_ESTRELAS.get(importancia, 0)
            impacto_total += peso

            if hora not in agrupados:
                agrupados[hora] = {"pontuacao": 0, "eventos": []}

            agrupados[hora]["pontuacao"] += peso
            agrupados[hora]["eventos"].append({
                "nome": nome_evento,
                "pais": pais,
                "moeda": moeda,
                "estrelas": importancia,
                "peso": peso,
            })

            # CHECAGEM 1: Notícia Máxima de 3 Estrelas no Brasil exatamente às 09:00h
            if hora == "09:00" and importancia == 3 and (pais == "Brazil" or moeda == "BRL"):
                alerta_3_estrelas_brasil_0900 = True

            # CHECAGEM 2: Notícias de 3 Estrelas em outros horários operacionais relevantes
            if importancia == 3 and hora != "09:00":
                noticias_3_estrelas_outros_horarios.append({
                    "hora": hora,
                    "pais": pais,
                    "moeda": moeda,
                    "evento": nome_evento,
                })

        # 4. COMPILAÇÃO CHRONOLÓGICA E CHECAGEM DE ACÚMULO DE SPREAD
        analise_horarios = []
        for hora, dados_hora in agrupados.items():
            qtd_duas_estrelas = sum(1 for ev in dados_hora["eventos"] if ev["estrelas"] == 2)

            # CHECAGEM 3: Concentração de 2 ou mais notícias de 2 estrelas no mesmo slot
            tem_multiplas_2 = qtd_duas_estrelas >= 2
            if tem_multiplas_2:
                horarios_com_multiplas_2_estrelas.append({
                    "hora": hora,
                    "quantidade_2_estrelas": qtd_duas_estrelas,
                })

            analise_horarios.append({
                "hora": hora,
                "pontuacao": dados_hora["pontuacao"],
                "classificacao": classificar_risco(dados_hora["pontuacao"]),
                "quantidade_eventos": len(dados_hora["eventos"]),
                "duas_estrelas_equivalente_alta": tem_multiplas_2,
                "eventos": dados_hora["eventos"],
            })

        # 5. MONTAGEM DO PAYLOAD CONSOLIDADO V2
        resultado = {
            "metadata": {
                "timestamp": timestamp_iso,
                "fonte": "Analise Noticias TV API V2",
            },
            "resumo": {
                "impacto_total": impacto_total,
                "classificacao": classificar_risco(impacto_total),
            },
            "alertas": {
                "tem_3_estrelas_brasil_0900": alerta_3_estrelas_brasil_0900,
                "tem_3_estrelas_outros_horarios": len(noticias_3_estrelas_outros_horarios) > 0,
                "noticias_3_estrelas_outros_horarios": noticias_3_estrelas_outros_horarios,
                "tem_multiplas_2_estrelas_mesmo_horario": len(horarios_com_multiplas_2_estrelas) > 0,
                "horarios_multiplas_2_estrelas": horarios_com_multiplas_2_estrelas,
                "risco_abertura_WIN": impacto_total >= 10,
            },
            "horarios": sorted(analise_horarios, key=lambda x: x["hora"]),
        }

        # 6. SALVAMENTO DA TOMADA DE DECISÃO MACRO NO DISCO
        COLETAS_DIR.mkdir(parents=True, exist_ok=True)
        with open(FILE_NOTICIAS_IMPACTO, "w", encoding="utf-8") as arquivo:
            json.dump(resultado, arquivo, indent=4, ensure_ascii=False)

        # Painel Informativo de Console (Lote logs)
        print(f"  └─ Impacto Global Processado : {impacto_total} pontos")
        print(f"  └─ Classificação Operacional : {resultado['resumo']['classificacao']}")
        print(f"  └─ Risco de Abertura WIN     : {'⚠️ ELEVADO' if resultado['alertas']['risco_abertura_WIN'] else '🟢 SEGURO'}")
        if alerta_3_estrelas_brasil_0900:
            print("  🚨 [TRAVA ATIVADA]: Evento 3 Estrelas BRL agendado para às 09:00h!")
        print(f"✅ Arquivo de impacto gravado com sucesso em: {FILE_NOTICIAS_IMPACTO.name}\n")
        
        return resultado

    except Exception as e:
        print(f"❌ [ERRO CRÍTICO NO MÓDULO NOTÍCIAS]: {e}")
        traceback.print_exc()
        
        # Isola a falha e grava o payload defensivo para não derrubar o main_pipeline.py
        with open(FILE_NOTICIAS_IMPACTO, "w", encoding="utf-8") as arquivo:
            json.dump(resultado_padrao, arquivo, indent=4, ensure_ascii=False)
        return resultado_padrao

if __name__ == "__main__":
    analisar_noticias_lote()

```

### `Calculadora.py`

```python
# ============================================================
# ARQUIVO: Calculadora.py
# DATA: 30/07/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Fase 4 - Cálculo de Spreads, Curva DI, Mercado Externo
#         e Indicadores Compostos alinhados aos IDs do Validador.
# DESCRICAO:
#   Esta engine processa os dados validados (Dados_Validados.json)
#   e calcula métricas financeiras essenciais:
#     - Spread WDO vs PTAX (arbitragem de câmbio)
#     - Inclinação da curva de juros (DI1 2027 vs 2029)
#     - Indicador de Mercado Externo (VIX, Petróleo, Minério)
#     - Indicador de ADRs Brasileiras (soma das variações percentuais)
#     - Resumo de desempenho de ADRs e índices globais
#
#   O resultado é salvo em Metricas_Calculadas.json.
#   Ponderação definida empiricamente para o Mini Índice:
# - EWZ captura o sentimento do Brasil via ETF
# - Cesta de ADRs (VALE/PETR/ITUB/BBD) representa o peso setorial do Ibovespa
# - S&P500 traz o beta com o mercado americano
# - Commodities (minério + petróleo) capturam o lado cíclico
# ============================================================

import json
import os
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO DE DIRETÓRIOS E ARQUIVOS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
FILE_INPUT = os.path.join(COLETAS_DIR, "Dados_Validados.json")
FILE_OUTPUT = os.path.join(COLETAS_DIR, "Metricas_Calculadas.json")

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def carregar_dados_validados() -> dict:
    """
    Carrega o arquivo Dados_Validados.json e o converte em um dicionário
    indexado pelo campo 'ativo_id' para fácil acesso.
    
    Retorna:
        dict: Dicionário Mapeado por ativo_id, ou None em caso de falha de leitura.
    """
    if not os.path.exists(FILE_INPUT):
        print(f"[ERRO] Arquivo não encontrado: {FILE_INPUT}")
        return None

    try:
        with open(FILE_INPUT, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Transforma a lista em dicionário chaveado pelo ativo_id para acesso O(1)
        mapa = {item["ativo_id"]: item for item in data.get("ativos_validados", [])}
        return mapa
    except Exception as e:
        print(f"[ERRO] Falha ao processar arquivo JSON: {e}")
        return None

# ============================================================
# FUNÇÃO PRINCIPAL DE CÁLCULO
# ============================================================

def calcular_metricas() -> None:
    """
    Executa a engine de cálculos:
      1. Carrega os dados validados.
      2. Calcula spreads, inclinação da curva e indicadores compostos.
      3. Gera o arquivo de saída com todas as métricas consolidadas.
    """
    mapa = carregar_dados_validados()
    if not mapa:
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando engine de cálculos...")

    # ------------------------------------------------------------
    # 1. SPREAD DÓLAR FUTURO (WDO) VS PTAX
    # ------------------------------------------------------------
    ptax = mapa.get("USD_PTAX", {}).get("close")
    wdo = mapa.get("WDO_FUT", {}).get("close")

    spread_wdo_ptax_pts = None
    spread_wdo_ptax_pct = None
    
    if isinstance(ptax, (int, float)) and isinstance(wdo, (int, float)) and ptax > 0:
        ptax_em_pontos = ptax * 1000
        spread_wdo_ptax_pts = round(wdo - ptax_em_pontos, 2)
        spread_wdo_ptax_pct = round(((wdo / ptax_em_pontos) - 1) * 100, 4)

    # ------------------------------------------------------------
    # 2. INCLINAÇÃO DA CURVA DE JUROS (DI1 2027 vs 2029)
    # ------------------------------------------------------------
    di27 = mapa.get("DI1_2027", {}).get("close")
    di29 = mapa.get("DI1_2029", {}).get("close")

    inclinacao_di_bps = None
    if isinstance(di27, (int, float)) and isinstance(di29, (int, float)):
        inclinacao_di_bps = round((di29 - di27) * 100, 1)   # em pontos base (bps)

    # ------------------------------------------------------------
    # 3. INDICADOR DE MERCADO EXTERNO
    #    Fórmula: -(VIX_pct) + CRUDE_OIL_pct + IRON_ORE_2M_pct
    # ------------------------------------------------------------
    vix_obj = mapa.get("VIX", {})
    vix_close = vix_obj.get("close")
    vix_pct = vix_obj.get("change_percent")

    dxy = mapa.get("DXY", {}).get("close")

    crude_obj = mapa.get("CRUDE_OIL", {})
    crude_close = crude_obj.get("close")
    crude_pct = crude_obj.get("change_percent")

    fef2_obj = mapa.get("IRON_ORE_2M", {})
    iron_fef2_close = fef2_obj.get("close")
    iron_fef2_pct = fef2_obj.get("change_percent")

    ind_mercado_externo = None
    if all(isinstance(v, (int, float)) for v in [vix_pct, crude_pct, iron_fef2_pct]):
        ind_mercado_externo = round((-vix_pct) + crude_pct + iron_fef2_pct, 4)

    # ------------------------------------------------------------
    # 4. DESEMPENHO DE ADRs E ÍNDICES GLOBAIS
    # ------------------------------------------------------------
    ewz_var = mapa.get("EWZ", {}).get("change_percent")
    sp_var = mapa.get("SP500_FUT", {}).get("change_percent")
    nq_var = mapa.get("NASDAQ_FUT", {}).get("change_percent")

    # Lista de ADRs brasileiras monitoradas
    adrs_chaves = [
        "BBD_ADR",
        "ITUB_ADR",
        "PETR_ADR",
        "VALE_ADR",
        "BBAS_ADR",
        "B3_ADR",
    ]

    resumo_adrs = {}
    soma_variacoes_adrs = 0.0
    qtd_adrs_validas = 0

    for adr_id in adrs_chaves:
        if adr_id in mapa:
            obj = mapa[adr_id]
            c_val = obj.get("close")
            pct_val = obj.get("change_percent")

            resumo_adrs[adr_id] = {
                "close": c_val,
                "change_percent": pct_val,
            }

            if isinstance(pct_val, (int, float)):
                soma_variacoes_adrs += pct_val
                qtd_adrs_validas += 1

    # Indicador ADRs Brasileiras = soma das variações
    ind_adrs_brasileiras = round(soma_variacoes_adrs, 4) if qtd_adrs_validas > 0 else None

    # ------------------------------------------------------------
    # 5. PRESERVA PENÚLTIMA COLETA (antes de sobrescrever)
    # ------------------------------------------------------------
    anterior = None
    if os.path.exists(FILE_OUTPUT):
        try:
            with open(FILE_OUTPUT, "r", encoding="utf-8") as f:
                metricas_anteriores = json.load(f)
            ind_ant = metricas_anteriores.get("indicadores_compostos", {})
            ts_ant = metricas_anteriores.get("metadata_calculo", {}).get("timestamp")
            # Só grava como "anterior" se houver valores válidos
            if ind_ant.get("indicador_mercado_externo") is not None or ind_ant.get("indicador_adrs_brasileiras") is not None:
                anterior = {
                    "indicador_mercado_externo": ind_ant.get("indicador_mercado_externo"),
                    "indicador_adrs_brasileiras": ind_ant.get("indicador_adrs_brasileiras"),
                    "timestamp": ts_ant,
                }
        except Exception:
            anterior = None

    # ------------------------------------------------------------
    # 6. MONTAGEM DO RESULTADO FINAL
    # ------------------------------------------------------------
    agora_iso = datetime.now().isoformat()
    metricas = {
        "metadata_calculo": {
            "timestamp": agora_iso,
            "total_ativos_processados": len(mapa),
        },
        "cambio_e_arbitragem": {
            "usd_ptax": ptax,
            "wdo_fut": wdo,
            "spread_wdo_ptax_pontos": spread_wdo_ptax_pts,
            "spread_wdo_ptax_percentual": spread_wdo_ptax_pct,
        },
        "curva_juros_b3": {
            "di1_2027_taxa": di27,
            "di1_2029_taxa": di29,
            "inclinacao_29_27_bps": inclinacao_di_bps,
        },
        "indicadores_macro": {
            "vix": vix_close,
            "vix_change_pct": vix_pct,
            "dxy": dxy,
            "crude_oil": crude_close,
            "crude_oil_change_pct": crude_pct,
            "iron_ore_fef2": {
                "close": iron_fef2_close,
                "change_percent": iron_fef2_pct,
            },
        },
        "performance_relativa": {
            "ewz_change_pct": ewz_var,
            "sp500_fut_change_pct": sp_var,
            "nasdaq_fut_change_pct": nq_var,
            "adrs_brasileiras": resumo_adrs,
        },
        "indicadores_compostos": {
            "indicador_mercado_externo": ind_mercado_externo,
            "indicador_adrs_brasileiras": ind_adrs_brasileiras,
        },
        "anterior": anterior,
        "atualizado_em": agora_iso,
    }

    # Salva o arquivo de saída
    with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(metricas, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------
    # 7. EXIBIÇÃO DO PAINEL NO CONSOLE
    # ------------------------------------------------------------
    print("\n" + "=" * 60)
    print(" PAINEL DE MÉTRICAS CALCULADAS ")
    print("=" * 60)
    print(f"Spread WDO vs PTAX      : {spread_wdo_ptax_pts} pts ({spread_wdo_ptax_pct}%)")
    print(f"Inclinação DI (29-27)   : {inclinacao_di_bps} bps")
    print(f"VIX (Volatilidade)      : {vix_close} ({vix_pct}%)")
    print(f"Minério FEF2 (2º Mês)   : {iron_fef2_close} ({iron_fef2_pct}%)")
    print("------------------------------------------------------------")
    print(f"IND. MERCADO EXTERNO    : {ind_mercado_externo}%")
    print(f"IND. ADRs BRASILEIRAS   : {ind_adrs_brasileiras}%")
    if anterior:
        print(f"PENÚLTIMA MERC. EXT.    : {anterior.get('indicador_mercado_externo')}%")
        print(f"PENÚLTIMA ADRs          : {anterior.get('indicador_adrs_brasileiras')}%")
        print(f"Timestamp penúltima     : {anterior.get('timestamp')}")
    print("=" * 60)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Arquivo gerado: {os.path.basename(FILE_OUTPUT)}\n")

# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    print("============================================================")
    print(" FASE 4: ENGINE DE CÁLCULO E MÉTRICAS FINANCEIRAS")
    print("============================================================")
    calcular_metricas()
```

### `CalculadoraEstimativaAbertura.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: CalculadoraEstimativaAbertura.py (Versão Otimizada V2 + Cost of Carry + SMC)
Objetivo: Processar estimativas e pivôs para o WIN eliminando ruído de leilão.
Regra: 09:00 usa o Last Tick congelado da noite. 10:00 usa o último close de M1/M5.
Preserva: Cálculos originais de Pivô Clássico (Floor Pockets) para consumo em páginas externas.
"""

import json
import os
import sys
from datetime import datetime, time
from pathlib import Path

from config import (
    COLETAS_DIR,
    FILE_VALIDADOS as FILE_INPUT,
    FILE_ESTIMATIVA_ABERTURA as FILE_OUTPUT,
    PESOS_ESTIMATIVA_ABERTURA,
)

# Força codificação UTF-8 no terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

FILE_SMC_DADOS = Path(COLETAS_DIR) / "AnaliseGraficaSMC_Regras.json"
FILE_CACHE_VAR_TEORICA = Path(COLETAS_DIR) / "EstimativaAbertura_Cache.json"


def extrair_variacao(ativos_dict: dict, ativo_id: str) -> float:
    dados = ativos_dict.get(ativo_id, {}).get("change_percent")
    return float(dados) if isinstance(dados, (int, float)) else 0.0


def carregar_niveis_institucionais_smc() -> dict:
    """Lê a POC e a VWAP do dia anterior geradas pelo motor SMC."""
    if not os.path.exists(FILE_SMC_DADOS):
        return {"poc_ontem": 0.0, "vwap_ontem": 0.0}
    try:
        with open(FILE_SMC_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados.get("niveis_institucionais", {})
    except Exception:
        return {"poc_ontem": 0.0, "vwap_ontem": 0.0}


def _carregar_cache_var() -> dict:
    """Le o cache da variacao teorica, se existir."""
    if not os.path.exists(FILE_CACHE_VAR_TEORICA):
        return {}
    try:
        with open(FILE_CACHE_VAR_TEORICA, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_cache_var(payload: dict) -> None:
    """Persiste o cache da variacao teorica."""
    try:
        os.makedirs(os.path.dirname(FILE_CACHE_VAR_TEORICA), exist_ok=True)
        with open(FILE_CACHE_VAR_TEORICA, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[AVISO] Falha ao salvar cache var teorica: {e}")


def _resolver_var_teorica(data_ref: str, ajuste: float, var_teorica_atual: float):
    """
    Resolve a var_teorica_pct a ser usada neste ciclo.

    Retorna (var_final, veio_do_cache, timestamp_cache).
      - Se cache existe e bate (data + ajuste): usa cache
      - Se nao: salva o valor atual no cache e retorna ele

    `timestamp_cache` e None quando recalculado agora.
    """
    cache = _carregar_cache_var()
    ajuste_arredondado = round(float(ajuste or 0.0), 0)

    cache_data = cache.get("data_ref")
    cache_ajuste = cache.get("ajuste")
    if cache_data is not None:
        try:
            cache_ajuste = round(float(cache_ajuste), 0)
        except (TypeError, ValueError):
            cache_ajuste = None

    if cache_data == data_ref and cache_ajuste == ajuste_arredondado:
        var = cache.get("variacao_teorica_pct")
        ts = cache.get("timestamp_geracao")
        if var is not None:
            return float(var), True, ts

    # Cache invalido ou inexistente -> salva o atual
    novo = {
        "data_ref": data_ref,
        "ajuste": ajuste_arredondado,
        "variacao_teorica_pct": float(var_teorica_atual) if var_teorica_atual is not None else 0.0,
        "timestamp_geracao": datetime.now().isoformat(),
    }
    _salvar_cache_var(novo)
    return float(var_teorica_atual) if var_teorica_atual is not None else 0.0, False, None


def calcular_abertura_win(ativos_dict: dict, preco_referencia_base: float) -> dict:
    """Calcula a estimativa de abertura combinando o Delta Overnight com o Cost of Carry."""
    ewz = extrair_variacao(ativos_dict, "EWZ")
    sp500 = extrair_variacao(ativos_dict, "SP500_FUT")
    vale = extrair_variacao(ativos_dict, "VALE_ADR")
    petr = extrair_variacao(ativos_dict, "PETR_ADR")
    
    pesos = PESOS_ESTIMATIVA_ABERTURA
    cesta_adrs = (vale * pesos.get("adr_vale", 0.30)) + (petr * pesos.get("adr_petr", 0.25))
    var_pct = (ewz * pesos.get("ewz", 0.30)) + (cesta_adrs * pesos.get("cesta_adrs", 0.35)) + (sp500 * pesos.get("sp500_fut", 0.20))
    
    abertura_estimada = 0.0
    if preco_referencia_base > 0:
        abertura_estimada = preco_referencia_base * (1 + (var_pct / 100))

    # --- CUSTO DE CARREGAMENTO (COST OF CARRY INSTITUCIONAL) ---
    taxa_di1 = ativos_dict.get("DI1_2027", {}).get("close", 13.5) / 100.0
    dias_uteis_ano = 252.0
    fator_carregamento_diario = (1 + taxa_di1) ** (1.0 / dias_uteis_ano) - 1
    preco_cost_of_carry = preco_referencia_base * (1 + fator_carregamento_diario) if preco_referencia_base > 0 else 0.0

    return {
        "variacao_teorica_pct": round(var_pct, 4),
        "preco_referencia_base": preco_referencia_base,
        "abertura_teorica_pontos": round(abertura_estimada, 0),
        "cost_of_carry": {
            "taxa_di_anual_pct": round(taxa_di1 * 100, 2),
            "fator_diario_pct": round(fator_carregamento_diario * 100, 6),
            "preco_teorico_carregado": round(preco_cost_of_carry, 0)
        }
    }


def processar_calculos_operacionais():
    print("=" * 60)
    print(" 🧮 CALCULADORA DE ESTIMATIVA DE ABERTURA & COST OF CARRY")
    print("=" * 60)

    if not os.path.exists(FILE_INPUT):
        print(f"❌ Arquivo de entrada não encontrado: {FILE_INPUT}")
        return

    with open(FILE_INPUT, "r", encoding="utf-8") as f:
        dados_json = json.load(f)

    ativos_dict = {item["ativo_id"]: item for item in dados_json.get("ativos_validados", [])}

        # --- PREÇO BASE DE REFERÊNCIA (sempre o ajuste oficial) ---
    # O ajuste oficial da B3 é estável durante o dia e é o padrão institucional
    # para cálculo de gap de abertura. NÃO usar WIN_FUT.close (preço atual),
    # que muda a cada tick e faz a "abertura teórica" variar.
    preco_base = ativos_dict.get("WIN_AJUSTE", {}).get("close", 0.0)

    if preco_base <= 0:
        # Fallback: se o ajuste não estiver disponível, usa o fechamento congelado
        preco_base = ativos_dict.get("WIN_LAST_TICK", {}).get("close", 0.0)
        contexto_janela = "FALLBACK_LAST_TICK"
    else:
        contexto_janela = "REFERENCIA_AJUSTE_OFICIAL"

    print(f"🕒 Horário da Consulta    : {datetime.now().strftime('%H:%M:%S')}")
    print(f"📌 Janela Temporal        : {contexto_janela}")
    print(f"💰 Preço Base Referência  : {preco_base}")

    win_metrics = calcular_abertura_win(ativos_dict, preco_base)
    win_metrics["contexto_janela"] = contexto_janela

    # ---- CONGELA variacao_teorica_pct por dia (data + ajuste) ----
    var_teorica_calculada = win_metrics.get("variacao_teorica_pct")
    var_teorica_final, do_cache, ts_cache = _resolver_var_teorica(
        data_ref=datetime.now().date().isoformat(),
        ajuste=preco_base,
        var_teorica_atual=var_teorica_calculada,
    )

    # Recalcula a abertura teorica com a var congelada
    abertura_congelada = round(preco_base * (1 + var_teorica_final / 100), 0) if preco_base > 0 else 0.0

    win_metrics["variacao_teorica_pct"] = round(var_teorica_final, 4)
    win_metrics["abertura_teorica_pontos"] = abertura_congelada
    win_metrics["var_teorica_congelada"] = True
    win_metrics["var_teorica_do_cache"] = bool(do_cache)
    win_metrics["var_teorica_timestamp_cache"] = ts_cache
    win_metrics["var_teorica_calculada_agora"] = (
        round(var_teorica_calculada, 4) if var_teorica_calculada is not None else None
    )

    # --- PONTOS DE PIVÔ CLÁSSICOS (MANTIDOS INTEGRALMENTE PARA SUAS PAGES) ---
    win_fut = ativos_dict.get("WIN_FUT", {})
    high_d1 = win_fut.get("high", 0.0)
    low_d1 = win_fut.get("low", 0.0)
    close_d1 = win_fut.get("previous_close", 0.0) or win_fut.get("close", 0.0)

    pivots = {}
    if high_d1 > 0 and low_d1 > 0 and close_d1 > 0:
        pp = (high_d1 + low_d1 + close_d1) / 3
        pivots = {
            "PP": round(pp, 2),
            "R1": round((2 * pp) - low_d1, 2),
            "R2": round(pp + (high_d1 - low_d1), 2),
            "S1": round((2 * pp) - high_d1, 2),
            "S2": round(pp - (high_d1 - low_d1), 2)
        }

    # --- PONTOS DE PIVÔ INSTITUCIONAIS (SMC / VOLUME PROFILE) ---
    niveis_smc = carregar_niveis_institucionais_smc()

    payload = {
        "metadata_calculo": {
            "timestamp_calculo": datetime.now().isoformat(),
            "janela_ativa": contexto_janela,
            "var_teorica_congelada": win_metrics.get("var_teorica_congelada", False),
            "var_teorica_do_cache": win_metrics.get("var_teorica_do_cache", False),
            "var_teorica_timestamp_cache": win_metrics.get("var_teorica_timestamp_cache"),
        },
        "estimativa_abertura": {"WIN_INDICE": win_metrics},
        "pivot_points": {"WIN_FUT": pivots},
        "pivots_institucionais": {
            "poc_ontem": niveis_smc.get("poc_ontem", 0.0),
            "vwap_ontem": niveis_smc.get("vwap_ontem", 0.0)
        }
    }

    with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # --- SAÍDA FORMATADA NO TERMINAL ---
    print("\n" + "-" * 60)
    print(" 🎯 ESTIMATIVAS DE ABERTURA & CARREGAMENTO")
    print("-" * 60)
    if win_metrics.get("var_teorica_do_cache"):
        ts_cache = win_metrics.get("var_teorica_timestamp_cache") or "?"
        ts_curto = ts_cache[11:19] if len(ts_cache) >= 19 else ts_cache
        origem_var = f"🔒 CONGELADA (do cache, gerada {ts_curto})"
    else:
        origem_var = "🆕 RECALCULADA AGORA (primeira vez hoje ou ajuste mudou)"

    print(f" Variação Teórica (Delta) : {win_metrics['variacao_teorica_pct']}%")
    print(f"   └─ Origem              : {origem_var}")
    print(f" Abertura Teórica WIN     : {win_metrics['abertura_teorica_pontos']} pts")
    
    coc = win_metrics["cost_of_carry"]
    print(f" Taxa DI Referência       : {coc['taxa_di_anual_pct']}% a.a.")
    print(f" Preço Carregado (DI/252) : {coc['preco_teorico_carregado']} pts")

    print("\n" + "-" * 60)
    print(" 📍 PONTOS DE PIVÔ CLÁSSICOS (PÁGINAS EXTERNAS)")
    print("-" * 60)
    print(f" R2: {pivots.get('R2')} | R1: {pivots.get('R1')} | PP: {pivots.get('PP')} | S1: {pivots.get('S1')} | S2: {pivots.get('S2')}")

    print("\n" + "-" * 60)
    print(" 🏦 PIVÔS INSTITUCIONAIS (SMC / VOLUME PROFILE)")
    print("-" * 60)
    print(f" POC (Ontem)  : {niveis_smc.get('poc_ontem')} pts")
    print(f" VWAP (Ontem) : {niveis_smc.get('vwap_ontem')} pts")

    print("\n" + "=" * 60)
    print(f" ✅ Resultados gravados com sucesso em: {FILE_OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    processar_calculos_operacionais()
```

### `Coleta_Noticias_Calendario.py`

```python
# ============================================================
# ARQUIVO: Coleta_Noticias_Calendario.py
# MOTIVO: Coletar eventos econômicos Brasil e EUA (2 e 3 estrelas)
# FONTE: TradingView Economic Calendar API (Sem necessidade de Playwright)
# ============================================================
#
# Descrição:
#   Este script consulta a API pública do calendário econômico do TradingView
#   para obter eventos de alto e médio impacto (2 e 3 estrelas) para Brasil e EUA.
#   Gera dois arquivos JSON:
#     1. Noticias_Calendario_0900.json → alerta específico para eventos
#        brasileiros de 3 estrelas às 09:00 (horário de Brasília).
#     2. Noticias_Calendario.json → lista completa de todos os eventos
#        de 2 e 3 estrelas para Brasil e EUA.
#
# ============================================================

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta

# ============================================================
# CONFIGURAÇÕES DE DIRETÓRIOS E ARQUIVOS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")

FILE_OUTPUT_0900 = os.path.join(COLETAS_DIR, "Noticias_Calendario_0900.json")
FILE_OUTPUT_GERAL = os.path.join(COLETAS_DIR, "Noticias_Calendario.json")

HORA_ALERTA = "09:00"   # Horário de Brasília para o alerta especial

# ============================================================
# CONSULTA À API DO TRADINGVIEW
# ============================================================

def consultar_api_tradingview(data_inicio: str, data_fim: str) -> list:
    """
    Consulta a API pública de calendário econômico do TradingView.

    Parâmetros:
        data_inicio (str): Data de início no formato YYYY-MM-DD.
        data_fim (str): Data de fim no formato YYYY-MM-DD.

    Retorna:
        list: Lista de eventos brutos retornados pela API.
              Retorna lista vazia em caso de erro.
    """
    url = "https://economic-calendar.tradingview.com/events"
    params = f"?from={data_inicio}T00:00:00.000Z&to={data_fim}T23:59:59.000Z&countries=BR,US"

    req = urllib.request.Request(
        url + params,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Origin": "https://www.tradingview.com",
            "Referer": "https://www.tradingview.com/",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.getcode() == 200:
                dados = json.loads(response.read().decode("utf-8"))
                return dados.get("result", [])
    except Exception as e:
        print(f"[ERRO API TRADINGVIEW] Falha na requisição: {e}")
        return []

    return []

# ============================================================
# PROCESSAMENTO DOS EVENTOS
# ============================================================

def processar_eventos(eventos_raw: list) -> tuple:
    """
    Processa os eventos brutos da API, aplicando filtros e classificações.

    Parâmetros:
        eventos_raw (list): Lista de eventos brutos da API.

    Retorna:
        tuple: (eventos_geral, eventos_0900)
            - eventos_geral: todos os eventos de 2 e 3 estrelas (Brasil e EUA)
            - eventos_0900: eventos brasileiros de 3 estrelas às 09:00
    """
    eventos_geral = []
    eventos_0900 = []

    # Palavras-chave para classificação manual (3 estrelas - alto impacto)
    TERMOS_3_ESTRELAS = [
        "inflation rate", "ipca", "cpi", "ppi",
        "interest rate", "selic", "fed interest rate", "fomc", "copom",
        "non farm payrolls", "unemployment rate",
        "gdp", "pib", "pnad", "caged",
        "core cpi", "pce price index",
    ]

    # Palavras-chave para classificação manual (2 estrelas - médio impacto)
    TERMOS_2_ESTRELAS = [
        "retail sales", "industrial production", "pmi",
        "trade balance", "balance of trade",
        "consumer confidence", "business confidence",
        "s&p global", "fgv", "igp-m",
        "durable goods", "building permits",
    ]

    for item in eventos_raw:
        try:
            # Identificação do país
            country = item.get("country", "")
            if country == "BR":
                moeda = "BRL"
                pais = "Brazil"
            elif country == "US":
                moeda = "USD"
                pais = "United States"
            else:
                continue

            nome_evento = item.get("title", "")
            nome_lower = nome_evento.lower()

            # Classificação original da API: -1 = 1★, 0 = 2★, 1 = 3★
            importance_raw = item.get("importance", -1)
            if importance_raw == 1:
                estrelas = 3
            elif importance_raw == 0:
                estrelas = 2
            else:
                estrelas = 1

            # Ajuste manual por palavras-chave (corrige subavaliações da API)
            if any(term in nome_lower for term in TERMOS_3_ESTRELAS):
                estrelas = 3
            elif estrelas < 2 and any(term in nome_lower for term in TERMOS_2_ESTRELAS):
                estrelas = 2

            # Filtra apenas eventos de 2 ou 3 estrelas
            if estrelas < 2:
                continue

            # Conversão do horário (UTC → Brasília)
            date_utc_str = item.get("date", "")
            hora_br = ""
            if date_utc_str:
                dt_utc = datetime.fromisoformat(date_utc_str.replace("Z", "+00:00"))
                dt_br = dt_utc - timedelta(hours=3)
                hora_br = dt_br.strftime("%H:%M")

            # Valores (atual, previsão, anterior)
            atual = str(item.get("actual", "")) if item.get("actual") is not None else ""
            previsao = str(item.get("forecast", "")) if item.get("forecast") is not None else ""
            anterior = str(item.get("previous", "")) if item.get("previous") is not None else ""

            # Monta o dicionário do evento
            item_evento = {
                "hora": hora_br,
                "pais": pais,
                "moeda": moeda,
                "evento": nome_evento,
                "importancia": estrelas,
                "anterior": anterior,
                "previsao": previsao,
                "atual": atual,
            }

            eventos_geral.append(item_evento)

            # Alerta especial: Brasil + 3 estrelas + horário 09:00
            if pais == "Brazil" and estrelas == 3 and hora_br.startswith(HORA_ALERTA):
                eventos_0900.append(item_evento)

        except Exception:
            continue

    return eventos_geral, eventos_0900

# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def obter_noticias_hoje(data_alvo: str = None) -> tuple:
    """
    Obtém o calendário econômico para a data alvo (hoje por padrão).

    Parâmetros:
        data_alvo (str, opcional): Data no formato YYYY-MM-DD.
                                   Se None, usa a data atual.

    Retorna:
        tuple: (res_geral, res_0900)
            - res_geral: dicionário completo com todos os eventos.
            - res_0900: dicionário com o alerta específico para 09:00.
    """
    if data_alvo is None:
        data_referencia = datetime.now().strftime("%Y-%m-%d")
    else:
        data_referencia = data_alvo

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Coletando calendário via TradingView API para: {data_referencia}..."
    )

    eventos_raw = consultar_api_tradingview(data_referencia, data_referencia)
    print(f"[DEBUG] Eventos brutos retornados pela API: {len(eventos_raw)}")

    eventos_geral, eventos_0900 = processar_eventos(eventos_raw)

    timestamp_iso = datetime.now().isoformat()

    # Arquivo 1: alerta específico para 09:00
    res_0900 = {
        "metadata": {
            "fonte": "TradingView API",
            "timestamp": timestamp_iso,
            "data_referencia": data_referencia,
        },
        "alerta_noticia_0900": {
            "tem_evento_3_estrelas": len(eventos_0900) > 0,
            "quantidade_eventos": len(eventos_0900),
            "eventos": eventos_0900,
        },
    }

    # Arquivo 2: calendário completo
    res_geral = {
        "metadata": {
            "fonte": "TradingView API",
            "timestamp": timestamp_iso,
            "data_referencia": data_referencia,
            "filtros": "Brasil e EUA (2 e 3 Estrelas)",
        },
        "calendario_eventos": {
            "quantidade_eventos": len(eventos_geral),
            "eventos": eventos_geral,
        },
    }

    # Garante que a pasta de saída existe
    os.makedirs(COLETAS_DIR, exist_ok=True)

    with open(FILE_OUTPUT_0900, "w", encoding="utf-8") as f1:
        json.dump(res_0900, f1, indent=2, ensure_ascii=False)

    with open(FILE_OUTPUT_GERAL, "w", encoding="utf-8") as f2:
        json.dump(res_geral, f2, indent=2, ensure_ascii=False)

    return res_geral, res_0900

# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    data_argumento = None

    # Suporte ao argumento --data YYYY-MM-DD
    if len(sys.argv) > 1:
        if "--data" in sys.argv:
            idx = sys.argv.index("--data")
            if idx + 1 < len(sys.argv):
                data_argumento = sys.argv[idx + 1]
        else:
            data_argumento = sys.argv[1]

    res_geral, res_0900 = obter_noticias_hoje(data_alvo=data_argumento)

    data_exibida = res_geral["metadata"]["data_referencia"]

    # Exibe resumo no console
    print()
    print("============================================================")
    print(f" CALENDÁRIO ECONÔMICO BRASIL E EUA - TRADINGVIEW ({data_exibida})")
    print("============================================================")
    print(
        f" Total de eventos 2/3★ (BRL/USD): {res_geral['calendario_eventos']['quantidade_eventos']}"
    )

    if res_0900["alerta_noticia_0900"]["tem_evento_3_estrelas"]:
        print(" Alerta 3 Estrelas BR às 09:00 : SIM ⚠️")
    else:
        print(" Alerta 3 Estrelas BR às 09:00 : NÃO 🟢")

    print("============================================================")
    print(f" Arquivo 1 gerado: {FILE_OUTPUT_0900}")
    print(f" Arquivo 2 gerado: {FILE_OUTPUT_GERAL}")
    print("============================================================")
    print()
```

### `Coletor.py`

```python
# ============================================================
# ARQUIVO: Coletor.py
# DATA: 30/07/2026 | Atualizado 18/09/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Ingestão de Dados (BACEN SGS 10813 + TV + B3 WIN/WDO Separados)
#         Engine de Rotação Temporal de Memória e
#         Geração do Arquivo Unificado dos Ativos Mapeados.
#
# ATUALIZAÇÃO 01/09/2026 (Fase 0):
#   - WIN_FUT SEMPRE MT5 ao vivo
#   - WIN_LAST_TICK: MT5 só FORA do pregão + grava LastTick_Congelado.json
#   - No pregão: LAST lido do arquivo fixo (não depende da rotação ROM)
#   - Idem WDO
#
# ATUALIZAÇÃO 18/09/2026 (Opção C — ajuste + fechamento via brapi):
#   - B3_AJUSTE_WIN/WDO agora vêm da brapi.dev (campo 'settlement')
#   - B3_FECHAMENTO_WIN/WDO também vêm da brapi (campo 'close') [auditoria]
#   - Fallback: se o MT5 não entregar 'last' para WIN/WDO, usa o fechamento
#     da brapi em vez de cair direto no cache congelado (pipeline não para
#     mesmo se MT5 estiver offline).
#   - Fix typo: esta_fora_do_pregão → esta_fora_do_pregao
#
# ATUALIZAÇÃO 18/09/2026 (v2 — cosmético):
#   - coletar_ajuste_oficial(silencioso=False): TV fallback agora pode ser
#     chamado em modo silencioso quando roda em paralelo com brapi.
#     Motivo: o TV imprimia "Dentro da janela. Coletando ajuste TV..." mesmo
#     quando o brapi já tinha resolvido — confundia o log.
# ============================================================

from __future__ import annotations

import json
import os
import shutil
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

import MetaTrader5 as mt5
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    BASE_DIR,
    COLETAS_DIR,
    ARQUIVOS_ROM,
    FILE_ROM0,
    FILE_RAM,
    FILE_UNIFICADO,
    FILE_MT5,
    FILE_MT5_V2,
    FILE_LAST_TICK_CONGELADO,
    FINNHUB_API_KEY,
    TICKER_FEF2,
    TICKERS_TRADINGVIEW,
    ATIVOS_FINNHUB,
    ATIVOS_MT5_B3,
    MAPEAMENTO_TICKERS,
    TIMEOUT_TRADINGVIEW,
    TIMEOUT_FINNHUB,
    TIMEOUT_BACEN,
    esta_na_janela_ajuste,
    esta_fora_do_pregao,
    JANELA_AJUSTE_INICIO,
    JANELA_AJUSTE_FIM,
)

# Compatibilidade: paths como str para código legado
BASE_DIR = str(BASE_DIR)
COLETAS_DIR = str(COLETAS_DIR)
ARQUIVOS_ROM = [str(p) for p in ARQUIVOS_ROM]
FILE_ROM0 = str(FILE_ROM0)
FILE_RAM = str(FILE_RAM)
FILE_UNIFICADO = str(FILE_UNIFICADO)
FILE_MT5 = str(FILE_MT5)
FILE_MT5_V2 = str(FILE_MT5_V2)
FILE_LAST_TICK_CONGELADO = str(FILE_LAST_TICK_CONGELADO)

for _cfg in ATIVOS_FINNHUB + ATIVOS_MT5_B3:
    if "id_interno" in _cfg and "id_limpo" not in _cfg:
        _cfg["id_limpo"] = _cfg["id_interno"]

os.makedirs(COLETAS_DIR, exist_ok=True)


# ------------------------------------------------------------
# HTTP Session (pool + retry leve)
# ------------------------------------------------------------
def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


_HTTP = _build_session()


# ------------------------------------------------------------
# LAST MT5 (leitura de arquivo já coletado)
# ------------------------------------------------------------
def capturar_last_do_mt5() -> dict:
    """
    Extrai o 'last' dos contratos principais de WIN e WDO.

    Prioridade:
      1. Dados_MT5_v2_2.json
      2. Dados_MT5.json (legado)
    """
    resultado: dict = {}

    if os.path.exists(FILE_MT5_V2):
        try:
            with open(FILE_MT5_V2, "r", encoding="utf-8") as f:
                dados = json.load(f)

            timestamp = dados.get("timestamp", datetime.now().isoformat())
            ativos = dados.get("ativos", {})

            for prefixo in ("WIN", "WDO"):
                info_ativo = ativos.get(prefixo, {})
                if info_ativo.get("status") == "OK" or info_ativo.get("last") is not None:
                    last = info_ativo.get("last")
                    contrato = info_ativo.get("contrato_principal")
                    if last is not None and last > 0 and contrato:
                        resultado[prefixo] = {
                            "contrato": contrato,
                            "last": float(last),
                            "timestamp": timestamp,
                            "fonte": "MT5_v2.2",
                        }

            if resultado:
                if "WIN" in resultado:
                    print(
                        f"   ✅ Last WIN via MT5 v2.2: "
                        f"{resultado['WIN']['last']} ({resultado['WIN']['contrato']})"
                    )
                if "WDO" in resultado:
                    print(
                        f"   ✅ Last WDO via MT5 v2.2: "
                        f"{resultado['WDO']['last']} ({resultado['WDO']['contrato']})"
                    )
                return resultado

        except Exception as e:
            print(f"[AVISO] Falha ao ler Dados_MT5_v2_2.json: {e}. Tentando formato antigo...")

    if not os.path.exists(FILE_MT5):
        print("[AVISO] Nenhum arquivo MT5 encontrado (v2.2 nem v1).")
        return resultado

    try:
        with open(FILE_MT5, "r", encoding="utf-8") as f:
            dados = json.load(f)

        contratos = dados.get("contratos", {})
        timestamp = dados.get("timestamp", datetime.now().isoformat())
        mapeamento_contratos = {
            "WIN": ["WINQ26", "WINV26", "WINZ26"],
            "WDO": ["WDOQ26", "WDOV26", "WDOZ26", "WDOU26"],
        }

        for ativo, lista in mapeamento_contratos.items():
            for contrato in lista:
                if contrato in contratos:
                    info = contratos[contrato]
                    last = info.get("last")
                    if last is not None and last > 0:
                        resultado[ativo] = {
                            "contrato": contrato,
                            "last": float(last),
                            "timestamp": timestamp,
                            "fonte": "MT5_v1",
                        }
                        break

        if "WIN" in resultado:
            print(
                f"   ✅ Last WIN via MT5 v1: "
                f"{resultado['WIN']['last']} ({resultado['WIN']['contrato']})"
            )
        if "WDO" in resultado:
            print(
                f"   ✅ Last WDO via MT5 v1: "
                f"{resultado['WDO']['last']} ({resultado['WDO']['contrato']})"
            )
        return resultado

    except Exception as e:
        print(f"[ERRO] Falha ao ler Dados_MT5.json: {e}")
        return {}


# ------------------------------------------------------------
# Finnhub (paralelo)
# ------------------------------------------------------------
def coletar_finnhub() -> List[Dict[str, Any]]:
    timestamp = datetime.now().isoformat()
    if not FINNHUB_API_KEY:
        print("⚠️ [AVISO] FINNHUB_API_KEY ausente no .env")
        return []

    def _um(cfg: dict) -> dict:
        ticker = cfg["ticker_coleta"]
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
        try:
            res = _HTTP.get(url, timeout=TIMEOUT_FINNHUB or 5).json()
            if "error" in res:
                return {
                    "ativo": cfg["ativo"],
                    "fonte": "FINNHUB",
                    "timestamp": timestamp,
                    "status": "ERRO",
                    "dados_reais": None,
                }
            if "c" in res and res["c"] != 0:
                return {
                    "ativo": cfg["ativo"],
                    "fonte": "FINNHUB",
                    "timestamp": timestamp,
                    "status": "OK",
                    "dados_reais": {
                        "close": float(res["c"]),
                        "open": None,
                        "high": None,
                        "low": None,
                        "change_percent": round(float(res.get("dp", 0.0)), 2),
                        "volume": None,
                        "var_abs": round(float(res.get("d", 0.0)), 2),
                        "fechamento_anterior": float(res.get("pc", 0.0)),
                    },
                }
            return {
                "ativo": cfg["ativo"],
                "fonte": "FINNHUB",
                "timestamp": timestamp,
                "status": "SEM_DADOS",
                "dados_reais": None,
            }
        except Exception as e:
            print(f"❌ Finnhub ({ticker}): {e}")
            return {
                "ativo": cfg["ativo"],
                "fonte": "FINNHUB",
                "timestamp": timestamp,
                "status": "ERRO",
                "dados_reais": None,
            }

    workers = min(8, max(1, len(ATIVOS_FINNHUB)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_um, ATIVOS_FINNHUB))


# ------------------------------------------------------------
# Ações B3 via MT5
# ------------------------------------------------------------
def coletar_mt5_acoes_b3(mt5_ja_inicializado: bool = False) -> List[Dict[str, Any]]:
    timestamp = datetime.now().isoformat()
    resultados: List[Dict[str, Any]] = []

    own_init = False
    if not mt5_ja_inicializado:
        if not mt5.initialize():
            print("⚠️ MT5 não inicializou para ações B3")
            return resultados
        own_init = True

    try:
        for cfg in ATIVOS_MT5_B3:
            symbol = cfg["ticker_coleta"]
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)

            if not info or not tick:
                resultados.append({
                    "ativo": cfg["ativo"],
                    "fonte": "MetaTrader5",
                    "timestamp": timestamp,
                    "status": "ERRO",
                    "dados_reais": None,
                })
                continue

            prev_close = float(getattr(info, "session_close", 0.0) or 0.0)
            preco = float(
                tick.last if tick.last > 0 else (tick.bid if tick.bid > 0 else tick.ask)
            )

            if preco <= 0:
                resultados.append({
                    "ativo": cfg["ativo"],
                    "fonte": "MetaTrader5",
                    "timestamp": timestamp,
                    "status": "SEM_DADOS",
                    "dados_reais": None,
                })
                continue

            var_pct = (
                round(((preco / prev_close) - 1) * 100, 2) if prev_close > 0 else 0.0
            )
            resultados.append({
                "ativo": cfg["ativo"],
                "fonte": "MetaTrader5",
                "timestamp": timestamp,
                "status": "OK",
                "dados_reais": {
                    "close": preco,
                    "open": None,
                    "high": None,
                    "low": None,
                    "change_percent": var_pct,
                    "volume": None,
                    "var_abs": round(preco - prev_close, 2) if prev_close > 0 else 0.0,
                    "fechamento_anterior": prev_close,
                },
            })
    finally:
        if own_init:
            mt5.shutdown()

    return resultados


# ------------------------------------------------------------
# BACEN PTAX
# ------------------------------------------------------------
def coletar_bacen_ptax() -> dict:
    timestamp = datetime.now().isoformat()
    url_sgs = (
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.10813/dados/ultimos/5?formato=json"
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url_sgs, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT_BACEN or 10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res:
                valor = float(res[-1]["valor"].replace(",", "."))
                return {
                    "ativo": "USD_PTAX",
                    "fonte": "BACEN_SGS_10813",
                    "timestamp": timestamp,
                    "status": "OK",
                    "dados_reais": {
                        "close": valor,
                        "open": None,
                        "high": None,
                        "low": None,
                        "change_percent": None,
                        "volume": None,
                    },
                }
    except Exception as e:
        print(f"[AVISO] Bacen SGS: {e}. Fallback TV...")

    try:
        payload = {"symbols": {"tickers": ["FX_IDC:USDBRL"]}, "columns": ["close"]}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://scanner.tradingview.com/global/scan",
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            vals = res.get("data", [])[0].get("d", [])
            if vals and vals[0] is not None:
                return {
                    "ativo": "USD_PTAX",
                    "fonte": "TRADINGVIEW_FALLBACK",
                    "timestamp": timestamp,
                    "status": "OK",
                    "dados_reais": {
                        "close": float(vals[0]),
                        "open": None,
                        "high": None,
                        "low": None,
                        "change_percent": None,
                        "volume": None,
                    },
                }
    except Exception:
        pass

    return {
        "ativo": "USD_PTAX",
        "fonte": "BACEN_API",
        "timestamp": timestamp,
        "status": "SEM_DADOS",
        "dados_reais": None,
    }


# ------------------------------------------------------------
# Ajuste + Fechamento oficial B3 — via brapi.dev (FONTE PRIMÁRIA)
# ------------------------------------------------------------
def _descobrir_contrato_win() -> str:
    """
    Lê o contrato principal do WIN no MT5 v2.2 e devolve o símbolo
    pronto pro brapi (ex: 'WINV26'). Fallback: WINV26.
    """
    if os.path.exists(FILE_MT5_V2):
        try:
            with open(FILE_MT5_V2, "r", encoding="utf-8") as f:
                mt5_json = json.load(f)
            contrato = (
                (mt5_json.get("ativos") or {}).get("WIN", {}).get("contrato_principal")
            )
            if contrato and str(contrato).upper().startswith("WIN"):
                return str(contrato).upper()
        except Exception:
            pass
    return "WINV26"


def _descobrir_contrato_wdo() -> str:
    """Idem ao WIN, mas pro WDO."""
    if os.path.exists(FILE_MT5_V2):
        try:
            with open(FILE_MT5_V2, "r", encoding="utf-8") as f:
                mt5_json = json.load(f)
            contrato = (
                (mt5_json.get("ativos") or {}).get("WDO", {}).get("contrato_principal")
            )
            if contrato and str(contrato).upper().startswith("WDO"):
                return str(contrato).upper()
        except Exception:
            pass
    return "WDOU26"


def coletar_ajuste_brapi() -> List[dict]:
    """
    Busca AJUSTE + FECHAMENTO oficiais via brapi.dev em uma única chamada.

    Retorna 4 itens por ciclo:
      - B3_AJUSTE_WIN      → settlement (ajuste oficial B3)
      - B3_AJUSTE_WDO      → settlement
      - B3_FECHAMENTO_WIN  → close (último negócio, auditoria + fallback)
      - B3_FECHAMENTO_WDO  → close

    IMPORTANTE: o TradingView WIN1! retorna 'close' (último negócio), não o
    ajuste oficial. A brapi expõe 'settlement' que É o ajuste publicado
    pela B3 (usado para acerto diário de posições).
    """
    timestamp = datetime.now().isoformat()
    saida: List[dict] = []

    contrato_win = _descobrir_contrato_win()
    contrato_wdo = _descobrir_contrato_wdo()

    try:
        url = (
            f"https://brapi.dev/api/v2/futures/quote?"
            f"symbols={contrato_win},{contrato_wdo}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"   ⚠️ brapi ajuste falhou: {e}")
        return []

    for item in dados.get("quotes", []) or []:
        symbol = str(item.get("symbol", "")).upper()
        settlement = item.get("settlement")
        close_val = item.get("close")

        if symbol.startswith("WIN"):
            prefixo = "WIN"
        elif symbol.startswith("WDO"):
            prefixo = "WDO"
        else:
            continue

        # ---- 1. Ajuste oficial (settlement) ----
        if settlement and float(settlement) > 0:
            saida.append({
                "ativo": f"B3_AJUSTE_{prefixo}",
                "fonte": "BRAPI_SETTLEMENT",
                "timestamp": timestamp,
                "status": "OK",
                "dados_reais": {
                    "close": float(settlement),          # AJUSTE OFICIAL
                    "open": item.get("open"),
                    "high": item.get("high"),
                    "low": item.get("low"),
                    "change_percent": item.get("oscillationPct"),
                    "volume": item.get("volume"),
                    "fechamento_real": close_val,        # informativo
                    "preco_medio": item.get("average"),  # informativo
                },
            })

        # ---- 2. Fechamento oficial (close) ----
        if close_val and float(close_val) > 0:
            saida.append({
                "ativo": f"B3_FECHAMENTO_{prefixo}",
                "fonte": "BRAPI_CLOSE",
                "timestamp": timestamp,
                "status": "OK",
                "dados_reais": {
                    "close": float(close_val),
                    "open": item.get("open"),
                    "high": item.get("high"),
                    "low": item.get("low"),
                    "change_percent": item.get("oscillationPct"),
                    "volume": item.get("volume"),
                    "preco_medio": item.get("average"),
                },
            })

    for it in saida:
        print(
            f"   ✅ {it['ativo']} via brapi: {it['dados_reais']['close']:.4f}"
        )

    return saida


# ------------------------------------------------------------
# Ajuste oficial (TV) — FALLBACK quando brapi falha
# ------------------------------------------------------------
def coletar_ajuste_oficial(silencioso: bool = False) -> List[dict]:
    """
    Fallback do ajuste (TradingView). ATENÇÃO: o TV retorna 'close'
    (último negócio), NÃO o ajuste oficial B3. Use apenas se a brapi falhar.

    Parâmetro `silencioso`: quando True, suprime os prints cosméticos
    ("Dentro da janela...", "Fora da janela..."). Usado quando chamada em
    paralelo com brapi (evita log ruidoso).
    """
    timestamp = datetime.now().isoformat()
    hora_atual = datetime.now().time()

    if JANELA_AJUSTE_FIM < hora_atual < JANELA_AJUSTE_INICIO:
        if not silencioso:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Fora da janela de ajuste. Cache...")
        for arquivo_cache in (FILE_RAM, FILE_ROM0):
            if not os.path.exists(arquivo_cache):
                continue
            try:
                with open(arquivo_cache, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                encontrados = [
                    item
                    for item in dados.get("coletas", [])
                    if item.get("ativo") in ("B3_AJUSTE_WIN", "B3_AJUSTE_WDO")
                ]
                if encontrados:
                    saida = []
                    for item in encontrados:
                        item = dict(item)
                        item["fonte"] = "CACHE_DISCO (Fora da janela)"
                        item["timestamp"] = timestamp
                        saida.append(item)
                    return saida
            except Exception:
                continue
        return [
            {
                "ativo": "B3_AJUSTE_WIN",
                "fonte": "NENHUM_DADO",
                "timestamp": timestamp,
                "status": "FORA_JANELA_SEM_CACHE",
                "dados_reais": None,
            },
            {
                "ativo": "B3_AJUSTE_WDO",
                "fonte": "NENHUM_DADO",
                "timestamp": timestamp,
                "status": "FORA_JANELA_SEM_CACHE",
                "dados_reais": None,
            },
        ]

    if not silencioso:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Dentro da janela. Coletando ajuste TV (FALLBACK)...")
    simbolos = [
        {"ativo": "B3_AJUSTE_WIN", "ticker": "BMFBOVESPA:WIN1!"},
        {"ativo": "B3_AJUSTE_WDO", "ticker": "BMFBOVESPA:WDO1!"},
    ]

    def _um(item: dict) -> dict:
        url = (
            f"https://scanner.tradingview.com/symbol?"
            f"symbol={item['ticker']}&fields=close,change"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_TRADINGVIEW or 10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                close_val = res.get("close")
                change_val = res.get("change", 0.0)
                return {
                    "ativo": item["ativo"],
                    "fonte": "TRADINGVIEW_DIRECT_SYMBOL",
                    "timestamp": timestamp,
                    "status": "OK" if close_val is not None else "ERRO",
                    "dados_reais": {
                        "close": float(close_val) if close_val is not None else None,
                        "open": None,
                        "high": None,
                        "low": None,
                        "change_percent": float(change_val) if change_val is not None else 0.0,
                        "volume": None,
                    },
                }
        except Exception as e:
            if not silencioso:
                print(f"   ❌ Ajuste {item['ativo']}: {e}")
            return {
                "ativo": item["ativo"],
                "fonte": "TRADINGVIEW_DIRECT_SYMBOL",
                "timestamp": timestamp,
                "status": "ERRO",
                "dados_reais": None,
            }

    with ThreadPoolExecutor(max_workers=2) as ex:
        return list(ex.map(_um, simbolos))


# ------------------------------------------------------------
# TradingView Scanner (batch)
# ------------------------------------------------------------
def coletar_tradingview() -> List[dict]:
    url = "https://scanner.tradingview.com/global/scan"
    timestamp = datetime.now().isoformat()
    payload = {
        "symbols": {"tickers": TICKERS_TRADINGVIEW},
        "columns": ["close", "open", "high", "low", "change", "volume"],
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_TRADINGVIEW or 10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            resultados = []
            for item in res.get("data", []):
                ticker = item.get("s")
                vals = item.get("d", [])
                ticker_chave = "SGX:FEF2!" if ticker == TICKER_FEF2 else ticker
                if len(vals) >= 5 and vals[0] is not None:
                    resultados.append({
                        "ativo": ticker_chave,
                        "fonte": "TRADINGVIEW_SCANNER",
                        "timestamp": timestamp,
                        "status": "OK",
                        "dados_reais": {
                            "close": float(vals[0]),
                            "open": float(vals[1]) if vals[1] is not None else None,
                            "high": float(vals[2]) if vals[2] is not None else None,
                            "low": float(vals[3]) if vals[3] is not None else None,
                            "change_percent": float(vals[4]) if vals[4] is not None else 0.0,
                            "volume": (
                                float(vals[5])
                                if len(vals) > 5 and vals[5] is not None
                                else None
                            ),
                        },
                    })
            return resultados
    except Exception as e:
        print(f"[ERRO] TradingView Scanner: {e}")
        return []


# ------------------------------------------------------------
# Rotação e unificado
# ------------------------------------------------------------
def executar_rotacao_memoria(is_ram_mode: bool = False) -> str:
    if is_ram_mode:
        return FILE_RAM

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] "
        f"Rotação de memória (12 slots)..."
    )
    for i in range(len(ARQUIVOS_ROM) - 1, 0, -1):
        origem = ARQUIVOS_ROM[i - 1]
        destino = ARQUIVOS_ROM[i]
        if os.path.exists(origem):
            try:
                os.replace(origem, destino)
            except OSError:
                shutil.copy2(origem, destino)
    return ARQUIVOS_ROM[0]


def gerar_arquivo_unificado(coletas: List[dict]) -> None:
    ativos_map: Dict[str, Any] = {}
    for item in coletas:
        ativo_raw = item.get("ativo")
        dados = item.get("dados_reais") or {}
        nome = MAPEAMENTO_TICKERS.get(ativo_raw, ativo_raw)
        ativos_map[nome] = {
            "preco": float(dados.get("close") or 0.0),
            "variacao_pct": float(dados.get("change_percent") or 0.0),
            "ticker_original": ativo_raw,
            "status": item.get("status", "OK"),
        }

    estrutura = {
        "metadata": {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_ativos": len(ativos_map),
        },
        "ativos": ativos_map,
    }
    with open(FILE_UNIFICADO, "w", encoding="utf-8") as f:
        json.dump(estrutura, f, ensure_ascii=False, separators=(",", ":"))
    print(f"✅ Unificado: {FILE_UNIFICADO}")


# ------------------------------------------------------------
# Montagem WIN_FUT / WIN_LAST_TICK a partir do MT5
# + arquivo fixo LastTick_Congelado.json (Fase 0)
# + fallback brapi quando MT5 falhar (Opção C)
# ------------------------------------------------------------
def _carregar_cache_coletas(*arquivos: str) -> list:
    """Lê itens de coletas dos arquivos de cache (ordem de prioridade)."""
    for arq in arquivos:
        if not os.path.exists(arq):
            continue
        try:
            with open(arq, "r", encoding="utf-8") as f:
                cache = json.load(f)
            itens = cache.get("coletas") or []
            if itens:
                return list(itens)
        except Exception as e:
            print(f"   ⚠️ Cache {os.path.basename(arq)}: {e}")
    return []


def _item_cache_por_ativo(itens: list, ativo: str) -> Optional[dict]:
    for item in itens:
        if item.get("ativo") == ativo:
            return dict(item)
    return None


def _carregar_last_tick_congelado() -> dict:
    """
    Lê Coletas/LastTick_Congelado.json.
    Retorno: {"WIN_LAST_TICK": {...item coleta...}, "WDO_LAST_TICK": {...}}
    """
    if not os.path.exists(FILE_LAST_TICK_CONGELADO):
        return {}
    try:
        with open(FILE_LAST_TICK_CONGELADO, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("ticks") or {}
    except Exception as e:
        print(f"   ⚠️ Leitura LastTick_Congelado: {e}")
        return {}


def _salvar_last_tick_congelado(ticks: Dict[str, dict]) -> None:
    """
    Persiste snapshot de LAST fora do pregão.
    ticks: {"WIN_LAST_TICK": item, "WDO_LAST_TICK": item}
    """
    if not ticks:
        return
    atual = _carregar_last_tick_congelado()
    atual.update(ticks)
    payload = {
        "timestamp_congelamento": datetime.now().isoformat(),
        "fonte": "MT5_v2.2",
        "ticks": atual,
    }
    try:
        with open(FILE_LAST_TICK_CONGELADO, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"   💾 LastTick_Congelado.json atualizado ({', '.join(ticks.keys())})")
    except Exception as e:
        print(f"   ⚠️ Falha ao gravar LastTick_Congelado: {e}")


def _montar_win_wdo_mt5(coletas: List[dict]) -> bool:
    """
    WIN_FUT / WDO_FUT:
        SEMPRE a partir do MT5 (candle/preço atual).

    WIN_LAST_TICK / WDO_LAST_TICK:
        - FORA do pregão → MT5 ao vivo + grava LastTick_Congelado.json
        - NO pregão     → lê arquivo fixo (fallback: RAM/ROM se arquivo ausente)

    FALLBACK (novo): se o MT5 não entregar 'last' para WIN/WDO, usa o
    fechamento oficial da brapi (B3_FECHAMENTO_WIN/WDO) antes de cair
    no cache congelado. Isso evita perder o ciclo quando o MT5 falha.

    Retorna True se montou pelo menos WIN_FUT fresco do MT5.
    """
    mt5_json: dict = {}
    if os.path.exists(FILE_MT5_V2):
        try:
            with open(FILE_MT5_V2, "r", encoding="utf-8") as f:
                mt5_json = json.load(f)
        except Exception as e:
            print(f"   ⚠️ Leitura MT5 v2.2: {e}")

    lasts = capturar_last_do_mt5()
    ativos_mt5 = (mt5_json.get("ativos") or {}) if isinstance(mt5_json, dict) else {}
    ts = datetime.now().isoformat()
    fora_pregao = esta_fora_do_pregao()
    montou_win_fut = False
    ticks_para_congelar: Dict[str, dict] = {}

    # ✅ Fallback brapi: coleta os fechamentos já presentes em `coletas`
    fech_brapi: Dict[str, float] = {}
    for item in coletas:
        ativo = item.get("ativo")
        if ativo in ("B3_FECHAMENTO_WIN", "B3_FECHAMENTO_WDO"):
            if item.get("status") == "OK":
                close_v = (item.get("dados_reais") or {}).get("close")
                if close_v and float(close_v) > 0:
                    fech_brapi[ativo] = float(close_v)

    freeze_map = _carregar_last_tick_congelado() if not fora_pregao else {}
    cache_itens: list = []
    if not fora_pregao and not freeze_map:
        cache_itens = _carregar_cache_coletas(FILE_RAM, FILE_ROM0)

    mapa = {
        "WIN": ("WIN_LAST_TICK", "BMFBOVESPA:WIN1!"),
        "WDO": ("WDO_LAST_TICK", "BMFBOVESPA:WDO1!"),
    }

    for prefixo, (ativo_last, ativo_fut) in mapa.items():
        info = ativos_mt5.get(prefixo) or {}
        last_val = (lasts.get(prefixo) or {}).get("last") or info.get("last")

        # ✅ Fallback brapi quando MT5 não tem last
        if last_val is None or float(last_val or 0) <= 0:
            brapi_close = fech_brapi.get(f"B3_FECHAMENTO_{prefixo}")
            if brapi_close and brapi_close > 0:
                print(
                    f"   🔄 {prefixo}: MT5 sem last — usando fechamento brapi "
                    f"{brapi_close:.0f}"
                )
                last_val = brapi_close

        # ---------- FUT: sempre MT5 (ou brapi fallback) ----------
        if last_val is not None and float(last_val or 0) > 0:
            last_val = float(last_val)
            last_real = last_val
            close_d1 = info.get("close")
            if close_d1 is not None and float(close_d1 or 0) > 0:
                last_real = float(close_d1)

            open_v = info.get("open")
            high_v = info.get("high")
            low_v = info.get("low")
            prev_c = info.get("prev_close") or info.get("session_close")
            var_pct = info.get("change_percent")
            vol_v = info.get("volume_d1") or info.get("volume")
            bid = info.get("bid")
            ask = info.get("ask")

            if var_pct is None and prev_c and float(prev_c or 0) > 0:
                var_pct = round(((last_val / float(prev_c)) - 1) * 100, 4)

            last_fut = last_val
            if (
                isinstance(bid, (int, float))
                and isinstance(ask, (int, float))
                and bid > 0
                and ask > 0
                and (last_fut < bid or last_fut > ask)
            ):
                mid = round((float(bid) + float(ask)) / 2.0, 1)
                print(
                    f"   ⚠️ {prefixo} last={last_fut} fora do spread "
                    f"[{bid},{ask}] → mid={mid} (apenas FUT)"
                )
                last_fut = mid

            ohlc_fut = {
                "close": last_fut,
                "open": float(open_v) if open_v is not None else None,
                "high": float(high_v) if high_v is not None else None,
                "low": float(low_v) if low_v is not None else None,
                "change_percent": var_pct,
                "volume": float(vol_v) if vol_v is not None else None,
                "fechamento_anterior": float(prev_c) if prev_c else None,
            }
            var_pct_real = var_pct
            if prev_c and float(prev_c or 0) > 0 and last_real > 0:
                var_pct_real = round(((last_real / float(prev_c)) - 1) * 100, 4)
            ohlc_last = {
                "close": last_real,
                "open": float(open_v) if open_v is not None else None,
                "high": float(high_v) if high_v is not None else None,
                "low": float(low_v) if low_v is not None else None,
                "change_percent": var_pct_real,
                "volume": float(vol_v) if vol_v is not None else None,
                "fechamento_anterior": float(prev_c) if prev_c else None,
            }
            contrato = (
                info.get("contrato_principal")
                or (lasts.get(prefixo) or {}).get("contrato")
            )

            coletas.append({
                "ativo": ativo_fut,
                "fonte": "MT5_v2.2",
                "timestamp": ts,
                "status": "OK",
                "dados_reais": dict(ohlc_fut),
            })
            print(
                f"   ✅ {prefixo}_FUT SEMPRE ({contrato}): last={last_fut} "
                f"OHLC=({ohlc_fut['open']}/{ohlc_fut['high']}/{ohlc_fut['low']}) var={var_pct}"
            )
            if prefixo == "WIN":
                montou_win_fut = True

            # ---------- LAST_TICK ----------
            if fora_pregao:
                item_last = {
                    "ativo": ativo_last,
                    "fonte": "MT5_v2.2",
                    "timestamp": ts,
                    "status": "OK",
                    "dados_reais": dict(ohlc_last),
                }
                coletas.append(item_last)
                ticks_para_congelar[ativo_last] = item_last
                print(
                    f"   ✅ {ativo_last} MT5 real close={last_real} "
                    f"(sem mid; fora do pregão)"
                )
            else:
                frozen = freeze_map.get(ativo_last)
                if frozen and (frozen.get("dados_reais") or {}).get("close"):
                    item = dict(frozen)
                    item["fonte"] = "LAST_TICK_CONGELADO (arquivo fixo)"
                    item["timestamp"] = ts
                    item["status"] = item.get("status") or "OK"
                    coletas.append(item)
                    preco = (item.get("dados_reais") or {}).get("close")
                    print(f"   🧊 {ativo_last} CONGELADO (arquivo) close={preco}")
                else:
                    cached = _item_cache_por_ativo(cache_itens, ativo_last)
                    if cached and (cached.get("dados_reais") or {}).get("close"):
                        cached = dict(cached)
                        cached["fonte"] = "CACHE_DISCO_CONGELADO (pregão; fallback)"
                        cached["timestamp"] = ts
                        coletas.append(cached)
                        preco = (cached.get("dados_reais") or {}).get("close")
                        print(f"   🧊 {ativo_last} CONGELADO (cache fallback) close={preco}")
                    else:
                        print(
                            f"   ⚠️ {ativo_last}: sem arquivo fixo nem cache — "
                            f"chave ausente neste ciclo"
                        )
        else:
            print(f"   ⚠️ {prefixo}: sem last MT5 nem brapi para FUT")
            if not fora_pregao:
                frozen = freeze_map.get(ativo_last)
                if frozen:
                    item = dict(frozen)
                    item["fonte"] = "LAST_TICK_CONGELADO (arquivo; sem FUT MT5)"
                    item["timestamp"] = ts
                    coletas.append(item)
                    print(f"   🧊 {ativo_last} CONGELADO (só arquivo)")
                else:
                    cached = _item_cache_por_ativo(cache_itens, ativo_last)
                    if cached:
                        cached = dict(cached)
                        cached["fonte"] = "CACHE_DISCO_CONGELADO (pregão; sem FUT)"
                        cached["timestamp"] = ts
                        coletas.append(cached)
                        print(f"   🧊 {ativo_last} CONGELADO (só cache)")

    if fora_pregao and ticks_para_congelar:
        _salvar_last_tick_congelado(ticks_para_congelar)

    return montou_win_fut


def _reutilizar_cache_last_fut(coletas: List[dict]) -> None:
    """Fallback fora do pregão se MT5 falhar totalmente."""
    freeze = _carregar_last_tick_congelado()
    added = False
    for ativo in ("WIN_LAST_TICK", "WDO_LAST_TICK"):
        item = freeze.get(ativo)
        if item:
            item = dict(item)
            item["fonte"] = f"LAST_TICK_CONGELADO (MT5 offline)"
            item["timestamp"] = datetime.now().isoformat()
            coletas.append(item)
            added = True
    if added:
        print("   ✅ LAST do arquivo fixo (MT5 offline)")
        return

    itens = _carregar_cache_coletas(FILE_RAM, FILE_ROM0)
    if not itens:
        return
    for ativo in (
        "WIN_LAST_TICK",
        "WDO_LAST_TICK",
        "BMFBOVESPA:WIN1!",
        "BMFBOVESPA:WDO1!",
    ):
        item = _item_cache_por_ativo(itens, ativo)
        if item:
            item["fonte"] = f"CACHE_DISCO ({item.get('fonte', 'N/A')})"
            item["timestamp"] = datetime.now().isoformat()
            coletas.append(item)
            added = True
    if added:
        print("   ✅ Cache LAST/FUT reutilizado (MT5 offline)")


# ------------------------------------------------------------
# Pipeline principal
# ------------------------------------------------------------
def executar_pipeline_coleta() -> None:
    t0 = datetime.now()
    is_ram = "--ram" in sys.argv
    arquivo_destino = executar_rotacao_memoria(is_ram)

    print(f"[{t0.strftime('%H:%M:%S')}] Iniciando coleta paralela...")

    coletas: List[dict] = []

    # --- Fontes HTTP independentes em paralelo (com brapi) ---
    # TV fallback roda em modo SILENCIOSO — só aparece se brapi falhar.
    with ThreadPoolExecutor(max_workers=5) as ex:
        fut_ptax = ex.submit(coletar_bacen_ptax)
        fut_ajuste_brapi = ex.submit(coletar_ajuste_brapi)         # PRIMÁRIO
        fut_ajuste_tv = ex.submit(coletar_ajuste_oficial, True)    # FALLBACK (silencioso)
        fut_tv = ex.submit(coletar_tradingview)
        fut_fh = ex.submit(coletar_finnhub)

        ptax = fut_ptax.result()
        ajustes_brapi = fut_ajuste_brapi.result()
        ajustes_tv = fut_ajuste_tv.result()
        tv_dados = fut_tv.result()
        finnhub_dados = fut_fh.result()

    # ---- Ajuste oficial: brapi primeiro, TV como fallback ----
    if ajustes_brapi:
        coletas.extend(ajustes_brapi)
        n_ajustes = sum(1 for x in ajustes_brapi if x["ativo"].startswith("B3_AJUSTE"))
        n_fech = sum(1 for x in ajustes_brapi if x["ativo"].startswith("B3_FECHAMENTO"))
        print(
            f"   ✅ brapi OK — {n_ajustes} ajustes + {n_fech} fechamentos"
        )
    else:
        # brapi falhou — aí sim imprime o retorno do TV (fallback real)
        print(f"   ⚠️ brapi indisponível — usando TV fallback ({len(ajustes_tv)} itens)")
        # Re-executa TV em modo verboso pra dar visibilidade
        ajustes_tv_verbose = coletar_ajuste_oficial(silencioso=False)
        coletas.extend(ajustes_tv_verbose or ajustes_tv)

    coletas.append(ptax)
    coletas.extend(tv_dados)
    coletas.extend(finnhub_dados)

    ok_fh = sum(1 for d in finnhub_dados if d.get("status") == "OK")
    print(
        f"   ✅ Finnhub: {ok_fh} OK | TV: {len(tv_dados)}"
    )

    # --- MT5: sempre coleta v2.2 (WIN_FUT precisa estar fresco) ---
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando MT5 (WIN_FUT sempre)...")
    mt5_ok = False
    try:
        from Coletor_MT5_v2_2 import executar_coleta_mt5_v2

        dados_mt5 = executar_coleta_mt5_v2()
        if (dados_mt5 or {}).get("status") == "OK":
            mt5_ok = True
            print("   ✅ MT5 v2.2 OK")
        else:
            print(f"   ⚠️ MT5 v2.2 status={(dados_mt5 or {}).get('status')!r}")
    except Exception as e:
        print(f"   ⚠️ MT5 v2.2: {e}")

    # Ações B3
    mt5_b3 = coletar_mt5_acoes_b3()
    coletas.extend(mt5_b3)
    print(
        f"   ✅ MT5 B3: "
        f"{sum(1 for d in mt5_b3 if d.get('status') == 'OK')} OK"
    )

    # Monta WIN_FUT (sempre) + WIN_LAST_TICK (vivo fora / congelado no pregão)
    montou = _montar_win_wdo_mt5(coletas)

    if not montou and not mt5_ok and esta_fora_do_pregao():
        print("   ⚠️ MT5 falhou fora do pregão — tentando cache LAST/FUT")
        _reutilizar_cache_last_fut(coletas)

    # Persistência (JSON compacto)
    conteudo = {
        "metadata_coleta": {
            "timestamp_coleta": datetime.now().isoformat(),
            "modo_execucao": "RAM" if is_ram else "PADRAO_ROTATIVO",
            "total_ativos_solicitados": len(coletas),
            "arquivo_gerado": os.path.basename(arquivo_destino),
            "latencia_ms": int((datetime.now() - t0).total_seconds() * 1000),
            "fora_do_pregao": esta_fora_do_pregao(),
        },
        "coletas": coletas,
    }

    with open(arquivo_destino, "w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False, separators=(",", ":"))

    if not is_ram:
        with open(FILE_RAM, "w", encoding="utf-8") as f:
            json.dump(conteudo, f, ensure_ascii=False, separators=(",", ":"))
        print(f"✅ RAM: {FILE_RAM}")

    gerar_arquivo_unificado(coletas)

    elapsed = (datetime.now() - t0).total_seconds()
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Coleta OK | "
        f"{len(coletas)} itens | {elapsed:.2f}s | "
        f"{'FORA' if esta_fora_do_pregao() else 'DENTRO'} do pregão"
    )


if __name__ == "__main__":
    print("=" * 60)
    print(" COLETOR — WIN_FUT sempre | LAST arquivo fixo (Fase 0)")
    print("        + Ajuste e Fechamento oficiais via brapi.dev")
    print("=" * 60)
    executar_pipeline_coleta()
```

### `Coletor_MT5_v2_2.py`

```python
# ================================================================
# COLETOR MT5 v2.2
# Mercado B3 - WINFUT / WDO / DI1
#
# NÃO ALTERA OS COLETORES ANTERIORES
# ================================================================

import MetaTrader5 as mt5
import json
import os
from datetime import datetime


# ================================================================
# CONFIGURAÇÃO
# ================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
HISTORICO_DIR = os.path.join(COLETAS_DIR, "Historico_MT5")

ARQUIVO_ATUAL = os.path.join(
    COLETAS_DIR,
    "Dados_MT5_v2_2.json"
)

os.makedirs(COLETAS_DIR, exist_ok=True)
os.makedirs(HISTORICO_DIR, exist_ok=True)


# ================================================================
# ATIVOS
# ================================================================

ATIVOS = {
    "WIN": {
        "prefixo": "WIN",
        "descricao": "Mini Índice B3",
        # "expiracao" = front-month (menor vencimento futuro) — correto p/ WIN/WDO
        # "volume"    = maior liquidez do dia — correto p/ DI1
        "criterio": "expiracao"
    },

    "WDO": {
        "prefixo": "WDO",
        "descricao": "Mini Dólar B3",
        "criterio": "expiracao"
    },

    "DI1": {
        "prefixo": "DI1",
        "descricao": "DI Futuro B3",
        "criterio": "volume"
    }
}


# ================================================================
# CONEXÃO MT5
# ================================================================

def conectar_mt5():

    print()
    print("=" * 70)
    print("🚀 INICIANDO COLETOR MT5 v2.2")
    print("=" * 70)

    if not mt5.initialize():
        print()
        print("❌ FALHA AO INICIALIZAR MT5")
        print("Erro:", mt5.last_error())
        return False

    # Confirma se o terminal está de fato ligado à corretora
    terminal = mt5.terminal_info()
    conta = mt5.account_info()
    versao = mt5.version()

    conectado = bool(terminal and getattr(terminal, "connected", False))
    empresa = getattr(terminal, "company", None) if terminal else None

    print()
    print("🔌 MT5")
    print(f"   Versão: {versao}")
    print(f"   Empresa: {empresa}")
    print(f"   Conectado à corretora: {conectado}")
    if conta:
        print(f"   Conta: {getattr(conta, 'login', '?')}")

    if not conectado:
        print()
        print("⚠️ MT5 abriu, mas NÃO está conectado à corretora.")
        print("   Abra o terminal, faça login e tente de novo.")
        print("   Pipeline seguirá com cache, se houver.")
        try:
            mt5.shutdown()
        except Exception:
            pass
        return False

    return True


# ================================================================
# DATA/HORA
# ================================================================

def agora():

    return datetime.now().isoformat(timespec="milliseconds")


# ================================================================
# IDENTIFICAÇÃO DO CONTRATO
# ================================================================

def obter_contratos(prefixo):

    """
    Procura somente contratos reais do ativo (rápido).

    Estratégia (evita symbols_get() de toda a corretora, que trava no Windows):
      1) symbols_get(group="PREFIX*") se o broker suportar
      2) Candidatos por código de mês B3 (ex: WINV26, WDOU26, DI1F27)
      3) Fallback: varrer symbols_get() completo só se 1 e 2 falharem
    """

    terminal = mt5.terminal_info()
    if terminal is None or not getattr(terminal, "connected", False):
        print(f"   ⚠️ obter_contratos({prefixo}): MT5 sem conexão — abortando busca.")
        return []

    def _eh_contrato_valido(nome: str) -> bool:
        if not nome.startswith(prefixo):
            return False
        if "$" in nome or "@" in nome:
            return False
        # opções: C/P após o prefixo (heurística)
        resto = nome[len(prefixo):]
        if "C" in resto or "P" in resto:
            # DI1 e WIN usam letras de mês; letras de opção costumam vir no meio
            # Mantém filtro leve: se terminar com C/P + dígitos de strike, ignora
            if any(ch.isdigit() for ch in resto) and (resto.endswith("C") or resto.endswith("P")):
                return False
        return True

    def _monta_info(s) -> dict:
        nome = s.name
        data_expiracao = getattr(s, "expiration_time", 0) or 0
        if data_expiracao:
            try:
                data_expiracao = datetime.fromtimestamp(data_expiracao)
            except Exception:
                data_expiracao = None
        else:
            data_expiracao = None

        tick = mt5.symbol_info_tick(nome)
        if tick:
            volume = float(getattr(tick, "volume", 0) or 0)
            bid = float(getattr(tick, "bid", 0) or 0)
            ask = float(getattr(tick, "ask", 0) or 0)
            last = float(getattr(tick, "last", 0) or 0)
        else:
            volume = bid = ask = last = 0.0

        return {
            "nome": nome,
            "simbolo": s,
            "expiracao": data_expiracao,
            "volume": volume,
            "bid": bid,
            "ask": ask,
            "last": last,
        }

    contratos = []
    vistos = set()

    # ---- 1) Filtro por grupo (rápido) ----
    for group in (f"{prefixo}*", f"*{prefixo}*"):
        try:
            simbolos = mt5.symbols_get(group=group)
        except Exception:
            simbolos = None
        if not simbolos:
            continue
        print(f"   🔎 {prefixo}: {len(simbolos)} símbolos via group='{group}'")
        for s in simbolos:
            nome = s.name
            if nome in vistos or not _eh_contrato_valido(nome):
                continue
            vistos.add(nome)
            mt5.symbol_select(nome, True)
            contratos.append(_monta_info(s))
        if contratos:
            return contratos

    # ---- 2) Candidatos explícitos (mês B3 + ano) ----
    # Códigos de mês B3: F G H J K M N Q U V X Z
    meses = list("FGHJKMNQUVXZ")
    agora_dt = datetime.now()
    anos = [agora_dt.year % 100, (agora_dt.year + 1) % 100]
    candidatos = []
    for aa in anos:
        for m in meses:
            candidatos.append(f"{prefixo}{m}{aa:02d}")
    # Contínuos / genéricos comuns na Genial
    if prefixo == "WIN":
        candidatos.extend(["WIN$", "WINV26", "WINZ26"])
    elif prefixo == "WDO":
        candidatos.extend(["WDO$", "WDOU26", "WDOV26"])
    elif prefixo == "DI1":
        candidatos.extend(["DI1F27", "DI1F28", "DI1F29"])

    print(f"   🔎 {prefixo}: testando {len(candidatos)} candidatos diretos...")
    for nome in candidatos:
        if nome in vistos:
            continue
        info_s = mt5.symbol_info(nome)
        if info_s is None:
            continue
        if not _eh_contrato_valido(nome):
            continue
        vistos.add(nome)
        mt5.symbol_select(nome, True)
        contratos.append(_monta_info(info_s))

    if contratos:
        print(f"   ✅ {prefixo}: {len(contratos)} contratos via candidatos")
        return contratos

    # ---- 3) Fallback completo (pode ser lento) ----
    print(f"   ⏳ {prefixo}: fallback symbols_get() completo (pode demorar)...")
    simbolos = mt5.symbols_get()
    if simbolos is None:
        print(f"   ⚠️ symbols_get() retornou None (prefixo={prefixo})")
        return []

    for s in simbolos:
        nome = s.name
        if nome in vistos or not _eh_contrato_valido(nome):
            continue
        vistos.add(nome)
        mt5.symbol_select(nome, True)
        contratos.append(_monta_info(s))

    print(f"   ✅ {prefixo}: {len(contratos)} contratos via varredura completa")
    return contratos


def selecionar_contrato(prefixo, criterio="expiracao"):

    contratos = obter_contratos(prefixo)

    agora_dt = datetime.now()

    validos = []

    for c in contratos:

        expiracao = c["expiracao"]

        # --------------------------------------------------------
        # Sem data de vencimento
        # --------------------------------------------------------

        if expiracao is None:
            continue

        # --------------------------------------------------------
        # Contrato vencido
        # --------------------------------------------------------

        if expiracao <= agora_dt:
            continue

        # --------------------------------------------------------
        # Não considerar contratos sem mercado
        # --------------------------------------------------------

        if (
            c["bid"] <= 0
            and c["ask"] <= 0
            and c["last"] <= 0
        ):
            continue

        validos.append(c)

    # ------------------------------------------------------------
    # Ordenação
    #
    # Primeiro:
    #   contrato vigente
    #
    # Depois:
    #   maior volume
    #
    # ------------------------------------------------------------

    # Criterio por ativo:
    #   WIN/WDO → front-month (menor expiracao futura), volume desempata.
    #   DI1     → maior volume (liquidez nao esta no vencimento mais
    #             proximo; pula p/ jan. do ano seguinte).
    if criterio == "volume":
        validos.sort(
            key=lambda x: (
                -x["volume"],
                x["expiracao"].timestamp(),
            )
        )
    else:
        validos.sort(
            key=lambda x: (
                x["expiracao"].timestamp(),
                -x["volume"],
            )
        )

    if not validos:

        return None, []

    principal = validos[0]

    return principal, validos


# ================================================================
# PREÇO TEÓRICO
# ================================================================

def obter_preco_teorico(nome):

    info = mt5.symbol_info(nome)

    if info is None:
        return None

    try:

        valor = getattr(
            info,
            "price_theoretical",
            None
        )

        if valor is None:
            return None

        valor = float(valor)

        if valor <= 0:
            return None

        return valor

    except Exception:

        return None


# ================================================================
# MARKET BOOK
# ================================================================

def obter_book(nome):

    resultado = {
        "disponivel": False,
        "quantidade_niveis": 0,
        "bids": [],
        "asks": []
    }

    try:

        # --------------------------------------------------------
        # Assina Market Book
        # --------------------------------------------------------

        if not mt5.market_book_add(nome):

            return resultado

        # --------------------------------------------------------
        # Obtém Book
        # --------------------------------------------------------

        book = mt5.market_book_get(nome)

        if not book:

            mt5.market_book_release(nome)

            return resultado

        resultado["disponivel"] = True

        for nivel in book:

            tipo = getattr(
                nivel,
                "type",
                None
            )

            preco = float(
                getattr(
                    nivel,
                    "price",
                    0
                ) or 0
            )

            volume = float(
                getattr(
                    nivel,
                    "volume",
                    0
                ) or 0
            )

            item = {
                "preco": preco,
                "volume": volume
            }

            # ----------------------------------------------------
            # Tipos do Market Book
            # ----------------------------------------------------

            if tipo == mt5.BOOK_TYPE_BUY:

                resultado["bids"].append(item)

            elif tipo == mt5.BOOK_TYPE_SELL:

                resultado["asks"].append(item)

        resultado["quantidade_niveis"] = len(book)

        mt5.market_book_release(nome)

    except Exception:

        try:
            mt5.market_book_release(nome)
        except Exception:
            pass

    return resultado


# ================================================================
# COLETA DE UM ATIVO
# ================================================================

def coletar_ativo(nome_ativo, configuracao):

    prefixo = configuracao["prefixo"]

    criterio = configuracao.get("criterio", "expiracao")
    principal, contratos = selecionar_contrato(prefixo, criterio=criterio)

    if principal is None:

        print()
        print(f"📌 {nome_ativo}")
        print("   ❌ Nenhum contrato vigente encontrado")

        return {
            "ativo": nome_ativo,
            "status": "sem_contrato"
        }

    nome = principal["nome"]

    # ------------------------------------------------------------
    # Garantir símbolo selecionado
    # ------------------------------------------------------------

    mt5.symbol_select(nome, True)

    tick = mt5.symbol_info_tick(nome)

    if tick is None:

        print()
        print(f"📌 {nome_ativo}")
        print(f"   Contrato: {nome}")
        print("   ❌ Não foi possível obter tick")

        return {
            "ativo": nome_ativo,
            "status": "sem_tick",
            "contrato": nome
        }

    # ------------------------------------------------------------
    # Preços
    # ------------------------------------------------------------

    bid = float(
        getattr(tick, "bid", 0) or 0
    )

    ask = float(
        getattr(tick, "ask", 0) or 0
    )

    last = float(
        getattr(tick, "last", 0) or 0
    )

    volume = float(
        getattr(tick, "volume", 0) or 0
    )

    spread = None

    if bid > 0 and ask > 0:

        spread = ask - bid

    # ------------------------------------------------------------
    # OHLC D1 + fechamento anterior (para pivots / WIN_FUT / WDO_FUT)
    # ------------------------------------------------------------

    open_d1 = None
    high_d1 = None
    low_d1 = None
    close_d1 = None
    volume_d1 = None
    prev_close = None
    change_percent = None

    try:
        info = mt5.symbol_info(nome)
        if info is not None:
            prev_close = float(getattr(info, "session_close", 0) or 0) or None

        # copy_rates_from_pos: array ordenado do mais ANTIGO → mais RECENTE
        # rates[-1] = barra atual (hoje) | rates[-2] = dia anterior
        rates = mt5.copy_rates_from_pos(nome, mt5.TIMEFRAME_D1, 0, 3)
        if rates is not None and len(rates) > 0:
            r_atual = rates[-1]
            try:
                open_d1 = float(r_atual["open"])
                high_d1 = float(r_atual["high"])
                low_d1 = float(r_atual["low"])
                close_d1 = float(r_atual["close"])
                volume_d1 = (
                    float(r_atual["tick_volume"])
                    if "tick_volume" in r_atual.dtype.names
                    else None
                )
            except Exception:
                open_d1 = float(r_atual[1])
                high_d1 = float(r_atual[2])
                low_d1 = float(r_atual[3])
                close_d1 = float(r_atual[4])
                volume_d1 = float(r_atual[5]) if len(r_atual) > 5 else None

            # Fechamento anterior: session_close ou close da barra D1 anterior
            if (prev_close is None or prev_close <= 0) and len(rates) >= 2:
                r_ant = rates[-2]
                try:
                    prev_close = float(r_ant["close"])
                except Exception:
                    prev_close = float(r_ant[4])

        preco_ref = last if last > 0 else (close_d1 or 0)
        if prev_close and prev_close > 0 and preco_ref > 0:
            change_percent = round(((preco_ref / prev_close) - 1) * 100, 4)
    except Exception as e:
        print(f"   ⚠️ OHLC D1 ({nome}): {e}")

    # ------------------------------------------------------------
    # Preço teórico
    # ------------------------------------------------------------

    teorico = obter_preco_teorico(nome)

    # ------------------------------------------------------------
    # Book
    # ------------------------------------------------------------

    book = obter_book(nome)

    # ------------------------------------------------------------
    # Contratos vigentes
    # ------------------------------------------------------------

    contratos_saida = []

    for c in contratos:

        contratos_saida.append({
            "contrato": c["nome"],
            "expiracao": (
                c["expiracao"].isoformat()
                if c["expiracao"]
                else None
            ),
            "volume": c["volume"],
            "bid": c["bid"],
            "ask": c["ask"],
            "last": c["last"]
        })

    # ------------------------------------------------------------
    # Resultado
    # ------------------------------------------------------------

    dados = {

        "ativo": nome_ativo,

        "descricao": configuracao["descricao"],

        "contrato_principal": nome,

        "timestamp": agora(),

        "bid": bid,

        "ask": ask,

        "last": last,

        "volume": volume,

        "spread": spread,

        # OHLC diário (pivots / WIN_FUT / WDO_FUT)
        "open": open_d1,
        "high": high_d1,
        "low": low_d1,
        "close": close_d1 if close_d1 else (last if last > 0 else None),
        "volume_d1": volume_d1,
        "prev_close": prev_close,
        "change_percent": change_percent,
        "session_close": prev_close,

        "preco_teorico": teorico,

        "vencimento": (
            principal["expiracao"].isoformat()
            if principal["expiracao"]
            else None
        ),

        "market_book": book,

        "contratos_vigentes": contratos_saida,

        "status": "OK"
    }

    # ------------------------------------------------------------
    # Console
    # ------------------------------------------------------------

    print()
    print(f"📌 {nome_ativo}")
    print(f"   Contrato principal: {nome}")

    print()
    print("   Contratos vigentes:")

    for c in contratos_saida:

        print(
            f"      • {c['contrato']} | "
            f"Volume: {c['volume']}"
        )

    print()
    print(f"   Bid:    {bid}")
    print(f"   Ask:    {ask}")
    print(f"   Last:   {last}")
    print(f"   Volume: {volume}")
    print(f"   Spread: {spread}")
    if high_d1 is not None:
        print(f"   D1 O/H/L/C: {open_d1} / {high_d1} / {low_d1} / {close_d1}")
    if prev_close:
        print(f"   Prev close: {prev_close} | var: {change_percent}%")

    if teorico is not None:

        print(
            f"   Preço teórico: {teorico}"
        )

    else:

        print(
            "   Preço teórico: "
            "⚠️ indisponível"
        )

    # ------------------------------------------------------------
    # Book
    # ------------------------------------------------------------

    if book["disponivel"]:

        print(
            "   Market Book: "
            f"✅ {book['quantidade_niveis']} níveis"
        )

    else:

        print(
            "   Market Book: "
            "⚠️ indisponível/vazio"
        )

    return dados


# ================================================================
# SALVAR JSON
# ================================================================

def salvar_json(dados):

    # ------------------------------------------------------------
    # Arquivo atual
    # ------------------------------------------------------------

    with open(
        ARQUIVO_ATUAL,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

    # ------------------------------------------------------------
    # Histórico
    # ------------------------------------------------------------

    agora_dt = datetime.now()

    nome_historico = (
        f"MT5_v2_2_"
        f"{agora_dt.strftime('%Y%m%d_%H%M%S_%f')}.json"
    )

    arquivo_historico = os.path.join(
        HISTORICO_DIR,
        nome_historico
    )

    with open(
        arquivo_historico,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

    return arquivo_historico


# ================================================================
# FUNÇÃO PARA INTEGRAÇÃO COM O PIPELINE (Coletor.py)
# ================================================================

def executar_coleta_mt5_v2():
    """
    Função principal para ser chamada pelo Coletor.py / pipeline.
    Retorna o dicionário completo dos dados coletados ou None em caso de falha.
    Também grava Dados_MT5_v2_2.json e o histórico.
    Nunca deve travar o pipeline: se MT5 estiver offline, retorna None cedo.
    """
    if not conectar_mt5():
        return {
            "versao_coletor": "2.2",
            "timestamp": agora(),
            "mt5": {"conectado": False},
            "ativos": {},
            "status": "OFFLINE",
        }

    try:
        timestamp = agora()

        print()
        print("=" * 70)
        print("📊 COLETOR MT5 v2.2 (integração pipeline)")
        print("=" * 70)
        print(f"🕒 Coleta: {timestamp}")

        dados = {
            "versao_coletor": "2.2",
            "timestamp": timestamp,
            "mt5": {
                "conectado": True,
                "versao": mt5.version()
            },
            "ativos": {},
            "status": "OK"
        }

        for nome_ativo, configuracao in ATIVOS.items():
            print(f"\n➡️  Coletando {nome_ativo} ({configuracao['descricao']})...")
            dados["ativos"][nome_ativo] = coletar_ativo(
                nome_ativo,
                configuracao
            )

        print()
        print("=" * 70)

        arquivo_historico = salvar_json(dados)

        print()
        print("💾 Arquivo atual:")
        print(f"   {ARQUIVO_ATUAL}")
        print()
        print("📚 Histórico:")
        print(f"   {arquivo_historico}")

        return dados

    except Exception as erro:
        print()
        print("❌ ERRO DURANTE A COLETA v2.2")
        print(f"   {erro}")
        return None

    finally:
        mt5.shutdown()
        print()
        print("🔌 MT5 desconectado.")
        print()


# ================================================================
# MAIN (execução direta)
# ================================================================

def main():
    executar_coleta_mt5_v2()


# ================================================================
# EXECUÇÃO
# ================================================================

if __name__ == "__main__":
    main()




```

### `Gerar_Mapa_Fluxo.py`

```python
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
```

### `Gerar_Mapa_Inventario_Tecnico.py`

```python
# ============================================================
# GERADOR DE ARQUIVOS DO PROJETO - V2.1
#
# Projeto:
# Analisador_Financeiro
#
# Objetivo:
# Criar mapa estrutural do projeto para análise humana/IA
#
# Data alteração:
# 2026-07-31
#
# NÃO EDITAR O ARQUIVO GERADO MANUALMENTE
# ============================================================


import os
import datetime


# ============================================================
# CONFIGURAÇÃO
# ============================================================

PASTA_PROJETO = r"E:\ProjetosPython\Analisador_Financeiro"

PASTA_SAIDA = os.path.join(
    PASTA_PROJETO,
    "Coletas"
)

ARQUIVO_SAIDA = os.path.join(
    PASTA_SAIDA,
    "ArquivosApp.py"
)


# Pastas antigas/backups

PASTAS_IGNORAR = {

    "__pycache__",
    ".git",
    "1",
    "2",
    "1_Olds"

}


# Arquivos que não entram no mapa

ARQUIVOS_IGNORAR = {

    "Gerar_ArquivosApp.py",
    "ArquivosApp.py"

}



# ============================================================
# CLASSIFICAR ARQUIVO
# ============================================================

def classificar_categoria(caminho):

    caminho = caminho.lower()


    if "coletas" in caminho:
        return "DADOS"


    if "relatorios" in caminho:
        return "RELATORIOS"


    if "pages" in caminho:
        return "INTERFACE"


    if "teste" in caminho:
        return "TESTE"


    return "CORE"



# ============================================================
# TAMANHO
# ============================================================

def tamanho_kb(caminho):

    try:

        return round(
            os.path.getsize(caminho) / 1024,
            2
        )

    except:

        return 0



# ============================================================
# DATA ALTERAÇÃO
# ============================================================

def data_alteracao(caminho):

    try:

        data = datetime.datetime.fromtimestamp(
            os.path.getmtime(caminho)
        )

        return data.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    except:

        return ""



# ============================================================
# COLETAR ARQUIVOS
# ============================================================

def coletar_arquivos():

    lista = []


    for raiz, pastas, arquivos in os.walk(
        PASTA_PROJETO
    ):


        pastas[:] = [

            p for p in pastas

            if p not in PASTAS_IGNORAR

        ]


        for arquivo in arquivos:


            if arquivo in ARQUIVOS_IGNORAR:
                continue



            caminho = os.path.join(
                raiz,
                arquivo
            )


            relativo = os.path.relpath(
                caminho,
                PASTA_PROJETO
            )


            extensao = os.path.splitext(
                arquivo
            )[1]


            tipo = extensao.replace(
                ".",
                ""
            ).upper()



            lista.append({

                "arquivo": arquivo,

                "categoria":
                    classificar_categoria(
                        relativo
                    ),

                "local":
                    relativo,

                "tipo":
                    tipo,

                "tamanho_kb":
                    tamanho_kb(
                        caminho
                    ),

                "ultima_alteracao":
                    data_alteracao(
                        caminho
                    )

            })


    return sorted(
        lista,
        key=lambda x:x["local"]
    )



# ============================================================
# RESUMO
# ============================================================

def gerar_resumo(lista):

    resumo = {}


    for item in lista:

        tipo = item["tipo"]

        resumo[tipo] = resumo.get(
            tipo,
            0
        ) + 1


    return resumo



# ============================================================
# GERAR ARQUIVO
# ============================================================

def gerar():

    arquivos = coletar_arquivos()

    resumo = gerar_resumo(
        arquivos
    )


    data = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    with open(
        ARQUIVO_SAIDA,
        "w",
        encoding="utf-8"
    ) as f:


        f.write(
f"""# ============================================================
# MAPA DO PROJETO - ANALISADOR FINANCEIRO
#
# GERADO AUTOMATICAMENTE
#
# Data geração:
# {data}
#
# Arquivos catalogados:
# {len(arquivos)}
#
# NÃO EDITAR MANUALMENTE
# ============================================================


ARQUIVOS_PROJETO = [
"""
        )


        for item in arquivos:

            f.write(
                repr(item)
            )

            f.write(
                ",\n"
            )


        f.write(
"""
]


RESUMO_PROJETO = """
        )


        f.write(
            repr(resumo)
        )


        f.write(
"""


def listar_arquivos():

    for item in ARQUIVOS_PROJETO:

        print("="*60)

        print("Arquivo:", item["arquivo"])

        print("Categoria:", item["categoria"])

        print("Local:", item["local"])

        print("Tipo:", item["tipo"])

        print("Tamanho KB:", item["tamanho_kb"])

        print(
            "Última alteração:",
            item["ultima_alteracao"]
        )



def listar_resumo():

    print("="*60)

    print(
        "RESUMO PROJETO ANALISADOR FINANCEIRO"
    )

    print("="*60)

    print(
        "Total arquivos:",
        len(ARQUIVOS_PROJETO)
    )


    print()


    for tipo,qtd in RESUMO_PROJETO.items():

        print(
            tipo,
            ":",
            qtd
        )



if __name__ == "__main__":

    listar_resumo()

"""
        )



    print()

    print("="*60)

    print(
        " GERADOR DE ARQUIVOS DO PROJETO V2.1"
    )

    print("="*60)

    print()

    print(
        "Arquivos encontrados:",
        len(arquivos)
    )

    print()

    print(
        "Catálogo gerado:"
    )

    print(
        ARQUIVO_SAIDA
    )

    print("="*60)



# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    gerar()
```

### `Gerar_Mapa_Projeto.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: Gerar_Mapa_Projeto.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Classificar os arquivos do inventário técnico e gerar o Mapa_Projeto.json.
"""

import json
import os
from datetime import datetime
from config import COLETAS_DIR

# Definição segura do arquivo de saída baseado no config
FILE_MAPA_PROJETO = COLETAS_DIR / "Mapa_Projeto.json"

def classificar_arquivo(nome_arquivo: str, local_relativo: str) -> str:
    """
    Classifica os módulos do projeto em categorias lógicas baseadas 
    na nomenclatura e na estrutura de pastas da V1 e V2.
    """
    nome = nome_arquivo.lower()
    local = local_relativo.lower()

    # 1. Novas Estruturas e Contratos Oficiais da V2
    if "v2/" in local or "v2_" in nome:
        if "pages" in local or "page" in nome:
            return "INTERFACE_V2"
        return "CORE_V2"

    # 2. Módulos de Notícias, Calendário e Macro
    if "noticia" in nome or "calendario" in nome:
        if nome.endswith(".py"):
            return "NOTICIAS_MACRO"
        return "DADOS"

    # 3. Motores Ingestão e Coletores
    if "coleta" in nome or "coletor" in nome:
        return "COLETA"

    # 4. Sanitização, Validação e Testes Smoke
    if "valid" in nome or "teste" in nome or "smoke" in nome:
        return "VALIDACAO"

    # 5. Motores de Cálculo e Estimativas Quantitativas
    if "calcul" in nome or "metrica" in nome or "estimativa" in nome:
        return "CALCULOS"

    # 6. Orquestradores, Pipelines e Core Engines
    if "engine" in nome or "decisao" in nome or "pipeline" in nome:
        return "CORE_V1"

    # 7. Relatórios de Auditoria e Mensageria
    if "relatorio" in nome or "mensagem" in nome:
        return "RELATORIOS"

    # 8. Interfaces Visuais Standard (Streamlit Pages)
    if "app" in nome or "page" in nome or "pages/" in local:
        return "INTERFACE_V1"

    # 9. Arquivos de Dados Soltos
    if nome.endswith(".json") or nome.endswith(".csv") or nome.endswith(".log"):
        return "DADOS"

    return "OUTROS"

def executar_mapeamento_projeto():
    print("=" * 60)
    print(" 🗺️ EXECUTANDO ATUALIZAÇÃO DO MAPA LOGÍSTICO DO PROJETO (V2)")
    print("=" * 60)

    # Importa de forma segura o inventário gerado pela etapa anterior do pipeline
    try:
        from Coletas.ArquivosApp import ARQUIVOS_PROJETO
    except ImportError:
        print("❌ [ERRO] Inventário básico 'ArquivosApp.py' não localizado na pasta Coletas.")
        print("   -> Certifique-se de que a etapa 'Gerar_Mapa_Inventario_Tecnico.py' rodou primeiro.")
        return

    mapa = {
        "metadata": {
            "projeto": "Analisador_Financeiro",
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fonte": "Coletas/ArquivosApp.py",
            "versao_arquitetura": "V2.0 (Fase 3 Unificada)"
        },
        "estrutura": {},
        "total_arquivos_catalogados": len(ARQUIVOS_PROJETO),
    }

    # Distribui os arquivos nas novas gavetas lógicas da V2
    for item in ARQUIVOS_PROJETO:
        categoria = classificar_arquivo(item["arquivo"], item["local"])

        if categoria not in mapa["estrutura"]:
            mapa["estrutura"][categoria] = []

        mapa["estrutura"][categoria].append({
            "arquivo": item["arquivo"],
            "local": item["local"],
            "tipo": item["tipo"],
            "tamanho_kb": item["tamanho_kb"],
            "ultima_alteracao": item["ultima_alteracao"],
        })

    # Persistência estável em disco do arquivo de auditoria consumido pelo Streamlit
    try:
        COLETAS_DIR.mkdir(parents=True, exist_ok=True)
        with open(FILE_MAPA_PROJETO, "w", encoding="utf-8") as arquivo:
            json.dump(mapa, arquivo, indent=4, ensure_ascii=False)
            
        print(f"📊 Inventário Analisado: {mapa['total_arquivos_catalogados']} arquivos.")
        for categoria, lista in mapa["grid_estrutura" if "grid" in mapa else "estrutura"].items():
            print(f"  • {categoria:<15} : {len(lista)} arquivos cadastrados")
            
        print(f"\n✅ Mapa do projeto gerado com sucesso em: {FILE_MAPA_PROJETO.name}\n")
    except Exception as e:
        print(f"❌ Erro ao salvar o arquivo Mapa_Projeto.json: {e}")

if __name__ == "__main__":
    executar_mapeamento_projeto()

```

### `Gerar_Relatorio_Mensagem.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: Gerar_Relatorio_Mensagem.py
Versão: 2.4 (Integração SMC / Volume Profile + Cost of Carry)
Objetivo: Consolida os arquivos de decisão, estimativas e cotações unificadas em um relatório executivo em Markdown.
"""

import json
from pathlib import Path
from datetime import datetime

# ==============================================================================
# RESOLUÇÃO DE CAMINHOS E LEITURA DE JSON
# ==============================================================================
RAIZ_PROJETO = Path(__file__).resolve().parent

def carregar_json(nome_arquivo):
    locais = [
        RAIZ_PROJETO / nome_arquivo,
        RAIZ_PROJETO / "Coletas" / nome_arquivo,
        RAIZ_PROJETO / "v2" / nome_arquivo,
        Path.cwd() / nome_arquivo,
        Path.cwd() / "Coletas" / nome_arquivo
    ]
    for p in locais:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}

# ATENCAO: os JSONs eram carregados no nivel de modulo (bug).
# Como o main_pipeline importa este modulo no topo, os carregamentos
# rodavam ANTES de qualquer fase executar — o relatorio mostrava sempre
# o estado do ciclo ANTERIOR.
# Agora sao carregados em _carregar_estado(), chamada dentro de executar().

def _carregar_estado():
    """Carrega todos os JSONs frescos e retorna dict com as variaveis."""
    unificados = carregar_json("DadosAtivosUnificados.json")
    decisao_v2 = carregar_json("Decisao_V2.json")
    resultado_operacional = carregar_json("Resultado_Calculadora_Operacional_Abertura.json")
    estimativas = carregar_json("EstimativaAbertura.json") or carregar_json("Resultado_Calculadora.json")
    smc_dados = carregar_json("AnaliseGraficaSMC_Regras.json")

    ativos = unificados.get("ativos", {})
    obj_decisao = decisao_v2.get("decisao", {})
    meta_decisao = obj_decisao.get("metadados", {})

    return {
        "ativos": ativos,
        "obj_decisao": obj_decisao,
        "meta_decisao": meta_decisao,
        "estimativas": estimativas,
        "resultado_operacional": resultado_operacional,
        "smc_dados": smc_dados,
    }

# Placeholders para compatibilidade com funcoes que usam essas vars no
# nivel de modulo (get_preco_str, get_var_str, etc). Serao preenchidos
# por executar() antes de formatar o relatorio.
ativos = {}
obj_decisao = {}
meta_decisao = {}
estimativas = {}
resultado_operacional = {}
smc_dados = {}

# ==============================================================================
# FUNÇÕES DE EXTRAÇÃO E FORMATAÇÃO DE DADOS
# ==============================================================================
def get_preco_str(ativos_dict, chave, sufixo=""):
    if chave in ativos_dict:
        val = ativos_dict[chave].get("preco")
        if val is not None and isinstance(val, (int, float)):
            return f"{val:,.2f}{sufixo}"
    return "N/A"

def get_var_str(ativos_dict, chave):
    if chave in ativos_dict:
        val = ativos_dict[chave].get("variacao_pct")
        if val is not None and isinstance(val, (int, float)):
            return f"{val:+.2f}%"
    return "N/A"

def get_num_fmt(dicionario, chave, padrao=0.0):
    val = dicionario.get(chave, padrao)
    if isinstance(val, (int, float)) and val > 0:
        return f"{val:,.0f}"
    return "—"

# Extração de Decisão e Targets
# FIX30b: este bloco agora roda DENTRO de executar() (antes ficava no
# nivel de modulo, congelando os valores do import).
def _calcular_derivados(estado):
    """Calcula todos os campos derivados a partir do dict de estado."""
    ativos = estado["ativos"]
    obj_decisao = estado["obj_decisao"]
    meta_decisao = estado["meta_decisao"]
    estimativas = estado["estimativas"]
    resultado_operacional = estado["resultado_operacional"]
    smc_dados = estado["smc_dados"]

    vies_final = obj_decisao.get("vies_final") or "NEUTRO"
    confianca = obj_decisao.get("confianca", 0)
    icone_confianca = "🔴" if confianca >= 80 else ("🟡" if confianca >= 50 else "⚪")

    gatilho = obj_decisao.get("gatilho") or obj_decisao.get("entrada") or obj_decisao.get("entrada_sugerida") or meta_decisao.get("entrada", 0.0)
    stop = obj_decisao.get("stop") or obj_decisao.get("stop_loss") or meta_decisao.get("stop", 0.0)

    alvos = obj_decisao.get("alvos") or meta_decisao.get("alvos", [])
    alvo_1 = alvos[0] if isinstance(alvos, list) and len(alvos) > 0 else (obj_decisao.get("alvo_1") or 0.0)

    win_est = estimativas.get("estimativa_abertura", {}).get("WIN_INDICE") or estimativas.get("estimativa_abertura", {}).get("WIN_FUT") or {}
    teorico = win_est.get("abertura_teorica_pontos") or resultado_operacional.get("previsao_abertura", {}).get("teorico_win") or meta_decisao.get("teorico_win", 0.0)
    teorico_str = f"{teorico:,.0f} pts" if isinstance(teorico, (int, float)) and teorico > 0 else "—"

    coc_dados = win_est.get("cost_of_carry", {})
    preco_carregado = coc_dados.get("preco_teorico_carregado", 0.0)
    carregado_str = f"{preco_carregado:,.0f} pts" if isinstance(preco_carregado, (int, float)) and preco_carregado > 0 else "—"

    var_est = win_est.get("variacao_teorica_pct") or resultado_operacional.get("previsao_abertura", {}).get("variacao_estimada", 0.0)
    var_est_str = f"{var_est:+.2f}%"

    ajuste = meta_decisao.get("ajuste") or ativos.get("WIN_AJUSTE", {}).get("preco", 0.0)
    ajuste_str = f"{ajuste:,.0f} pts" if isinstance(ajuste, (int, float)) and ajuste > 0 else "— pts"

    pivots = estimativas.get("pivot_points", {}).get("WIN_FUT") or meta_decisao.get("pivots") or {}
    niveis_inst = smc_dados.get("niveis_institucionais", {}) or estimativas.get("pivots_institucionais", {})
    poc_ontem = niveis_inst.get("poc_ontem", 0.0)
    vwap_ontem = niveis_inst.get("vwap_ontem", 0.0)

    poc_str = f"{poc_ontem:,.0f} pts" if isinstance(poc_ontem, (int, float)) and poc_ontem > 0 else "—"
    vwap_str = f"{vwap_ontem:,.1f} pts" if isinstance(vwap_ontem, (int, float)) and vwap_ontem > 0 else "—"

    vix_val = get_preco_str(ativos, "VIX")
    iron_val = get_preco_str(ativos, "IRON_ORE")
    oil_val = get_preco_str(ativos, "CRUDE_OIL")
    di27_val = get_var_str(ativos, "DI1_2027")
    di29_val = get_var_str(ativos, "DI1_2029")

    return {
        "vies_final": vies_final,
        "confianca": confianca,
        "icone_confianca": icone_confianca,
        "gatilho": gatilho,
        "stop": stop,
        "alvos": alvos,
        "alvo_1": alvo_1,
        "teorico_str": teorico_str,
        "carregado_str": carregado_str,
        "var_est_str": var_est_str,
        "ajuste_str": ajuste_str,
        "pivots": pivots,
        "poc_str": poc_str,
        "vwap_str": vwap_str,
        "vix_val": vix_val,
        "iron_val": iron_val,
        "oil_val": oil_val,
        "di27_val": di27_val,
        "di29_val": di29_val,
    }

# ==============================================================================
# MONTAGEM E GRAVAÇÃO DO RELATÓRIO
# ==============================================================================
def executar():
    print("=" * 60)
    print("🚀 INICIANDO GERADOR DE RELATÓRIO OPERACIONAL EXECUTIVO (V2)")
    print("=" * 60)

    # --- FIX30 + FIX30b: recarrega estado E recalcula derivados ---
    estado = _carregar_estado()

    # Recalcula TODOS os derivados (gatilho, stop, alvos, teorico, etc)
    _d = _calcular_derivados(estado)
    vies_final = _d["vies_final"]
    confianca = _d["confianca"]
    icone_confianca = _d["icone_confianca"]
    gatilho = _d["gatilho"]
    stop = _d["stop"]
    alvos = _d["alvos"]
    alvo_1 = _d["alvo_1"]
    teorico_str = _d["teorico_str"]
    carregado_str = _d["carregado_str"]
    var_est_str = _d["var_est_str"]
    ajuste_str = _d["ajuste_str"]
    pivots = _d["pivots"]
    poc_str = _d["poc_str"]
    vwap_str = _d["vwap_str"]
    vix_val = _d["vix_val"]
    iron_val = _d["iron_val"]
    oil_val = _d["oil_val"]
    di27_val = _d["di27_val"]
    di29_val = _d["di29_val"]

    agora_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
    
    gatilho_str = f"{gatilho:,.0f} pts" if isinstance(gatilho, (int, float)) and gatilho > 0 else "—"
    stop_str = f"{stop:,.0f} pts" if isinstance(stop, (int, float)) and stop > 0 else "—"
    alvo_1_str = f"{alvo_1:,.0f} pts" if isinstance(alvo_1, (int, float)) and alvo_1 > 0 else "—"

    relatorio_md = f"""📊 *QUANT TERMINAL B3 — MORNING REPORT V2* 📊
⏱ _Pregão Analisado: {agora_str}_
--------------------------------------------------
🎯 *ESTRUTURA DIRECIONAL CORE V2*
• **Viés Institucional:** `{vies_final}`
• **Força de Confluência:** `{icone_confianca} {confianca}%`
• **Ordem Gatilho (Entry):** `{gatilho_str}`
• **Stop Loss Técnico:** `{stop_str}`
• **Alvo Principal (T1):** `{alvo_1_str}`

--------------------------------------------------
📈 *PREVISÃO DE ESTIMATIVA E GAP (WIN)*
• **Preço Teórico de Abertura:** `{teorico_str}`
• **Abertura Carregada (DI/252):** `{carregado_str}`
• **Variação Estimada:** `{var_est_str}`
• **Ajuste Base Anterior:** `{ajuste_str}`

🏦 *Pivôs Institucionais (Volume Profile / Tesouraria):*
• **POC (Ontem - Maior Volume):** `{poc_str}`
• **VWAP (Ontem - Preço Ponderado):** `{vwap_str}`

📍 *Níveis Críticos de Pivô (Floor):*
• Resistência 2 (R2): `{get_num_fmt(pivots, 'R2', pivots.get('r2', 0))}` | Resistência 1 (R1): `{get_num_fmt(pivots, 'R1', pivots.get('r1', 0))}`
• **Ponto de Pivô (PP):** `{get_num_fmt(pivots, 'PP', pivots.get('pp', 0))}`
• Suporte 1 (S1): `{get_num_fmt(pivots, 'S1', pivots.get('s1', 0))}` | Suporte 2 (S2): `{get_num_fmt(pivots, 'S2', pivots.get('s2', 0))}`

--------------------------------------------------
🌐 *TERMÔMETRO CONTEXTUAL MACRO*
• VIX Volatilidade : `{vix_val}`
• Minério de Ferro  : `US$ {iron_val}`
• Petróleo WTI      : `US$ {oil_val}`
• Curva de Juros    : DI27: `{di27_val}` | DI29: `{di29_val}`
--------------------------------------------------
⚠️ _Relatório quantitativo confidencial para apoio operational à mesa._
"""

    caminho_saida = RAIZ_PROJETO / "Coletas" / "Relatorio_Executivo.md"
    if not caminho_saida.parent.exists():
        caminho_saida = RAIZ_PROJETO / "Relatorio_Executivo.md"
        
    try:
        with open(caminho_saida, "w", encoding="utf-8") as f:
            f.write(relatorio_md)
        print("✨ Mensagem compilada e formatada com sucesso!")
        print(f"✅ Arquivo salvo para integração em: {caminho_saida.name}\n")
        print(relatorio_md)
    except Exception as e:
        print(f"❌ Erro ao salvar o relatório: {e}")

if __name__ == "__main__":
    executar()
```

### `Gerar_Resultado_Operacional_Abertura.py`

```python
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

```

### `Limpar_Imagens_TradingView.py`

```python
import glob
import os
import re
import shutil
import sys
from pathlib import Path

# Forca UTF-8 no terminal Windows (evita UnicodeEncodeError com emojis
# quando o script e chamado via subprocess.run() no main_pipeline.py)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

# ============================================================
# CONFIGURAÇÃO DE CAMINHOS E METAS
# ============================================================
PASTA_DOWNLOADS = os.path.expanduser(r"~\Downloads")
MANTER_RECENTES = 2

# Pasta Coletas relativa à raiz do projeto
BASE_DIR = Path(__file__).resolve().parent
PASTA_COLETAS = BASE_DIR / "Coletas"

# Padronização de Regex para capturar contratos do WIN (WINQ2026, WINV26, BMFBOVESPA_WIN, etc)
# e capturas padrão do TradingView
PADRAO_REGEX_TRADINGVIEW = re.compile(
    r"^(WIN[A-Z]\d{2,4}|tradingview|BMFBOVESPA_WIN)", re.IGNORECASE
)


def e_imagem_tradingview(nome_arquivo):
    """Verifica se o arquivo é uma imagem e atende aos padrões de nome do WIN ou TradingView."""
    extensao_valida = nome_arquivo.lower().endswith((".png", ".jpg", ".jpeg"))
    match_nome = bool(PADRAO_REGEX_TRADINGVIEW.search(nome_arquivo))
    return extensao_valida and match_nome


def limpar_e_processar_imagens():
    print("============================================================")
    print("🧹 GERENCIADOR DINÂMICO DE IMAGENS (WIN / TRADINGVIEW)")
    print("============================================================")

    if not os.path.exists(PASTA_DOWNLOADS):
        print(f"❌ Pasta não encontrada: {PASTA_DOWNLOADS}")
        return

    # Garante que a pasta Coletas existe no projeto
    PASTA_COLETAS.mkdir(exist_ok=True)

    # 1. Varre a pasta e filtra os arquivos dinamicamente
    todos_arquivos = os.listdir(PASTA_DOWNLOADS)
    imagens_filtradas = [
        os.path.join(PASTA_DOWNLOADS, f)
        for f in todos_arquivos
        if e_imagem_tradingview(f)
    ]

    if not imagens_filtradas:
        print(
            "ℹ️ Nenhuma imagem recente de contrato WIN/TradingView foi encontrada."
        )
        return

    # 2. Ordena da mais RECENTE [index 0] para a mais ANTIGA [index -1]
    imagens_ordenadas = sorted(
        imagens_filtradas, key=os.path.getmtime, reverse=True
    )

    total_encontrados = len(imagens_ordenadas)
    print(
        f"🔍 Total de imagens WIN/TradingView identificadas: {total_encontrados}"
    )

    # 3. Separa as 2 mais recentes do restante
    para_manter = imagens_ordenadas[:MANTER_RECENTES]
    para_deletar = imagens_ordenadas[MANTER_RECENTES:]

    print("\n✅ MANTIDAS (Mais recentes):")
    for arq in para_manter:
        print(f"  └─ {os.path.basename(arq)}")

    # ------------------------------------------------------------
    # 4. COPIA E RENOMEIA PARA A PASTA COLETAS
    # ------------------------------------------------------------
    if len(para_manter) >= 2:
        img_1min_origem = para_manter[0]  # Mais recente (1min)
        img_5min_origem = para_manter[1]  # Mais antiga das duas (5min)

        dest_1min = PASTA_COLETAS / "WIN_1min.png"
        dest_5min = PASTA_COLETAS / "WIN_5min.png"

        try:
            shutil.copy2(img_1min_origem, dest_1min)
            shutil.copy2(img_5min_origem, dest_5min)

            print("\n📁 COPIADAS PARA /Coletas:")
            print(
                f"  ├─ {os.path.basename(img_5min_origem)} ➔ Coletas/WIN_5min.png (5 min)"
            )
            print(
                f"  └─ {os.path.basename(img_1min_origem)} ➔ Coletas/WIN_1min.png (1 min)"
            )
        except Exception as err:
            print(f"❌ Erro ao copiar arquivos para Coletas: {err}")
    else:
        print("\n⚠️ Menos de 2 imagens encontradas. Cópia parcial cancelada.")

    # 5. Deleta as antigas da pasta Downloads
    if para_deletar:
        print(f"\n🗑️ REMOVENDO {len(para_deletar)} IMAGEM(NS) ANTIGA(S)...")
        for arq in para_deletar:
            try:
                os.remove(arq)
                print(f"  ❌ Removido: {os.path.basename(arq)}")
            except Exception as e:
                print(f"  ⚠️ Erro ao remover {os.path.basename(arq)}: {e}")
    else:
        print("\n✨ Nenhuma imagem antiga para deletar.")

    print("\n============================================================")


if __name__ == "__main__":
    limpar_e_processar_imagens()
```

### `MapearTendencia15Min.py`

```python
import json
import os
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO DE CAMINHOS E PARÂMETROS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
PASTA_COLETAS = BASE_DIR / "Coletas"

# Tolerancia em % para desconsiderar ruidos insignificantes.
# 0.005 = 0.005%: no WIN (~190k) ~9,5 pts; no WDO (~5.1k) ~0,25 pts.
# Bate com o threshold do mini_velocimetro (0.005).
TOLERANCIA_PERCENTUAL = 0.005


def carregar_e_mapear_coleta(nome_arquivo):
    """
    Lê o JSON da pasta Coletas e transforma a lista de coletas em um dicionário:
    { "NOME_DO_ATIVO": preco_close }
    """
    caminho = PASTA_COLETAS / nome_arquivo
    if not caminho.exists():
        print(f"⚠️ Aviso: Arquivo {nome_arquivo} não encontrado em {PASTA_COLETAS}")
        return {}

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)

        mapa_precos = {}
        # Iterar sobre a lista 'coletas' do JSON
        for item in dados.get("coletas", []):
            ativo = item.get("ativo")
            dados_reais = item.get("dados_reais", {})
            close = dados_reais.get("close")

            if ativo and close is not None:
                try:
                    mapa_precos[ativo] = float(close)
                except (ValueError, TypeError):
                    continue

        return mapa_precos

    except json.JSONDecodeError:
        print(f"❌ Erro: O arquivo {nome_arquivo} está corrompido ou vazio.")
        return {}


def determinar_tendencia(preco_anterior, preco_atual):
    """Calcula a variação relativa e a direção do movimento."""
    if preco_anterior == 0 or preco_atual == 0:
        return {"variacao_abs": 0.0, "variacao_pct": 0.0, "tendencia": "SEM_DADOS"}

    var_abs = preco_atual - preco_anterior
    var_pct = (var_abs / preco_anterior) * 100

    if var_pct > TOLERANCIA_PERCENTUAL:
        tendencia = "Alta"
    elif var_pct < -TOLERANCIA_PERCENTUAL:
        tendencia = "Baixa"
    else:
        tendencia = "Estavel"

    return {
        "variacao_abs": round(var_abs, 4),
        "variacao_pct": round(var_pct, 4),
        "tendencia": tendencia,
    }


def analisar_arquivos_e_gerar_comparativo():
    """Lê as 3 coletas e gera a estrutura comparativa sequencial."""
    print("============================================================")
    print("📊 INICIANDO ANÁLISE DE TENDÊNCIAS (10m ➔ 5m ➔ 0m)")
    print("============================================================")

    # 1. Carrega e mapeia as 3 coletas
    coletarom10 = carregar_e_mapear_coleta("Coleta_rom-10.json")
    coletarom5 = carregar_e_mapear_coleta("Coleta_rom-5.json")
    coletarom0 = carregar_e_mapear_coleta("Coleta_rom-0.json")

    comparativo = {}

    # 2. Une todos os ativos encontrados nas 3 coletas
    todos_ativos = (
        set(coletarom10.keys())
        | set(coletarom5.keys())
        | set(coletarom0.keys())
    )

    if not todos_ativos:
        print("⚠️ Nenhum ativo foi extraído dos arquivos. Verifique a pasta Coletas.")
        return

    # 3. Compara ativo por ativo
    for ativo in todos_ativos:
        p10 = coletarom10.get(ativo)
        p5 = coletarom5.get(ativo)
        p0 = coletarom0.get(ativo)

        # Se faltar o preço em algum dos 3 arquivos, pula para não distorcer a análise
        if p10 is None or p5 is None or p0 is None:
            continue

        mov_10_5 = determinar_tendencia(p10, p5)
        mov_5_0 = determinar_tendencia(p5, p0)

        padrao = f"{mov_10_5['tendencia']}_E_{mov_5_0['tendencia']}"

        comparativo[ativo] = {
            "precos": {"10m": p10, "5m": p5, "0m": p0},
            "intervalo_10_para_5": mov_10_5,
            "intervalo_5_para_0": mov_5_0,
            "padrao_comportamento": padrao,
        }

    # 4. Salva o resultado no JSON de saída
    caminho_saida = PASTA_COLETAS / "Analise_Tendencias.json"

    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(comparativo, f, indent=4, ensure_ascii=False)

    print(f"✅ Análise concluída com sucesso! {len(comparativo)} ativos processados.")
    print(f"📁 Arquivo salvo em: {caminho_saida}")
    print("============================================================")


if __name__ == "__main__":
    analisar_arquivos_e_gerar_comparativo()
```

### `Motor_SMC_Regras.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor_SMC_Regras.py
===================
Motor de regras SMC/ICT SEM IA — Versão 2.1 (Refatorada + Bugfixes)

Melhorias v2.0:
- Order Blocks validados por BOS/CHoCH posterior
- Cascata de entradas: OB → FVG → Preço atual
- Timezone BRT explícita (MT5 retorna UTC)
- Tick size configurável por ativo (sem hardcode)
- Expansão FORTE (volume AND corpo) vs FRACA (OR)
- Equal Highs/Lows detectados como liquidez confirmada
- Confiança ponderada por pesos (0-100 normalizado)
- Logging estruturado
- Histórico opcional de saídas
- CLI com argparse para execução isolada

Bugfixes v2.1:
- Alvos filtrados pelo lado correto (compra=acima, venda=abaixo)
- Stop mínimo por ATR (evita stop apertado em M5)
- Fallback de OBs brutos quando nenhum valida por BOS/CHoCH
- Filtro de OB mínimo (range < 30 pts = ruído)
- Alerta de divergência Macro × SMC
- Janela de validação OB ampliada (40 candles)
- Distância OB↔POC ampliada (300 WIN / 30 WDO)

Entrada: lista/DataFrame de candles OHLCV
Saída: JSON estruturado em Coletas/AnaliseGraficaSMC_Regras.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

# ============================================================
# FIX: FORÇA UTF-8 NO TERMINAL WINDOWS
# ============================================================
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# ============================================================
# LOGGING ESTRUTURADO
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("MotorSMC")

# ============================================================
# CONFIGURAÇÃO DE DIRETÓRIOS E ARQUIVOS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
COLETAS_DIR = BASE_DIR / "Coletas"

if not COLETAS_DIR.exists():
    alt = BASE_DIR.parent / "Coletas"
    if alt.exists():
        COLETAS_DIR = alt

FILE_MT5_DADOS = COLETAS_DIR / "Dados_MT5_v2_2.json"
ARQUIVO_SAIDA = COLETAS_DIR / "AnaliseGraficaSMC_Regras.json"
HISTORICO_SMC_DIR = COLETAS_DIR / "Historico_SMC"
METRICAS_FILE = COLETAS_DIR / "Metricas_Calculadas.json"

# Timezone Brasil
BRT = timezone(timedelta(hours=-3))


# ============================================================
# CONFIGURAÇÃO
# ============================================================
@dataclass
class ConfigSMC:
    swing_left: int = 2
    swing_right: int = 2
    fvg_min_pontos: float = 20.0
    eq_tol_pontos: float = 15.0
    max_niveis: int = 12
    max_fvgs: int = 8
    max_obs: int = 6
    lookback: int = 120  # fallback quando TF nao esta no mapa
    lookback_map: Dict[str, int] = field(
        default_factory=lambda: {
            "1m": 240,
            "5m": 120,
            "15m": 80,
        }
    )

    # Filtro de volume e expansão
    vol_ma_period: int = 20
    vol_factor_min: float = 1.2
    expansion_factor_min: float = 1.3

    # POC/VWAP
    tick_size_default: float = 5.0
    tick_size_map: Dict[str, float] = field(
        default_factory=lambda: {
            "WIN": 5.0,
            "WDO": 0.5,
            "VALE3": 0.01,
            "PETR4": 0.01,
            "ITUB4": 0.01,
            "BBAS3": 0.01,
            "BBDC4": 0.01,
            "B3SA3": 0.01,
            "ES": 0.25,
            "NQ": 0.25,
        }
    )

    # Validação de OB
    ob_validacao_janela: int = 40
    ob_min_range: float = 30.0
    ob_fallback_brutos: bool = True

    # Deduplicação de OBs por ativo (threshold em pontos)
    # WIN tem tick de 5 pts → OBs separados por <50 pts são o mesmo bloco
    # WDO tem tick de 0.5 pts → 5 pts já é generoso
    dedup_ob_dist: Dict[str, float] = field(
        default_factory=lambda: {
            "WIN": 50.0,
            "WDO": 5.0,
        }
    )
    dedup_ob_dist_default: float = 10.0

    # Confluência OB ↔ POC
    ob_poc_dist_win: float = 300.0
    ob_poc_dist_wdo: float = 30.0


    # Stop mínimo (proteção contra ruído M5)
    stop_min_dist: float = 150.0
    stop_atr_mult: float = 0.8
    stop_atr_period: int = 20


CONFIG = ConfigSMC()


# ============================================================
# DATACLASSES
# ============================================================
@dataclass
class Candle:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    idx: int = 0


@dataclass
class Swing:
    idx: int
    preco: float
    tipo: str  # "HIGH" | "LOW" | "HIGH_EQ" | "LOW_EQ"
    time: str = ""


@dataclass
class FVG:
    tipo: str
    superior: float
    inferior: float
    idx: int
    time: str = ""
    preenchido: bool = False


@dataclass
class OrderBlock:
    tipo: str
    high: float
    low: float
    preco_ref: float
    idx: int
    time: str = ""
    validado_por: str = ""  # "BOS" | "CHOCH" | "FALLBACK" | ""


@dataclass
class EventoEstrutura:
    tipo: str  # "BOS" | "CHOCH"
    direcao: str  # "ALTA" | "BAIXA"
    preco: float
    idx: int
    time: str = ""


# ============================================================
# HELPERS
# ============================================================
def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _tick_size_para(ativo: str, config: ConfigSMC = CONFIG) -> float:
    """Retorna o tick size adequado para o ativo."""
    ativo_up = (ativo or "").upper()
    for chave, tick in config.tick_size_map.items():
        if chave in ativo_up:
            return tick
    return config.tick_size_default


def _dedup_dist_para(ativo: str, config: ConfigSMC = CONFIG) -> float:
    """
    Retorna a distancia minima (em pontos) para considerar dois OBs distintos.

    WIN: 50 pts (blocos muito proximos sao o mesmo OB visto de angulos diferentes)
    WDO: 5 pts
    Default: 10 pts
    """
    ativo_up = (ativo or "").upper()
    for chave, dist in config.dedup_ob_dist.items():
        if chave in ativo_up:
            return dist
    return config.dedup_ob_dist_default


# ============================================================
# NORMALIZAÇÃO DE CANDLES
# ============================================================
def normalizar_candles(dados: Any) -> List[Candle]:
    rows: List[Any] = []
    if hasattr(dados, "to_dict") and hasattr(dados, "columns"):
        try:
            rows = dados.to_dict(orient="records")
        except Exception:
            rows = list(dados)
    else:
        rows = list(dados)

    candles: List[Candle] = []
    for row in rows:
        if isinstance(row, dict):
            o = row.get("open", row.get("Open", row.get("o")))
            h = row.get("high", row.get("High", row.get("h")))
            l = row.get("low", row.get("Low", row.get("l")))
            c = row.get("close", row.get("Close", row.get("c")))
            t = row.get("time", row.get("Time", row.get("datetime", row.get("date", ""))))
            vol = row.get("real_volume", row.get("volume", row.get("Volume", row.get("tick_volume", 0))))
        elif isinstance(row, (list, tuple)) and len(row) >= 5:
            if isinstance(row[0], (int, float)) and not isinstance(row[1], str):
                t, o, h, l, c = "", row[0], row[1], row[2], row[3]
                vol = row[4] if len(row) > 4 else 0
            else:
                t = row[0]
                o, h, l, c = row[1], row[2], row[3], row[4]
                vol = row[5] if len(row) > 5 else 0
        else:
            continue

        o, h, l, c = _to_float(o), _to_float(h), _to_float(l), _to_float(c)
        if h <= 0 or l <= 0 or c <= 0:
            continue
        if h < l:
            h, l = l, h

        candles.append(
            Candle(
                time=str(t) if t is not None else "",
                open=o,
                high=h,
                low=l,
                close=c,
                volume=_to_float(vol),
                idx=len(candles),
            )
        )

    return candles


def aplicar_lookback(candles: List[Candle], lookback: int) -> List[Candle]:
    if lookback and lookback > 0 and len(candles) > lookback:
        slice_c = candles[-lookback:]
        for i, c in enumerate(slice_c):
            c.idx = i
        return slice_c
    return candles


# ============================================================
# MÉTRICAS DE VOLUME / EXPANSÃO
# ============================================================
def calcular_metricas_medias(
    candles: List[Candle], idx_atual: int, config: ConfigSMC = CONFIG
) -> Tuple[float, float]:
    periodo = config.vol_ma_period
    inicio = max(0, idx_atual - periodo)
    janela = candles[inicio:idx_atual]

    if not janela:
        return 0.0, 0.0

    media_vol = sum(c.volume for c in janela) / len(janela)
    media_corpo = sum(abs(c.close - c.open) for c in janela) / len(janela)
    return media_vol, media_corpo


def classificar_candle(
    candle: Candle, media_vol: float, media_corpo: float, config: ConfigSMC = CONFIG
) -> str:
    """
    Retorna:
    - "FORTE":  volume E corpo acima do limiar (expansão real)
    - "FRACO":  volume OU corpo acima do limiar (expansão parcial)
    - "NENHUM": sem expansão
    """
    corpo = abs(candle.close - candle.open)

    if media_vol <= 0 and media_corpo <= 0:
        return "NENHUM"

    vol_ok = media_vol > 0 and candle.volume >= media_vol * config.vol_factor_min
    corpo_ok = media_corpo > 0 and corpo >= media_corpo * config.expansion_factor_min

    if vol_ok and corpo_ok:
        return "FORTE"
    if vol_ok or corpo_ok:
        return "FRACO"
    return "NENHUM"


def e_candle_expansao(
    candle: Candle, media_vol: float, media_corpo: float, config: ConfigSMC = CONFIG
) -> bool:
    """Compatibilidade: aceita FRACO ou FORTE."""
    return classificar_candle(candle, media_vol, media_corpo, config) in ("FORTE", "FRACO")


# ============================================================
# POC / VWAP (dia anterior)
# ============================================================
def calcular_poc_vwap(candles: List[Candle], ativo: str, config: ConfigSMC = CONFIG) -> Dict[str, float]:
    """
    Calcula VWAP e POC do dia anterior.
    POC usa distribuição de volume entre High-Low (Volume Profile correto).
    Tick size vem do ConfigSMC, não é mais hardcoded.
    """
    if len(candles) < 20:
        return {"poc": 0.0, "vwap": 0.0}

    df = pd.DataFrame([c.__dict__ for c in candles])
    try:
        df["time_dt"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert(BRT)
    except Exception:
        df["time_dt"] = pd.to_datetime(df["time"], errors="coerce")

    df["date"] = df["time_dt"].dt.date

    datas_unicas = sorted([d for d in df["date"].unique() if pd.notna(d)])
    hoje = datetime.now(BRT).date()

    datas_passadas = [d for d in datas_unicas if d < hoje]

    if datas_passadas:
        data_alvo = datas_passadas[-1]
    elif datas_unicas:
        data_alvo = datas_unicas[-1]
    else:
        return {"poc": 0.0, "vwap": 0.0}

    df_ontem = df[df["date"] == data_alvo].copy()
    if df_ontem.empty:
        df_ontem = df

    # 1. VWAP
    df_ontem["preco_tipico"] = (df_ontem["high"] + df_ontem["low"] + df_ontem["close"]) / 3
    df_ontem["vol_financeiro"] = df_ontem["preco_tipico"] * df_ontem["volume"]

    vol_total = df_ontem["volume"].sum()
    vwap = df_ontem["vol_financeiro"].sum() / vol_total if vol_total > 0 else 0.0

    # 2. POC (Volume Profile distribuído)
    tick_size = _tick_size_para(ativo, config)
    profile_dict: Dict[float, float] = {}

    for _, row in df_ontem.iterrows():
        h = row["high"]
        l = row["low"]
        v = row["volume"]

        if h <= 0 or l <= 0 or v <= 0:
            continue
        if h < l:
            h, l = l, h

        bins_candle = np.arange(
            np.floor(l / tick_size) * tick_size,
            np.ceil(h / tick_size) * tick_size + tick_size,
            tick_size,
        )

        if len(bins_candle) > 0:
            vol_por_bin = v / len(bins_candle)
            for b in bins_candle:
                b_rounded = round(float(b), 4)
                profile_dict[b_rounded] = profile_dict.get(b_rounded, 0.0) + vol_por_bin

    poc = max(profile_dict, key=profile_dict.get) if profile_dict else 0.0

    return {"poc": float(poc), "vwap": round(float(vwap), 1)}


# ============================================================
# SWINGS
# ============================================================
def detectar_swings(
    candles: List[Candle],
    config: ConfigSMC = CONFIG,
) -> List[Swing]:
    left = config.swing_left
    right = config.swing_right
    swings: List[Swing] = []
    n = len(candles)
    if n < left + right + 1:
        return swings

    for i in range(left, n - right):
        window = candles[i - left : i + right + 1]
        highs = [c.high for c in window]
        lows = [c.low for c in window]
        mid = candles[i]

        # HIGH — aceita equal highs
        if mid.high >= max(highs):
            tipo = "HIGH_EQ" if highs.count(mid.high) > 1 else "HIGH"
            swings.append(Swing(idx=i, preco=mid.high, tipo=tipo, time=mid.time))

        # LOW — aceita equal lows
        if mid.low <= min(lows):
            tipo = "LOW_EQ" if lows.count(mid.low) > 1 else "LOW"
            swings.append(Swing(idx=i, preco=mid.low, tipo=tipo, time=mid.time))

    return swings


def _so_highs(swings: List[Swing]) -> List[Swing]:
    return [s for s in swings if s.tipo.startswith("HIGH")]


def _so_lows(swings: List[Swing]) -> List[Swing]:
    return [s for s in swings if s.tipo.startswith("LOW")]


# ============================================================
# BOS / CHOCH
# ============================================================
def detectar_bos_choch(
    candles: List[Candle],
    swings: List[Swing],
    config: ConfigSMC = CONFIG,
) -> Tuple[List[EventoEstrutura], str]:
    eventos: List[EventoEstrutura] = []
    if len(swings) < 4 or len(candles) < 5:
        return eventos, "LATERAL"

    highs = _so_highs(swings)
    lows = _so_lows(swings)

    bias = "LATERAL"
    if len(highs) >= 2 and len(lows) >= 2:
        hh = highs[-1].preco > highs[-2].preco
        hl = lows[-1].preco > lows[-2].preco
        lh = highs[-1].preco < highs[-2].preco
        ll = lows[-1].preco < lows[-2].preco
        if hh and hl:
            bias = "ALTA"
        elif lh and ll:
            bias = "BAIXA"

    last_high: Optional[Swing] = None
    last_low: Optional[Swing] = None
    tendencia_atual = bias if bias != "LATERAL" else "LATERAL"

    for s in swings:
        if s.tipo.startswith("HIGH"):
            if last_high:
                for c in candles[s.idx:]:
                    if c.close > last_high.preco:
                        tipo_ev = "BOS" if tendencia_atual == "ALTA" else "CHOCH"
                        eventos.append(
                            EventoEstrutura(
                                tipo=tipo_ev,
                                direcao="ALTA",
                                preco=last_high.preco,
                                idx=c.idx,
                                time=c.time,
                            )
                        )
                        tendencia_atual = "ALTA"
                        break
            last_high = s

        if s.tipo.startswith("LOW"):
            if last_low:
                for c in candles[s.idx:]:
                    if c.close < last_low.preco:
                        tipo_ev = "BOS" if tendencia_atual == "BAIXA" else "CHOCH"
                        eventos.append(
                            EventoEstrutura(
                                tipo=tipo_ev,
                                direcao="BAIXA",
                                preco=last_low.preco,
                                idx=c.idx,
                                time=c.time,
                            )
                        )
                        tendencia_atual = "BAIXA"
                        break
            last_low = s

    # Fix43: dedup por (idx, tipo, direcao). O mesmo candle pode
    # romper multiplos swings ao mesmo tempo e gerar eventos duplicados
    # no mesmo timestamp — isso inflava contagens e confianca.
    if eventos:
        # Fix43: dedup por (idx, tipo, direcao)
        vistos = set()
        unicos = []
        for e in eventos:
            chave = (e.idx, e.tipo, e.direcao)
            if chave in vistos:
                continue
            vistos.add(chave)
            unicos.append(e)
        eventos = unicos

        # Fix44: ordena cronologicamente pelo idx do candle de rompimento.
        # Sem isso, eventos[-1] nao era o mais recente (bug pre-existente).
        eventos.sort(key=lambda e: e.idx)

    if eventos:
        bias = eventos[-1].direcao
    return eventos, bias


# ============================================================
# FVG
# ============================================================
def detectar_fvg(candles: List[Candle], config: ConfigSMC = CONFIG) -> List[FVG]:
    fvgs: List[FVG] = []
    n = len(candles)
    if n < 3:
        return fvgs

    for i in range(2, n):
        c0, c1, c2 = candles[i - 2], candles[i - 1], candles[i]
        media_vol, media_corpo = calcular_metricas_medias(candles, i - 1, config)
        # Exige expansão FORTE para validar FVG
        if classificar_candle(c1, media_vol, media_corpo, config) != "FORTE":
            continue

        if c2.low > c0.high and (c2.low - c0.high) >= config.fvg_min_pontos:
            fvgs.append(
                FVG(tipo="COMPRA", superior=c2.low, inferior=c0.high, idx=i, time=c2.time)
            )

        if c2.high < c0.low and (c0.low - c2.high) >= config.fvg_min_pontos:
            fvgs.append(
                FVG(tipo="VENDA", superior=c0.low, inferior=c2.high, idx=i, time=c2.time)
            )

    # Marca FVGs preenchidos
    for fvg in fvgs:
        for c in candles[fvg.idx + 1:]:
            if fvg.tipo == "COMPRA" and c.low <= fvg.inferior:
                fvg.preenchido = True
                break
            if fvg.tipo == "VENDA" and c.high >= fvg.superior:
                fvg.preenchido = True
                break

    return fvgs


# ============================================================
# ORDER BLOCKS (com validação BOS/CHoCH + fallback + min range)
# ============================================================
def detectar_order_blocks(
    candles: List[Candle],
    swings: List[Swing],
    eventos_estrutura: List[EventoEstrutura],
    ativo: str = "WIN",
    config: ConfigSMC = CONFIG,
) -> List[OrderBlock]:
    obs_brutos: List[OrderBlock] = []
    n = len(candles)
    if n < 5 or len(swings) < 2:
        return obs_brutos

    for s in swings[-10:]:
        i = s.idx
        if i < 1 or i >= n - 1:
            continue

        cand = candles[i]
        prev = candles[i - 1]

        # OB é a última candle contrária
        if s.tipo.startswith("LOW"):
            ob_cand = prev if prev.close < prev.open else cand
        else:
            ob_cand = prev if prev.close > prev.open else cand

        # FILTRO: OB muito pequeno é ruído
        range_ob = ob_cand.high - ob_cand.low
        if range_ob < config.ob_min_range:
            continue

        media_vol, media_corpo = calcular_metricas_medias(candles, i, config)
        candle_saida = candles[i + 1] if (i + 1) < n else cand

        if not e_candle_expansao(candle_saida, media_vol, media_corpo, config):
            continue

        if s.tipo.startswith("LOW"):
            if any(c.close > cand.high for c in candles[i + 1 : min(i + 4, n)]):
                obs_brutos.append(
                    OrderBlock(
                        tipo="COMPRA",
                        high=ob_cand.high,
                        low=ob_cand.low,
                        preco_ref=round((ob_cand.high + ob_cand.low) / 2, 1),
                        idx=ob_cand.idx,
                        time=ob_cand.time,
                    )
                )

        if s.tipo.startswith("HIGH"):
            if any(c.close < cand.low for c in candles[i + 1 : min(i + 4, n)]):
                obs_brutos.append(
                    OrderBlock(
                        tipo="VENDA",
                        high=ob_cand.high,
                        low=ob_cand.low,
                        preco_ref=round((ob_cand.high + ob_cand.low) / 2, 1),
                        idx=ob_cand.idx,
                        time=ob_cand.time,
                    )
                )

    # ---- Validação: OB só é válido se houver BOS/CHoCH posterior
    obs_validados: List[OrderBlock] = []
    for ob in obs_brutos:
        direcao_alvo = "ALTA" if ob.tipo == "COMPRA" else "BAIXA"
        for e in eventos_estrutura:
            if (
                e.idx > ob.idx
                and e.idx <= ob.idx + config.ob_validacao_janela
                and e.direcao == direcao_alvo
            ):
                ob.validado_por = e.tipo
                obs_validados.append(ob)
                break

    # ---- LOG diagnóstico
    logger.info(
        f"OBs brutos: {len(obs_brutos)} | OBs validados por BOS/CHoCH: {len(obs_validados)}"
    )

    # ---- FALLBACK: se nenhum passou, usa os brutos
    if not obs_validados and obs_brutos and config.ob_fallback_brutos:
        logger.warning("Nenhum OB validado por BOS/CHoCH — usando brutos como fallback")
        for ob in obs_brutos:
            ob.validado_por = "FALLBACK"
        obs_validados = obs_brutos

    # ---- Deduplicação (threshold por ativo)
    dist_dedup = _dedup_dist_para(ativo, config)
    unicos: List[OrderBlock] = []
    for ob in obs_validados:
        if not any(
            abs(ob.preco_ref - u.preco_ref) < dist_dedup and ob.tipo == u.tipo
            for u in unicos
        ):
            unicos.append(ob)

    # Log diagnostico (ajuda a ver quantos OBs foram consolidados)
    if len(unicos) < len(obs_validados):
        logger.info(
            f"Dedup OB [{ativo}] (thr {dist_dedup:.0f} pts): "
            f"{len(obs_validados)} -> {len(unicos)}"
        )

    return unicos


# ============================================================
# LIQUIDEZ
# ============================================================
def detectar_liquidez(swings: List[Swing], config: ConfigSMC = CONFIG) -> Dict[str, List[float]]:
    tol = config.eq_tol_pontos
    bsl: List[float] = []
    ssl: List[float] = []

    highs = _so_highs(swings)
    lows = _so_lows(swings)

    # Equal highs (BSL)
    for i in range(len(highs)):
        for j in range(i + 1, len(highs)):
            if abs(highs[i].preco - highs[j].preco) <= tol:
                nivel = round((highs[i].preco + highs[j].preco) / 2, 1)
                if not any(abs(nivel - x) <= tol for x in bsl):
                    bsl.append(nivel)

    # Equal lows (SSL)
    for i in range(len(lows)):
        for j in range(i + 1, len(lows)):
            if abs(lows[i].preco - lows[j].preco) <= tol:
                nivel = round((lows[i].preco + lows[j].preco) / 2, 1)
                if not any(abs(nivel - x) <= tol for x in ssl):
                    ssl.append(nivel)

    # Swings marcados como *_EQ
    for s in highs:
        if s.tipo == "HIGH_EQ":
            nivel = round(s.preco, 1)
            if not any(abs(nivel - x) <= tol for x in bsl):
                bsl.append(nivel)

    for s in lows:
        if s.tipo == "LOW_EQ":
            nivel = round(s.preco, 1)
            if not any(abs(nivel - x) <= tol for x in ssl):
                ssl.append(nivel)

    bsl.sort(reverse=True)
    ssl.sort()
    return {"bsl": bsl[:6], "ssl": ssl[:6]}


# ============================================================
# ATR
# ============================================================
def _calcular_atr(candles: List[Candle], periodo: int = 20) -> float:
    """ATR aproximado (True Range médio)."""
    if len(candles) < 2:
        return 0.0
    n = min(periodo, len(candles) - 1)
    janela = candles[-n:]
    trs = []
    for i in range(1, len(janela)):
        c_atual = janela[i]
        c_ant = janela[i - 1]
        tr = max(
            c_atual.high - c_atual.low,
            abs(c_atual.high - c_ant.close),
            abs(c_atual.low - c_ant.close),
        )
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


# ============================================================
# CASCATA DE ENTRADA / STOP / ALVOS (com filtro de lado + ATR)
# ============================================================
def calcular_entrada_stop_alvos(
    bias: str,
    obs: List[OrderBlock],
    fvgs_abertos: List[FVG],
    liq: Dict[str, List[float]],
    preco_atual: float,
    candles: Optional[List[Candle]] = None,
    config: ConfigSMC = CONFIG,
) -> Tuple[Optional[float], Optional[float], List[float]]:
    """
    Cascata: OB → FVG → Preço atual.
    Alvos: liquidez BSL/SSL FILTRADA pelo lado correto + projeções measured move.
    Stop: aplica piso mínimo por ATR para evitar stops apertados em M5.
    """
    entrada: Optional[float] = None
    stop: Optional[float] = None
    alvos: List[float] = []

    # --- 1. ENTRADA (cascata OB → FVG → preço) ---
    if bias == "ALTA":
        ob = next((o for o in reversed(obs) if o.tipo == "COMPRA"), None)
        if ob:
            entrada = round(ob.high, 0)
        else:
            fvg = next((f for f in reversed(fvgs_abertos) if f.tipo == "COMPRA"), None)
            if fvg:
                entrada = round(fvg.superior, 0)
            else:
                entrada = round(preco_atual, 0)

    elif bias == "BAIXA":
        ob = next((o for o in reversed(obs) if o.tipo == "VENDA"), None)
        if ob:
            entrada = round(ob.low, 0)
        else:
            fvg = next((f for f in reversed(fvgs_abertos) if f.tipo == "VENDA"), None)
            if fvg:
                entrada = round(fvg.inferior, 0)
            else:
                entrada = round(preco_atual, 0)

    if entrada is None:
        return None, None, []

    # --- 2. STOP com piso por ATR ---
    atr = _calcular_atr(candles, config.stop_atr_period) if candles else 0.0
    stop_min = max(config.stop_min_dist, atr * config.stop_atr_mult)

    if bias == "ALTA":
        ob = next((o for o in reversed(obs) if o.tipo == "COMPRA"), None)
        if ob:
            stop_candidato = ob.low - 50
        else:
            fvg = next((f for f in reversed(fvgs_abertos) if f.tipo == "COMPRA"), None)
            stop_candidato = (fvg.inferior - 50) if fvg else (preco_atual - 100)

        if entrada - stop_candidato < stop_min:
            stop = round(entrada - stop_min, 0)
            logger.info(
                f"Stop ajustado por ATR: {stop_candidato:.0f} → {stop:.0f} "
                f"(ATR={atr:.0f}, min={stop_min:.0f})"
            )
        else:
            stop = round(stop_candidato, 0)

    elif bias == "BAIXA":
        ob = next((o for o in reversed(obs) if o.tipo == "VENDA"), None)
        if ob:
            stop_candidato = ob.high + 50
        else:
            fvg = next((f for f in reversed(fvgs_abertos) if f.tipo == "VENDA"), None)
            stop_candidato = (fvg.superior + 50) if fvg else (preco_atual + 100)

        if stop_candidato - entrada < stop_min:
            stop = round(entrada + stop_min, 0)
            logger.info(
                f"Stop ajustado por ATR: {stop_candidato:.0f} → {stop:.0f} "
                f"(ATR={atr:.0f}, min={stop_min:.0f})"
            )
        else:
            stop = round(stop_candidato, 0)

    # --- 3. ALVOS filtrados pelo lado correto ---
    if bias == "ALTA":
        if liq["bsl"]:
            alvos.extend([round(x, 0) for x in liq["bsl"][:3] if x > entrada])
    elif bias == "BAIXA":
        if liq["ssl"]:
            alvos.extend([round(x, 0) for x in liq["ssl"][:3] if x < entrada])

    # Projeções measured move
    dist = abs(entrada - stop)
    if dist > 0:
        if bias == "ALTA":
            alvos.append(round(entrada + dist, 0))
            alvos.append(round(entrada + dist * 1.618, 0))
        elif bias == "BAIXA":
            alvos.append(round(entrada - dist, 0))
            alvos.append(round(entrada - dist * 1.618, 0))

    # Deduplicação e ordenação
    alvos = sorted(set(alvos), key=lambda x: abs(x - entrada))

    # Sanity check final
    if bias == "ALTA":
        alvos = [a for a in alvos if a > entrada]
    elif bias == "BAIXA":
        alvos = [a for a in alvos if a < entrada]

    return entrada, stop, alvos[:4]


# ============================================================
# CONFIANÇA PONDERADA
# ============================================================
def calcular_confianca(
    bias: str,
    bos: bool,
    choch: bool,
    fvgs_abertos: List[FVG],
    obs: List[OrderBlock],
    ob_confluente: bool,
) -> int:
    """
    Calcula um SCORE TECNICO de presenca de criterios (0-100).

    IMPORTANTE: NAO e probabilidade de acerto.

    Mede a presenca dos 6 criterios tecnicos com pesos fixos:
        bias (25) + bos (20) + choch (10) + fvg (15) + ob (15) + ob_confluente (15)

    Um setup com 1 OB e 1 FVG pode legitimamente bater 100% se todos os
    criterios forem atendidos. Para setups com pouca estrutura, esse numero
    tende a superestimar a qualidade percebida.

    Interpretar como "score tecnico", nao como "confianca operacional".

    Ref: fix48 (2026-09-26) - semantica documentada apos caso M1 com 100%
    em setup de 2 OBs + 1 FVG.
    """
    pesos = {
        "bias": 25,
        "bos": 20,
        "choch": 10,
        "fvg": 15,
        "ob": 15,
        "ob_confluente": 15,
    }
    total_possivel = sum(pesos.values())

    score = 0
    if bias in ("ALTA", "BAIXA"):
        score += pesos["bias"]
    if bos:
        score += pesos["bos"]
    if choch:
        score += pesos["choch"]
    if fvgs_abertos:
        score += pesos["fvg"]
    if obs:
        score += pesos["ob"]
    if ob_confluente:
        score += pesos["ob_confluente"]

    return min(100, round((score / total_possivel) * 100))


# ============================================================
# ALERTA DE DIVERGÊNCIA MACRO × SMC
# ============================================================
def _checar_divergencia_macro(bias: str) -> Optional[str]:
    """Lê Metricas_Calculadas.json e retorna alerta se Macro × SMC brigarem."""
    try:
        if not METRICAS_FILE.exists():
            return None
        with open(METRICAS_FILE, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        ind_ext = metrics.get("indicadores_compostos", {}).get("indicador_mercado_externo")
        if ind_ext is None:
            return None

        if ind_ext < -2 and bias == "ALTA":
            return (
                f"⚠️ DIVERGÊNCIA: Macro em FORTE VENDA ({ind_ext:+.2f}%) "
                f"vs SMC em ALTA — possível armadilha de abertura"
            )
        if ind_ext > 2 and bias == "BAIXA":
            return (
                f"⚠️ DIVERGÊNCIA: Macro em FORTE COMPRA ({ind_ext:+.2f}%) "
                f"vs SMC em BAIXA — possível armadilha de abertura"
            )
    except Exception:
        return None
    return None


# ============================================================
# ANÁLISE PRINCIPAL
# ============================================================
def analisar_smc(
    dados_candles: Any,
    ativo: str = "WIN",
    timeframe: str = "5m",
    config: ConfigSMC = CONFIG,
) -> Dict[str, Any]:
    candles = normalizar_candles(dados_candles)

    # 1. Níveis institucionais
    inst_niveis = calcular_poc_vwap(candles, ativo, config)
    poc = inst_niveis["poc"]
    vwap = inst_niveis["vwap"]

    # 2. Lookback especifico por timeframe
    lookback_efetivo = config.lookback_map.get(timeframe, config.lookback)
    candles = aplicar_lookback(candles, lookback_efetivo)

    if len(candles) < 10:
        logger.warning(f"Candles insuficientes ({len(candles)}), abortando análise")
        return {
            "timestamp": datetime.now(BRT).isoformat(),
            "ativo": ativo,
            "timeframe": timeframe,
            "fonte": "regras_smc",
            "erro": "Candles insuficientes (mínimo 10)",
            "bias_direcional": "LATERAL",
            "direcao_estrutura": "LATERAL",
            "bos": False,
            "choch": False,
            "confianca_visual": 0,
        }

    # 3. Detecções
    swings = detectar_swings(candles, config)
    eventos, bias = detectar_bos_choch(candles, swings, config)
    fvgs = detectar_fvg(candles, config)
    obs = detectar_order_blocks(candles, swings, eventos, ativo, config)
    liq = detectar_liquidez(swings, config)

    # Fix43: BOS/CHoCH so contam se apontarem na direcao do bias.
    # Sem isso, um BOS contra-tendencia somava pontos indevidamente.
    _bias_dirs = {"ALTA", "BAIXA"}
    if bias in _bias_dirs:
        bos = any(e.tipo == "BOS" and e.direcao == bias for e in eventos[-3:])
        choch = any(e.tipo == "CHOCH" and e.direcao == bias for e in eventos[-3:])
    else:
        bos = any(e.tipo == "BOS" for e in eventos[-3:])
        choch = any(e.tipo == "CHOCH" for e in eventos[-3:])

    fvgs_abertos = [f for f in fvgs if not f.preenchido][-config.max_fvgs :]
    obs = obs[-config.max_obs :]

    preco_atual = candles[-1].close

    logger.info(
        f"[{ativo}] {len(candles)} candles | {len(swings)} swings | "
        f"{len(obs)} OBs | {len(fvgs_abertos)} FVGs abertos | bias={bias}"
    )

    # 4. Confluência OB ↔ POC
    ob_confluente = False
    if obs:
        ob_recente = obs[-1]
        distancia_poc = abs(ob_recente.preco_ref - poc)
        lim = config.ob_poc_dist_win if "WIN" in ativo.upper() else config.ob_poc_dist_wdo
        if distancia_poc <= lim:
            ob_confluente = True

    # 5. Estruturas textuais
    estruturas: List[str] = []
    for s in swings[-config.max_niveis :]:
        label = {
            "HIGH": "Swing High",
            "LOW": "Swing Low",
            "HIGH_EQ": "Equal High (BSL)",
            "LOW_EQ": "Equal Low (SSL)",
        }.get(s.tipo, "Swing")
        estruturas.append(f"{s.preco:.0f}: {label}")

    for ob in obs:
        estruturas.append(
            f"{ob.preco_ref:.0f}: OB {ob.tipo} ({ob.low:.0f}-{ob.high:.0f}) [{ob.validado_por}]"
        )

    for fvg in fvgs_abertos:
        estruturas.append(
            f"{(fvg.superior + fvg.inferior) / 2:.0f}: FVG {fvg.tipo} ({fvg.inferior:.0f}-{fvg.superior:.0f})"
        )

    # 6. Liquidez textual
    liquidez_txt: List[str] = [
        f"POC Institucional (Ontem): {poc:.0f}",
        f"VWAP (Ontem): {vwap:.0f}",
    ]
    for p in liq["bsl"]:
        liquidez_txt.append(f"BSL: {p:.0f} (equal highs / liquidez acima)")
    for p in liq["ssl"]:
        liquidez_txt.append(f"SSL: {p:.0f} (equal lows / liquidez abaixo)")

    # 7. Cenários
    cenarios: List[str] = []
    if bias == "BAIXA":
        res = next((o for o in reversed(obs) if o.tipo == "VENDA"), None)
        fvg_v = next((f for f in reversed(fvgs_abertos) if f.tipo == "VENDA"), None)
        zona = res.preco_ref if res else (fvg_v.superior if fvg_v else preco_atual)
        alvo = liq["ssl"][0] if liq["ssl"] else preco_atual * 0.99
        cenarios.append(
            f"Cenário Vendedor: rejeição em {zona:.0f} (OB/FVG validado por volume) visando {alvo:.0f}."
        )
    elif bias == "ALTA":
        dem = next((o for o in reversed(obs) if o.tipo == "COMPRA"), None)
        fvg_c = next((f for f in reversed(fvgs_abertos) if f.tipo == "COMPRA"), None)
        zona = dem.preco_ref if dem else (fvg_c.inferior if fvg_c else preco_atual)
        alvo = liq["bsl"][0] if liq["bsl"] else preco_atual * 1.01
        cenarios.append(
            f"Cenário Comprador: defesa em {zona:.0f} (OB/FVG validado por volume) visando {alvo:.0f}."
        )
    else:
        cenarios.append("Cenário Lateral: aguardar BOS com fechamento fora da faixa recente.")

    # 8. Alerta de divergência Macro × SMC
    alerta = _checar_divergencia_macro(bias)
    if alerta:
        logger.warning(alerta)
        cenarios.append(alerta)

    # 9. Confiança
    # Nota (fix48): confianca_visual e score de PRESENCA de criterios,
    # nao probabilidade de acerto. Pode bater 100% em setups com pouca
    # estrutura (1 OB, 1 FVG). Ver docstring de calcular_confianca.
    conf = calcular_confianca(bias, bos, choch, fvgs_abertos, obs, ob_confluente)

    # 10. Entrada / Stop / Alvos
    entrada, stop, alvos = calcular_entrada_stop_alvos(
        bias, obs, fvgs_abertos, liq, preco_atual, candles=candles, config=config
    )

    return {
        "timestamp": datetime.now(BRT).isoformat(),
        "ativo": ativo,
        "timeframe": timeframe,
        "fonte": "regras_smc",
        "preco_atual": preco_atual,
        "timeframes_identificados": timeframe,
        "bias_direcional": bias,
        "direcao_estrutura": bias,
        "bos": bos,
        "choch": choch,
        "confianca_visual": conf,
        "niveis_institucionais": {
            "poc_ontem": poc,
            "vwap_ontem": vwap,
            "ob_alinhado_com_poc": ob_confluente,
        },
        "order_blocks": [
            {
                "tipo": o.tipo,
                "preco": o.preco_ref,
                "high": o.high,
                "low": o.low,
                "validado_por": o.validado_por,
            }
            for o in obs
        ],
        "fair_value_gaps": [
            {
                "tipo": f.tipo,
                "superior": f.superior,
                "inferior": f.inferior,
                "preenchido": f.preenchido,
            }
            for f in fvgs_abertos
        ],
        "liquidez": liq,
        "eventos_estrutura": [
            {"tipo": e.tipo, "direcao": e.direcao, "preco": e.preco, "time": e.time}
            for e in eventos[-6:]
        ],
        "swings_recentes": [
            {"tipo": s.tipo, "preco": s.preco, "time": s.time} for s in swings[-10:]
        ],
        "estruturas_coletadas": estruturas[-config.max_niveis :],
        "liquidez_relevante": liquidez_txt,
        "zonas_de_interesse_e_cenarios": cenarios,
        "entrada_sugerida": entrada,
        "stop_sugerido": stop,
        "alvos": alvos,
        "metadados": {
            "n_candles": len(candles),
            "n_swings": len(swings),
            "n_fvgs_abertos": len(fvgs_abertos),
            "n_obs": len(obs),
            "filtro_volume_real_aplicado": True,
            "versao_motor": "2.1",
            "config": asdict(config),
            # Fix43: breakdown dos 6 criterios de confianca
            "_debug_confianca": {
                "bias_ativo": bias in ("ALTA", "BAIXA"),
                "bos_ativo": bos,
                "choch_ativo": choch,
                "fvg_ativo": bool(fvgs_abertos),
                "ob_ativo": bool(obs),
                "ob_confluente_ativo": ob_confluente,
                "total_eventos": len(eventos),
                "ultimos_3_eventos": [
                    {"tipo": e.tipo, "direcao": e.direcao, "time": e.time}
                    for e in eventos[-3:]
                ],
            },
        },
    }


# ============================================================
# SALVAMENTO (com histórico opcional)
# ============================================================
def salvar_resultado(
    resultado: Dict[str, Any], caminho: Optional[Path] = None, guardar_historico: bool = False
) -> Path:
    caminho = caminho or ARQUIVO_SAIDA
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    if guardar_historico:
        try:
            HISTORICO_SMC_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(BRT).strftime("%Y%m%d_%H%M%S")
            hist = HISTORICO_SMC_DIR / f"SMC_{ts}.json"
            with open(hist, "w", encoding="utf-8") as f:
                json.dump(resultado, f, indent=2, ensure_ascii=False)
            logger.info(f"Histórico salvo em {hist}")
        except Exception as e:
            logger.warning(f"Falha ao salvar histórico: {e}")

    return caminho


# ============================================================
# MT5 — CARREGAMENTO
# ============================================================
def _candidatos_simbolo(symbol: str) -> List[str]:
    s = (symbol or "").strip().upper()
    candidatos: List[str] = []

    def add(x: str):
        if x and x not in candidatos:
            candidatos.append(x)

    add(symbol)
    add(s)

    if s.startswith("WIN") or s in ("", "WIN", "WIN$"):
        for c in ("WIN$", "WIN$N", "WIN@N", "WIN", "WINc"):
            add(c)
        meses = "FGHJKMNQUVXZ"
        ano = datetime.now().year % 100
        for m in meses:
            add(f"WIN{m}{ano:02d}")
            add(f"WIN{m}{ano + 1:02d}")

    if FILE_MT5_DADOS.exists():
        try:
            with open(FILE_MT5_DADOS, "r", encoding="utf-8") as f:
                data = json.load(f)
            contratos = data.get("contratos", {})
            if isinstance(contratos, dict):
                for nome in contratos.keys():
                    add(str(nome))
        except Exception:
            pass

    return candidatos


def carregar_mt5(
    symbol: str = "WIN$",
    timeframe_min: int = 5,
    qtd: int = 300,
    validar_pregao: bool = False,
) -> Tuple[List[Dict[str, Any]], str]:
    try:
        import MetaTrader5 as mt5
    except ImportError as e:
        raise RuntimeError("MetaTrader5 não instalado.") from e

    if validar_pregao:
        try:
            from config import esta_no_pregao

            if not esta_no_pregao():
                logger.warning("Fora do pregão — coleta pode trazer dados parciais")
        except ImportError:
            pass

    if not mt5.initialize():
        raise RuntimeError(f"Falha ao inicializar MT5: {mt5.last_error()}")

    tf_map = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15}
    tf = tf_map.get(timeframe_min, mt5.TIMEFRAME_M5)

    candidatos = _candidatos_simbolo(symbol)
    rates, simbolo_ok = None, None

    for sym in candidatos:
        info = mt5.symbol_info(sym)
        if info is None:
            continue
        if not info.visible:
            mt5.symbol_select(sym, True)

        r = mt5.copy_rates_from_pos(sym, tf, 0, qtd)
        if r is not None and len(r) > 0:
            rates = r
            simbolo_ok = sym
            logger.info(f"Símbolo MT5 selecionado: {sym}")
            break

    if rates is None or simbolo_ok is None:
        mt5.shutdown()
        raise RuntimeError(f"Sem dados no MT5 para o símbolo informado: {symbol}")

    out = []
    for r in rates:
        v_real = 0.0
        try:
            if "real_volume" in r.dtype.names:
                v_real = float(r["real_volume"])
        except Exception:
            pass

        if v_real <= 0:
            try:
                if "tick_volume" in r.dtype.names:
                    v_real = float(r["tick_volume"])
            except Exception:
                pass

        # MT5 retorna UTC — converte para BRT
        dt_brt = datetime.fromtimestamp(r["time"], tz=timezone.utc).replace(tzinfo=BRT)

        out.append(
            {
                "time": dt_brt.isoformat(),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": v_real,
            }
        )

    mt5.shutdown()
    return out, simbolo_ok


# ============================================================
# CLI — execução isolada
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Motor SMC/ICT — análise de candles")
    parser.add_argument("--ativo", default="WIN$", help="Símbolo MT5 (ex: WIN$, WDO$)")
    parser.add_argument("--tf", type=int, default=5, help="Timeframe em minutos (1, 5, 15)")
    parser.add_argument("--qtd", type=int, default=300, help="Quantidade de candles")
    parser.add_argument("--historico", action="store_true", help="Salva cópia em Historico_SMC/")
    parser.add_argument("--validar-pregao", action="store_true", help="Só roda se estiver no pregão")
    args = parser.parse_args()

    logger.info(f"Iniciando análise SMC — ativo={args.ativo} tf={args.tf}m qtd={args.qtd}")

    try:
        candles, simbolo_ok = carregar_mt5(args.ativo, args.tf, args.qtd, args.validar_pregao)
    except Exception as e:
        logger.error(f"Falha na coleta MT5: {e}")
        sys.exit(1)

    resultado = analisar_smc(candles, ativo=simbolo_ok or args.ativo, timeframe=f"{args.tf}m")
    caminho = salvar_resultado(resultado, guardar_historico=args.historico)

    logger.info(f"✅ Resultado salvo em {caminho}")
    print(f"\n📊 Resultado:")
    print(f"   Bias:      {resultado['bias_direcional']}")
    print(f"   Confiança: {resultado['confianca_visual']}%")
    print(f"   Preço:     {resultado['preco_atual']:.0f}")
    print(f"   POC ontem: {resultado['niveis_institucionais']['poc_ontem']:.0f}")
    print(f"   VWAP onte: {resultado['niveis_institucionais']['vwap_ontem']:.0f}")
    if resultado.get("entrada_sugerida"):
        print(f"   Entrada:   {resultado['entrada_sugerida']:.0f}")
        print(f"   Stop:      {resultado['stop_sugerido']:.0f}")
        print(f"   Alvos:     {resultado['alvos']}")


if __name__ == "__main__":
    main()
```

### `README.md`

```markdown
# Analisador Financeiro

Sistema de analise financeira institucional para WIN/WDO na B3.

## Requisitos

- Python 3.14+
- MetaTrader 5 (Genial Investimentos)
- Tesseract OCR (sniper de leilao)

## Instalacao

    pip install -r requirements.txt

### Dependencias extras por feature

- streamlit-autorefresh - Pagina 7.1_SMC_Regras (auto-refresh 5min)
  Instalar: pip install streamlit-autorefresh

## Comandos principais

    python main_pipeline.py           # Pipeline completo
    python Agendador.py               # Agendador (5min em :04, :09...)
    streamlit run Home.py             # Dashboard Streamlit

    python Rodar_SMC_Regras.py        # SMC multi-TF manual (M1/M5/M15)
    python gerar_snapshot_mtf_ia.py   # Snapshot para colar em IA
    python win_abertura_sniper.py     # Sniper de leilao (08:50-09:05)
    python analisar_rompimento_10h.py # Snapshot ORB (10:00-10:15)

## Estrutura

    Coletas/                     # JSONs runtime
      cache/                     # Cache incremental de candles
      Historico_Aberturas/       # Sessoes gravadas
    v2/                          # Orquestrador V2
      core/engines/              # v2_orchestrator, decision_engine
    pages/                       # Streamlit pages
    Motor_SMC_Regras.py          # Motor SMC/ICT
    main_pipeline.py             # Orquestrador do pipeline
    config.py                    # Configuracao central

## Arquitetura

- Coleta: Coletor.py + Coletor_MT5_v2_2.py (brapi, Finnhub, TV, MT5)
- Validacao: Validador.py (sanitiza 34 ativos)
- Analise SMC: Motor_SMC_Regras.py (POC, VWAP, OB, FVG, liquidez)
- Estimativa: CalculadoraEstimativaAbertura.py
- Decisao: v2/core/engines/v2_orchestrator.py (SMC x NOVO_MOTOR + MTF)

## Notas

Para anotacoes pessoais de trabalho, crie um NOTAS.md local
(nao versionado - esta no .gitignore).

```

### `Rodar_SMC_Regras.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rodar_SMC_Regras.py -- v3 (multi-timeframe)

Roda a analise SMC em 3 timeframes (M1, M5, M15) numa unica conexao MT5.

Saidas:
    Coletas/AnaliseGraficaSMC_Regras.json      -> M5 (compatibilidade)
    Coletas/AnaliseGraficaSMC_Regras_M1.json   -> micro
    Coletas/AnaliseGraficaSMC_Regras_M15.json  -> macro
    Coletas/AnaliseGraficaSMC_MTF.json         -> consolidacao

Fluxo:
    1. mt5.initialize() (uma vez)
    2. Para cada TF: copy_rates_from_pos -> analisar_smc -> salvar
    3. Consolida biases num veredito MTF
    4. mt5.shutdown()
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

try:
    from Motor_SMC_Regras import (
        analisar_smc, salvar_resultado, CONFIG,
        BRT, _candidatos_simbolo,
    )
except ImportError as e:
    print(f"[ERRO] Import Motor_SMC_Regras: {e}")
    sys.exit(1)

from cache_candles import obter_candles_multi_tf

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


# ---------------------------------------------------------------------------
# CONFIG MTF
# ---------------------------------------------------------------------------
ATIVO = "WIN$"

# timeframe_label -> (mt5_min, qtd_pedir, arquivo_saida)
TIMEFRAMES: Dict[str, Dict[str, Any]] = {
    "15m": {"min": 15, "qtd": 300, "arquivo": "AnaliseGraficaSMC_Regras_M15.json"},
    "5m":  {"min": 5,  "qtd": 300, "arquivo": "AnaliseGraficaSMC_Regras.json"},
    "1m":  {"min": 1,  "qtd": 600, "arquivo": "AnaliseGraficaSMC_Regras_M1.json"},
}

ARQUIVO_MTF = BASE_DIR / "Coletas" / "AnaliseGraficaSMC_MTF.json"


# ---------------------------------------------------------------------------
# COLETA MT5 (uma conexao, N TFs)
# ---------------------------------------------------------------------------
def carregar_multi_mt5(symbol: str, tf_spec: Dict[str, Dict[str, Any]]) -> Dict[str, Tuple[List[Dict[str, Any]], str]]:
    """Abre MT5 uma vez, puxa rates de cada TF, fecha. Retorna {tf_label: (candles, simbolo_real)}."""
    try:
        import MetaTrader5 as mt5
    except ImportError as e:
        raise RuntimeError("MetaTrader5 nao instalado.") from e

    if not mt5.initialize():
        raise RuntimeError(f"Falha ao inicializar MT5: {mt5.last_error()}")

    tf_map = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15}

    try:
        candidatos = _candidatos_simbolo(symbol)
        simbolo_ok = None
        for sym in candidatos:
            info = mt5.symbol_info(sym)
            if info is None:
                continue
            if not info.visible:
                mt5.symbol_select(sym, True)
            # Testa com M5 (ou o primeiro TF) para validar simbolo
            r = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 5)
            if r is not None and len(r) > 0:
                simbolo_ok = sym
                break

        if simbolo_ok is None:
            raise RuntimeError(f"Sem dados MT5 para simbolo: {symbol}")

        print(f"   [OK] Simbolo MT5: {simbolo_ok}")

        resultados: Dict[str, Tuple[List[Dict[str, Any]], str]] = {}
        for tf_label, spec in tf_spec.items():
            tf = tf_map.get(spec["min"], mt5.TIMEFRAME_M5)
            rates = mt5.copy_rates_from_pos(simbolo_ok, tf, 0, spec["qtd"])
            if rates is None or len(rates) == 0:
                print(f"   [AVISO] {tf_label}: sem rates")
                resultados[tf_label] = ([], simbolo_ok)
                continue

            candles = []
            for r in rates:
                v_real = 0.0
                try:
                    if "real_volume" in r.dtype.names:
                        v_real = float(r["real_volume"])
                except Exception:
                    pass
                if v_real <= 0:
                    try:
                        if "tick_volume" in r.dtype.names:
                            v_real = float(r["tick_volume"])
                    except Exception:
                        pass

                from datetime import timezone
                dt_brt = datetime.fromtimestamp(r["time"], tz=timezone.utc).replace(tzinfo=BRT)
                candles.append({
                    "time": dt_brt.isoformat(),
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": v_real,
                })

            print(f"   [OK] {tf_label}: {len(candles)} candles")
            resultados[tf_label] = (candles, simbolo_ok)

        return resultados
    finally:
        mt5.shutdown()


# ---------------------------------------------------------------------------
# CONFLUENCIA MTF
# ---------------------------------------------------------------------------
def _direcao(bias: str) -> str:
    if bias in ("ALTA", "BAIXA"):
        return bias
    return "LATERAL"


def calcular_confluencia_mtf(
    r15: Dict[str, Any], r5: Dict[str, Any], r1: Dict[str, Any]
) -> Dict[str, Any]:
    # Detecta quais TFs realmente retornaram dados (fix36)
    tfs_presentes = []
    if r15 and r15.get("bias_direcional"):
        tfs_presentes.append("15m")
    if r5 and r5.get("bias_direcional"):
        tfs_presentes.append("5m")
    if r1 and r1.get("bias_direcional"):
        tfs_presentes.append("1m")
    n_tfs = len(tfs_presentes)
    parcial = n_tfs < 3

    b15 = _direcao(r15.get("bias_direcional", "LATERAL")) if r15 else "LATERAL"
    b5 = _direcao(r5.get("bias_direcional", "LATERAL")) if r5 else "LATERAL"
    b1 = _direcao(r1.get("bias_direcional", "LATERAL")) if r1 else "LATERAL"

    c15 = int(r15.get("confianca_visual", 0) or 0) if r15 else 0
    c5 = int(r5.get("confianca_visual", 0) or 0) if r5 else 0
    c1 = int(r1.get("confianca_visual", 0) or 0) if r1 else 0

    direcoes = [b for b in (b15, b5, b1) if b in ("ALTA", "BAIXA")]
    n_dir = len(direcoes)

    if n_tfs == 0:
        veredito, alinhamento, racional = (
            "NEUTRO", "SEM_TFS",
            "Nenhum timeframe retornou dados.",
        )
    elif n_dir == 0:
        veredito, alinhamento, racional = (
            "NEUTRO", "SEM_DIRECAO",
            f"Nenhum dos {n_tfs} TFs marcou direcao clara.",
        )
    elif len(set(direcoes)) == 1 and n_dir == n_tfs and n_tfs >= 2:
        veredito, alinhamento, racional = (
            "ALINHADO_FORTE", f"{n_dir}/{n_tfs}",
            f"{', '.join(tfs_presentes)} em {direcoes[0]} — sinal forte"
            + (" (parcial)" if parcial else "") + ".",
        )
    elif n_tfs < 3:
        # Parcial: sem todas as pernas. Alinhamento passa a refletir
        # se as direcoes disponiveis concordam ou divergem (fix37c).
        _dirs_unicas = set(direcoes)
        if len(_dirs_unicas) >= 2:
            _alinh = "PARCIAL_DIVERGENTE"
        elif len(_dirs_unicas) == 1:
            _alinh = "PARCIAL_ALINHADO"
        else:
            _alinh = "PARCIAL_INDEFINIDO"
        veredito, alinhamento, racional = (
            "PARCIAL", _alinh,
            f"Parcial: apenas {', '.join(tfs_presentes)} disponiveis. "
            f"Direcao = {direcoes[0] if direcoes else 'NEUTRO'}.",
        )
    elif b15 == b5 and b5 != b1 and b1 in ("ALTA", "BAIXA"):
        veredito, alinhamento, racional = (
            "PULLBACK", "MACRO_MEDIO",
            f"Macro+Médio em {b15}; micro contra ({b1}). Aguardar pullback no M1.",
        )
    elif b15 != b5 and b5 == b1 and b5 in ("ALTA", "BAIXA"):
        # Opcao C: micro+medio contra macro.
        # Se a soma das confiancas do micro+medio supera o macro por um
        # fator (1.8), considera possivel reversao em curso.
        soma_micro_medio = c5 + c1
        limiar_reversao = c15 * 1.8
        if soma_micro_medio >= limiar_reversao:
            veredito, alinhamento, racional = (
                "REVERSAO_MICRO_MEDIO", "MICRO_MEDIO_CONTRA_MACRO",
                f"Micro ({b1}, {c1}%) e medio ({b5}, {c5}%) contra macro "
                f"{b15} ({c15}%). Possivel reversao em curso.",
            )
        else:
            veredito, alinhamento, racional = (
                "CONFLITO_MACRO", "MICRO_ALINHADO_CONTRA_MACRO",
                f"Micro e médio em {b5}, macro em {b15}. Nao operar contra M15.",
            )
    else:
        veredito, alinhamento, racional = (
            "DIVERGENTE", "SEM_CONFLUENCIA",
            f"Biases: M15={b15}, M5={b5}, M1={b1}. Sem confluencia.",
        )

    pesos = {"15m": 2.0, "5m": 1.5, "1m": 1.0}
    conf_pond = (
        c15 * pesos["15m"] + c5 * pesos["5m"] + c1 * pesos["1m"]
    ) / sum(pesos.values())

    if veredito == "REVERSAO_MICRO_MEDIO":
        direcao_dom = b5  # micro+medio mandam no cenario de reversao
    elif b15 in ("ALTA", "BAIXA"):
        direcao_dom = b15
    elif b5 in ("ALTA", "BAIXA"):
        direcao_dom = b5
    else:
        direcao_dom = b1

    # Campos auxiliares (apenas para debug/auditoria)
    try:
        soma_micro_medio_dbg = c5 + c1
        limiar_reversao_dbg = round(c15 * 1.8, 1)
    except NameError:
        soma_micro_medio_dbg = None
        limiar_reversao_dbg = None

    return {
        "bias_m15": b15,
        "bias_m5": b5,
        "bias_m1": b1,
        "confianca_m15": c15,
        "confianca_m5": c5,
        "confianca_m1": c1,
        "confianca_micro_medio_soma": soma_micro_medio_dbg,
        "limiar_reversao": limiar_reversao_dbg,
        "veredito_mtf": veredito,
        "alinhamento": alinhamento,
        "direcao_dominante": direcao_dom,
        "confianca_ponderada": round(conf_pond, 1),
        "racional": racional,
        "timeframes_disponiveis": tfs_presentes,
        "n_tfs_disponiveis": n_tfs,
        "parcial": parcial,
        "direcoes_concordam": (len(set(direcoes)) == 1) if len(direcoes) >= 2 else None,
    }


def _resumo_tf(r: Dict[str, Any]) -> Dict[str, Any]:
    niveis = r.get("niveis_institucionais") or {}
    return {
        "bias": r.get("bias_direcional"),
        "confianca": r.get("confianca_visual"),
        "preco_atual": r.get("preco_atual"),
        "poc_ontem": niveis.get("poc_ontem"),
        "vwap_ontem": niveis.get("vwap_ontem"),
        "ob_alinhado_com_poc": niveis.get("ob_alinhado_com_poc"),
        "n_obs": len(r.get("order_blocks") or []),
        "n_fvgs": len(r.get("fair_value_gaps") or []),
        "entrada": r.get("entrada_sugerida"),
        "stop": r.get("stop_sugerido"),
        "alvos": r.get("alvos") or [],
    }


# ---------------------------------------------------------------------------
# EXECUCAO
# ---------------------------------------------------------------------------
def _salvar_mtf(resultados: Dict[str, Dict[str, Any]], ativo_real: str) -> Path:
    confluencia = calcular_confluencia_mtf(
        resultados.get("15m", {}),
        resultados.get("5m", {}),
        resultados.get("1m", {}),
    )

    preco_atual = (
        resultados.get("1m", {}).get("preco_atual")
        or resultados.get("5m", {}).get("preco_atual")
        or resultados.get("15m", {}).get("preco_atual")
    )

    payload = {
        "timestamp": datetime.now(BRT).isoformat(),
        "ativo": ativo_real,
        "preco_atual": preco_atual,
        "timeframes": {
            "15m": _resumo_tf(resultados.get("15m", {})),
            "5m":  _resumo_tf(resultados.get("5m", {})),
            "1m":  _resumo_tf(resultados.get("1m", {})),
        },
        "confluencia": confluencia,
    }

    ARQUIVO_MTF.parent.mkdir(parents=True, exist_ok=True)
    with open(ARQUIVO_MTF, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return ARQUIVO_MTF


def executar() -> int:
    print("=" * 62)
    print(" SMC Multi-Timeframe (M1 / M5 / M15)")
    print("=" * 62)

    try:
        print(f"-> Coletando {ATIVO} em 3 TFs numa conexao MT5...")
        # fix41: usa cache incremental em vez de pull de 300 velas do MT5
        tf_qtd = {
            1:  TIMEFRAMES["1m"]["qtd"],
            5:  TIMEFRAMES["5m"]["qtd"],
            15: TIMEFRAMES["15m"]["qtd"],
        }
        mapa_labels = {1: "1m", 5: "5m", 15: "15m"}

        coletas_por_tf = obter_candles_multi_tf(ATIVO, tf_qtd)

        coletas = {}
        for tf_min, (candles, contrato) in coletas_por_tf.items():
            coletas[mapa_labels[tf_min]] = (candles, contrato)
    except Exception as e:
        print(f"[ERRO] Coleta MT5: {e}")
        return 1

    resultados: Dict[str, Dict[str, Any]] = {}
    for tf_label, spec in TIMEFRAMES.items():
        candles, simbolo_real = coletas.get(tf_label, ([], ""))
        if not candles:
            print(f"[AVISO] {tf_label}: sem candles, pulando.")
            continue

        resultado = analisar_smc(
            dados_candles=candles,
            ativo=simbolo_real or ATIVO,
            timeframe=tf_label,
            config=CONFIG,
        )
        resultados[tf_label] = resultado

        # Salva arquivo por TF
        arquivo = BASE_DIR / "Coletas" / spec["arquivo"]
        salvar_resultado(resultado, caminho=arquivo)
        print(
            f"   [OK] {tf_label}: bias={resultado.get('bias_direcional')} "
            f"conf={resultado.get('confianca_visual')}% -> {arquivo.name}"
        )

    if not resultados:
        print("[ERRO] Nenhum TF processado.")
        return 1

    # Consolida MTF
    ativo_real = (coletas.get("5m") or ("", ""))[1] or ATIVO
    caminho_mtf = _salvar_mtf(resultados, ativo_real)
    print(f"   [OK] MTF -> {caminho_mtf.name}")

    # Resumo
    print("\n" + "-" * 62)
    print(" RESUMO MTF")
    print("-" * 62)
    confluencia = calcular_confluencia_mtf(
        resultados.get("15m", {}),
        resultados.get("5m", {}),
        resultados.get("1m", {}),
    )
    for k in ("bias_m15", "bias_m5", "bias_m1", "veredito_mtf",
              "alinhamento", "direcao_dominante", "confianca_ponderada"):
        print(f"  {k:22s}: {confluencia[k]}")
    print(f"  racional              : {confluencia['racional']}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(executar())

```

### `Temp_Validacao_Smoke.py`

```python
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

```

### `Validador.py`

```python
# ============================================================
# ARQUIVO: Validador.py
# DATA: 30/07/2026 | Atualizado 18/09/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Fase 3 - Validação, sanitização e padronização dos
#         34 ativos (com WIN e WDO Ajustes separados).
# DESCRICAO:
#   Processa o arquivo JSON bruto oriundo da fase de coleta,
#   aplica regras de negócio para consistência de dados,
#   padroniza os identificadores dos ativos (tickers) e
#   gera um arquivo JSON estruturado para consumo posterior.
#
# ATUALIZAÇÃO 18/09/2026 (refactor):
#   - Remove dict MAPEAMENTO_TICKERS local (era cópia do config.py).
#     Isso causava inconsistência: adicionar um ticker no config não
#     refletia no Validador (ex: B3_FECHAMENTO_WIN ficava com chave
#     bruta no Dados_Validados.json).
#   - Import único de MAPEAMENTO_TICKERS, COLETAS_DIR, FILE_ROM0,
#     FILE_VALIDADOS a partir de config.py (fonte única de verdade).
#   - Path em vez de os.path (consistência com o resto da V2).
#   - Preserva campos extras (var_abs, fechamento_real, preco_medio)
#     quando disponíveis — úteis para auditoria de ajuste brapi.
# ============================================================

from __future__ import annotations

import json
from datetime import datetime

from config import (
    COLETAS_DIR,
    FILE_ROM0,
    FILE_VALIDADOS,
    MAPEAMENTO_TICKERS,
)

# ------------------------------------------------------------
# CAMINHOS
# ------------------------------------------------------------
FILE_INPUT = FILE_ROM0
FILE_OUTPUT = FILE_VALIDADOS


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def _to_float_safe(valor, default=None):
    """Converte para float, preservando None quando inválido."""
    if valor is None:
        return default
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


# ------------------------------------------------------------
# VALIDAÇÃO
# ------------------------------------------------------------
def validar_item(item: dict):
    """
    Executa regras estritas de validação, integridade e sanitização em um item.

    Parâmetros:
        item (dict): Registro individual extraído da lista de coletas.

    Retorno:
        tuple (bool, str, dict):
            - bool: True se o item for válido, False caso contrário.
            - str: Mensagem descritiva do resultado da auditoria.
            - dict: Dicionário sanitizado se aprovado, None se rejeitado.
    """
    ativo_raw = item.get("ativo")
    status_fonte = item.get("status")
    dados = item.get("dados_reais")

    # 1. Validação do Status da Coleta e Estrutura dos Dados
    if status_fonte != "OK" or not dados:
        return False, f"Status de coleta inválido: {status_fonte}", None

    close = dados.get("close")

    # 2. Validação do Preço/Taxa de Fechamento (obrigatório, numérico e estritamente positivo)
    if close is None or not isinstance(close, (int, float)) or close <= 0:
        return False, f"Preço/Taxa de fechamento inválido ou zerado: {close}", None

    # 3. Mapeamento para Identificador Padrão Interno
    nome_padronizado = MAPEAMENTO_TICKERS.get(ativo_raw, ativo_raw)

    # 4. Sanitização e Normalização dos Tipos de Dados
    dados_sanitizados = {
        "ativo_id": nome_padronizado,
        "ticker_original": ativo_raw,
        "fonte": item.get("fonte"),
        "timestamp_coleta": item.get("timestamp"),
        "close": float(close),

        # Fechamento do dia anterior (vem como "fechamento_anterior" da coleta)
        "previous_close": _to_float_safe(dados.get("fechamento_anterior")),

        "open": _to_float_safe(dados.get("open")),
        "high": _to_float_safe(dados.get("high")),
        "low": _to_float_safe(dados.get("low")),
        "change_percent": _to_float_safe(dados.get("change_percent")),
        "volume": _to_float_safe(dados.get("volume")),
    }

    # 5. Campos opcionais extras (só inclui se existirem — mantém payload enxuto)
    for chave_extra in ("var_abs", "fechamento_real", "preco_medio"):
        if chave_extra in dados and dados[chave_extra] is not None:
            dados_sanitizados[chave_extra] = _to_float_safe(dados[chave_extra])

    return True, "Aprovado", dados_sanitizados


# ------------------------------------------------------------
# ORQUESTRAÇÃO
# ------------------------------------------------------------
def executar_validacao() -> bool:
    """
    Orquestra o processo de validação do arquivo de coleta.

    Passos:
        1. Carrega o arquivo JSON bruto de entrada.
        2. Itera sobre cada ativo aplicando as regras de auditoria.
        3. Exibe o log em tempo real no console formatado em colunas.
        4. Consolida e grava os ativos aprovados e o relatório de rejeições na saída.

    Retorna True se todos os itens foram aprovados.
    """
    if not FILE_INPUT.exists():
        print(f"[ERRO] Arquivo de entrada não encontrado: {FILE_INPUT}")
        return False

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Lendo {FILE_INPUT.name}...")

    with open(FILE_INPUT, "r", encoding="utf-8") as f:
        coleta = json.load(f)

    itens = coleta.get("coletas", [])
    aprovados = []
    rejeitados = []

    # Cabeçalho da Tabela de Auditoria no Terminal
    print(f"\n{'ATIVO ORIGINAL':<22} | {'ID PADRÃO':<22} | {'PREÇO/TAXA':<10} | {'STATUS AUDITORIA'}")
    print("-" * 90)

    for item in itens:
        valido, motivo, dados_limpos = validar_item(item)
        ativo_raw = item.get("ativo", "UNKNOWN")
        id_padrao = MAPEAMENTO_TICKERS.get(ativo_raw, ativo_raw)

        if valido:
            aprovados.append(dados_limpos)
            print(f"{ativo_raw:<22} | {id_padrao:<22} | {dados_limpos['close']:<10.4f} | [OK] {motivo}")
        else:
            rejeitados.append({"ativo": ativo_raw, "motivo": motivo})
            print(f"{ativo_raw:<22} | {id_padrao:<22} | {'N/A':<10} | [REJEITADO] {motivo}")

    print("-" * 90)

    saida = {
        "metadata_validacao": {
            "timestamp_validacao": datetime.now().isoformat(),
            "arquivo_origem": FILE_INPUT.name,
            "total_recebidos": len(itens),
            "total_aprovados": len(aprovados),
            "total_rejeitados": len(rejeitados),
        },
        "ativos_validados": aprovados,
        "relatorio_rejeicoes": rejeitados,
    }

    with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(saida, f, indent=2, ensure_ascii=False)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Validação concluída!")
    print(f"Aprovados: {len(aprovados)}/{len(itens)} | Arquivo gerado: {FILE_OUTPUT.name}\n")
    return len(rejeitados) == 0


# ------------------------------------------------------------
# PONTO DE ENTRADA
# ------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print(" FASE 3: ENGINE DE VALIDAÇÃO E SANITIZAÇÃO DE DADOS (34 ATIVOS)")
    print("=" * 60)
    executar_validacao()
```

### `abertura 25set.txt`

```text
=== 🕒 09:02:04 | PREVISÃO DE ABERTURA === [MUDANCA_LEILAO]
💰 PREÇO TEÓRICO : 185000 (Conf: 0.95)
📊 GAP DO AJUSTE : -54 pts [ABAIXO]
📉 GAP DO FECHTO : +20 pts [ACIMA]
🏢 DISTÂNCIA POC : -1940 pts [ABAIXO]
🌊 MICROFLUXO    : ALTA (Força/Aceleração: +8.5)
----------------------------------------
🎯 VEREDITO      : ⚠️ ALERTA DE FINTA (Fluxo divergente do Macro)
========================================
🎪 Modo LEILÃO ativo — filtro de salto relaxado
📊 Stats: 903 tent | 903 OK | 0 falhas OCR | 0 rejeitadas filtro | 95 mudança | 14 tempo
[09:02:05] ⬛ [LEILAO] Barra azul ausente — OCR PAUSADO
[09:16:40] Fora do leilao (sem fundo azul)

Finalizado! Dados armazenados em Coletas/
============================================================
 📊 ESTATÍSTICAS FINAIS
============================================================
  Tentativas totais       : 904
  Leituras OK (aceitas)   : 904
  Leituras com falha OCR  : 0
  Rejeitadas pelo filtro  : 0
      ├─ fora faixa abs.  : 0
      └─ salto vs mediana : 0
  Ciclos fora do leilao   : 3493
  Gravações por mudança   : 95
  Gravações forçadas      : 14
  Total gravado no CSV    : 109
============================================================
PS E:\ProjetosPython\Analisador_Financeiro> 
```

### `analisar_divergencia.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analisa os tipos de divergencia no leilao."""

import json
import re
from collections import Counter
from pathlib import Path

DIR = Path("Coletas/Historico_Decisoes_V2")
LEILAO_INICIO = 8 * 60 + 45
LEILAO_FIM = 9 * 60 + 30


def _hora(nome):
    m = re.search(r"_(\d{2})(\d{2})\d{2}\.json$", nome)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


print("=" * 60)
print(" Analise de divergencia no LEILAO")
print("=" * 60)

tipos = Counter()
exemplos = {}

for arq in sorted(DIR.glob("*.json")):
    h = _hora(arq.name)
    if h is None or not (LEILAO_INICIO <= h <= LEILAO_FIM):
        continue

    try:
        d = json.load(open(arq, "r", encoding="utf-8"))
    except Exception:
        continue

    dec = d.get("decisao", {}) or {}
    nm = (dec.get("metadados") or {}).get("novo_motor") or {}
    gap_dir = nm.get("direcao") or "?"
    score_dir = nm.get("score_direcao") or "?"
    diverg = nm.get("divergencia_direcao")

    if not diverg:
        tipos["SEM_DIVERGENCIA"] += 1
        continue

    # Classifica
    if score_dir == "NEUTRO":
        tipo = f"{gap_dir}_vs_NEUTRO"
    elif gap_dir == "NEUTRO":
        tipo = f"NEUTRO_vs_{score_dir}"
    else:
        tipo = f"{gap_dir}_vs_{score_dir}"

    tipos[tipo] += 1
    if tipo not in exemplos:
        exemplos[tipo] = {
            "arquivo": arq.name,
            "gap_pontos": nm.get("gap_pontos"),
            "score_magnitude": nm.get("score_magnitude"),
            "motivos": dec.get("motivos", [])[:3],
        }

print()
print("TIPOS DE DIVERGENCIA (leilao):")
for tipo, qtd in tipos.most_common():
    print(f"  {tipo:30s} {qtd:3d}")

print()
print("EXEMPLO DE CADA TIPO:")
for tipo, info in exemplos.items():
    print(f"\n  [{tipo}] {info['arquivo']}")
    print(f"    gap_pontos: {info['gap_pontos']}")
    print(f"    score_magnitude: {info['score_magnitude']}")
    print(f"    motivos: {info['motivos']}")
```

### `analisar_historico.py`

```python
﻿#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analisar_historico.py — Analise estatistica dos scores do NOVO_MOTOR
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


DIR_HISTORICO = Path("Coletas/Historico_Decisoes_V2")


def carregar_amostras() -> list:
    if not DIR_HISTORICO.exists():
        print(f"[ERRO] Pasta nao encontrada: {DIR_HISTORICO}")
        return []

    arquivos = sorted(DIR_HISTORICO.glob("*.json"))
    print(f"[INFO] {len(arquivos)} arquivos encontrados em {DIR_HISTORICO}")

    amostras = []
    erros = 0

    for arq in arquivos:
        try:
            with open(arq, "r", encoding="utf-8") as f:
                dados = json.load(f)

            decisao = dados.get("decisao", {}) or {}
            meta = decisao.get("metadados", {}) or {}
            nm = meta.get("novo_motor", {}) or {}

            amostras.append({
                "arquivo": arq.name,
                "score_magnitude": nm.get("score_magnitude"),
                "score_direcao": nm.get("score_direcao"),
                "score_forca": nm.get("score_forca"),
                "vies_final": decisao.get("vies_final"),
                "confianca": decisao.get("confianca"),
            })
        except Exception:
            erros += 1
            continue

    print(f"[INFO] {len(amostras)} amostras validas, {erros} erros de leitura")
    return amostras


def percentil(valores, p):
    if not valores:
        return 0.0
    n = len(valores)
    idx = int(p / 100 * n)
    return valores[min(idx, n - 1)]


def analisar(amostras: list, limiar: int = 10) -> None:
    if not amostras:
        print("[AVISO] Sem amostras pra analisar.")
        return

    com_score = [a for a in amostras if a.get("score_magnitude") is not None]
    print(f"[INFO] {len(com_score)} amostras com score_magnitude preenchido")

    if not com_score:
        print("[AVISO] Nenhuma amostra tem score_magnitude.")
        return

    total = len(com_score)

    # Histograma
    print()
    print("=" * 60)
    print(f" DISTRIBUICAO DE SCORE_MAGNITUDE (n={total})")
    print("=" * 60)

    bins = Counter()
    for a in com_score:
        m = a["score_magnitude"]
        faixa = int(m // 5) * 5
        bins[faixa] += 1

    for faixa in sorted(bins.keys()):
        qtd = bins[faixa]
        pct = qtd / total * 100
        barra = "#" * int(pct / 2)
        print(f"  [{faixa:3d}-{faixa+4:3d}]  {qtd:4d} ({pct:5.1f}%) {barra}")

    # Forca
    print()
    print("=" * 60)
    print(" DISTRIBUICAO POR FORCA")
    print("=" * 60)
    forcas = Counter(a.get("score_forca") or "N/A" for a in com_score)
    for forca, qtd in forcas.most_common():
        pct = qtd / total * 100
        print(f"  {str(forca):20s}  {qtd:4d} ({pct:5.1f}%)")

    # Direcao
    print()
    print("=" * 60)
    print(" DISTRIBUICAO POR DIRECAO")
    print("=" * 60)
    direcoes = Counter(a.get("score_direcao") or "N/A" for a in com_score)
    for d, qtd in direcoes.most_common():
        pct = qtd / total * 100
        print(f"  {str(d):20s}  {qtd:4d} ({pct:5.1f}%)")

    # Vies final
    print()
    print("=" * 60)
    print(" VIES FINAL (orquestrador)")
    print("=" * 60)
    vieses = Counter(a.get("vies_final") or "N/A" for a in com_score)
    for v, qtd in vieses.most_common():
        pct = qtd / total * 100
        print(f"  {str(v):20s}  {qtd:4d} ({pct:5.1f}%)")

    # Limiar
    print()
    print("=" * 60)
    print(f" ANALISE DO LIMIAR (atual = {limiar})")
    print("=" * 60)

    abaixo = sum(1 for a in com_score if a["score_magnitude"] < limiar)
    acima = sum(1 for a in com_score if a["score_magnitude"] >= limiar)
    pct_abaixo = abaixo / total * 100
    pct_acima = acima / total * 100

    print(f"  Abaixo do limiar ({limiar}):  {abaixo:4d} ({pct_abaixo:5.1f}%)")
    print(f"  Acima/igual        ({limiar}):  {acima:4d} ({pct_acima:5.1f}%)")

    print()
    print("  --- Simulacao de limiares alternativos ---")
    for alt in [3, 5, 8, 10, 12, 15, 20]:
        qtd_passaria = sum(1 for a in com_score if a["score_magnitude"] >= alt)
        pct = qtd_passaria / total * 100
        marcador = " <- ATUAL" if alt == limiar else ""
        print(f"  Limiar {alt:3d}: {qtd_passaria:4d} passariam ({pct:5.1f}%){marcador}")

    # Estatisticas
    print()
    print("=" * 60)
    print(" ESTATISTICAS DESCRITIVAS")
    print("=" * 60)

    valores = sorted(a["score_magnitude"] for a in com_score)
    media = sum(valores) / total

    print(f"  Minimo   : {valores[0]:.1f}")
    print(f"  P25      : {percentil(valores, 25):.1f}")
    print(f"  Mediana  : {percentil(valores, 50):.1f}")
    print(f"  P75      : {percentil(valores, 75):.1f}")
    print(f"  P90      : {percentil(valores, 90):.1f}")
    print(f"  Maximo   : {valores[-1]:.1f}")
    print(f"  Media    : {media:.1f}")

    # Sugestao
    print()
    print("=" * 60)
    print(" SUGESTAO")
    print("=" * 60)

    p50 = percentil(valores, 50)
    p30 = percentil(valores, 30)

    if pct_abaixo > 50:
        print(f"  ATENCAO: {pct_abaixo:.1f}% das leituras estao ABAIXO do limiar {limiar}.")
        print(f"  Sugestao: reduzir para ~{int(p50)} (mediana) para aceitar 50% dos casos.")
    elif pct_abaixo < 20:
        print(f"  OK: apenas {pct_abaixo:.1f}% abaixo do limiar {limiar}.")
        print(f"  O limiar esta calibrado ou ate conservador demais.")
    else:
        print(f"  ZONA CINZA: {pct_abaixo:.1f}% abaixo do limiar {limiar}.")
        print(f"  Considere reduzir para ~{int(p30)} (P30) para aceitar 70% dos casos.")

    print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limiar", type=int, default=10)
    args = parser.parse_args()

    print("=" * 60)
    print(" analisar_historico.py — Distribuicao de scores do NOVO_MOTOR")
    print("=" * 60)

    amostras = carregar_amostras()
    analisar(amostras, limiar=args.limiar)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### `analisar_historico_v2.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analisar_historico_v2.py — Analise segmentada por horario e divergencia
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


DIR_HISTORICO = Path("Coletas/Historico_Decisoes_V2")

# Janela de leilao (a que importa operacionalmente)
LEILAO_INICIO = 8 * 60 + 45   # 08:45
LEILAO_FIM = 9 * 60 + 30      # 09:30
PREGAO_INICIO = 9 * 60        # 09:00
PREGAO_FIM = 18 * 60 + 25     # 18:25


def _extrair_hora(nome_arquivo: str) -> int | None:
    """Extrai HH*60+MM do nome tipo '20260903_084901.json'."""
    m = re.search(r"_(\d{2})(\d{2})\d{2}\.json$", nome_arquivo)
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def carregar_amostras() -> list:
    if not DIR_HISTORICO.exists():
        print(f"[ERRO] Pasta nao encontrada: {DIR_HISTORICO}")
        return []

    arquivos = sorted(DIR_HISTORICO.glob("*.json"))
    print(f"[INFO] {len(arquivos)} arquivos encontrados")

    amostras = []
    for arq in arquivos:
        try:
            with open(arq, "r", encoding="utf-8") as f:
                dados = json.load(f)

            decisao = dados.get("decisao", {}) or {}
            meta = decisao.get("metadados", {}) or {}
            nm = meta.get("novo_motor", {}) or {}

            hora = _extrair_hora(arq.name)

            amostras.append({
                "arquivo": arq.name,
                "hora_min": hora,
                "score_magnitude": nm.get("score_magnitude"),
                "score_direcao": nm.get("score_direcao"),
                "gap_pontos": nm.get("gap_pontos"),
                "gap_pct": nm.get("gap_pct"),
                "divergencia": nm.get("divergencia_direcao"),
                "vies_final": decisao.get("vies_final"),
                "confianca": decisao.get("confianca"),
                "motivos": decisao.get("motivos") or [],
            })
        except Exception:
            continue

    print(f"[INFO] {len(amostras)} amostras validas")
    return amostras


def filtrar(amostras: list, inicio: int, fim: int) -> list:
    return [a for a in amostras if a.get("hora_min") is not None and inicio <= a["hora_min"] <= fim]


def analisar_grupo(nome: str, amostras: list) -> None:
    total = len(amostras)
    if total == 0:
        print(f"\n### {nome}: SEM AMOSTRAS")
        return

    com_score = [a for a in amostras if a.get("score_magnitude") is not None]
    if not com_score:
        print(f"\n### {nome}: {total} amostras, sem score_magnitude")
        return

    n = len(com_score)
    mediana = sorted(a["score_magnitude"] for a in com_score)[n // 2]
    media = sum(a["score_magnitude"] for a in com_score) / n

    # Contadores
    direcionais = sum(1 for a in com_score if a.get("vies_final") in ("COMPRA", "VENDA"))
    neutros = sum(1 for a in com_score if a.get("vies_final") == "NEUTRO")
    divergencias = sum(1 for a in com_score if a.get("divergencia") is True)
    sem_diverg = sum(1 for a in com_score if a.get("divergencia") is False)

    print(f"\n### {nome} (n={n})")
    print(f"  Score  : mediana={mediana:.1f} | media={media:.1f}")
    print(f"  Vies   : direcional={direcionais} ({direcionais/n*100:.1f}%) | neutro={neutros} ({neutros/n*100:.1f}%)")
    print(f"  Diverg : True={divergencias} ({divergencias/n*100:.1f}%) | False={sem_diverg} ({sem_diverg/n*100:.1f}%)")

    # Motivos mais comuns
    motivos_counter = Counter()
    for a in com_score:
        for m in a.get("motivos", []):
            # Simplifica: pega so o prefixo antes de ":"
            prefixo = m.split(":")[0].strip() if ":" in m else m[:40]
            motivos_counter[prefixo] += 1

    print(f"  Motivos top 5:")
    for motivo, qtd in motivos_counter.most_common(5):
        pct = qtd / n * 100
        print(f"    - {motivo[:60]:60s} {qtd:4d} ({pct:5.1f}%)")


def main() -> int:
    print("=" * 60)
    print(" analisar_historico_v2.py — Segmentacao por horario")
    print("=" * 60)

    amostras = carregar_amostras()
    if not amostras:
        return 1

    # Cobertura por faixa
    print()
    print("=" * 60)
    print(" COBERTURA POR HORARIO")
    print("=" * 60)

    leilao = filtrar(amostras, LEILAO_INICIO, LEILAO_FIM)
    pregao = filtrar(amostras, PREGAO_INICIO, PREGAO_FIM)
    fora = [a for a in amostras if a.get("hora_min") is None or
            a["hora_min"] < PREGAO_INICIO or a["hora_min"] > PREGAO_FIM]

    print(f"  Janela leilao (08:45-09:30): {len(leilao)}")
    print(f"  Janela pregao (09:00-18:25): {len(pregao)}")
    print(f"  Fora do pregao            : {len(fora)}")

    # Analisa os 3 grupos
    analisar_grupo("LEILAO (08:45-09:30)", leilao)
    analisar_grupo("PREGAO (09:00-18:25)", pregao)
    analisar_grupo("FORA (resto)", fora)

    print()
    print("=" * 60)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### `analisar_rompimento_10h.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analisar_rompimento_10h.py
==========================
Le os JSONs do pipeline + a vela M5 de 10:00 do MT5 e monta um snapshot
pronto para copiar/colar no prompt de analise (PromptIA/Prompt_Rompimento_10h.txt).

Uso:
    python analisar_rompimento_10h.py
    python analisar_rompimento_10h.py --force     # gera snapshot mesmo fora de 10:00
    python analisar_rompimento_10h.py --vela-manual "186850,187100,186720,187050"

Saida:
    Coletas/snapshot_rompimento_10h.txt
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path


BASE_DIR = Path(".").resolve()
COLETAS_DIR = BASE_DIR / "Coletas"
PROMPT_PATH = BASE_DIR / "PromptIA" / "Prompt_Rompimento_10h.txt"
SAIDA_PATH = COLETAS_DIR / "snapshot_rompimento_10h.txt"

ARQUIVOS = {
    "ativos":       COLETAS_DIR / "DadosAtivosUnificados.json",
    "metricas":     COLETAS_DIR / "Metricas_Calculadas.json",
    "estimativa":   COLETAS_DIR / "EstimativaAbertura.json",
    "smc":          COLETAS_DIR / "AnaliseGraficaSMC_Regras.json",
    "decisao":      COLETAS_DIR / "Decisao_V2.json",
}

# Fallback estatico — a lista real vem de Coletas/Dados_MT5_v2_2.json
SIMBOLOS_MT5_FALLBACK = ["WINV26", "WINZ26", "WIN$"]
JSON_MT5 = COLETAS_DIR / "Dados_MT5_v2_2.json"


def _descobrir_contrato_vigente():
    """
    Le Coletas/Dados_MT5_v2_2.json e retorna a lista de simbolos a testar
    no MT5. Prioriza ativos.WIN.contrato_principal e completa com
    contratos_vigentes (na ordem). Se falhar, usa o fallback estatico.
    """
    try:
        if JSON_MT5.exists():
            with open(JSON_MT5, "r", encoding="utf-8") as f:
                data = json.load(f)
            win = ((data.get("ativos") or {}).get("WIN") or {})
            principal = win.get("contrato_principal")
            simbolos = []
            if principal:
                simbolos.append(principal)
            for c in (win.get("contratos_vigentes") or []):
                nome = c.get("contrato")
                if nome and nome not in simbolos:
                    simbolos.append(nome)
            if simbolos:
                print(f"[DIAG] Contrato vigente do JSON: {principal}")
                print(f"[DIAG] Simbolos a testar: {simbolos}")
                return simbolos
    except Exception as e:
        print(f"[DIAG] Falha ao ler {JSON_MT5}: {e}")
    print(f"[DIAG] Usando fallback estatico: {SIMBOLOS_MT5_FALLBACK}")
    return list(SIMBOLOS_MT5_FALLBACK)


def _obter_spot_mt5():
    """
    Le o spot REAL do MT5 no instante da geracao (last/bid/ask).
    Usa o contrato vigente do JSON. Retorna dict ou None.
    Nao deve travar o pipeline: qualquer erro retorna None.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return None
    if not mt5.initialize():
        return None
    try:
        simbolos = _descobrir_contrato_vigente()
        simbolo = simbolos[0] if simbolos else None
        if not simbolo:
            return None
        info = mt5.symbol_info(simbolo)
        if info is None:
            return None
        if not info.visible:
            mt5.symbol_select(simbolo, True)
        tick = mt5.symbol_info_tick(simbolo)
        if tick is None:
            return None
        return {
            "simbolo": simbolo,
            "bid": float(getattr(tick, "bid", 0) or 0),
            "ask": float(getattr(tick, "ask", 0) or 0),
            "last": float(getattr(tick, "last", 0) or 0),
            "time": datetime.fromtimestamp(tick.time).isoformat(),
        }
    except Exception:
        return None
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


# ============================================================
# HELPERS
# ============================================================
def carregar_json(caminho: Path) -> dict:
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fmt(valor, casas=2, sufixo=""):
    if valor is None:
        return "—"
    try:
        return f"{float(valor):,.{casas}f}{sufixo}"
    except (TypeError, ValueError):
        return str(valor)


def fmt_pct(valor):
    if valor is None:
        return "—"
    try:
        return f"{float(valor):+.2f}%"
    except (TypeError, ValueError):
        return "—"


# ============================================================
# VELA 10:00 DO MT5
# ============================================================
def obter_vela_10h():
    """Busca a vela M5 de 10:00 no MT5. Retorna dict ou None."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[AVISO] MetaTrader5 nao instalado. Use --vela-manual.")
        return None

    if not mt5.initialize():
        print(f"[AVISO] MT5 nao inicializou: {mt5.last_error()}")
        return None

    try:
        simbolos = _descobrir_contrato_vigente()
        hoje = datetime.now().date()

        # Tenta hoje e cai para ate 7 dias uteis anteriores se nao achar
        # (fim de semana, feriado, ou rodada fora da janela do pregao).
        for offset_dias in range(0, 7):
            alvo = hoje - timedelta(days=offset_dias)
            for simbolo in simbolos:
                info = mt5.symbol_info(simbolo)
                if info is None:
                    print(f"[DIAG] {simbolo}: symbol_info=None (nao existe)")
                    continue
                if not info.visible:
                    mt5.symbol_select(simbolo, True)

                rates = mt5.copy_rates_from_pos(
                    simbolo, mt5.TIMEFRAME_M5, 0, 500
                )
                if rates is None or len(rates) == 0:
                    print(
                        f"[DIAG] {simbolo}: copy_rates_from_pos "
                        f"retornou vazio (last_error={mt5.last_error()})"
                    )
                    continue

                dt_first = datetime.fromtimestamp(rates[0]["time"])
                dt_last = datetime.fromtimestamp(rates[-1]["time"])
                print(
                    f"[DIAG] {simbolo} qtd=500: {len(rates)} barras, "
                    f"{dt_first.isoformat()} -> {dt_last.isoformat()} "
                    f"(alvo={alvo.isoformat()})"
                )

                for r in rates:
                    dt = datetime.fromtimestamp(r["time"])
                    if (
                        dt.date() == alvo
                        and dt.hour == 10
                        and dt.minute == 0
                    ):
                        agora = datetime.now()
                        em_formacao = agora.time() < dt_time(10, 5)
                        if alvo != hoje:
                            print(
                                f"[DIAG] Vela 10:00 de hoje nao achada; "
                                f"usando ultimo dia util: {alvo.isoformat()}"
                            )
                        return {
                            "simbolo": simbolo,
                            "time": dt.isoformat(),
                            "open": float(r["open"]),
                            "high": float(r["high"]),
                            "low": float(r["low"]),
                            "close": float(r["close"]),
                            "volume": float(r["tick_volume"]),
                            "status": (
                                "EM_FORMACAO" if em_formacao else "FECHADA"
                            ),
                        }

        print(
            "[AVISO] Vela 10:00 nao encontrada nos ultimos 7 dias "
            "em nenhum simbolo testado."
        )
        return None
    finally:
        mt5.shutdown()


def vela_manual(csv: str):
    """Formato: open,high,low,close"""
    try:
        partes = [float(x.strip()) for x in csv.split(",")]
        if len(partes) != 4:
            raise ValueError("Esperado 4 valores: open,high,low,close")
        return {
            "simbolo": "MANUAL",
            "time": datetime.now().isoformat(),
            "open": partes[0],
            "high": partes[1],
            "low": partes[2],
            "close": partes[3],
            "volume": 0.0,
            "status": "MANUAL",
        }
    except Exception as e:
        print(f"[ERRO] --vela-manual invalido: {e}")
        return None


# ============================================================
# BLOCOS DE DADOS
# ============================================================
def bloco_ativos(unif: dict) -> str:
    a = (unif.get("ativos") or {}) if isinstance(unif, dict) else {}

    def linha(nome, unidade=""):
        item = a.get(nome) or {}
        preco = item.get("preco")
        var = item.get("variacao_pct")
        return f"  {nome:20s} {fmt(preco, 2):>12s}{unidade}  {fmt_pct(var):>9s}"

    linhas = [
        "--- BLOCO A: ATIVOS (DadosAtivosUnificados) ---",
        "",
        "[ B3 / Futuros ]",
        linha("WIN_FUT", " pts"),
        linha("WIN_LAST_TICK", " pts"),
        linha("WIN_AJUSTE", " pts"),
        linha("WIN_FECHAMENTO_B3", " pts"),
        linha("WDO_FUT"),
        linha("WDO_AJUSTE"),
        "",
        "[ Curva DI ]",
        linha("DI1_2027", " %"),
        linha("DI1_2029", " %"),
        "",
        "[ Global ]",
        linha("VIX"),
        linha("SP500_FUT"),
        linha("NASDAQ_FUT"),
        linha("DXY"),
        linha("USD_BRL"),
        linha("USD_PTAX"),
        "",
        "[ Commodities ]",
        linha("IRON_ORE_2M"),
        linha("CRUDE_OIL"),
        linha("GOLD"),
        "",
        "[ ADRs Brasileiras ]",
        linha("EWZ"),
        linha("VALE_ADR"),
        linha("PETR_ADR"),
        linha("ITUB_ADR"),
        linha("BBAS_ADR"),
        linha("BBD_ADR"),
        linha("B3_ADR"),
        "",
        "[ Acoes B3 ]",
        linha("VALE3"),
        linha("PETR4"),
        linha("ITUB4"),
        linha("BBAS3"),
        linha("BBDC4"),
        linha("B3SA3"),
    ]
    return "\n".join(linhas)


def bloco_metricas(met: dict) -> str:
    ind = (met.get("indicadores_compostos") or {}) if isinstance(met, dict) else {}
    cambio = (met.get("cambio_e_arbitragem") or {})
    curva = (met.get("curva_juros_b3") or {})
    return "\n".join([
        "--- BLOCO B: METRICAS (Metricas_Calculadas) ---",
        "",
        f"  Indicador Mercado Externo : {fmt_pct(ind.get('indicador_mercado_externo'))}",
        f"  Indicador ADRs Brasileiras: {fmt_pct(ind.get('indicador_adrs_brasileiras'))}",
        f"  Spread WDO vs PTAX        : {fmt(cambio.get('spread_wdo_ptax_pontos'))} pts",
        f"  Inclinacao DI (29-27)     : {fmt(curva.get('inclinacao_29_27_bps'), 1)} bps",
    ])


def bloco_estimativa(est: dict) -> str:
    if not est:
        return "--- BLOCO C: ESTIMATIVA (EstimativaAbertura) ---\n  [arquivo vazio]"
    win = (est.get("estimativa_abertura") or {}).get("WIN_INDICE") or {}
    piv = (est.get("pivot_points") or {}).get("WIN_FUT") or {}
    coc = win.get("cost_of_carry") or {}
    return "\n".join([
        "--- BLOCO C: ESTIMATIVA (EstimativaAbertura) ---",
        "",
        f"  Abertura Teorica  : {fmt(win.get('abertura_teorica_pontos'), 0)} pts",
        f"  Variacao Teorica  : {fmt_pct(win.get('variacao_teorica_pct'))}",
        f"  Preco Carregado DI: {fmt(coc.get('preco_teorico_carregado'), 0)} pts",
        "",
        "  Pivots Classicos:",
        f"    R2: {fmt(piv.get('R2'), 0)} | R1: {fmt(piv.get('R1'), 0)} | PP: {fmt(piv.get('PP'), 0)} | S1: {fmt(piv.get('S1'), 0)} | S2: {fmt(piv.get('S2'), 0)}",
    ])


def bloco_smc(smc: dict) -> str:
    if not smc:
        return "--- BLOCO D: SMC (AnaliseGraficaSMC_Regras) ---\n  [arquivo vazio]"
    niv = smc.get("niveis_institucionais") or {}
    liq = smc.get("liquidez") or {}
    return "\n".join([
        "--- BLOCO D: SMC (AnaliseGraficaSMC_Regras) ---",
        "",
        f"  Vies Direcional    : {smc.get('bias_direcional', '—')}",
        f"  Confianca Visual   : {smc.get('confianca_visual', '—')}%",
        f"  POC Ontem          : {fmt(niv.get('poc_ontem'), 0)} pts",
        f"  VWAP Ontem         : {fmt(niv.get('vwap_ontem'), 1)} pts",
        f"  OB Alinhado com POC: {niv.get('ob_alinhado_com_poc', False)}",
        "",
        f"  Order Blocks       : {len(smc.get('order_blocks') or [])}",
        f"  Fair Value Gaps    : {len(smc.get('fair_value_gaps') or [])}",
        f"  BSL (topos)        : {liq.get('bsl', [])}",
        f"  SSL (fundos)       : {liq.get('ssl', [])}",
    ])


def bloco_vela10(vela: dict) -> str:
    if not vela:
        return "\n".join([
            "--- BLOCO E: VELA 10:00 (M5) ---",
            "",
            "  [NAO DISPONIVEL — use --vela-manual open,high,low,close]",
        ])

    amplitude = vela["high"] - vela["low"]
    dentro = 50 <= amplitude <= 700
    status_filtro = "DENTRO DO FILTRO" if dentro else "FORA DO FILTRO"

    return "\n".join([
        "--- BLOCO E: VELA 10:00 (M5) ---",
        "",
        f"  Status   : {vela['status']}",
        f"  Simbolo  : {vela['simbolo']}",
        f"  Abertura : {fmt(vela['open'], 0)}",
        f"  Maxima   : {fmt(vela['high'], 0)}",
        f"  Minima   : {fmt(vela['low'], 0)}",
        f"  Close    : {fmt(vela['close'], 0)}",
        f"  Amplitude: {fmt(amplitude, 0)} pts  [{status_filtro}]",
        f"  Volume   : {fmt(vela['volume'], 0)}",
    ])


def bloco_risco_orb(vela: dict, spot: dict, ajuste: float = None, win_fut: float = None) -> str:
    """
    Bloco E.5 — Risco do setup ORB.
    Explicita M, m, stops, alvos e o estado REAL do rompimento
    (usando o spot do MT5, nao o WIN_FUT defasado do Bloco A).
    """
    if not vela:
        return "--- BLOCO E.5: RISCO ORB ---\n  [sem vela 10:00 para calcular]"

    M = float(vela["high"])
    m = float(vela["low"])
    A = M - m

    preco_ref = None
    fonte_ref = "—"
    if spot and spot.get("last", 0) > 0:
        preco_ref = spot["last"]
        fonte_ref = f"MT5 spot ({spot.get('simbolo','?')})"

    linhas = [
        "--- BLOCO E.5: RISCO ORB ---",
        "",
        f"  Gatilho COMPRA (M) : {fmt(M, 0)}",
        f"  Stop  COMPRA       : {fmt(m, 0)}   (risco {fmt(A, 0)} pts)",
        f"  Alvo  COMPRA       : {fmt(M + A, 0)}",
        "",
        f"  Gatilho VENDA  (m) : {fmt(m, 0)}",
        f"  Stop  VENDA        : {fmt(M, 0)}   (risco {fmt(A, 0)} pts)",
        f"  Alvo  VENDA        : {fmt(m - A, 0)}",
        "",
        f"  Preco spot MT5     : {fmt(preco_ref, 0) if preco_ref else '—'}   ({fonte_ref})",
    ]

    # --- Alerta automatico de divergencia WIN_FUT vs spot MT5 ---
    if preco_ref and win_fut and abs(preco_ref - win_fut) > 100:
        delta = preco_ref - win_fut
        linhas.append("")
        linhas.append("  DIVERGENCIA DE REFERENCIA:")
        linhas.append(f"    WIN_FUT (Bloco A) : {fmt(win_fut, 0)}")
        linhas.append(f"    Spot MT5 (E.5)    : {fmt(preco_ref, 0)}")
        linhas.append(f"    Delta             : {fmt(delta, 0)} pts")
        linhas.append("    -> Use spot MT5 como verdade. WIN_FUT pode estar defasado.")

    if preco_ref:
        if preco_ref > M:
            dist = preco_ref - M
            linhas.append(f"  Rompimento REAL    : ALTA  (dist {fmt(dist, 0)} pts)")
        elif preco_ref < m:
            dist = m - preco_ref
            linhas.append(f"  Rompimento REAL    : BAIXA (dist {fmt(dist, 0)} pts)")
        else:
            linhas.append("  Rompimento REAL    : NAO OCORREU (preco dentro da faixa)")

    # --- REGRA 10 (prioridade maxima) ---
    if preco_ref and ajuste and ajuste > 0:
        gap = abs(preco_ref - ajuste)
        if preco_ref > ajuste:
            posicao = "ACIMA"
            direcao_bloqueada = "VENDA"
        elif preco_ref < ajuste:
            posicao = "ABAIXO"
            direcao_bloqueada = "COMPRA"
        else:
            posicao = "NO AJUSTE"
            direcao_bloqueada = None

        linhas.append("")
        linhas.append(f"  WIN_AJUSTE B3      : {fmt(ajuste, 0)}")
        linhas.append(f"  Posicao vs ajuste  : {posicao}  (gap {fmt(gap, 0)} pts)")
        if gap > 500 and direcao_bloqueada:
            linhas.append(f"  REGRA 10 ATIVA     : {direcao_bloqueada} BLOQUEADA (gap > 500)")
            linhas.append("  -> VIES FINAL = AGUARDAR (prioridade maxima).")
        else:
            linhas.append(f"  REGRA 10           : ok (gap {fmt(gap, 0)} < 500)")

    if A > 400:
        linhas.append("")
        linhas.append(f"  ALERTA: amplitude {fmt(A, 0)} pts — stop largo.")
        linhas.append(f"  Loss potencial (1 contrato) = {fmt(A, 0)} pts por lado.")

    linhas.append("")
    linhas.append("  NOTA: quando o alinhamento e DIVERGENTE mas o gatilho")
    linhas.append("  mecanico JA disparou ha menos de 150 pts, o setup ORB")
    linhas.append("  segue valido — com confianca reduzida e stop = amplitude.")

    return "\n".join(linhas)


def bloco_decisao(dec: dict) -> str:
    if not dec:
        return "--- BLOCO F: DECISAO V2 ---\n  [arquivo vazio]"
    d = dec.get("decisao") or {}
    meta = d.get("metadados") or {}
    nm = meta.get("novo_motor") or {}
    motivos = d.get("motivos") or []
    riscos = d.get("riscos") or []

    linhas = [
        "--- BLOCO F: DECISAO V2 ---",
        "",
        f"  Vies Final       : {d.get('vies_final', '—')}",
        f"  Confianca        : {d.get('confianca', '—')}%",
        f"  Entrada          : {fmt(d.get('entrada'), 0)}",
        f"  Stop             : {fmt(d.get('stop_loss'), 0)}",
        f"  Alvo 1 / Alvo 2  : {fmt(d.get('alvo_1'), 0)} / {fmt(d.get('alvo_2'), 0)}",
        "",
        f"  NOVO_MOTOR direcao : {nm.get('direcao', '—')}",
        f"  NOVO_MOTOR gap     : {fmt(nm.get('gap_pontos'), 0)} pts ({fmt_pct(nm.get('gap_pct'))})",
        f"  NOVO_MOTOR score   : {fmt(nm.get('score_magnitude'), 1)} ({nm.get('score_forca', '—')})",
        f"  Fonte abertura     : {nm.get('fonte_abertura', '—')}",
    ]
    if motivos:
        linhas.append("")
        linhas.append("  Motivos:")
        for m in motivos[:5]:
            linhas.append(f"    - {m}")
    if riscos:
        linhas.append("")
        linhas.append("  Riscos:")
        for r in riscos[:5]:
            linhas.append(f"    - {r}")
    return "\n".join(linhas)


# ============================================================
# MONTAGEM
# ============================================================
def montar_snapshot(vela: dict) -> str:
    ativos = carregar_json(ARQUIVOS["ativos"])
    metricas = carregar_json(ARQUIVOS["metricas"])
    estimativa = carregar_json(ARQUIVOS["estimativa"])
    smc = carregar_json(ARQUIVOS["smc"])
    decisao = carregar_json(ARQUIVOS["decisao"])

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Spot real do MT5 no instante da geracao (contorna defasagem do Bloco A)
    spot = _obter_spot_mt5()
    if spot:
        print(f"[DIAG] Spot MT5: {spot['simbolo']} last={spot['last']} "
              f"bid={spot['bid']} ask={spot['ask']}")

    # Ajuste B3 (para checagem da Regra 10 no Bloco E.5)
    _aj = ((ativos.get("ativos") or {}).get("WIN_AJUSTE") or {}).get("preco")
    try:
        ajuste_b3 = float(_aj) if _aj else None
    except (TypeError, ValueError):
        ajuste_b3 = None
    if ajuste_b3:
        print(f"[DIAG] Ajuste B3: {ajuste_b3}")

    # WIN_FUT (Bloco A) — para deteccao de divergencia vs spot MT5 no E.5
    _wf = ((ativos.get("ativos") or {}).get("WIN_FUT") or {}).get("preco")
    try:
        win_fut = float(_wf) if _wf else None
    except (TypeError, ValueError):
        win_fut = None

    # Le o prompt do arquivo (se existir)
    if PROMPT_PATH.exists():
        prompt_txt = PROMPT_PATH.read_text(encoding="utf-8")
    else:
        prompt_txt = "[AVISO] Prompt nao encontrado em PromptIA/Prompt_Rompimento_10h.txt"

    sep = "=" * 65

    partes = [
        sep,
        "PROMPT — ANALISE DE ROMPIMENTO 10:00 (WINFUT)",
        f"Snapshot gerado em: {agora}",
        sep,
        "",
        prompt_txt,
        "",
        "",
        sep,
        "DADOS REAIS — SNAPSHOT DO PIPELINE",
        f"Timestamp: {agora}",
        sep,
        "",
        bloco_ativos(ativos),
        "",
        bloco_metricas(metricas),
        "",
        bloco_estimativa(estimativa),
        "",
        bloco_smc(smc),
        "",
        bloco_vela10(vela),
        "",
        bloco_risco_orb(vela, spot, ajuste_b3, win_fut),
        "",
        bloco_decisao(decisao),
        "",
        sep,
        "FIM DO SNAPSHOT — COPIE TUDO E COLE NA IA",
        sep,
    ]

    return "\n".join(partes)


# ============================================================
# MAIN
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Gera snapshot mesmo fora da janela 10:00-10:10")
    parser.add_argument("--vela-manual", type=str, default=None,
                        help="Vela manual: 'open,high,low,close'")
    args = parser.parse_args()

    # Janela recomendada
    agora = datetime.now().time()
    if not args.force and not (dt_time(9, 55) <= agora <= dt_time(10, 15)):
        print(f"[AVISO] Fora da janela ideal (09:55-10:15). Agora: {agora.strftime('%H:%M:%S')}")
        print(f"        Use --force para gerar mesmo assim.")

    # Vela
    if args.vela_manual:
        vela = vela_manual(args.vela_manual)
    else:
        vela = obter_vela_10h()

    # Monta snapshot
    texto = montar_snapshot(vela)

    # Salva
    COLETAS_DIR.mkdir(parents=True, exist_ok=True)
    SAIDA_PATH.write_text(texto, encoding="utf-8")

    print()
    print("=" * 60)
    print(" SNAPSHOT GERADO")
    print("=" * 60)
    print(f"  Arquivo : {SAIDA_PATH}")
    print(f"  Tamanho : {len(texto)} caracteres")
    if vela:
        print(f"  Vela    : {vela['status']} | O={vela['open']:.0f} H={vela['high']:.0f} L={vela['low']:.0f} C={vela['close']:.0f}")
    print()
    print("  Abrindo no Notepad...")
    print()
    print("  Proximo passo (dentro do Notepad):")
    print("    1. Ctrl+A (seleciona tudo)")
    print("    2. Ctrl+C (copia)")
    print("    3. Cola na IA (Claude, GPT-4, etc)")
    print()

    # Abre automaticamente no Notepad (Windows)
    try:
        import subprocess
        subprocess.Popen(["notepad.exe", str(SAIDA_PATH)])
        print("  [OK] Notepad aberto.")
    except FileNotFoundError:
        # Fallback: os.startfile (abre com app padrao do .txt)
        try:
            import os
            os.startfile(str(SAIDA_PATH))
            print("  [OK] Arquivo aberto no app padrao.")
        except Exception as e:
            print(f"  [AVISO] Nao foi possivel abrir automaticamente: {e}")
            print(f"  Abra manualmente: notepad {SAIDA_PATH}")
    except Exception as e:
        print(f"  [AVISO] Falha ao abrir Notepad: {e}")
        print(f"  Abra manualmente: notepad {SAIDA_PATH}")

    print()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### `app_home.py`

```python
# ============================================================
# ARQUIVO: app_home.py
# MOTIVO: Home / Landing Page + Roteador Central (st.navigation)
# VERSÃO: 2.1 — menu agrupado Decisão V2 / Operacional / Legado
# DATA: 27/08/2026 (migração V1 → V2)
# ============================================================


import os
import sys
import warnings
from pathlib import Path
from datetime import datetime

import streamlit as st

# ------------------------------------------------------------
# TRATAMENTO DE AVISOS
# ------------------------------------------------------------
if sys.platform == "win32":
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="asyncio")

# ------------------------------------------------------------
# CAMINHOS BASE
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PASTA_PAGES = BASE_DIR / "pages"
PASTA_V2 = BASE_DIR / "v2/pages"  # Mapeamento da pasta externa v2
PASTA_IMAGENS = BASE_DIR / "Imagens"
COLETAS_DIR = BASE_DIR / "Coletas"

# Garantir que as pastas existam no caminho de busca do Python
for path_dir in [PASTA_PAGES, PASTA_V2]:
    if path_dir.exists() and str(path_dir) not in sys.path:
        sys.path.append(str(path_dir))

# ------------------------------------------------------------
# VERIFICAÇÃO DE IMAGEM DA HOME
# ------------------------------------------------------------
CAMINHO_IMAGEM = None
for ext in [".jpg", ".png"]:
    caminho = PASTA_IMAGENS / f"SpikeIAGrande{ext}"
    if caminho.exists():
        CAMINHO_IMAGEM = caminho
        break

# ------------------------------------------------------------
# RENDERIZADOR DA PÁGINA HOME
# ------------------------------------------------------------

def render_home_page():
    """Função responsável por renderizar a Landing Page principal."""
    
    # CSS PERSONALIZADO - VERSÃO PROFISSIONAL
    st.markdown(
        """
    <style>
    /* FUNDO E TEMA */
    .stApp {
        background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%);
    }

    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%) !important;
        border-right: 1px solid #1e2a3a !important;
    }

    /* TÍTULO PRINCIPAL */
    .main-title {
        font-size: 3.5rem !important;
        font-weight: 900 !important;
        background: linear-gradient(135deg, #00d4ff 0%, #7b61ff 50%, #ff6b6b 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.2rem !important;
        letter-spacing: -1px;
    }

    .main-subtitle {
        font-size: 1.2rem !important;
        color: #8b949e !important;
        font-weight: 300 !important;
        letter-spacing: 2px;
        margin-top: 0 !important;
    }

    /* HERO CARD */
    .hero-card {
        background: linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(30,34,45,0.95) 100%);
        border: 1px solid #2a3a4a;
        border-radius: 16px;
        padding: 32px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        backdrop-filter: blur(10px);
    }

    /* CARDS DE RECURSOS */
    .feature-card {
        background: linear-gradient(145deg, #161b24 0%, #1c2230 100%);
        border-radius: 12px;
        padding: 24px 20px;
        border: 1px solid #2a3a4a;
        height: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    }

    .feature-card:hover {
        transform: translateY(-4px);
        border-color: #00d4ff;
        box-shadow: 0 8px 32px rgba(0,212,255,0.15);
    }

    .feature-card .icon { font-size: 2.2rem; margin-bottom: 12px; }
    .feature-card h3 { font-size: 1.1rem; font-weight: 700; margin-bottom: 8px; }
    .feature-card p { font-size: 0.9rem; color: #8b949e; line-height: 1.5; }

    /* TECH PILLS */
    .tech-pill {
        background: rgba(0,212,255,0.1);
        color: #00d4ff;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 500;
        display: inline-block;
        margin: 4px 6px 4px 0;
        border: 1px solid rgba(0,212,255,0.15);
    }

    .divider {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #2a3a4a, transparent);
        margin: 32px 0;
    }

    .diferencial-item {
        display: inline-block;
        background: rgba(0,212,255,0.05);
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        color: #c9d1d9;
        margin: 4px 8px 4px 0;
        border: 1px solid rgba(255,255,255,0.05);
    }

    .footer { text-align: center; padding: 24px 0; border-top: 1px solid #1e2a3a; margin-top: 32px; }
    .footer .version { color: #8b949e; font-size: 0.8rem; letter-spacing: 1px; }
    .footer .version span { color: #00d4ff; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # ------------------ SIDEBAR CUSTOMIZADA ------------------
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/bullish.png", width=60)
        st.title("⚡ Quant Terminal")
        st.caption("Analisador Financeiro v2.0")
        st.markdown("---")
        
        st.markdown("### 🟢 Status do Sistema")
        dados_recentes = False
        ultima_atualizacao = "N/A"
        
        if COLETAS_DIR.exists():
            arquivos = list(COLETAS_DIR.glob("*.json"))
            if arquivos:
                mais_recente = max(arquivos, key=lambda x: x.stat().st_mtime)
                ultima_atualizacao = datetime.fromtimestamp(
                    mais_recente.stat().st_mtime
                ).strftime("%H:%M:%S")
                dados_recentes = True
        
        st.markdown(f"**Status:** {'🟢 Online' if dados_recentes else '🟡 Aguardando'}")
        st.markdown(f"**Última:** {ultima_atualizacao}")
        st.markdown("---")

    # ------------------ HERO SECTION ------------------
    col_text, col_img = st.columns([1.2, 1], gap="large")
    
    with col_text:
        st.markdown(
            """
            <div class="main-title">ANALISADOR FINANCEIRO</div>
            <p class="main-subtitle">• PLATAFORMA QUANTITATIVA INSTITUCIONAL •</p>
            """,
            unsafe_allow_html=True,
        )
        
        st.markdown(
            """
            <div class="hero-card">
            <p style="color:#c9d1d9; font-size:1.05rem; line-height:1.7;">
            Transformamos <b style="color:#00d4ff;">dados macroeconômicos</b>, 
            <b style="color:#7b61ff;">fluxo institucional</b> e 
            <b style="color:#ff6b6b;">estruturas de preço</b> em um 
            <b style="color:#00ff88;">viés operacional claro</b> para 
            os contratos de <b>Mini-Índice (WIN)</b> e <b>Mini-Dólar (WDO)</b>.
            </p>
            <p style="color:#8b949e; font-size:0.95rem; margin-top:12px;">
            Integrando <b>Inteligência Artificial</b>, <b>Smart Money Concepts (SMC)</b>, 
            <b>ICT</b> e algoritmos quantitativos em tempo real.
            </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        st.markdown(
            """
            <div style="margin-top:8px;">
            <span class="tech-pill">🧠 Smart Money Concepts</span>
            <span class="tech-pill">📈 ICT</span>
            <span class="tech-pill">🔷 Order Blocks</span>
            <span class="tech-pill">🔶 Fair Value Gaps</span>
            <span class="tech-pill">🏦 Fluxo Institucional</span>
            <span class="tech-pill">🤖 IA</span>
            <span class="tech-pill">⚡ Tempo Real</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col_img:
        if CAMINHO_IMAGEM:
            st.image(str(CAMINHO_IMAGEM), width="stretch")
        else:
            st.markdown(
                """
                <div style="background: linear-gradient(135deg, #1a2230, #0d1520); border-radius: 16px; padding: 60px 20px; text-align: center; border: 1px solid #2a3a4a;">
                    <div style="font-size: 4rem; margin-bottom: 12px;">📊</div>
                    <p style="color: #8b949e;">Analisador Financeiro<br>Quant Terminal</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ------------------ PILARES DO SISTEMA ------------------
    st.markdown("### 🧩 Arquitetura Analítica")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="feature-card">
                <div class="icon">📊</div>
                <h3 style="color:#00d4ff;">Operacional</h3>
                <p>Monitoramento dos mercados globais, índices futuros, ADRs brasileiras, commodities, dólar e juros.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="feature-card">
                <div class="icon">🎯</div>
                <h3 style="color:#00ff88;">Calculadora Operacional</h3>
                <p>Estimativa de abertura, Gap, Preço Justo, Pivôs, VWAP, Alvos, Stops e níveis institucionais.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="feature-card">
                <div class="icon">⚙️</div>
                <h3 style="color:#ffaa00;">Core Engine</h3>
                <p>Motor principal que consolida informações e gera viés institucional usando SMC, ICT e modelos quantitativos.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ------------------ DIFERENCIAIS ------------------
    st.markdown("### ⭐ Diferenciais")
    diferenciais = [
        "✅ Coleta automática", "✅ Atualização contínua",
        "✅ Inteligência Artificial", "✅ Análise Institucional",
        "✅ SMC & ICT", "✅ Dashboard Operacional",
        "✅ Estimativa da Abertura", "✅ Preço Justo",
        "✅ Monitoramento Realtime", "✅ Suporte a Pastas v2"
    ]

    cols = st.columns(5)
    for i, item in enumerate(diferenciais):
        with cols[i % 5]:
            st.markdown(f'<span class="diferencial-item">{item}</span>', unsafe_allow_html=True)

    st.markdown("---")

    st.markdown(
        """
        <div class="footer">
            <div class="version">
                ⚡ <b>ANALISADOR FINANCEIRO</b> • Versão <span>2.0</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------
# CONFIGURAÇÃO DAS PÁGINAS E NAVEGAÇÃO (st.navigation)
# ------------------------------------------------------------

# 1. Página Principal (Home) declarada como função
page_home = st.Page(
    render_home_page,
    title="Home / Dashboard",
    icon="🏠",
    default=True,
)

# ------------------------------------------------------------
# Páginas legadas de DECISÃO (mostrar com aviso no menu)
# ------------------------------------------------------------
LEGADO_DECISAO = {
    "1.2_🔮_Previsao_Inteligente_Abertura.py",
    "1.3_🔮_Previsao_Inteligente_Abertura_Comparador.py",
    "2.0_📈_Previsao_Abertura_WINFUT.py",
}

# 2. Core Engine (já migrado para V2 — destaque)
core_engine = None
core_path = PASTA_PAGES / "5.3_⚙️_Core_Engine.py"
if core_path.exists():
    core_engine = st.Page(
        core_path.relative_to(BASE_DIR).as_posix(),
        title="Core Engine (V2)",
        icon="⚙️",
    )

# 3. Pasta pages/ — separar operacional vs legado de decisão
paginas_operacional = []
paginas_legado = []
if PASTA_PAGES.exists():
    for arq in sorted(PASTA_PAGES.glob("*.py")):
        if arq.name.startswith("__"):
            continue
        # Core Engine já tratado acima
        if arq.name == "5.3_⚙️_Core_Engine.py":
            continue

        rel_path = arq.relative_to(BASE_DIR).as_posix()
        nome_limpo = arq.stem
        for prefixo in [
            "10_", "4_", "5_", "6_", "7_", "8_", "21_",
            "🎯_", "🔢_", "⚙️_", "🔬_", "📡_", "📊_", "📅_",
            "🤖_", "📥_", "🗺️_", "🔑_", "⚡_", "📈_", "🔮_",
        ]:
            nome_limpo = nome_limpo.replace(prefixo, "")

        titulo = nome_limpo.replace("_", " ").strip()

        if arq.name in LEGADO_DECISAO:
            paginas_legado.append(
                st.Page(rel_path, title=f"[LEGADO] {titulo}", icon="⚠️")
            )
        else:
            paginas_operacional.append(
                st.Page(rel_path, title=titulo, icon="📌")
            )

# 4. Pasta v2/pages/ — decisão oficial
paginas_v2 = []
if PASTA_V2.exists():
    for arq in sorted(PASTA_V2.glob("*.py")):
        if arq.name.startswith("__"):
            continue
        rel_path = arq.relative_to(BASE_DIR).as_posix()
        mapa_titulo = {
            "1.1_dashboard_v2": "Dashboard V2",
            "1.2_comparador": "Comparador V1 × V2",
            "1.3_analise_detalhada": "Análise Detalhada",
        }
        chave = arq.stem
        titulo = mapa_titulo.get(chave, chave.replace("_", " ").title())
        paginas_v2.append(
            st.Page(rel_path, title=titulo, icon="🚀")
        )

# ------------------------------------------------------------
# Estrutura do Menu (ordem de exibição)
# ------------------------------------------------------------
estrutura_menu = {
    "Navegação Principal": [page_home],
}

# Decisão oficial em destaque
bloco_decisao = []
if core_engine is not None:
    bloco_decisao.append(core_engine)
bloco_decisao.extend(paginas_v2)
if bloco_decisao:
    estrutura_menu["🎯 Decisão V2 (oficial)"] = bloco_decisao

# Demais módulos operacionais
if paginas_operacional:
    estrutura_menu["Operacional"] = paginas_operacional

# Legado por último
if paginas_legado:
    estrutura_menu["⚠️ Legado (somente referência)"] = paginas_legado


# Configurações globais do Streamlit
st.set_page_config(
    page_title="Analisador Financeiro - Quant Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inicializa o roteador do Streamlit
pg = st.navigation(estrutura_menu)

# Executa a página ativa selecionada
pg.run()
```

### `backtest_bias_estabilidade.py`

```python
"""
backtest_bias_estabilidade.py

Compara estabilidade do bias SMC com bias_janela=1 (comportamento antigo)
vs bias_janela=5 (fix31) sobre candles historicos M1 do MT5.

Estrategia:
    1. Baixa N candles M1 do MT5 (default 1000 = ~16h)
    2. Para cada sub-janela deslizante (passo = 25 candles):
       roda analisar_smc 2x com configs diferentes
    3. Conta "flips" do bias entre janelas consecutivas

Interpretacao:
    - flips_janela1 = comportamento anterior (bias = ultimo evento)
    - flips_janela5 = comportamento atual (bias = maioria de 5)
    - Se flips_janela5 < flips_janela1, o fix31 ajudou.

Uso:
    python backtest_bias_estabilidade.py
    python backtest_bias_estabilidade.py --qtd 2000 --passo 50
"""

import argparse
from dataclasses import replace
from typing import List

from Motor_SMC_Regras import carregar_mt5, analisar_smc, CONFIG


def rodar_slices(candles_all, cfg, passo: int, min_candles: int = 200) -> List[str]:
    biases = []
    n = len(candles_all)
    for k in range(min_candles, n + 1, passo):
        sub = candles_all[:k]
        try:
            r = analisar_smc(sub, ativo="WIN$", timeframe="1m", config=cfg)
            b = r.get("bias_direcional") or "LATERAL"
            biases.append(b)
        except Exception:
            biases.append("ERRO")
    return biases


def contar_flips(seq: List[str]) -> int:
    if len(seq) < 2:
        return 0
    return sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qtd", type=int, default=1000,
                    help="Candles M1 a baixar (default 1000)")
    ap.add_argument("--passo", type=int, default=25,
                    help="Passo entre slices (default 25 candles)")
    args = ap.parse_args()

    print("=" * 62)
    print(" BACKTEST: Estabilidade do bias SMC (fix31)")
    print("=" * 62)

    print(f"\n-> Baixando {args.qtd} candles M1 do MT5...")
    try:
        candles, simbolo = carregar_mt5("WIN$", timeframe_min=1, qtd=args.qtd)
    except Exception as e:
        print(f"[ERRO] Falha MT5: {e}")
        return 1

    if not candles:
        print("[ERRO] Nenhum candle retornado.")
        return 1

    print(f"   [OK] {len(candles)} candles de {simbolo}")

    # Config A: comportamento antigo (janela=1, sem margem)
    cfg_antigo = replace(CONFIG, bias_janela=1, bias_min_margem=0)
    # Config B: atual (janela=5, margem=1)
    cfg_novo = replace(CONFIG, bias_janela=5, bias_min_margem=1)

    print(f"\n-> Rodando {len(range(200, len(candles) + 1, args.passo))} slices "
          f"com passo={args.passo}...")

    biases_antigo = rodar_slices(candles, cfg_antigo, args.passo)
    biases_novo = rodar_slices(candles, cfg_novo, args.passo)

    flips_antigo = contar_flips(biases_antigo)
    flips_novo = contar_flips(biases_novo)

    print("\n" + "-" * 62)
    print(" RESULTADOS")
    print("-" * 62)
    print(f"  Slices rodados        : {len(biases_antigo)}")
    print(f"  bias_janela=1 (antigo): {flips_antigo} flips")
    print(f"  bias_janela=5 (atual) : {flips_novo} flips")
    print(f"  Reducao               : {flips_antigo - flips_novo} flips "
          f"({(1 - flips_novo / max(flips_antigo, 1)) * 100:.1f}%)")
    print()

    # Distribuicao de biases
    from collections import Counter
    print("  Distribuicao antigo   :", dict(Counter(biases_antigo)))
    print("  Distribuicao novo     :", dict(Counter(biases_novo)))
    print("=" * 62)

    if flips_novo < flips_antigo:
        print("✅ fix31 REDUZIU flips — filtro de maioria esta funcionando.")
    elif flips_novo == flips_antigo:
        print("⚪ Empate — filtro nao muda neste periodo. Ver com mais dados.")
    else:
        print("⚠️ fix31 AUMENTOU flips — investigar. Talvez janela muito curta.")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### `cache_candles.py`

```python
"""
cache_candles.py — Cache incremental de candles do MT5

Objetivo: reduzir o custo de puxar centenas de candles a cada chamada.
Mantém cache em disco por (contrato, timeframe) e só faz fetch dos
candles novos (incremental).

Formato: JSON em Coletas/cache/candles_{CONTRATO}_{TF}m.json

Rollover: cache é keyed no contrato real (WINV26). Quando muda, o cache
antigo é movido para Coletas/cache/_arquivo/ e um novo é criado.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "Coletas" / "cache"
ARQUIVO_DIR = CACHE_DIR / "_arquivo"

BRT = timezone(timedelta(hours=-3))
MAX_CACHE_POR_TF = 1000
QTD_REFRESH_INCREMENTAL = 60
DIAS_RETENCAO = 30

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def _rate_para_dict(rate) -> Dict[str, Any]:
    try:
        dt_brt = datetime.fromtimestamp(rate["time"], tz=timezone.utc).replace(tzinfo=BRT)
    except Exception:
        dt_brt = datetime.now(BRT)

    v_real = 0.0
    try:
        if "real_volume" in rate.dtype.names:
            v_real = float(rate["real_volume"])
    except Exception:
        pass
    if v_real <= 0:
        try:
            if "tick_volume" in rate.dtype.names:
                v_real = float(rate["tick_volume"])
        except Exception:
            pass

    return {
        "time": dt_brt.isoformat(),
        "open": float(rate["open"]),
        "high": float(rate["high"]),
        "low": float(rate["low"]),
        "close": float(rate["close"]),
        "volume": v_real,
    }


def _resolver_contrato_real(symbol: str) -> str:
    import MetaTrader5 as mt5
    info = mt5.symbol_info(symbol)
    if info is None:
        return symbol
    basis = (getattr(info, "basis", "") or "").strip()
    return basis if basis else symbol


def _base_symbol(contrato: str) -> str:
    m = re.match(r"^([A-Z]+)", contrato)
    return m.group(1) if m else contrato


def _cache_path(contrato: str, tf_min: int) -> Path:
    return CACHE_DIR / f"candles_{contrato}_{tf_min}m.json"


def _ler_cache(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[CACHE] Erro lendo {path.name}: {e}")
        return None


def _salvar_cache(path: Path, contrato: str, tf_min: int, candles: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "versao": 1,
        "simbolo": contrato,
        "tf_min": tf_min,
        "atualizado_em": datetime.now(BRT).isoformat(timespec="seconds"),
        "total_candles": len(candles),
        "candles": candles,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    tmp.replace(path)


def _arquivar_cache(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    ARQUIVO_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = ARQUIVO_DIR / f"{path.stem}_{ts}.json"
    try:
        shutil.move(str(path), str(destino))
        print(f"[CACHE] Arquivado: {path.name} -> _arquivo/{destino.name}")
        return destino
    except Exception as e:
        print(f"[CACHE] Falha ao arquivar {path.name}: {e}")
        return None


def _arquivar_contratos_antigos(contrato_atual: str, tf_min: int) -> int:
    """Move caches de outros contratos da MESMA familia para _arquivo/."""
    base = _base_symbol(contrato_atual)
    arquivados = 0
    if not CACHE_DIR.exists():
        return 0
    for arq in CACHE_DIR.glob(f"candles_{base}*_{tf_min}m.json"):
        if f"_{contrato_atual}_" in arq.name:
            continue
        _arquivar_cache(arq)
        arquivados += 1
    return arquivados


def _merge_candles(antigos: List[Dict], novos: List[Dict]) -> List[Dict]:
    mapa = {c["time"]: c for c in antigos if "time" in c}
    for c in novos:
        if "time" in c:
            mapa[c["time"]] = c
    return sorted(mapa.values(), key=lambda c: c["time"])


def _limpar_arquivo_antigo(dias: int = DIAS_RETENCAO) -> int:
    if not ARQUIVO_DIR.exists():
        return 0
    corte = datetime.now() - timedelta(days=dias)
    removidos = 0
    for arq in ARQUIVO_DIR.glob("*.json"):
        try:
            if datetime.fromtimestamp(arq.stat().st_mtime) < corte:
                arq.unlink()
                removidos += 1
        except Exception:
            continue
    return removidos

def _fetch_mt5(
    simbolo_mt5: str, tf_min: int, qtd: int
) -> List[Dict[str, Any]]:
    """Busca candles do MT5. Assume que MT5 já está inicializado."""
    import MetaTrader5 as mt5

    tf_map = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15}
    tf = tf_map.get(tf_min)
    if tf is None:
        raise ValueError(f"TF nao suportado: {tf_min}")

    rates = mt5.copy_rates_from_pos(simbolo_mt5, tf, 0, qtd)
    if rates is None or len(rates) == 0:
        return []
    return [_rate_para_dict(r) for r in rates]


def _obter_com_mt5_aberto(
    simbolo_mt5: str, tf_min: int, qtd: int
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Retorna (candles, contrato_real).
    Assume MT5 já inicializado pelo caller.
    """
    import MetaTrader5 as mt5

    info = mt5.symbol_info(simbolo_mt5)
    if info is None:
        raise RuntimeError(f"Simbolo nao encontrado no MT5: {simbolo_mt5}")
    if not info.visible:
        mt5.symbol_select(simbolo_mt5, True)

    contrato_real = _resolver_contrato_real(simbolo_mt5)

    # Rollover: arquiva caches antigos de outros contratos da mesma familia
    _arquivar_contratos_antigos(contrato_real, tf_min)

    path = _cache_path(contrato_real, tf_min)
    cache = _ler_cache(path)

    # Cache vazio ou corrompido: puxa tudo do MT5
    if cache is None or "candles" not in cache:
        candles = _fetch_mt5(simbolo_mt5, tf_min, qtd)
        if candles:
            _salvar_cache(path, contrato_real, tf_min, candles)
        return candles[-qtd:] if len(candles) > qtd else candles, contrato_real

    antigos = cache.get("candles") or []
    if not antigos:
        candles = _fetch_mt5(simbolo_mt5, tf_min, qtd)
        if candles:
            _salvar_cache(path, contrato_real, tf_min, candles)
        return candles[-qtd:] if len(candles) > qtd else candles, contrato_real

    # Verifica se o cache esta obsoleto (mais de 1 dia)
    try:
        ultimo_ts = datetime.fromisoformat(antigos[-1]["time"])
        agora = datetime.now(BRT)
        if (agora - ultimo_ts).days >= 1:
            print(f"[CACHE] Cache obsoleto ({contrato_real} {tf_min}m) — refresh total")
            candles = _fetch_mt5(simbolo_mt5, tf_min, qtd)
            if candles:
                _salvar_cache(path, contrato_real, tf_min, candles)
            return candles[-qtd:] if len(candles) > qtd else candles, contrato_real
    except Exception:
        pass

    # fix41b: se cache tem menos candles que o caller pediu,
    # faz refresh TOTAL em vez de incremental.
    if len(antigos) < qtd:
        print(f"[CACHE] Cache insuficiente ({len(antigos)} < {qtd}) — refresh total")
        candles = _fetch_mt5(simbolo_mt5, tf_min, qtd)
        if candles:
            _salvar_cache(path, contrato_real, tf_min, candles)
        return candles, contrato_real

    # Fetch incremental
    novos = _fetch_mt5(simbolo_mt5, tf_min, QTD_REFRESH_INCREMENTAL)
    if not novos:
        return antigos[-qtd:] if len(antigos) > qtd else antigos, contrato_real

    merged = _merge_candles(antigos, novos)
    if len(merged) > MAX_CACHE_POR_TF:
        merged = merged[-MAX_CACHE_POR_TF:]

    _salvar_cache(path, contrato_real, tf_min, merged)

    return merged[-qtd:] if len(merged) > qtd else merged, contrato_real


def obter_candles(
    symbol: str = "WIN$",
    tf_min: int = 5,
    qtd: int = 200,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    API publica. Retorna (candles, contrato_real).

    Gerencia init/shutdown do MT5 se necessario. Se MT5 ja esta
    inicializado por outro caller, usa a conexao existente.

    Args:
        symbol: simbolo MT5 (ex: "WIN$", "WDO$")
        tf_min: 1, 5 ou 15
        qtd: numero de candles desejados

    Returns:
        (lista de candles ordenados por tempo, contrato real ex: "WINV26")
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[CACHE] MT5 nao instalado — retornando lista vazia")
        return [], symbol

    ja_inicializado = mt5.terminal_info() is not None
    if not ja_inicializado:
        if not mt5.initialize():
            print(f"[CACHE] mt5.initialize falhou: {mt5.last_error()}")
            return [], symbol

    try:
        return _obter_com_mt5_aberto(symbol, tf_min, qtd)
    except Exception as e:
        print(f"[CACHE] Erro em obter_candles: {e}")
        return [], symbol
    finally:
        if not ja_inicializado:
            try:
                mt5.shutdown()
            except Exception:
                pass


def obter_candles_multi_tf(
    symbol: str = "WIN$",
    tf_qtd: Optional[Dict[int, int]] = None,
) -> Dict[int, Tuple[List[Dict[str, Any]], str]]:
    """
    Puxa varios TFs numa unica conexao MT5.

    Args:
        tf_qtd: dict {tf_min: qtd}, ex {1: 600, 5: 300, 15: 300}

    Returns:
        {tf_min: (candles, contrato_real)}
    """
    if tf_qtd is None:
        tf_qtd = {1: 600, 5: 300, 15: 300}

    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {tf: ([], symbol) for tf in tf_qtd}

    ja_inicializado = mt5.terminal_info() is not None
    if not ja_inicializado:
        if not mt5.initialize():
            return {tf: ([], symbol) for tf in tf_qtd}

    resultado: Dict[int, Tuple[List[Dict[str, Any]], str]] = {}
    try:
        for tf_min, qtd in tf_qtd.items():
            try:
                resultado[tf_min] = _obter_com_mt5_aberto(symbol, tf_min, qtd)
            except Exception as e:
                print(f"[CACHE] Erro em TF {tf_min}: {e}")
                resultado[tf_min] = ([], symbol)
    finally:
        if not ja_inicializado:
            try:
                mt5.shutdown()
            except Exception:
                pass

    return resultado


def invalidar_cache(symbol: str = "WIN$", tf_min: Optional[int] = None) -> int:
    """
    Apaga caches. Se tf_min=None, apaga todos os TFs do contrato.
    Retorna numero de arquivos removidos.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return 0

    ja_inicializado = mt5.terminal_info() is not None
    if not ja_inicializado:
        if not mt5.initialize():
            return 0

    removidos = 0
    try:
        contrato = _resolver_contrato_real(symbol)
        tfs = [tf_min] if tf_min else [1, 5, 15]
        for tf in tfs:
            p = _cache_path(contrato, tf)
            if p.exists():
                p.unlink()
                removidos += 1
                print(f"[CACHE] Invalidado: {p.name}")
    except Exception as e:
        print(f"[CACHE] Erro ao invalidar: {e}")
    finally:
        if not ja_inicializado:
            try:
                mt5.shutdown()
            except Exception:
                pass

    return removidos


def limpar_arquivo_antigo() -> int:
    """Remove caches arquivados com mais de DIAS_RETENCAO dias."""
    return _limpar_arquivo_antigo()


if __name__ == "__main__":
    import argparse as _argparse

    ap = _argparse.ArgumentParser(description="Debug do cache de candles")
    ap.add_argument("--symbol", default="WIN$")
    ap.add_argument("--tf", type=int, default=5)
    ap.add_argument("--qtd", type=int, default=200)
    ap.add_argument("--invalidar", action="store_true")
    ap.add_argument("--limpar-arquivo", action="store_true")
    args = ap.parse_args()

    if args.invalidar:
        n = invalidar_cache(args.symbol, args.tf)
        print(f"[OK] {n} arquivos invalidados")
    elif args.limpar_arquivo:
        n = limpar_arquivo_antigo()
        print(f"[OK] {n} arquivos antigos removidos de _arquivo/")
    else:
        candles, contrato = obter_candles(args.symbol, args.tf, args.qtd)
        print(f"Contrato: {contrato}")
        print(f"Candles: {len(candles)}")
        if candles:
            print(f"Primeiro: {candles[0]['time']}")
            print(f"Ultimo:   {candles[-1]['time']}")
            print(f"Ultimo close: {candles[-1]['close']}")
```

### `comçarNovotrab.txt`

```text


=== 🕒 09:02:09 | PREVISÃO DE ABERTURA === [FORCADO_TEMPO_LEILAO]
💰 PREÇO TEÓRICO : 186680 (Conf: 0.95)
📊 GAP DO AJUSTE : -364 pts [ABAIXO]
📉 GAP DO FECHTO : +0 pts [NO FECHAMENTO]
🏢 DISTÂNCIA POC : -975 pts [ABAIXO]
🌊 MICROFLUXO    : LATERAL (Força/Aceleração: +0.0)
----------------------------------------
🎯 VEREDITO      : AGUARDAR 🕒
========================================
⏱️  Gravação forçada: preço estável há 10s
🎪 Modo LEILÃO ativo — filtro de salto relaxado
📊 Stats: 950 tent | 950 OK | 0 falhas OCR | 0 rejeitadas filtro | 25 mudança | 32 tempo
[09:02:12] ⬛ [LEILAO] Barra azul ausente — OCR PAUSADO
[09:05:56] Fora do leilao (sem fundo azul)

Finalizado! Dados armazenados em Coletas/
============================================================
 📊 ESTATÍSTICAS FINAIS
============================================================
  Tentativas totais       : 958
  Leituras OK (aceitas)   : 958
  Leituras com falha OCR  : 0
  Rejeitadas pelo filtro  : 0
      ├─ fora faixa abs.  : 0
      └─ salto vs mediana : 0
  Ciclos fora do leilao   : 1887
  Gravações por mudança   : 25
  Gravações forçadas      : 32
  Total gravado no CSV    : 57
============================================================
PS E:\ProjetosPython\Analisador_Financeiro> 





O que sobrou do backlog original
Prioridade	Item
Alta	Backtest dos pesos 0.60/0.40
Alta	Calibrar modificadores MTF
Alta	Calibrar fator 1.8 do REVERSAO
Alta	Calibrar LIMIAR_DIRECAO do motor_score.py
Baixa	Remover CONFIG global dos detectores SMC
Baixa	Refatorar global do Gerar_Relatorio_Mensagem
Baixa	Revisar MAX_CACHE_POR_TF
Baixa	Documentar convenção timezone MT5
Baixa	Padronizar encoding nos scripts PowerShell
```

### `config.py`

```python
# ============================================================
# config.py — Configuração central do Analisador Financeiro
# Roadmap A2 | Fase 1 da migração V1 → V2
# Data: 27/08/2026 | Atualizado 01/09/2026 — FILE_LAST_TICK_CONGELADO (Fase 0)
#
# Única fonte de:
#   - Caminhos (BASE_DIR, Coletas, nomes de JSON)
#   - Listas de tickers (TradingView, Finnhub, MT5 B3)
#   - Mapeamento de tickers → IDs internos
#   - Pesos da estimativa de abertura e do NOVO_MOTOR
#   - Janelas temporais, timeouts, flags de migração
#
# Uso:
#   from config import COLETAS_DIR, FILE_UNIFICADO, TICKERS_TRADINGVIEW, ...
# ============================================================

from __future__ import annotations

import os
import sys
from datetime import time
from pathlib import Path
from typing import Any, Dict, List

# ------------------------------------------------------------
# 1. RAIZ DO PROJETO E PATH
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Carrega .env o mais cedo possível (chaves de API)
try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=BASE_DIR / ".env")
except ImportError:
    pass

# KeyManager (opcional — só falha se utils não existir ainda)
try:
    from utils.KeyManager import get_groq_client, key_manager  # noqa: F401
except ImportError:
    get_groq_client = None  # type: ignore
    key_manager = None  # type: ignore

# ------------------------------------------------------------
# 2. DIRETÓRIOS
# ------------------------------------------------------------
COLETAS_DIR = BASE_DIR / "Coletas"
LOGS_DIR = BASE_DIR / "logs"
IMAGENS_DIR = BASE_DIR / "Imagens"
PROMPT_IA_DIR = BASE_DIR / "PromptIA"
HISTORICO_ABERTURAS_DIR = COLETAS_DIR / "Historico_Aberturas"
HISTORICO_DECISOES_V2_DIR = COLETAS_DIR / "Historico_Decisoes_V2"
HISTORICO_MT5_DIR = COLETAS_DIR / "Historico_MT5"

# Garante pastas essenciais
for _d in (COLETAS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# 3. NOMES DE ARQUIVOS JSON (entrada / saída do pipeline)
# ------------------------------------------------------------
# Coleta / unificado
FILE_RAM = COLETAS_DIR / "Coleta_ram.json"
FILE_UNIFICADO = COLETAS_DIR / "DadosAtivosUnificados.json"
FILE_MT5 = COLETAS_DIR / "Dados_MT5.json"
FILE_MT5_V2 = COLETAS_DIR / "Dados_MT5_v2_2.json"
FILE_VALIDADOS = COLETAS_DIR / "Dados_Validados.json"

# Rotação temporal (12 slots = 60 min, a cada 5 min)
ROM_INTERVALOS_MIN = list(range(0, 60, 5))  # 0, 5, ..., 55
ARQUIVOS_ROM: List[Path] = [
    COLETAS_DIR / f"Coleta_rom-{i}.json" for i in ROM_INTERVALOS_MIN
]
FILE_ROM0 = ARQUIVOS_ROM[0]

# Notícias
FILE_NOTICIAS_CALENDARIO = COLETAS_DIR / "Noticias_Calendario.json"
FILE_NOTICIAS_CALENDARIO_0900 = COLETAS_DIR / "Noticias_Calendario_0900.json"
FILE_NOTICIAS_IMPACTO = COLETAS_DIR / "Noticias_Impacto_Dia.json"

# Métricas e estimativas
FILE_METRICAS = COLETAS_DIR / "Metricas_Calculadas.json"
FILE_ESTIMATIVA_ABERTURA = COLETAS_DIR / "EstimativaAbertura.json"
FILE_TENDENCIAS = COLETAS_DIR / "Analise_Tendencias.json"
FILE_RESULTADO_OPERACIONAL = COLETAS_DIR / "Resultado_Calculadora_Operacional_Abertura.json"

# Decisões
# Decisões — V2 é a única fonte oficial (Engine_Vies movido para _legado/)
FILE_DECISAO_V2 = COLETAS_DIR / "Decisao_V2.json"  # oficial V2

# Pipeline / logs
FILE_PIPELINE_LOG = COLETAS_DIR / "Pipeline_Log.json"
FILE_TOKEN_USAGE = COLETAS_DIR / "token_usage.log"

# SMC / visão
FILE_SMC_REGRAS = COLETAS_DIR / "AnaliseGraficaSMC_Regras.json"
FILE_SMC_MTF = COLETAS_DIR / "AnaliseGraficaSMC_MTF.json"
FILE_SMC_M1 = COLETAS_DIR / "AnaliseGraficaSMC_Regras_M1.json"
FILE_SMC_M15 = COLETAS_DIR / "AnaliseGraficaSMC_Regras_M15.json"

# Modificador de confianca SMC por veredito multi-timeframe.
# Aplicado ANTES de comparar com CONFIANCA_MINIMA_CONFLUENCIA (55).
# Opcao 2: o MTF refina a confianca, nao sobrescreve a direcao.
#
# CONFIANCA_MINIMA_FINAL: gate adicional sobre a confianca ponderada
# (0.6*SMC_ajustado + 0.4*NOVO_MOTOR). Mais baixo que o gate do SMC
# para nao bloquear operacoes legitimas quando o MTF derruba o SMC.
CONFIANCA_MINIMA_FINAL = 45.0

MODIFICADOR_MTF = {
    "ALINHADO_FORTE": +10,
    "PULLBACK": 0,
    "REVERSAO_MICRO_MEDIO": -10,
    "CONFLITO_MACRO": -25,
    "DIVERGENTE": -40,
    "NEUTRO": -15,
    "PARCIAL": -15,   # apenas 1-2 TFs disponiveis (analise incompleta)
}
FILE_WIN_1MIN = COLETAS_DIR / "WIN_1min.png"
FILE_WIN_5MIN = COLETAS_DIR / "WIN_5min.png"

# LAST_TICK congelado (fora da rotação ROM) — Fase 0
# Grava fora do pregão; lido no pregão para manter chave estável
FILE_LAST_TICK_CONGELADO = COLETAS_DIR / "LastTick_Congelado.json"

# ------------------------------------------------------------
# 4. CHAVES DE API (via ambiente)
# ------------------------------------------------------------
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
# Demais chaves ficam no KeyManager / .env (GROQ, etc.)

# ------------------------------------------------------------
# 5. JANELAS TEMPORAIS E TIMEOUTS
# ------------------------------------------------------------
# Janela de ajuste oficial B3 / overnight (ajuste TV vivo)
JANELA_AJUSTE_INICIO = time(19, 0, 0)  # 19:00
JANELA_AJUSTE_FIM = time(8, 50, 0)  # 08:50

# Horário cheio do pregão WIN (B3)
# WIN_FUT (contrato MT5) → sempre
# WIN_LAST_TICK → somente FORA deste intervalo
HORA_PREGAO_INICIO = time(9, 0, 0)   # 09:00
HORA_PREGAO_FIM = time(18, 25, 0)    # 18:25

# Janela de leilao (mesma janela usada pelo sniper OCR).
# Fora deste intervalo, o gap de abertura NAO participa mais da
# direcao do NOVO_MOTOR (Visao C so faz sentido durante o leilao).
JANELA_LEILAO_INICIO = time(8, 50, 0)  # 08:50
JANELA_LEILAO_FIM = time(9, 5, 0)      # 09:05

# Timeouts de HTTP (segundos)
TIMEOUT_TRADINGVIEW = 10
TIMEOUT_FINNHUB = 5
TIMEOUT_BACEN = 10
TIMEOUT_TRADINGVIEW_CALENDARIO = 15

MAX_TENTATIVAS_MT5 = 3
TICK_STALE_SEG = 120


# ------------------------------------------------------------
# 6. TICKERS — TRADINGVIEW SCANNER
# ------------------------------------------------------------
def _ticker_fef2() -> str:
    """Minério de ferro 2º mês (SGX) — ano corrente."""
    return f"SGX:FEFU{__import__('datetime').datetime.now().year}"


TICKER_FEF2 = _ticker_fef2()

TICKERS_TRADINGVIEW: List[str] = [
    # WIN/WDO NÃO vêm mais do TV — OHLC/last via MT5 (WIN_FUT / WDO_FUT)
    # Ajuste oficial continua em coletar_ajuste_oficial (B3_AJUSTE_*)
    "BMFBOVESPA:DI1F2027",
    "BMFBOVESPA:DI1F2029",
    "TVC:VIX",
    "SGX:FEF1!",
    TICKER_FEF2,
    "NYMEX:CL1!",
    "CME_MINI:ES1!",  # S&P 500 E-mini (preço real do futuro)
    "CME_MINI:NQ1!",  # Nasdaq 100 E-mini
    "TVC:DXY",
    "FX_IDC:USDMXN",
    "TVC:GOLD",
    "FX_IDC:USDBRL",
]

# Referências explícitas (ajuste dedicado / mapeamento)
TICKER_WIN_TV = "BMFBOVESPA:WIN1!"
TICKER_WDO_TV = "BMFBOVESPA:WDO1!"

# ------------------------------------------------------------
# 7. TICKERS — FINNHUB (ADRs + EWZ)  [Opção A]
# ------------------------------------------------------------
ATIVOS_FINNHUB: List[Dict[str, str]] = [
    {
        "ativo": "AMEX:EWZ",
        "ticker_coleta": "EWZ",
        "id_interno": "EWZ",
        "categoria": "Índices Globais",
    },
    {
        "ativo": "NYSE:VALE",
        "ticker_coleta": "VALE",
        "id_interno": "VALE_ADR",
        "categoria": "ADRs B3",
    },
    {
        "ativo": "NYSE:PBR",
        "ticker_coleta": "PBR",
        "id_interno": "PETR_ADR",
        "categoria": "ADRs B3",
    },
    {
        "ativo": "NYSE:ITUB",
        "ticker_coleta": "ITUB",
        "id_interno": "ITUB_ADR",
        "categoria": "ADRs B3",
    },
    {
        "ativo": "OTC:BDORY",
        "ticker_coleta": "BDORY",
        "id_interno": "BBAS_ADR",
        "categoria": "ADRs B3",
    },
    {
        "ativo": "NYSE:BBD",
        "ticker_coleta": "BBD",
        "id_interno": "BBD_ADR",
        "categoria": "ADRs B3",
    },
    {
        "ativo": "OTC:BOLSY",
        "ticker_coleta": "BOLSY",
        "id_interno": "B3_ADR",
        "categoria": "ADRs B3",
    },
]

# Mapeamento B3 → ADR (arbitragem pré-market / leilão)
MAPEAMENTO_ADR_B3: Dict[str, str] = {
    "VALE3": "VALE",
    "PETR4": "PBR-A",
    "PETR3": "PBR",
    "ITUB4": "ITUB",
    "BBDC4": "BBD",
}

# ------------------------------------------------------------
# 8. TICKERS — MT5 AÇÕES B3
# ------------------------------------------------------------
ATIVOS_MT5_B3: List[Dict[str, str]] = [
    {"ativo": "VALE3", "ticker_coleta": "VALE3", "id_interno": "VALE3", "categoria": "Ações B3"},
    {"ativo": "PETR4", "ticker_coleta": "PETR4", "id_interno": "PETR4", "categoria": "Ações B3"},
    {"ativo": "ITUB4", "ticker_coleta": "ITUB4", "id_interno": "ITUB4", "categoria": "Ações B3"},
    {"ativo": "BBAS3", "ticker_coleta": "BBAS3", "id_interno": "BBAS3", "categoria": "Ações B3"},
    {"ativo": "BBDC4", "ticker_coleta": "BBDC4", "id_interno": "BBDC4", "categoria": "Ações B3"},
    {"ativo": "B3SA3", "ticker_coleta": "B3SA3", "id_interno": "B3SA3", "categoria": "Ações B3"},
]

# ------------------------------------------------------------
# 9. MAPEAMENTO TICKER BRUTO → ID INTERNO
# ------------------------------------------------------------
MAPEAMENTO_TICKERS: Dict[str, str] = {
    "USD_PTAX": "USD_PTAX",
    "B3_AJUSTE_WIN": "WIN_AJUSTE",
    "B3_AJUSTE_WDO": "WDO_AJUSTE",
    "B3_FECHAMENTO_WIN": "WIN_FECHAMENTO_B3",   # ← ADICIONA
    "B3_FECHAMENTO_WDO": "WDO_FECHAMENTO_B3",   # ← ADICIONA
    "BMFBOVESPA:WIN1!": "WIN_FUT",
    "BMFBOVESPA:WDO1!": "WDO_FUT",
    "WIN_PREV_CLOSE": "WIN_PREV_CLOSE",
    "BMFBOVESPA:DI1F2027": "DI1_2027",
    "BMFBOVESPA:DI1F2029": "DI1_2029",
    "DI1_FUT": "DI1_FUT",
    "TVC:VIX": "VIX",
    "SGX:FEF1!": "IRON_ORE",
    "SGX:FEF2!": "IRON_ORE_2M",
    "NYMEX:CL1!": "CRUDE_OIL",
    "NYSE:VALE": "VALE_ADR",
    "NYSE:PBR": "PETR_ADR",
    "NYSE:ITUB": "ITUB_ADR",
    "OTC:BDORY": "BBAS_ADR",
    "NYSE:BBD": "BBD_ADR",
    "OTC:BOLSY": "B3_ADR",
    "AMEX:EWZ": "EWZ",
    "CME_MINI:ES1!": "SP500_FUT",
    "CME_MINI:NQ1!": "NASDAQ_FUT",
    "TVC:DXY": "DXY",
    "FX_IDC:USDMXN": "USD_MXN",
    "TVC:GOLD": "GOLD",
    "FX_IDC:USDBRL": "USD_BRL",
    "WIN_LAST_TICK": "WIN_LAST_TICK",
    "WDO_LAST_TICK": "WDO_LAST_TICK",
    "VALE3": "VALE3",
    "PETR4": "PETR4",
    "ITUB4": "ITUB4",
    "BBAS3": "BBAS3",
    "BBDC4": "BBDC4",
    "B3SA3": "B3SA3",
}

# ------------------------------------------------------------
# 10. PESOS — ESTIMATIVA DE ABERTURA WIN
#     (CalculadoraEstimativaAbertura / alinhado ao uso atual)
# ------------------------------------------------------------
PESOS_ESTIMATIVA_ABERTURA: Dict[str, Any] = {
    # Blocos principais (somam 1.0)
    "ewz": 0.30,
    "cesta_adrs": 0.35,
    "sp500_fut": 0.20,
    "cesta_commodities": 0.15,
    # Dentro da cesta de ADRs (somam 1.0)
    "adr_vale": 0.30,
    "adr_petr": 0.25,
    "adr_itub": 0.25,
    "adr_bbd": 0.20,
    # Dentro da cesta de commodities (somam 1.0)
    "iron_ore": 0.50,
    "crude_oil": 0.50,
}

# ------------------------------------------------------------
# 11. PESOS / LIMIARES — NOVO_MOTOR (score de previsão)
# ------------------------------------------------------------
PESOS_NOVO_MOTOR: Dict[str, float] = {
    "mercado_externo": 0.35,
    "adrs_brasileiras": 0.25,
    "vix": 0.10,
    "tendencia": 0.15,
    "gap_intensidade": 0.10,
    "noticias_impacto": 0.05,
}

SCORE_LIMIARES: Dict[str, int] = {
    "muito_forte": 80,
    "forte": 60,
    "moderado": 40,
    "fraco": 0,
}

GAP_LIMIARES_PTS: Dict[str, int] = {
    "micro": 20,
    "pequeno": 50,
    "moderado": 100,
    "forte": 200,
    "extremo": 999_999,
}

# Notícias — peso por estrela (Analise_Noticias)
PESO_ESTRELAS: Dict[int, int] = {1: 1, 2: 3, 3: 6}

# ------------------------------------------------------------
# 12. FLAGS DE MIGRAÇÃO V1 → V2
# ------------------------------------------------------------
USAR_DECISAO_V2 = True  # Páginas e orquestrador preferem Decisao_V2.json

# Fonte oficial de previsão (documentação / logs)
FONTE_OFICIAL_PREVISAO = "NOVO_MOTOR+OpeningScenario"

# ------------------------------------------------------------
# 13. HELPERS
# ------------------------------------------------------------
def esta_na_janela_ajuste() -> bool:
    """
    True entre 19:00 e 08:50 (overnight / pós-ajuste / pré-abertura).
    Controla coleta ao vivo do AJUSTE oficial (TV).
    """
    from datetime import datetime

    agora = datetime.now().time()
    return agora >= JANELA_AJUSTE_INICIO or agora <= JANELA_AJUSTE_FIM


def esta_no_pregao() -> bool:
    """True no horário cheio do WIN (09:00–18:25)."""
    from datetime import datetime

    agora = datetime.now().time()
    return HORA_PREGAO_INICIO <= agora <= HORA_PREGAO_FIM


def esta_fora_do_pregao() -> bool:
    """True fora do pregão — janela em que WIN_LAST_TICK deve ser coletado."""
    return not esta_no_pregao()


def caminho_json(nome: str) -> Path:
    """Atalho: retorna COLETAS_DIR / nome."""
    return COLETAS_DIR / nome


def id_interno(ticker_bruto: str) -> str:
    """Converte ticker de API para ID interno estável."""
    return MAPEAMENTO_TICKERS.get(ticker_bruto, ticker_bruto)


# Compatibilidade com código antigo que usa str
def _as_str(p: Path) -> str:
    return str(p)


# Aliases string (módulos legados que ainda usam os.path)
BASE_DIR_STR = str(BASE_DIR)
COLETAS_DIR_STR = str(COLETAS_DIR)
FILE_UNIFICADO_STR = str(FILE_UNIFICADO)
FILE_RAM_STR = str(FILE_RAM)
FILE_ROM0_STR = str(FILE_ROM0)
FILE_MT5_V2_STR = str(FILE_MT5_V2)
FILE_DECISAO_V2_STR = str(FILE_DECISAO_V2)


```

### `diag_orb_10h.py`

```python
import json
from pathlib import Path
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd

ROOT = Path(__file__).resolve().parent
JSON_MT5 = ROOT / "Coletas" / "Dados_MT5_v2_2.json"

def load_contrato():
    if not JSON_MT5.exists():
        print(f"[ERRO] JSON não encontrado: {JSON_MT5}")
        return None
    with open(JSON_MT5, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"[JSON] chaves root: {list(data.keys())}")
    candidatos = []
    def find(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                np = f"{path}.{k}" if path else k
                if any(s in k.lower() for s in ["contrato", "principal", "simbolo", "symbol", "ativo"]):
                    candidatos.append((np, v))
                find(v, np)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                find(v, f"{path}[{i}]")
    find(data)
    for p, v in candidatos:
        print(f"[JSON] candidato {p} = {v!r}")
    return None

def test_mt5():
    if not mt5.initialize():
        print(f"[ERRO] mt5.initialize falhou: {mt5.last_error()}")
        return False
    print("[OK] MT5 inicializado")
    print(f"[INFO] terminal: {mt5.terminal_info()}")
    print(f"[INFO] account: {mt5.account_info()}")
    return True

def test_symbol(sym):
    info = mt5.symbol_info(sym)
    if info is None:
        print(f"[SYMBOL] {sym}: NÃO ENCONTRADO (last_error={mt5.last_error()})")
        return False
    print(f"[SYMBOL] {sym}: " + str(info))
    if not info.visible:
        if not mt5.symbol_select(sym, True):
            print(f"[SYMBOL] {sym}: falha ao selecionar (last_error={mt5.last_error()})")
            return False
        print(f"[SYMBOL] {sym}: selecionado agora")
    return True

def test_bars(sym, qtd=100):
    rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, qtd)
    if rates is None or len(rates) == 0:
        print(f"[BARS] {sym} qtd={qtd}: NENHUMA BARRA (last_error={mt5.last_error()})")
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(f"[BARS] {sym} qtd={qtd}: {len(df)} barras, de {df['time'].iloc[0]} até {df['time'].iloc[-1]}")
    return df

def test_range(sym, dt_ini, dt_fim):
    rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M5, dt_ini, dt_fim)
    if rates is None or len(rates) == 0:
        print(f"[RANGE] {sym} {dt_ini} -> {dt_fim}: NENHUMA BARRA (last_error={mt5.last_error()})")
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(f"[RANGE] {sym} {dt_ini} -> {dt_fim}: {len(df)} barras, de {df['time'].iloc[0]} até {df['time'].iloc[-1]}")
    # Mostra barras entre 09:00 e 14:00 (para pegar 10:00 B3 se servidor for UTC+3)
    janela = df[(df['time'].dt.hour >= 9) & (df['time'].dt.hour <= 14)]
    if not janela.empty:
        print(f"[RANGE] {sym} janela 09-14h:\n{janela[['time','open','high','low','close','tick_volume']].to_string(index=False)}")
    return df

def test_tick_time(sym):
    tick = mt5.symbol_info_tick(sym)
    if tick:
        dt_tick = datetime.fromtimestamp(tick.time)
        print(f"[TZ] {sym} tick.time={tick.time} -> {dt_tick} | local now={datetime.now()} | diff={datetime.now() - dt_tick}")

def main():
    contrato = load_contrato()
    if not test_mt5():
        return
    symbols = [contrato, "WINZ26", "WIN$", "WINV26"] if contrato else ["WINZ26", "WIN$", "WINV26"]
    symbols = list(dict.fromkeys([s for s in symbols if s]))
    print(f"\n[SÍMBOLOS A TESTAR] {symbols}\n")

    for sym in symbols:
        test_symbol(sym)
        test_tick_time(sym)

    print("\n--- TESTE qtd=100 vs qtd=500 ---")
    for sym in symbols:
        test_bars(sym, 100)
        test_bars(sym, 500)

    print("\n--- TESTE RANGE 21/09 e 22/09 (09:00-14:00) ---")
    for sym in symbols:
        for dia in [datetime(2026,9,21), datetime(2026,9,22)]:
            ini = dia.replace(hour=9, minute=0)
            fim = dia.replace(hour=14, minute=0)
            test_range(sym, ini, fim)

    mt5.shutdown()

if __name__ == "__main__":
    main()
```

### `fix01.py`

```python
# -*- coding: utf-8 -*-
"""
fix01.py - Remove uso de `global` em Gerar_Relatorio_Mensagem.py
Substitui por parametros/dict explicitos em get_preco_str, get_var_str
e _calcular_derivados.

Uso:
    python fix01.py --dry-run   # mostra o que vai mudar, nao escreve
    python fix01.py             # aplica o patch (com backup)
    python fix01.py --reverter  # restaura do ultimo backup
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

ARQUIVO = Path("Gerar_Relatorio_Mensagem.py")

PATCHES = [
    (
        'def get_preco_str(chave, sufixo=""):\n'
        '    if chave in ativos:\n'
        '        val = ativos[chave].get("preco")\n'
        '        if val is not None and isinstance(val, (int, float)):\n'
        '            return f"{val:,.2f}{sufixo}"\n'
        '    return "N/A"\n'
        '\n'
        'def get_var_str(chave):\n'
        '    if chave in ativos:\n'
        '        val = ativos[chave].get("variacao_pct")\n'
        '        if val is not None and isinstance(val, (int, float)):\n'
        '            return f"{val:+.2f}%"\n'
        '    return "N/A"\n',

        'def get_preco_str(ativos_dict, chave, sufixo=""):\n'
        '    if chave in ativos_dict:\n'
        '        val = ativos_dict[chave].get("preco")\n'
        '        if val is not None and isinstance(val, (int, float)):\n'
        '            return f"{val:,.2f}{sufixo}"\n'
        '    return "N/A"\n'
        '\n'
        'def get_var_str(ativos_dict, chave):\n'
        '    if chave in ativos_dict:\n'
        '        val = ativos_dict[chave].get("variacao_pct")\n'
        '        if val is not None and isinstance(val, (int, float)):\n'
        '            return f"{val:+.2f}%"\n'
        '    return "N/A"\n'
    ),
    (
        'def _calcular_derivados():\n'
        '    """Calcula todos os campos derivados a partir das vars globais."""\n'
        '    vies_final = obj_decisao.get("vies_final") or "NEUTRO"\n'
        '    confianca = obj_decisao.get("confianca", 0)\n',

        'def _calcular_derivados(estado):\n'
        '    """Calcula todos os campos derivados a partir do dict de estado."""\n'
        '    ativos = estado["ativos"]\n'
        '    obj_decisao = estado["obj_decisao"]\n'
        '    meta_decisao = estado["meta_decisao"]\n'
        '    estimativas = estado["estimativas"]\n'
        '    resultado_operacional = estado["resultado_operacional"]\n'
        '    smc_dados = estado["smc_dados"]\n'
        '\n'
        '    vies_final = obj_decisao.get("vies_final") or "NEUTRO"\n'
        '    confianca = obj_decisao.get("confianca", 0)\n'
    ),
    (
        '    vix_val = get_preco_str("VIX")\n'
        '    iron_val = get_preco_str("IRON_ORE")\n'
        '    oil_val = get_preco_str("CRUDE_OIL")\n'
        '    di27_val = get_var_str("DI1_2027")\n'
        '    di29_val = get_var_str("DI1_2029")\n',

        '    vix_val = get_preco_str(ativos, "VIX")\n'
        '    iron_val = get_preco_str(ativos, "IRON_ORE")\n'
        '    oil_val = get_preco_str(ativos, "CRUDE_OIL")\n'
        '    di27_val = get_var_str(ativos, "DI1_2027")\n'
        '    di29_val = get_var_str(ativos, "DI1_2029")\n'
    ),
    (
        '    global ativos, obj_decisao, meta_decisao\n'
        '    global estimativas, resultado_operacional, smc_dados\n'
        '\n'
        '    estado = _carregar_estado()\n'
        '    ativos = estado["ativos"]\n'
        '    obj_decisao = estado["obj_decisao"]\n'
        '    meta_decisao = estado["meta_decisao"]\n'
        '    estimativas = estado["estimativas"]\n'
        '    resultado_operacional = estado["resultado_operacional"]\n'
        '    smc_dados = estado["smc_dados"]\n'
        '\n'
        '    # Recalcula TODOS os derivados (gatilho, stop, alvos, teorico, etc)\n'
        '    _d = _calcular_derivados()\n',

        '    estado = _carregar_estado()\n'
        '\n'
        '    # Recalcula TODOS os derivados (gatilho, stop, alvos, teorico, etc)\n'
        '    _d = _calcular_derivados(estado)\n'
    ),
]


def carregar_texto():
    if not ARQUIVO.is_file():
        print(f"ERRO: arquivo {ARQUIVO} nao encontrado.")
        sys.exit(1)
    return ARQUIVO.read_text(encoding="utf-8")


def validar(texto):
    faltantes = []
    for i, (antiga, _) in enumerate(PATCHES, 1):
        if antiga not in texto:
            faltantes.append(i)
    if faltantes:
        print(f"ERRO: ancora(s) nao encontrada(s) para patch(es): {faltantes}")
        print("Abortando. Nenhuma alteracao foi feita.")
        sys.exit(1)


def aplicar(texto, reverso=False):
    for antiga, nova in PATCHES:
        de, para = (nova, antiga) if reverso else (antiga, nova)
        texto = texto.replace(de, para)
    return texto


def fazer_backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = ARQUIVO.with_name(f"{ARQUIVO.stem}.bak_{ts}{ARQUIVO.suffix}")
    shutil.copy2(ARQUIVO, destino)
    print(f"Backup criado: {destino.name}")
    return destino


def encontrar_ultimo_backup():
    candidatos = sorted(ARQUIVO.parent.glob(f"{ARQUIVO.stem}.bak_*{ARQUIVO.suffix}"))
    if not candidatos:
        print("ERRO: nenhum backup encontrado para reverter.")
        sys.exit(1)
    return candidatos[-1]


def main():
    dry_run = "--dry-run" in sys.argv
    reverter = "--reverter" in sys.argv

    if reverter:
        backup = encontrar_ultimo_backup()
        shutil.copy2(backup, ARQUIVO)
        print(f"Revertido a partir de: {backup.name}")
        return

    texto = carregar_texto()
    validar(texto)
    texto_novo = aplicar(texto)

    if dry_run:
        print("DRY-RUN: patches validos, nenhuma alteracao seria escrita.")
        print(f"Total de patches: {len(PATCHES)}")
        return

    fazer_backup()
    ARQUIVO.write_text(texto_novo, encoding="utf-8")
    print(f"Patch aplicado com sucesso em {ARQUIVO}.")


if __name__ == "__main__":
    main()

```

### `fix02.py`

```python
#!/usr/bin/env python3
"""
fix02.py - Corrige defaults de CONFIG resolvidos em tempo de import
em Motor_SMC_Regras.py, e ajusta os call sites correspondentes.

Problema: calcular_metricas_medias, detectar_swings e detectar_liquidez
usam CONFIG.<atributo> como valor default de parametro. Isso resolve o
valor UMA VEZ, na carga do modulo. Se CONFIG mudar em runtime, essas
funcoes continuam usando o valor antigo.

Fix: troca o default para o objeto CONFIG inteiro (config: ConfigSMC =
CONFIG) e le o atributo dentro do corpo. Ajusta os 4 call sites que
passavam atributos extraidos como argumentos posicionais.

Uso:
    python fix02.py --dry-run     # mostra o que vai mudar
    python fix02.py                # aplica (com backup automatico)
    python fix02.py --reverter     # restaura o backup mais recente
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ARQUIVO = Path("Motor_SMC_Regras.py")
BACKUP_PREFIXO = "Motor_SMC_Regras.py.bak_"

PATCHES = [
    (
        "def calcular_metricas_medias(\n"
        "    candles: List[Candle], idx_atual: int, periodo: int = CONFIG.vol_ma_period\n"
        ") -> Tuple[float, float]:",
        "def calcular_metricas_medias(\n"
        "    candles: List[Candle], idx_atual: int, config: ConfigSMC = CONFIG\n"
        ") -> Tuple[float, float]:\n"
        "    periodo = config.vol_ma_period",
    ),
    (
        "def detectar_swings(\n"
        "    candles: List[Candle],\n"
        "    left: int = CONFIG.swing_left,\n"
        "    right: int = CONFIG.swing_right,\n"
        ") -> List[Swing]:\n"
        "    swings: List[Swing] = []",
        "def detectar_swings(\n"
        "    candles: List[Candle],\n"
        "    config: ConfigSMC = CONFIG,\n"
        ") -> List[Swing]:\n"
        "    left = config.swing_left\n"
        "    right = config.swing_right\n"
        "    swings: List[Swing] = []",
    ),
    (
        "def detectar_liquidez(swings: List[Swing], tol: float = CONFIG.eq_tol_pontos) -> Dict[str, List[float]]:",
        "def detectar_liquidez(swings: List[Swing], config: ConfigSMC = CONFIG) -> Dict[str, List[float]]:\n"
        "    tol = config.eq_tol_pontos",
    ),
    # Call sites
    (
        "media_vol, media_corpo = calcular_metricas_medias(candles, i - 1, config.vol_ma_period)",
        "media_vol, media_corpo = calcular_metricas_medias(candles, i - 1, config)",
    ),
    (
        "media_vol, media_corpo = calcular_metricas_medias(candles, i, config.vol_ma_period)",
        "media_vol, media_corpo = calcular_metricas_medias(candles, i, config)",
    ),
    (
        "swings = detectar_swings(candles, config.swing_left, config.swing_right)",
        "swings = detectar_swings(candles, config)",
    ),
    (
        "liq = detectar_liquidez(swings, config.eq_tol_pontos)",
        "liq = detectar_liquidez(swings, config)",
    ),
]


def ler_arquivo():
    if not ARQUIVO.exists():
        print(f"ERRO: {ARQUIVO} nao encontrado no diretorio atual.")
        sys.exit(1)
    return ARQUIVO.read_text(encoding="utf-8")


def validar_ancoras(conteudo):
    faltando = []
    for antiga, _ in PATCHES:
        if antiga not in conteudo:
            faltando.append(antiga[:70].replace("\n", " ") + "...")
    if faltando:
        print("ERRO: as seguintes ancoras nao foram encontradas no arquivo:")
        for f in faltando:
            print(f"  - {f}")
        print("\nNenhuma alteracao foi feita. Abortando.")
        sys.exit(1)


def aplicar_patches(conteudo):
    for antiga, nova in PATCHES:
        conteudo = conteudo.replace(antiga, nova, 1)
    return conteudo


def fazer_backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = Path(f"{BACKUP_PREFIXO}{ts}")
    shutil.copy2(ARQUIVO, destino)
    print(f"Backup criado: {destino}")
    return destino


def reverter():
    backups = sorted(Path(".").glob(f"{BACKUP_PREFIXO}*"), reverse=True)
    if not backups:
        print("ERRO: nenhum backup encontrado para reverter.")
        sys.exit(1)
    mais_recente = backups[0]
    shutil.copy2(mais_recente, ARQUIVO)
    print(f"Revertido a partir de: {mais_recente}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        reverter()
        return

    conteudo = ler_arquivo()
    validar_ancoras(conteudo)
    novo_conteudo = aplicar_patches(conteudo)

    if args.dry_run:
        print("--- DRY RUN: patches que seriam aplicados ---")
        for i, (antiga, nova) in enumerate(PATCHES, 1):
            print(f"\n[Patch {i}]")
            print("ANTES:")
            print(antiga)
            print("DEPOIS:")
            print(nova)
        print("\nNenhuma alteracao foi salva (dry-run).")
        return

    fazer_backup()
    ARQUIVO.write_text(novo_conteudo, encoding="utf-8")
    print(f"\n{len(PATCHES)} patches aplicados com sucesso em {ARQUIVO}.")


if __name__ == "__main__":
    main()

```

### `fix03.py`

```python
"""
fix03.py - Move item concluido de "Baixa prioridade" para "Concluidas
recentemente" em docs/melhorias.md.

Uso:
    python fix03.py --dry-run   # mostra o que sera alterado
    python fix03.py             # aplica o patch (com backup automatico)
    python fix03.py --reverter  # restaura o ultimo backup
"""

import argparse
import glob
import os
import shutil
from datetime import datetime

ARQUIVO = os.path.join("docs", "melhorias.md")

PATCHES = [
    (
        "\\- \\[ ] Remover uso de CONFIG global nos detectores SMC\n",
        "",
    ),
    (
        "\\- \\[x] Cache incremental de candles (v0.11.0)",
        "\\- \\[x] Remover uso de CONFIG global nos detectores SMC (fix02.py)\n"
        "\\- \\[x] Cache incremental de candles (v0.11.0)",
    ),
]


def ler_arquivo():
    if not os.path.exists(ARQUIVO):
        raise SystemExit(f"Arquivo nao encontrado: {ARQUIVO}")
    with open(ARQUIVO, "r", encoding="utf-8") as f:
        return f.read()


def validar_ancoras(conteudo):
    for i, (antes, _) in enumerate(PATCHES, 1):
        if antes not in conteudo:
            raise SystemExit(f"[Patch {i}] ancora nao encontrada. Abortando sem alterar nada.")


def aplicar_patches(conteudo):
    for antes, depois in PATCHES:
        conteudo = conteudo.replace(antes, depois, 1)
    return conteudo


def fazer_backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = f"{ARQUIVO}.bak_{ts}"
    shutil.copy2(ARQUIVO, destino)
    print(f"Backup criado: {destino}")


def reverter():
    backups = sorted(glob.glob(f"{ARQUIVO}.bak_*"))
    if not backups:
        raise SystemExit("Nenhum backup encontrado.")
    ultimo = backups[-1]
    shutil.copy2(ultimo, ARQUIVO)
    print(f"Revertido a partir de: {ultimo}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        reverter()
        return

    conteudo_original = ler_arquivo()
    validar_ancoras(conteudo_original)
    conteudo_novo = aplicar_patches(conteudo_original)

    if args.dry_run:
        print("--- DRY RUN: alteracoes que seriam aplicadas ---")
        print("\n[Patch 1] Remove a linha do item 'Remover uso de CONFIG global...' de Baixa prioridade")
        print("\n[Patch 2] Insere o item como concluido, no topo de 'Concluidas recentemente'")
        print("\nNenhuma alteracao foi salva (dry-run).")
        return

    fazer_backup()
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        f.write(conteudo_novo)
    print(f"\n{len(PATCHES)} patches aplicados com sucesso em {ARQUIVO}.")


if __name__ == "__main__":
    main()

```

### `fix04.py`

```python
# -*- coding: utf-8 -*-
"""
fix01.py - Adiciona compactacao de pastas de historico (so mantem o arquivo
mais recente) em gerar_dump_completo.py

Uso:
    python fix01.py --dry-run
    python fix01.py
    python fix01.py --reverter
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent / "gerar_dump_completo.py"

PATCHES = [
    (
        'EXT_TEXTO = {".py", ".md", ".toml", ".cfg", ".ini", ".json", ".txt"}',
        'EXT_TEXTO = {".py", ".md", ".toml", ".cfg", ".ini", ".json", ".txt"}\n\n'
        '# Pastas onde so entra o arquivo mais recente (evita dump gigante)\n'
        'PASTAS_COMPACTAS_PREFIXOS = (\n'
        '    "Coletas/Historico_Decisoes_V2",\n'
        '    "Coletas/Historico_MT5",\n'
        ')\n\n\n'
        'def _e_pasta_compacta(rel: str) -> bool:\n'
        '    for pref in PASTAS_COMPACTAS_PREFIXOS:\n'
        '        if rel == pref or rel.startswith(pref + "/"):\n'
        '            return True\n'
        '    return False'
    ),
    (
        '''def _listar_arquivos(base: Path) -> list[Path]:
    """Lista recursivamente arquivos de texto validos dentro de base."""
    resultado = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        if _ignorar_arquivo(p):
            continue
        if p.suffix.lower() not in EXT_TEXTO:
            continue
        resultado.append(p)
    return resultado''',
        '''def _listar_arquivos(base: Path) -> list[Path]:
    """Lista recursivamente arquivos de texto validos dentro de base.

    Pastas marcadas como compactas (PASTAS_COMPACTAS_PREFIXOS) so contribuem
    com o arquivo mais recente (por mtime).
    """
    candidatos = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        if _ignorar_arquivo(p):
            continue
        if p.suffix.lower() not in EXT_TEXTO:
            continue
        candidatos.append(p)

    resultado = []
    compactos_por_pasta: dict[str, list[Path]] = {}

    for p in candidatos:
        rel_pasta = p.parent.relative_to(RAIZ).as_posix()
        if _e_pasta_compacta(rel_pasta):
            compactos_por_pasta.setdefault(rel_pasta, []).append(p)
        else:
            resultado.append(p)

    for rel_pasta, arquivos in compactos_por_pasta.items():
        try:
            mais_recente = max(arquivos, key=lambda p: p.stat().st_mtime)
        except (PermissionError, FileNotFoundError):
            mais_recente = arquivos[0]
        resultado.append(mais_recente)

    return resultado'''
    ),
]


def _ler() -> str:
    return ARQUIVO.read_text(encoding="utf-8")


def _validar(conteudo: str) -> None:
    for antigo, _ in PATCHES:
        if antigo not in conteudo:
            print(f"[ABORTADO] Ancora nao encontrada:\n{antigo[:80]}...")
            sys.exit(1)


def _backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = ARQUIVO.with_suffix(f".py.bak_{ts}")
    shutil.copy2(ARQUIVO, destino)
    return destino


def aplicar(dry_run: bool) -> None:
    conteudo = _ler()
    _validar(conteudo)

    novo = conteudo
    for antigo, atualizado in PATCHES:
        novo = novo.replace(antigo, atualizado, 1)

    if dry_run:
        print("[DRY-RUN] Patches validos. Nenhuma alteracao escrita.")
        for i, (antigo, atualizado) in enumerate(PATCHES, 1):
            print(f"\n--- Patch {i} ---")
            print(f"ANTES ({len(antigo)} chars):\n{antigo[:150]}")
            print(f"DEPOIS ({len(atualizado)} chars):\n{atualizado[:150]}")
        return

    backup = _backup()
    ARQUIVO.write_text(novo, encoding="utf-8")
    print(f"[OK] Patch aplicado. Backup em: {backup}")


def reverter() -> None:
    backups = sorted(ARQUIVO.parent.glob("gerar_dump_completo.py.bak_*"))
    if not backups:
        print("[ERRO] Nenhum backup encontrado.")
        sys.exit(1)
    ultimo = backups[-1]
    shutil.copy2(ultimo, ARQUIVO)
    print(f"[OK] Revertido a partir de: {ultimo}")


def main() -> int:
    if "--reverter" in sys.argv:
        reverter()
        return 0
    dry_run = "--dry-run" in sys.argv
    aplicar(dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())

```

### `gerar_docs.py`

```python
# -*- coding: utf-8 -*-
"""
gerar_docs.py - Gera docs/arvore.md e docs/inventario.md a partir do disco

Uso:
    python gerar_docs.py

Saida:
    docs/arvore.md       - estrutura de diretorios (arvore)
    docs/inventario.md   - tabela de todos os .py (path, linhas, bytes, mtime)

Sempre roda a partir da raiz do projeto (onde este arquivo esta).
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DOCS = RAIZ / "docs"

# Diretorios ignorados (checados em QUALQUER nivel do path)
IGNORAR_DIRS = {
    ".git", "__pycache__", "lixeira_analise", ".venv", "venv",
    "node_modules", ".pytest_cache", ".mypy_cache", ".idea", ".vscode",
}

# Caminhos relativos a ignorar (com / no meio)
IGNORAR_CAMINHOS = {
    "Coletas/cache/_arquivo",
}

# Pastas onde listamos so o arquivo mais recente (evita poluir a arvore)
# Prefixos onde listamos so o arquivo mais recente
PASTAS_COMPACTAS_PREFIXOS = (
    "Coletas/Historico_",
    "Coletas/coleta_preco_teorico_historico",
    "Coletas/cache",
)


def _e_pasta_compacta(rel_base: str) -> bool:
    if not rel_base:
        return False
    for pref in PASTAS_COMPACTAS_PREFIXOS:
        if rel_base == pref or rel_base.startswith(pref):
            return True
    return False

# Extensoes consideradas no inventario
EXT_INVENTARIO = {".py"}


def _ignorar(path: Path) -> bool:
    """True se o path (ou qualquer ancestral) deve ser ignorado."""
    try:
        rel = path.relative_to(RAIZ).as_posix()
    except ValueError:
        return False

    # Ignora por componente exato (pega qualquer nivel)
    parts = rel.split("/")
    for ig in IGNORAR_DIRS:
        if ig in parts:
            return True

    # Ignora caminhos especificos (com /)
    for ig in IGNORAR_CAMINHOS:
        if rel == ig or rel.startswith(ig + "/"):
            return True

    return False


def _walk_dir(base: Path):
    """Itera arquivos e subdirs de base, respeitando IGNORAR_DIRS."""
    try:
        entries = sorted(base.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return
    for p in entries:
        if _ignorar(p):
            continue
        if p.name.startswith(".") and p.name not in (".gitignore", ".env.example"):
            continue
        yield p


def gerar_arvore() -> str:
    linhas = ["# Arvore de Arquivos", ""]
    linhas.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    linhas.append("")
    linhas.append("```")
    linhas.append(".")
    _arvore_rec(RAIZ, "", linhas)
    linhas.append("```")
    return "\n".join(linhas)


def _arvore_rec(base: Path, prefixo: str, linhas: list):
    """Recursao pra desenhar arvore. Pastas em PASTAS_COMPACTAS so mostram
    o arquivo mais recente + contador."""
    try:
        rel_base = base.relative_to(RAIZ).as_posix() if base != RAIZ else ""
    except ValueError:
        rel_base = ""

    compacto = _e_pasta_compacta(rel_base)

    if compacto:
        # So lista arquivos (ignora subdirs)
        try:
            arquivos = [p for p in base.iterdir() if p.is_file() and not _ignorar(p)]
        except (PermissionError, FileNotFoundError):
            arquivos = []

        if arquivos:
            try:
                mais_recente = max(arquivos, key=lambda p: p.stat().st_mtime)
            except (PermissionError, FileNotFoundError):
                mais_recente = arquivos[0]

            outros = len(arquivos) - 1
            linhas.append(f"{prefixo}`-- {mais_recente.name}")
            if outros > 0:
                linhas.append(f"{prefixo}    (+{outros} arquivos semelhantes)")
        return

    filhos = list(_walk_dir(base))
    for i, p in enumerate(filhos):
        ultimo = i == len(filhos) - 1
        conector = "`-- " if ultimo else "|-- "
        linhas.append(f"{prefixo}{conector}{p.name}")

        if p.is_dir():
            novo_prefixo = prefixo + ("    " if ultimo else "|   ")
            _arvore_rec(p, novo_prefixo, linhas)


def gerar_inventario() -> str:
    linhas = ["# Inventario de Arquivos", ""]
    linhas.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    linhas.append("")

    # Coleta
    itens = []
    for arq in RAIZ.rglob("*"):
        if not arq.is_file():
            continue
        if _ignorar(arq):
            continue
        if arq.suffix.lower() not in EXT_INVENTARIO:
            continue
        if arq.name == "gerar_docs.py":
            continue

        try:
            st = arq.stat()
            with arq.open("r", encoding="utf-8", errors="ignore") as f:
                linhas_arq = sum(1 for _ in f)
        except Exception:
            continue

        itens.append({
            "path": arq.relative_to(RAIZ).as_posix(),
            "linhas": linhas_arq,
            "bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })

    itens.sort(key=lambda x: x["path"])

    # Resumo
    total_arq = len(itens)
    total_linhas = sum(i["linhas"] for i in itens)
    total_bytes = sum(i["bytes"] for i in itens)

    linhas.append(f"**Total:** {total_arq} arquivos .py | "
                  f"{total_linhas:,} linhas | {total_bytes:,} bytes")
    linhas.append("")

    # Distribuicao por pasta top-level
    por_pasta = {}
    for it in itens:
        parts = it["path"].split("/")
        pasta = parts[0] if len(parts) > 1 else "(raiz)"
        por_pasta.setdefault(pasta, {"n": 0, "linhas": 0})
        por_pasta[pasta]["n"] += 1
        por_pasta[pasta]["linhas"] += it["linhas"]

    linhas.append("## Distribuicao por pasta")
    linhas.append("")
    linhas.append("| Pasta | Arquivos | Linhas |")
    linhas.append("|---|---:|---:|")
    for pasta in sorted(por_pasta.keys()):
        d = por_pasta[pasta]
        linhas.append(f"| `{pasta}` | {d['n']} | {d['linhas']:,} |")
    linhas.append("")

    # Tabela completa
    linhas.append("## Inventario completo")
    linhas.append("")
    linhas.append("| Path | Linhas | Bytes | Ultima mod. |")
    linhas.append("|---|---:|---:|---|")
    for it in itens:
        linhas.append(f"| `{it['path']}` | {it['linhas']:,} | {it['bytes']:,} | {it['mtime']} |")

    return "\n".join(linhas)


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(" GERADOR DE DOCS")
    print("=" * 60)

    print("\n-> Gerando arvore...")
    arvore = gerar_arvore()
    out_arvore = DOCS / "arvore.md"
    out_arvore.write_text(arvore, encoding="utf-8")
    print(f"   [OK] {out_arvore} ({len(arvore):,} chars)")

    print("\n-> Gerando inventario...")
    inventario = gerar_inventario()
    out_inventario = DOCS / "inventario.md"
    out_inventario.write_text(inventario, encoding="utf-8")
    print(f"   [OK] {out_inventario} ({len(inventario):,} chars)")

    print()
    print("=" * 60)
    print(" CONCLUIDO")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### `gerar_dump_completo.py`

```python
# -*- coding: utf-8 -*-
"""
gerar_dump_completo.py - Gera um .md por categoria (pasta de 1o nivel) do
projeto, contendo a arvore da categoria + conteudo integral de cada arquivo
de texto (codigo, config, etc).

Uso:
    python gerar_dump_completo.py

Saida:
    docs/dump_completo/<categoria>.md   - um arquivo por pasta de 1o nivel
    docs/dump_completo/_raiz.md         - arquivos soltos na raiz do projeto

Nunca inclui: .env, .git, __pycache__, venv/.venv, backups (*bak*), docs/.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "docs" / "dump_completo"

IGNORAR_DIRS = {
    ".git", "__pycache__", "lixeira_analise", ".venv", "venv",
    "node_modules", ".pytest_cache", ".mypy_cache", ".idea", ".vscode",
    "docs", "dump_completo",
}

IGNORAR_ARQUIVOS_EXATOS = {".env"}

# Padroes de nome ignorados (case-insensitive), casados com "in"
IGNORAR_PADROES_NOME = ("bak", ".bak_")

EXT_TEXTO = {".py", ".md", ".toml", ".cfg", ".ini", ".json", ".txt"}

# Pastas onde so entra o arquivo mais recente (evita dump gigante)
PASTAS_COMPACTAS_PREFIXOS = (
    "Coletas/Historico_Decisoes_V2",
    "Coletas/Historico_MT5",
)


def _e_pasta_compacta(rel: str) -> bool:
    for pref in PASTAS_COMPACTAS_PREFIXOS:
        if rel == pref or rel.startswith(pref + "/"):
            return True
    return False


def _ignorar_dir(path: Path) -> bool:
    try:
        rel = path.relative_to(RAIZ).as_posix()
    except ValueError:
        return False
    parts = rel.split("/")
    return any(p in IGNORAR_DIRS for p in parts)


def _ignorar_arquivo(path: Path) -> bool:
    if _ignorar_dir(path.parent):
        return True
    nome_lower = path.name.lower()
    if path.name in IGNORAR_ARQUIVOS_EXATOS:
        return True
    if any(pad in nome_lower for pad in IGNORAR_PADROES_NOME):
        return True
    if path.name.startswith(".") and path.name not in (".gitignore",):
        return True
    return False


def _listar_arquivos(base: Path) -> list[Path]:
    """Lista recursivamente arquivos de texto validos dentro de base.

    Pastas marcadas como compactas (PASTAS_COMPACTAS_PREFIXOS) so contribuem
    com o arquivo mais recente (por mtime).
    """
    candidatos = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        if _ignorar_arquivo(p):
            continue
        if p.suffix.lower() not in EXT_TEXTO:
            continue
        candidatos.append(p)

    resultado = []
    compactos_por_pasta: dict[str, list[Path]] = {}

    for p in candidatos:
        rel_pasta = p.parent.relative_to(RAIZ).as_posix()
        if _e_pasta_compacta(rel_pasta):
            compactos_por_pasta.setdefault(rel_pasta, []).append(p)
        else:
            resultado.append(p)

    for rel_pasta, arquivos in compactos_por_pasta.items():
        try:
            mais_recente = max(arquivos, key=lambda p: p.stat().st_mtime)
        except (PermissionError, FileNotFoundError):
            mais_recente = arquivos[0]
        resultado.append(mais_recente)

    return resultado


def _arvore_categoria(base: Path, arquivos: list[Path]) -> str:
    """Desenha arvore simples baseada na lista de arquivos ja filtrada."""
    linhas = ["```"]
    linhas.append(base.name if base != RAIZ else ".")
    rels = sorted(a.relative_to(base).as_posix() for a in arquivos)
    for i, rel in enumerate(rels):
        ultimo = i == len(rels) - 1
        conector = "`-- " if ultimo else "|-- "
        linhas.append(f"{conector}{rel}")
    linhas.append("```")
    return "\n".join(linhas)


def _bloco_arquivo(path_rel: str, conteudo: str, ext: str) -> str:
    lang = {"py": "python", "md": "markdown", "json": "json",
            "toml": "toml", "cfg": "ini", "ini": "ini", "txt": "text"}.get(ext.lstrip("."), "")
    return (
        f"### `{path_rel}`\n\n"
        f"```{lang}\n{conteudo}\n```\n"
    )


def gerar_categoria(nome_categoria: str, base: Path, arquivos: list[Path]) -> str:
    linhas = [f"# Dump completo - {nome_categoria}", ""]
    linhas.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    linhas.append(f"Total de arquivos: {len(arquivos)}")
    linhas.append("")
    linhas.append("## Arvore")
    linhas.append("")
    linhas.append(_arvore_categoria(base, arquivos))
    linhas.append("")
    linhas.append("## Conteudo dos arquivos")
    linhas.append("")

    for arq in sorted(arquivos, key=lambda p: p.relative_to(RAIZ).as_posix()):
        rel = arq.relative_to(RAIZ).as_posix()
        try:
            conteudo = arq.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            conteudo = f"[ERRO AO LER ARQUIVO: {e}]"
        linhas.append(_bloco_arquivo(rel, conteudo, arq.suffix))

    return "\n".join(linhas)


def main() -> int:
    SAIDA.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(" GERADOR DE DUMP COMPLETO POR CATEGORIA")
    print("=" * 60)

    # Categorias = pastas de 1o nivel (nao ignoradas)
    categorias = [
        p for p in sorted(RAIZ.iterdir())
        if p.is_dir() and not _ignorar_dir(p)
    ]

    total_geral = 0

    # Raiz (arquivos soltos, sem subpasta)
    arquivos_raiz = [
        p for p in RAIZ.iterdir()
        if p.is_file() and not _ignorar_arquivo(p) and p.suffix.lower() in EXT_TEXTO
    ]
    if arquivos_raiz:
        conteudo = gerar_categoria("_raiz", RAIZ, arquivos_raiz)
        out = SAIDA / "_raiz.md"
        out.write_text(conteudo, encoding="utf-8")
        print(f"-> {out} ({len(arquivos_raiz)} arquivos)")
        total_geral += len(arquivos_raiz)

    for cat in categorias:
        arquivos = _listar_arquivos(cat)
        if not arquivos:
            continue
        conteudo = gerar_categoria(cat.name, cat, arquivos)
        out = SAIDA / f"{cat.name}.md"
        out.write_text(conteudo, encoding="utf-8")
        print(f"-> {out} ({len(arquivos)} arquivos)")
        total_geral += len(arquivos)

    print()
    print(f"Total de arquivos processados: {total_geral}")
    print("=" * 60)
    print(" CONCLUIDO")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

```

### `gerar_snapshot_mtf_ia.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_snapshot_mtf_ia.py
========================
Gera um .txt com prompt + candles M5/M15 prontos para colar em uma IA.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from Motor_SMC_Regras import analisar_smc, CONFIG, BRT
from Rodar_SMC_Regras import carregar_multi_mt5

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

SAIDA_TXT = BASE_DIR / "Coletas" / "snapshot_mtf_ia.txt"
SAIDA_JSON = BASE_DIR / "Coletas" / "snapshot_mtf_scripts.json"

ATIVO = "WIN$"


def coletar(qtd_m5, qtd_m15):
    tf_spec = {
        "15m": {"min": 15, "qtd": qtd_m15, "arquivo": ""},
        "5m":  {"min": 5,  "qtd": qtd_m5,  "arquivo": ""},
    }
    return carregar_multi_mt5(ATIVO, tf_spec)


PROMPT_INSTRUCOES = """Voce e um analista institucional de mesa especializado em Smart Money Concepts (SMC/ICT). Sua tarefa e aplicar EXATAMENTE as regras descritas abaixo sobre os candles M15 e M5 do WIN fornecidos.

Nao invente dados. Se faltar informacao, use null. Devolva SOMENTE um bloco JSON no formato especificado no final, sem texto extra.
"""

REGRAS = """## Regras SMC/ICT (replicar identicamente)

### 1. Swings
- Janela: 2 candles a esquerda + 2 a direita
- Swing HIGH: candle[i].high >= max(high[i-2 : i+3])
- Swing LOW:  candle[i].low  <= min(low[i-2 : i+3])
- Equal High/Low (tol 15 pts): dois swings no mesmo nivel

### 2. BOS / CHoCH
- BOS de alta:  close > swing_high anterior, em tendencia de alta
- CHoCH de alta: close > swing_high anterior, em tendencia de baixa
- BOS/CHoCH de baixa: espelhado
- BIAS = direcao do ULTIMO evento de estrutura (BOS/CHoCH)

### 3. FVG (Fair Value Gap)
- Precisa do candle do meio com EXPANSAO FORTE
  (volume >= 1.2x media20 E corpo >= 1.3x media20)
- FVG de COMPRA: candle[i].low > candle[i-2].high, gap >= 20 pts
- FVG de VENDA: candle[i].high < candle[i-2].low, gap >= 20 pts
- Marcar como preenchido se o preco voltar a faixa

### 4. Order Block
- OB de COMPRA: ultimo candle de baixa antes de swing LOW rompido
- OB de VENDA: ultimo candle de alta antes de swing HIGH rompido
- Range do OB >= 30 pts (menor = ruido)
- Validacao: precisa de BOS/CHoCH na direcao alvo em ate 40 candles
- Dedup: OBs a menos de 50 pts (WIN) sao o mesmo bloco

### 5. Liquidez
- BSL: equal highs agrupados (tol 15 pts)
- SSL: equal lows agrupados (tol 15 pts)

### 6. Confluencia OB x POC
- Se OB mais recente esta a <= 300 pts do POC ontem -> confluente

### 7. Confianca ponderada (0-100)
Pesos: bias=25, BOS=20, CHoCH=10, FVG=15, OB=15, OB_confluente=15
Score = soma dos pesos dos criterios ativos / total_possivel * 100

### 8. Consolidacao Multi-Timeframe
- bias_m15, bias_m5 definidos pelo passo 2
- Se M15=M5: veredito ALINHADO
- Se M15!=M5 e um deles LATERAL: veredito PULLBACK
- Se M15!=M5 e ambos direcionais: veredito CONFLITO
"""
FORMATO_SAIDA = """## Formato de saida (JSON exato)

Devolva SOMENTE este JSON, sem texto antes ou depois:

{
  "bias_m15": "ALTA | BAIXA | LATERAL",
  "confianca_m15": 0,
  "bias_m5": "ALTA | BAIXA | LATERAL",
  "confianca_m5": 0,
  "poc_ontem": null,
  "vwap_ontem": null,
  "order_blocks_m15": [],
  "order_blocks_m5": [],
  "fair_value_gaps_m15": [],
  "fair_value_gaps_m5": [],
  "liquidez_m15": {"bsl": [], "ssl": []},
  "liquidez_m5": {"bsl": [], "ssl": []},
  "eventos_m15": [],
  "eventos_m5": [],
  "consolidacao_mtf": {
    "veredito": "ALINHADO_FORTE | PULLBACK | CONFLITO_MACRO | DIVERGENTE | NEUTRO",
    "direcao_dominante": "ALTA | BAIXA | LATERAL",
    "racional": "1-3 linhas"
  }
}
"""


def candles_para_json(candles, max_n=None):
    if max_n and len(candles) > max_n:
        candles = candles[-max_n:]
    return [
        {
            "t": c.get("time", ""),
            "o": round(float(c.get("open", 0)), 0),
            "h": round(float(c.get("high", 0)), 0),
            "l": round(float(c.get("low", 0)), 0),
            "c": round(float(c.get("close", 0)), 0),
            "v": int(float(c.get("volume", 0))),
        }
        for c in candles
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qtd-m5", type=int, default=300)
    ap.add_argument("--qtd-m15", type=int, default=300)
    ap.add_argument("--lookback-m5", type=int, default=120)
    ap.add_argument("--lookback-m15", type=int, default=80)
    ap.add_argument("--no-notepad", action="store_true")
    args = ap.parse_args()

    print("=" * 62)
    print(" GERADOR DE SNAPSHOT MTF PARA IA")
    print("=" * 62)

    print(f"\n-> Coletando {ATIVO}...")
    try:
        coletas = coletar(args.qtd_m5, args.qtd_m15)
    except Exception as e:
        print(f"[ERRO] Coleta MT5: {e}")
        return 1

    candles_5, simb_real = coletas.get("5m", ([], ""))
    candles_15, _ = coletas.get("15m", ([], ""))

    if not candles_5 or not candles_15:
        print("[ERRO] MT5 retornou candles vazios.")
        return 1

    print(f"   [OK] Simbolo: {simb_real}")
    print(f"   [OK] M5:  {len(candles_5)} candles")
    print(f"   [OK] M15: {len(candles_15)} candles")

    print("\n-> Rodando Motor_SMC_Regras em M5 e M15...")
    res_5 = analisar_smc(candles_5, ativo=simb_real or ATIVO, timeframe="5m", config=CONFIG)
    res_15 = analisar_smc(candles_15, ativo=simb_real or ATIVO, timeframe="15m", config=CONFIG)

    m5_ia = candles_para_json(candles_5, max_n=args.lookback_m5)
    m15_ia = candles_para_json(candles_15, max_n=args.lookback_m15)

    poc_ontem = (res_5.get("niveis_institucionais") or {}).get("poc_ontem")
    vwap_ontem = (res_5.get("niveis_institucionais") or {}).get("vwap_ontem")

    ts = datetime.now(BRT).strftime("%d/%m/%Y %H:%M")
    ts_iso = datetime.now(BRT).isoformat(timespec="seconds")

    sep = "=" * 62
    partes = [
        sep,
        f"ANALISE SMC MULTI-TIMEFRAME - {simb_real or ATIVO} ({ts})",
        sep,
        "",
        "[INSTRUCOES]",
        PROMPT_INSTRUCOES.strip(),
        "",
        "[REGRAS SMC/ICT]",
        REGRAS.strip(),
        "",
        "[NIVEIS JA CALCULADOS]",
        f"POC_ONTEM: {poc_ontem:.0f}" if poc_ontem else "POC_ONTEM: null",
        f"VWAP_ONTEM: {vwap_ontem:.1f}" if vwap_ontem else "VWAP_ONTEM: null",
        "",
        f"[CANDLES M15 - ultimos {len(m15_ia)} candles]",
        json.dumps(m15_ia, ensure_ascii=False, separators=(",", ":")),
        "",
        f"[CANDLES M5 - ultimos {len(m5_ia)} candles]",
        json.dumps(m5_ia, ensure_ascii=False, separators=(",", ":")),
        "",
        "[FORMATO DE SAIDA]",
        FORMATO_SAIDA.strip(),
        "",
        sep,
        f"FIM - snapshot gerado em {ts_iso}",
        sep,
    ]

    texto = "\n".join(partes)
    SAIDA_TXT.parent.mkdir(parents=True, exist_ok=True)
    SAIDA_TXT.write_text(texto, encoding="utf-8")

    payload_scripts = {
        "gerado_em": ts_iso,
        "ativo": simb_real or ATIVO,
        "timeframes": {
            "M15": {
                "bias": res_15.get("bias_direcional"),
                "confianca": res_15.get("confianca_visual"),
                "poc_ontem": (res_15.get("niveis_institucionais") or {}).get("poc_ontem"),
                "vwap_ontem": (res_15.get("niveis_institucionais") or {}).get("vwap_ontem"),
                "order_blocks": res_15.get("order_blocks"),
                "fvgs": res_15.get("fair_value_gaps"),
                "liquidez": res_15.get("liquidez"),
                "eventos": res_15.get("eventos_estrutura"),
            },
            "M5": {
                "bias": res_5.get("bias_direcional"),
                "confianca": res_5.get("confianca_visual"),
                "poc_ontem": (res_5.get("niveis_institucionais") or {}).get("poc_ontem"),
                "vwap_ontem": (res_5.get("niveis_institucionais") or {}).get("vwap_ontem"),
                "order_blocks": res_5.get("order_blocks"),
                "fvgs": res_5.get("fair_value_gaps"),
                "liquidez": res_5.get("liquidez"),
                "eventos": res_5.get("eventos_estrutura"),
            },
        },
    }
    SAIDA_JSON.write_text(
        json.dumps(payload_scripts, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("=" * 62)
    print(" SNAPSHOT GERADO")
    print("=" * 62)
    print(f"  TXT (IA)    : {SAIDA_TXT}")
    print(f"  JSON (ref)  : {SAIDA_JSON}")
    print(f"  Tamanho     : {len(texto):,} chars")
    print(f"  M15 candles : {len(m15_ia)}")
    print(f"  M5 candles  : {len(m5_ia)}")
    print(f"  Scripts M15 : {res_15.get('bias_direcional')} ({res_15.get('confianca_visual')}%)")
    print(f"  Scripts M5  : {res_5.get('bias_direcional')} ({res_5.get('confianca_visual')}%)")
    print("=" * 62)

    if not args.no_notepad:
        try:
            import subprocess
            subprocess.Popen(["notepad.exe", str(SAIDA_TXT)])
            print("  [OK] Notepad aberto.")
        except Exception as e:
            print(f"  [AVISO] {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

```

### `main_pipeline.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: main_pipeline.py (Versão V2.1 - Ordem Corrigida)
Objetivo: Orquestrar e disparar as tarefas garantindo rigor na cadeia de dependência dos arquivos JSON.

Correção v2.1:
- Orquestrador Final Decisao_V2 roda ANTES do Relatório e da Gravação Histórica
- Relatório e Sessão passam a ler o Decisao_V2.json já atualizado no ciclo atual
"""

import asyncio
import importlib
import logging
import os
import time
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

# Forca UTF-8 em TODOS os subprocess filhos (evita UnicodeEncodeError com
# emojis no cp1252 do Windows). Setar no processo pai faz o filho herdar.
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

# Configuração detalhada de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Imports dos módulos operacionais do pipeline
import Limpar_Imagens_TradingView
import Coletor
import Coleta_Noticias_Calendario
import Analise_Noticias
import Validador
import Rodar_SMC_Regras
import Calculadora
import CalculadoraEstimativaAbertura
import Gerar_Resultado_Operacional_Abertura
import Gerar_Relatorio_Mensagem
import v2_gravar_sessao_win
import v2_rodar_decisao_completa


def run_sync_module(module_object, name: str):
    """
    Executor dinâmico para módulos síncronos.
    Tenta invocar .main(), .executar(), .run(). Caso o script execute o código
    diretamente no bloco `if __name__ == '__main__'`, ele roda via subprocess.

    Quando roda via subprocess, captura stdout/stderr e exibe o traceback real
    do script filho em caso de falha (evita "returned non-zero exit status 1"
    sem contexto).
    """
    start = time.perf_counter()
    logging.info(f"🚀 Iniciando: {name}")
    try:
        if hasattr(module_object, "main") and callable(module_object.main):
            module_object.main()
        elif hasattr(module_object, "executar") and callable(module_object.executar):
            module_object.executar()
        elif hasattr(module_object, "run") and callable(module_object.run):
            module_object.run()
        else:
            script_path = getattr(module_object, "__file__", None)
            if script_path:
                # Captura stdout/stderr para exibir erro real do script filho
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if result.returncode != 0:
                    logging.error(
                        f"❌ Subprocess '{name}' falhou (exit {result.returncode})"
                    )
                    if result.stdout:
                        logging.error(f"--- STDOUT ---\n{result.stdout}")
                    if result.stderr:
                        logging.error(f"--- STDERR ---\n{result.stderr}")
                    raise subprocess.CalledProcessError(
                        result.returncode, result.args, result.stdout, result.stderr
                    )
            else:
                importlib.reload(module_object)

        elapsed = time.perf_counter() - start
        logging.info(f"✅ Concluído: {name} em {elapsed:.2f}s")
    except Exception as e:
        logging.error(f"❌ Erro crítico na execução de {name}: {e}", exc_info=True)
        raise e


async def main_pipeline_async():
    pipeline_start = time.perf_counter()
    logging.info("=== INICIANDO PIPELINE V2 (ASSÍNCRONO / PARALELO) ===")

    loop = asyncio.get_running_loop()

    with ThreadPoolExecutor(max_workers=6) as pool:

        # -------------------------------------------------------------
        # FASE 1: Limpeza e Preparação (Sequencial)
        # -------------------------------------------------------------
        await loop.run_in_executor(pool, run_sync_module, Limpar_Imagens_TradingView, "Limpeza de Imagens")

        # -------------------------------------------------------------
        # FASE 2: Coletas de Dados Em Paralelo (APIs + MT5)
        # -------------------------------------------------------------
        logging.info("📡 Disparando coletas paralelas (APIs/MT5 + Notícias/Calendário)...")

        task_coletor = loop.run_in_executor(pool, run_sync_module, Coletor, "Coletor Cotações/APIs")
        task_noticias = loop.run_in_executor(pool, run_sync_module, Coleta_Noticias_Calendario, "Coleta Notícias/Calendário")

        await asyncio.gather(task_coletor, task_noticias)

        # -------------------------------------------------------------
        # FASE 3: Processamento, Sanitização e Motor SMC (Estrutura Básica)
        # -------------------------------------------------------------
        await loop.run_in_executor(pool, run_sync_module, Analise_Noticias, "Análise Quantitativa de Notícias")
        await loop.run_in_executor(pool, run_sync_module, Validador, "Validador de Dados (34 Ativos)")

        # 💡 AJUSTE CRÍTICO: Roda o SMC AQUI para gerar a POC/VWAP antes das calculadoras
        await loop.run_in_executor(pool, run_sync_module, Rodar_SMC_Regras, "Motor SMC & ICT Regras (POC / VWAP)")

        # -------------------------------------------------------------
        # FASE 4: Motores de Cálculo Em Paralelo (Consumindo Dados Validados + SMC)
        # -------------------------------------------------------------
        logging.info("🧮 Processando calculadoras em paralelo...")

        task_calc_macro = loop.run_in_executor(pool, run_sync_module, Calculadora, "Calculadora (Spreads/DI/Macro)")
        task_calc_abertura = loop.run_in_executor(pool, run_sync_module, CalculadoraEstimativaAbertura, "Estimativa de Abertura & Cost of Carry")

        await asyncio.gather(task_calc_macro, task_calc_abertura)

        # -------------------------------------------------------------
        # FASE 5: Consolidação Operacional de Payload
        # -------------------------------------------------------------
        await loop.run_in_executor(pool, run_sync_module, Gerar_Resultado_Operacional_Abertura, "Consolidação de Payload Operacional")

        # -------------------------------------------------------------
        # FASE 6: Decisão Final V2 (gera Decisao_V2.json ANTES dos consumidores)
        # -------------------------------------------------------------
        logging.info("🧠 Consolidando decisão final V2...")
        await loop.run_in_executor(pool, run_sync_module, v2_rodar_decisao_completa, "Orquestrador Final Decisao_V2")

        # -------------------------------------------------------------
        # FASE 7: Relatórios e Gravação de Histórico
        # (em paralelo, lendo o Decisao_V2.json JÁ ATUALIZADO)
        # -------------------------------------------------------------
        logging.info("📝 Gerando relatórios e registrando sessão...")

        task_relatorio = loop.run_in_executor(pool, run_sync_module, Gerar_Relatorio_Mensagem, "Relatório em Markdown")
        task_sessao = loop.run_in_executor(pool, run_sync_module, v2_gravar_sessao_win, "Gravação Histórica da Sessão")

        await asyncio.gather(task_relatorio, task_sessao)

    total_time = time.perf_counter() - pipeline_start
    logging.info(f"🎉 PIPELINE V2 CONCLUÍDO COM SUCESSO EM {total_time:.2f} SEGUNDOS!")


if __name__ == "__main__":
    try:
        asyncio.run(main_pipeline_async())
    except Exception as e:
        logging.critical(f"💥 Falha fatal na execução do pipeline: {e}")
```

### `requirements.txt`

```text
# ============================================================
# REQUIREMENTS.TXT - ANALISADOR FINANCEIRO (OTIMIZADO)
# ============================================================
# Apenas bibliotecas realmente usadas pelo app
# ============================================================

# Interface e Dashboard
streamlit>=1.28.0

# Análise de Dados
pandas>=2.0.0
numpy>=1.24.0
yfinance>=0.2.28

# Visualização
plotly>=5.14.0
matplotlib>=3.7.0

# Inteligência Artificial
openai>=1.0.0
google-generativeai>=0.8.0
groq>=1.0.0

# Visão Computacional e Imagens
pillow>=10.0.0
pytesseract>=0.3.0

# Web Scraping e Coleta
beautifulsoup4>=4.12.0
selenium>=4.15.0
requests>=2.31.0
requests-html>=0.10.0

# Automação e Agendamento
schedule>=1.2.0

# Manipulação de Arquivos
openpyxl>=3.1.0

# Utilitários
python-dotenv>=1.0.0
click>=8.1.0
loguru>=0.7.0
pydantic>=2.0.0
python-dateutil>=2.8.0


# Conexao MT5 (Genial)
MetaTrader5>=5.0.45

# OCR e captura de tela (sniper de leilao)
mss>=9.0.0
opencv-python>=4.8.0

# Config (motor_score.py)
PyYAML>=6.0
streamlit-autorefresh==1.0.1

```

### `v2_gravar_sessao_win.py`

```python
# ============================================================
# ARQUIVO: v2_gravar_sessao_win.py
# FASE 5/7 — Etapa do pipeline: grava WinSession + cenário
#
# Uso:
#   1. Rodar isolado:  python v2_gravar_sessao_win.py
#   2. No main_pipeline.py, incluir na lista de etapas, por exemplo:
#      ("10 - V2 SESSAO WINFUT", "v2_gravar_sessao_win.py"),
#
# Não altera a V1. Falhas aqui não devem derrubar o pipeline
# se você preferir: troque raise por log e return.
# ============================================================

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def main() -> int:
    print("=" * 60)
    print(" V2 — Gravação de sessão WINFUT")
    print("=" * 60)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Montando WinSession...")

    try:
        from v2.core.services.win_session_builder import build_win_session
        from v2.core.engines.opening_scenario_engine import gerar_cenario_abertura
        from v2.core.services.session_history import salvar_sessao_hoje
    except ImportError as e:
        print(f"❌ Import V2 falhou: {e}")
        print("   Verifique se a pasta v2/ está na raiz do projeto.")
        return 1

    try:
        session = build_win_session()
        cenario = gerar_cenario_abertura(session)
        session.cenario = cenario

        caminho = salvar_sessao_hoje(session, cenario, tag="pipeline")

        print(f"Contrato     : {session.metadata.contrato_principal}")
        print(f"Ajuste       : {session.precos.ajuste}")
        print(f"Last MT5     : {session.precos.last_mt5}")
        print(f"Distância    : {session.distancias.last_vs_ajuste_pts} pts")
        print(f"Posição      : {cenario.relacao_com_ajuste.posicao}")
        print(f"Direção      : {cenario.direcao_provavel}")
        print(f"Notícias     : {session.noticias.classificacao_risco} "
              f"(impacto={session.noticias.impacto_total})")
        print(f"✅ Histórico  : {caminho}")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"❌ Erro ao gravar sessão V2: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

```

### `v2_rodar_decisao_completa.py`

```python
# ============================================================
# v2_rodar_decisao_completa.py  (raiz do projeto)
# ============================================================

from __future__ import annotations

import sys
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def main() -> int:
    print("=" * 60)
    print(" V2 — Decisão Completa (Confluence + Decision + Session)")
    print("=" * 60)

    try:
        from v2.core.engines.v2_orchestrator import executar_v2
    except ImportError as e:
        print(f"❌ Import V2 falhou: {e}")
        traceback.print_exc()
        return 1

    try:
        resultado = executar_v2(salvar_historico=True)
    except Exception as e:
        print(f"❌ Erro na execução V2: {e}")
        traceback.print_exc()
        return 1

    decisao = resultado.get("decisao") or {}
    if not isinstance(decisao, dict):
        decisao = {}

    print()
    print(f"Viés final     : {decisao.get('vies_final')}")
    print(f"Confiança      : {decisao.get('confianca')}%")
    print(f"Entrada        : {decisao.get('entrada')}")
    print(f"Stop           : {decisao.get('stop_loss')}")
    print(f"Alvo 1 / Alvo 2: {decisao.get('alvo_1')} / {decisao.get('alvo_2')}")
    print(f"Invalidação    : {decisao.get('invalidacao')}")

    ctx = resultado.get("contextos") or {}
    print(
        "Contextos      : "
        f"market={ctx.get('market_ok')} pred={ctx.get('prediction_ok')} "
        f"news={ctx.get('news_ok')} vision={ctx.get('vision_ok')} "
        f"session={ctx.get('session_ok')}"
    )
    erros = resultado.get("erros") or []
    if erros:
        print("Avisos:")
        for e in erros:
            print(f"   - {e}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

### `win_abertura_sniper.py`

```python
import cv2
import numpy as np
import mss
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import time
import re
import csv
import os
import json
import shutil
from datetime import datetime, time as dt_time
from collections import deque

# ==================== CONFIGURAÇÕES DE PASTAS ====================
PASTA_COLETAS = "Coletas"
PASTA_HISTORICO = os.path.join(PASTA_COLETAS, "coleta_preco_teorico_historico")
os.makedirs(PASTA_COLETAS, exist_ok=True)
os.makedirs(PASTA_HISTORICO, exist_ok=True)

ARQUIVO_CSV = os.path.join(PASTA_COLETAS, "preco_teorico_win_fluxo.csv")
ARQUIVO_CONFIG = os.path.join(PASTA_COLETAS, "config_regiao.json")
ARQUIVO_JSON_MACRO = os.path.join(PASTA_COLETAS, "DadosAtivosUnificados.json")
ARQUIVO_JSON_SMC = os.path.join(PASTA_COLETAS, "AnaliseGraficaSMC_Regras.json")

# Configurações do Leitor
INTERVALO = 0.25
TAMANHO_JANELA_TENDENCIA = 40  # ~10 segundos de memória do leilão
INTERVALO_FORCAR_GRAVACAO = 10.0  # segundos

# ============================================================
# FILTRO DE SANIDADE DO PREÇO
# ============================================================
# Limite absoluto: WIN nunca esteve fora dessa faixa na história
PRECO_MIN_ABSOLUTO = 50000
PRECO_MAX_ABSOLUTO = 300000

# Salto máximo aceito (em pontos) entre leituras consecutivas.
# Para replay acelerado, aumentar (ex: 2000). Para mercado real, 500 é OK.
LIMITE_SALTO_PTS = 1000

# Quantas leituras anteriores usar como referência de "regime atual"
JANELA_REFERENCIA = 5

# Janela de LEILÃO — durante esse período o preço teórico oscila MUITO
# (é descoberta de preço). O filtro de salto vs mediana é DESABILITADO.
LEILAO_INICIO = dt_time(8, 50)
LEILAO_FIM = dt_time(9, 5)


def _esta_no_leilao() -> bool:
    """True se estiver na janela de leilão (08:50–09:05)."""
    agora = datetime.now().time()
    return LEILAO_INICIO <= agora <= LEILAO_FIM
# ============================================================

# TRATAMENTO DINÂMICO DO TESSERACT
tesseract_bin = shutil.which("tesseract")
if tesseract_bin:
    pytesseract.pytesseract.tesseract_cmd = tesseract_bin
else:
    caminhos_padrao = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        os.path.expanduser(r'~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe')
    ]
    for caminho in caminhos_padrao:
        if os.path.exists(caminho):
            pytesseract.pytesseract.tesseract_cmd = caminho
            break
# =================================================================


# ============================================================
# ROTAÇÃO DIÁRIA DO CSV
# ============================================================
def _parse_data(texto: str):
    texto = texto.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    return None


def _ultima_data_no_csv() -> datetime:
    if not os.path.exists(ARQUIVO_CSV):
        return None

    ultima = None
    try:
        with open(ARQUIVO_CSV, "r", encoding="utf-8-sig") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or not linha[0].isdigit():
                    continue
                partes = linha.split(",")
                if not partes:
                    continue
                dt = _parse_data(partes[0])
                if dt:
                    ultima = dt
    except Exception:
        return None

    return ultima


def rotacionar_csv_se_necessario():
    ultima_data = _ultima_data_no_csv()
    if ultima_data is None:
        return

    hoje = datetime.now().date()
    if ultima_data.date() == hoje:
        return

    data_ref = ultima_data.date().isoformat()
    nome_hist = f"preco_teorico_{data_ref}.csv"
    destino = os.path.join(PASTA_HISTORICO, nome_hist)

    if os.path.exists(destino):
        try:
            with open(destino, "r", encoding="utf-8-sig") as f:
                linhas_hist = f.readlines()
            with open(ARQUIVO_CSV, "r", encoding="utf-8-sig") as f:
                linhas_novas = f.readlines()

            if linhas_novas and linhas_novas[0].lower().startswith("datahora"):
                linhas_novas = linhas_novas[1:]

            with open(destino, "w", encoding="utf-8") as f:
                f.writelines(linhas_hist)
                f.writelines(linhas_novas)

            os.remove(ARQUIVO_CSV)
            print(f"📦 CSV rotacionado (concat): {nome_hist} (+{len(linhas_novas)} linhas)")
        except Exception as e:
            print(f"⚠️ Falha ao concatenar: {e}")
    else:
        try:
            shutil.move(ARQUIVO_CSV, destino)
            print(f"📦 CSV rotacionado: {nome_hist}")
        except Exception as e:
            print(f"⚠️ Falha ao mover: {e}")
# ============================================================


# ============================================================
# FILTRO DE SANIDADE DO PREÇO
# ============================================================
class FiltroPreco:
    """
    Filtra leituras absurdas do OCR.

    Comportamento:
      - Durante o leilão (08:50–09:05): valida APENAS faixa absoluta.
        O preço teórico pode ir de 187k → 200k → 185k em segundos — isso
        é descoberta de preço, NÃO ruído. Não usar mediana móvel.
      - Fora do leilão: valida faixa absoluta + salto vs mediana.

    Contadores internos (para relatório final):
      - rejeicoes_absoluta: quantas vezes caiu fora de [MIN, MAX]
      - rejeicoes_mediana:  quantas vezes passou da faixa absoluta mas
                            foi rejeitada por salto vs mediana
    """

    def __init__(self):
        self.ultimos_aceitos = deque(maxlen=JANELA_REFERENCIA)
        self.modo_leilao = False
        self.rejeicoes_absoluta = 0
        self.rejeicoes_mediana = 0

    def aceitar(self, preco: int) -> tuple:
        """
        Retorna (aceitar: bool, motivo: str).
        """
        no_leilao = _esta_no_leilao()

        # Detecta transição de modo (log único)
        if no_leilao != self.modo_leilao:
            if no_leilao:
                print("[FILTRO] Entrando em modo LEILÃO — filtro de salto DESABILITADO")
                self.ultimos_aceitos.clear()
            else:
                print("[FILTRO] Saindo do leilão — filtro de salto REATIVADO")
            self.modo_leilao = no_leilao

        # Camada 1 — faixa absoluta (sempre aplica)
        if preco < PRECO_MIN_ABSOLUTO or preco > PRECO_MAX_ABSOLUTO:
            self.rejeicoes_absoluta += 1
            return False, f"fora da faixa absoluta [{PRECO_MIN_ABSOLUTO}, {PRECO_MAX_ABSOLUTO}]"

        # Camada 2 — salto vs mediana (só FORA do leilão)
        if no_leilao:
            self.ultimos_aceitos.append(preco)
            return True, "OK_LEILAO"

        # Sem histórico → aceita
        if not self.ultimos_aceitos:
            self.ultimos_aceitos.append(preco)
            return True, "primeira leitura"

        # Regra 2: comparar com mediana
        lista_ordenada = sorted(self.ultimos_aceitos)
        n = len(lista_ordenada)
        if n % 2 == 1:
            mediana = lista_ordenada[n // 2]
        else:
            mediana = (lista_ordenada[n // 2 - 1] + lista_ordenada[n // 2]) / 2

        delta = abs(preco - mediana)
        if delta > LIMITE_SALTO_PTS:
            self.rejeicoes_mediana += 1
            return False, f"salto de {delta:+.0f} pts da mediana {mediana:.0f}"

        self.ultimos_aceitos.append(preco)
        return True, "OK"

    def resetar(self):
        self.ultimos_aceitos.clear()
# ============================================================


def carregar_contextos():
    contexto = {
        "vies_macro": "NEUTRO",
        "score_macro": 0,
        "win_ajuste": 0,
        "win_fechamento": 0,
        "vies_smc": "NEUTRO",
        "poc_ontem": 0,
    }

    try:
        with open(ARQUIVO_JSON_MACRO, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            ativos = dados.get("ativos", {})
            ewz_var = ativos.get("EWZ", {}).get("variacao_pct", 0)
            sp500_var = ativos.get("SP500_FUT", {}).get("variacao_pct", 0)
            petr_var = ativos.get("PETR_ADR", {}).get("variacao_pct", 0)
            vale_var = ativos.get("VALE_ADR", {}).get("variacao_pct", 0)

            contexto["win_ajuste"] = ativos.get("WIN_AJUSTE", {}).get("preco", 0)
            contexto["win_fechamento"] = ativos.get("WIN_LAST_TICK", {}).get("preco", 0)

            score = ((ewz_var * 2) + sp500_var + petr_var + vale_var) / 5
            contexto["score_macro"] = score
            if score > 0.4:
                contexto["vies_macro"] = "ALTA"
            elif score < -0.4:
                contexto["vies_macro"] = "BAIXA"
    except Exception as e:
        print(f"[AVISO] Falha ao ler Macro: {e}")

    try:
        with open(ARQUIVO_JSON_SMC, 'r', encoding='utf-8') as f:
            smc = json.load(f)
            contexto["poc_ontem"] = smc.get("niveis_institucionais", {}).get("poc_ontem", 0)
            contexto["vies_smc"] = smc.get("bias_direcional", "NEUTRO")
    except Exception as e:
        print(f"[AVISO] Falha ao ler SMC: {e}")

    return contexto


def calcular_confluencia(preco_teorico, contexto, tendencia_micro):
    ajuste = contexto["win_ajuste"]
    fechamento = contexto["win_fechamento"]
    poc = contexto["poc_ontem"]

    gap_ajuste_pts = preco_teorico - ajuste if ajuste > 0 else 0
    gap_fechamento_pts = preco_teorico - fechamento if fechamento > 0 else 0
    distancia_poc = preco_teorico - poc if poc > 0 else 0

    posicao_ajuste = "ACIMA" if gap_ajuste_pts > 0 else "ABAIXO" if gap_ajuste_pts < 0 else "NO AJUSTE"
    posicao_fechamento = "ACIMA" if gap_fechamento_pts > 0 else "ABAIXO" if gap_fechamento_pts < 0 else "NO FECHAMENTO"
    posicao_poc = "ACIMA" if distancia_poc > 0 else "ABAIXO" if distancia_poc < 0 else "NA POC"

    vies_geral = contexto["vies_macro"]
    if contexto["vies_macro"] == "ALTA" and contexto["vies_smc"] == "ALTA":
        vies_geral = "FORTE ALTA"
    elif contexto["vies_macro"] == "BAIXA" and contexto["vies_smc"] == "BAIXA":
        vies_geral = "FORTE BAIXA"

    veredito = "AGUARDAR 🕒"
    if "ALTA" in vies_geral and tendencia_micro == "ALTA":
        veredito = "🟢 COMPRA A MERCADO (Confluência Macro + Fluxo)"
    elif "BAIXA" in vies_geral and tendencia_micro == "BAIXA":
        veredito = "🔴 VENDA A MERCADO (Confluência Macro + Fluxo)"
    elif tendencia_micro != "LATERAL":
        veredito = "⚠️ ALERTA DE FINTA (Fluxo divergente do Macro)"

    return gap_ajuste_pts, posicao_ajuste, gap_fechamento_pts, posicao_fechamento, distancia_poc, posicao_poc, veredito, vies_geral


def melhorar_para_ocr(img_pil):
    img = img_pil.convert('L')
    img = ImageEnhance.Contrast(img).enhance(3.0)
    img = img.filter(ImageFilter.SHARPEN)
    w, h = img.size
    return img.resize((w * 4, h * 4), Image.LANCZOS)


def extrair_numero(img_pil):
    try:
        img_proc = melhorar_para_ocr(img_pil)
        # PSM 8 (single word) — melhor pra essa fonte do MT5
        config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789.'
        texto_bruto = pytesseract.image_to_string(img_proc, config=config).strip()

        # Aceita padrão "189.142" ou "189142.00"
        # Primeiro tenta o formato com ponto de milhar
        match = re.search(r'(\d{3})\.(\d{3})', texto_bruto)
        if match:
            valor_str = match.group(1) + match.group(2)
            preco_int = int(valor_str)
            if 70000 < preco_int < 300000:
                return preco_int, 0.95

        # Fallback: 6 dígitos seguidos (ex: "189142")
        match6 = re.search(r'\d{6}', texto_bruto.replace(".", "").replace(",", ""))
        if match6:
            preco_int = int(match6.group(0))
            if 70000 < preco_int < 300000:
                return preco_int, 0.90
    except:
        pass
    return None, 0.0


def capturar_regiao(regiao):
    with mss.MSS() as sct:
        img = sct.grab(regiao)
        return Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")


def _regiao_e_azul_leilao(pil_image, threshold: float = 0.40) -> bool:
    """
    Detecta se a regiao tem fundo AZUL caracteristico da barra de leilao.

    Estrategia:
      - Reduz a imagem para 10x10 (rapido, robusto a ruido)
      - Conta pixels com B alto e dominante (R e G baixos)
      - Se a fracao de pixels azuis >= threshold, considera leilao ativo

    Args:
        pil_image: imagem capturada (PIL)
        threshold: fracao minima de pixels azuis (default 0.40)

    Returns:
        True se a regiao e predominantemente azul, False caso contrario.
    """
    try:
        small = pil_image.resize((10, 10))
        pixels = list(small.getdata())
        total = len(pixels)
        if total == 0:
            return False

        azuis = 0
        for r, g, b in pixels:
            # Azul do leilao (aprox RGB 30-80, 130-180, 220-255)
            # Regra: B alto E B > R+40 E B > G+30
            if b > 120 and b > (r + 40) and b > (g + 30):
                azuis += 1

        fracao = azuis / total
        return fracao >= threshold
    except Exception:
        # Em caso de erro, assume "nao leilao" (conservador)
        return False


def analisar_fluxo(historico):
    if len(historico) < 10:
        return "LATERAL", 0
    metade = len(historico) // 2
    media_antiga = sum(list(historico)[:metade]) / metade
    media_recente = sum(list(historico)[metade:]) / (len(historico) - metade)
    dif = media_recente - media_antiga
    if dif > 2.5:
        return "ALTA", dif
    if dif < -2.5:
        return "BAIXA", dif
    return "LATERAL", dif


def salvar_csv(preco, confianca, motivo="MUDANCA"):
    existe = os.path.isfile(ARQUIVO_CSV)
    with open(ARQUIVO_CSV, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(["DataHora", "PrecoTeorico", "Confianca", "Motivo"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            preco,
            f"{confianca:.3f}",
            motivo,
        ])


def main():
    print("=" * 60)
    print(" 🎯 SNIPER DE LEILÃO (ÂNCORA NO PONTO) ")
    print("=" * 60)
    print(f" Modo: gravação por MUDANÇA + força a cada {INTERVALO_FORCAR_GRAVACAO:.0f}s")
    print(f" Filtro: faixa [{PRECO_MIN_ABSOLUTO}, {PRECO_MAX_ABSOLUTO}] | salto máx {LIMITE_SALTO_PTS} pts")
    print(f" Leilão: filtro de salto DESABILITADO entre {LEILAO_INICIO.strftime('%H:%M')} e {LEILAO_FIM.strftime('%H:%M')}")
    print(f" Rotação: CSV por dia em '{PASTA_HISTORICO}/'")
    print("=" * 60)

    rotacionar_csv_se_necessario()

    if not os.path.exists(ARQUIVO_CONFIG):
        print(f"[ERRO CRÍTICO] Arquivo de mapeamento '{ARQUIVO_CONFIG}' não encontrado!")
        return

    with open(ARQUIVO_CONFIG, 'r', encoding='utf-8') as f:
        regiao = json.load(f)
    print(f"[OK] Coordenadas carregadas: {regiao}")

    contexto = carregar_contextos()
    print(f"[INFO] Macro Vies: {contexto['vies_macro']} | SMC Vies: {contexto['vies_smc']}")
    print(f"[INFO] Ajuste: {contexto['win_ajuste']} | Fechamento: {contexto['win_fechamento']} | POC: {contexto['poc_ontem']}")

    print("\n" + "=" * 60)
    print(" 🚀 MONITORAMENTO DE LEILÃO ATIVO (Pressione CTRL+C p/ sair)")
    print("=" * 60 + "\n")

    ultimo_preco = None
    ultimo_salvamento_dt = None
    historico = deque(maxlen=TAMANHO_JANELA_TENDENCIA)
    filtro = FiltroPreco()

    total_tentativas = 0
    total_leituras_ok = 0
    total_leituras_falhas = 0
    total_rejeitadas_filtro = 0
    total_mudanca = 0
    total_forcado = 0

    # Contador de ciclos fora do leilao (para relatorio final)
    total_fora_leilao = 0
    ultimo_estado_azul = None  # None | True | False

    try:
        while True:
            img = capturar_regiao(regiao)
            agora_dt = datetime.now()
            agora = agora_dt.strftime('%H:%M:%S')

            # ---- Deteccao de leilao por cor de fundo ----
            azul = _regiao_e_azul_leilao(img)

            # Log so na transicao (nao spamma)
            if azul != ultimo_estado_azul:
                if azul:
                    print(f"[{agora}] 🟦 [LEILAO] Barra azul detectada — OCR ATIVO")
                else:
                    print(f"[{agora}] ⬛ [LEILAO] Barra azul ausente — OCR PAUSADO")
                ultimo_estado_azul = azul

            if not azul:
                total_fora_leilao += 1
                print(f"[{agora}] Fora do leilao (sem fundo azul)", end="\r")
                time.sleep(INTERVALO)
                continue

            # ---- Leilao ativo: roda OCR normal ----
            preco, conf = extrair_numero(img)
            total_tentativas += 1

            if preco:
                # ---- FILTRO DE SANIDADE ----
                aceitar, motivo_filtro = filtro.aceitar(preco)

                if not aceitar:
                    total_rejeitadas_filtro += 1
                    print(
                        f"[{agora}] 🚫 Preço rejeitado: {preco} ({motivo_filtro})",
                        end="\r",
                    )
                    time.sleep(INTERVALO)
                    continue

                total_leituras_ok += 1
                historico.append(preco)
                tendencia_micro, forca = analisar_fluxo(historico)

                mudou = (preco != ultimo_preco)
                precisa_forcar = (
                    ultimo_salvamento_dt is not None
                    and (agora_dt - ultimo_salvamento_dt).total_seconds() >= INTERVALO_FORCAR_GRAVACAO
                )

                if mudou or precisa_forcar:
                    # Marca motivo base
                    if mudou:
                        motivo_base = "MUDANCA"
                        total_mudanca += 1
                    else:
                        motivo_base = "FORCADO_TEMPO"
                        total_forcado += 1

                    # Sufixo [MODO_LEILAO] quando aplicável
                    if _esta_no_leilao():
                        motivo = f"{motivo_base}_LEILAO"
                    else:
                        motivo = motivo_base

                    gap_ajuste, pos_ajuste, gap_fechamento, pos_fechamento, dist_poc, pos_poc, veredito, vies_geral = calcular_confluencia(preco, contexto, tendencia_micro)

                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"=== 🕒 {agora} | PREVISÃO DE ABERTURA === [{motivo}]")
                    print(f"💰 PREÇO TEÓRICO : {preco} (Conf: {conf:.2f})")
                    print(f"📊 GAP DO AJUSTE : {gap_ajuste:+.0f} pts [{pos_ajuste}]")
                    print(f"📉 GAP DO FECHTO : {gap_fechamento:+.0f} pts [{pos_fechamento}]")
                    print(f"🏢 DISTÂNCIA POC : {dist_poc:+.0f} pts [{pos_poc}]")
                    print(f"🌊 MICROFLUXO    : {tendencia_micro} (Força/Aceleração: {forca:+.1f})")
                    print("-" * 40)
                    print(f"🎯 VEREDITO      : {veredito}")
                    print("=" * 40)

                    if motivo_base == "FORCADO_TEMPO":
                        print(f"⏱️  Gravação forçada: preço estável há {INTERVALO_FORCAR_GRAVACAO:.0f}s")
                    if _esta_no_leilao():
                        print(f"🎪 Modo LEILÃO ativo — filtro de salto relaxado")

                    print(
                        f"📊 Stats: {total_tentativas} tent | {total_leituras_ok} OK | "
                        f"{total_leituras_falhas} falhas OCR | "
                        f"{total_rejeitadas_filtro} rejeitadas filtro | "
                        f"{total_mudanca} mudança | {total_forcado} tempo"
                    )

                    salvar_csv(preco, conf, motivo)
                    ultimo_preco = preco
                    ultimo_salvamento_dt = agora_dt

            else:
                total_leituras_falhas += 1
                print(f"[{agora}] Buscando âncora do ponto (.) na região...", end="\r")

            time.sleep(INTERVALO)

    except KeyboardInterrupt:
        print(f"\n\nFinalizado! Dados armazenados em {PASTA_COLETAS}/")
        print("=" * 60)
        print(" 📊 ESTATÍSTICAS FINAIS")
        print("=" * 60)
        print(f"  Tentativas totais       : {total_tentativas}")
        print(f"  Leituras OK (aceitas)   : {total_leituras_ok}")
        print(f"  Leituras com falha OCR  : {total_leituras_falhas}")
        print(f"  Rejeitadas pelo filtro  : {total_rejeitadas_filtro}")
        print(f"      ├─ fora faixa abs.  : {filtro.rejeicoes_absoluta}")
        print(f"      └─ salto vs mediana : {filtro.rejeicoes_mediana}")
        print(f"  Ciclos fora do leilao   : {total_fora_leilao}")
        print(f"  Gravações por mudança   : {total_mudanca}")
        print(f"  Gravações forçadas      : {total_forcado}")
        print(f"  Total gravado no CSV    : {total_mudanca + total_forcado}")
        print("=" * 60)


if __name__ == "__main__":
    main()
    
```
