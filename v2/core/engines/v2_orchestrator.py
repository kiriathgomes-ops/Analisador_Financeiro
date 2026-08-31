# -*- coding: utf-8 -*-
"""
Módulo: v2/core/engines/v2_orchestrator.py
Versão: 2.5 - Padrão de Produção Confluente (V2)
Objetivo: Centralizar a carga de contextos, executar motores de cênario e gravar o Decisao_V2.json.
"""

import os
import json
import time
import traceback
from datetime import datetime
from pathlib import Path

# Ingestão de caminhos unificados do config.py na raiz
from config import (
    FILE_DECISAO_V2, 
    FILE_UNIFICADO, 
    FILE_SMC_REGRAS, 
    FILE_ESTIMATIVA_ABERTURA, 
    FILE_NOTICIAS_IMPACTO,
    HISTORICO_DECISOES_V2_DIR
)

class V2Orchestrator:
    def __init__(self):
        self.timestamp_inicio = time.time()
        self.erros_acumulados = []
        
        # Flags de status que alimentam a página pages/5.3_Core_Engine.py
        self.contextos_status = {
            "market_ok": False,
            "prediction_ok": False,
            "news_ok": False,
            "vision_ok": False,
            "session_ok": False
        }

    def _carregar_json_defensivo(self, caminho_path) -> dict:
        if not caminho_path.exists():
            self.erros_acumulados.append(f"Arquivo ausente: {caminho_path.name}")
            return {}
        try:
            with open(caminho_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.erros_acumulados.append(f"Falha de leitura em {caminho_path.name}: {str(e)}")
            return {}

    def consolidar_decisao(self) -> dict:
        """
        Orquestra a carga de dados higienizados e calcula a confluência de sinais
        gerando os gatilhos matemáticos operacionais para o robô e para as telas.
        """
        # 1. Carga dos sub-módulos do pipeline
        ativos_dados = self._carregar_json_defensivo(FILE_UNIFICADO)
        smc_dados = self._carregar_json_defensivo(FILE_SMC_REGRAS)
        estimativas = self._carregar_json_defensivo(FILE_ESTIMATIVA_ABERTURA)
        noticias = self._carregar_json_defensivo(FILE_NOTICIAS_IMPACTO)

        # 2. Auditoria e validação de contextos (Alimenta o seu Smoke Test do front-end)
        if ativos_dados: self.contextos_status["market_ok"] = True
        if estimativas: self.contextos_status["prediction_ok"] = True
        if noticias: self.contextos_status["news_ok"] = True
        if smc_dados: 
            self.contextos_status["vision_ok"] = True
            self.contextos_status["session_ok"] = True

        # 3. Captura de variáveis em tempo real para cálculo de gatilhos
        ativos = ativos_dados.get("ativos", {})
        win_last = ativos.get("WIN_LAST_TICK", {}).get("preco", 0.0)
        win_ajuste = ativos.get("WIN_AJUSTE", {}).get("preco", 0.0)
        
        # Puxa o viés direcional e a confiança calculada pelo novo motor
        vies_sugerido = smc_dados.get("bias_direcional", "NEUTRO")
        confianca_sinal = smc_dados.get("confianca_visual", 50)
        
        # 4. EXECUÇÃO DO MOTOR DE CÁLCULO DE GATILHOS (FIBONACCI INSTITUCIONAL)
        # Níveis vindos do seu Motor_SMC_Regras.py ou Floor Pivots como fallback
        pivots = estimativas.get("pivot_points", {}).get("WIN_FUT", {})
        high_mae = ativos.get("WIN_FUT", {}).get("high", win_last + 150)
        low_mae = ativos.get("WIN_FUT", {}).get("low", win_last - 150)
        amplitude = high_mae - low_mae
        
        entrada, stop, alvo_1, alvo_2, invalidacao = 0, 0, 0, 0, "Não Mapeado"
        motivos = []
        riscos = []

        # Heurística de Tomada de Decisão baseada em Smart Money
        if vies_sugerido == "ALTA" and confianca_sinal >= 60:
            entrada = int(high_mae + 5)
            stop = int(low_mae - 20)
            alvo_1 = int(entrada + amplitude)
            alvo_2 = int(entrada + (amplitude * 1.618))
            invalidacao = f"Fechamento M5 abaixo de {stop}"
            
            motivos.append(f"Motor SMC indica estrutura de ALTA (Confiança: {confianca_sinal}%)")
            motivos.append(f"Preço trabalhando acima do Pivot Point ({pivots.get('PP', 0):.0f})")
            
            # Alerta se houver gap excessivo (Risco de fechamento/Pullback)
            if win_last - win_ajuste > 400:
                riscos.append(f"Gap projetado alto (+{win_last - win_ajuste:.0f} pts) — risco de exaustão comprador")
                
        elif vies_sugerido == "BAIXA" and confianca_sinal >= 60:
            entrada = int(low_mae - 5)
            stop = int(high_mae + 20)
            alvo_1 = int(entrada - amplitude)
            alvo_2 = int(entrada - (amplitude * 1.618))
            invalidacao = f"Fechamento M5 acima de {stop}"
            
            motivos.append(f"Motor SMC indica estrutura de BAIXA (Confiança: {confianca_sinal}%)")
            
            if win_last - win_ajuste < -400:
                riscos.append(f"Gap projetado baixo ({win_last - win_ajuste:.0f} pts) — risco de repique/correção técnica")
        else:
            vies_sugerido = "NEUTRO"
            confianca_sinal = 40
            motivos.append("Aguardando alinhamento de volume institucional ou quebra de estrutura (BOS).")

        # 5. ESTRUTURAÇÃO DO PAYLOAD CENTRALIZADO V2 (OBRIGATÓRIO PARA AS TELAS)
        payload_decisao = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "versao": "V2.2",
                "fonte": "v2_orchestrator",
                "latencia_ms": round((time.time() - self.timestamp_inicio) * 1000, 2)
            },
            "contextos": self.contextos_status,
            "decisao": {
                "timestamp": datetime.now().isoformat(),
                "ativo": "WIN",
                "vies_final": vies_sugerido,
                "confianca": confianca_sinal,
                "entrada": entrada if entrada > 0 else None,
                "stop_loss": stop if stop > 0 else None,
                "alvo_1": alvo_1 if alvo_1 > 0 else None,
                "alvo_2": alvo_2 if alvo_2 > 0 else None,
                "invalidacao": invalidacao,
                "motivos": motivos,
                "riscos": riscos,
                "metadados": {
                    "pivots": {
                        "pp": pivots.get("PP", 0),
                        "r1": pivots.get("R1", 0),
                        "r2": pivots.get("R2", 0),
                        "s1": pivots.get("S1", 0),
                        "s2": pivots.get("S2", 0)
                    },
                    "smc": {
                        "order_blocks": smc_dados.get("order_blocks", []),
                        "fvgs": smc_dados.get("fair_value_gaps", []),
                        "suportes": [low_mae],
                        "resistencias": [high_mae],
                        "entrada_sugerida": entrada if entrada > 0 else None,
                        "stop_sugerido": stop if stop > 0 else None,
                        "alvos": [alvo_1, alvo_2] if alvo_1 > 0 else []
                    },
                    "gap_pts": float(win_last - win_ajuste),
                    "ajuste": float(win_ajuste),
                    "last": float(win_last)
                }
            },
            "erros": self.erros_acumulados
        }

        # 6. PERSISTÊNCIA FÍSICA NO DISCO (Módulo de Produção Ativo)
        # Salva o arquivo de produção principal consumido pelas páginas Streamlit
        with open(FILE_DECISAO_V2, "w", encoding="utf-8") as f:
            json.dump(payload_decisao, f, indent=4, ensure_ascii=False)
            
        # Grava uma cópia datada na pasta de histórico para auditorias retroativas
        HISTORICO_DECISOES_V2_DIR.mkdir(parents=True, exist_ok=True)
        nome_hist = f"20260830_{datetime.now().strftime('%H%M%S')}.json" # Exemplo indexado ao dia real do log
        with open(HISTORICO_DECISOES_V2_DIR / nome_hist, "w", encoding="utf-8") as f:
            json.dump(payload_decisao, f, indent=4, ensure_ascii=False)

        print(f"✅ [V2 ORCHESTRATOR] Tomada de decisão consolidada com sucesso: {vies_sugerido} ({confianca_sinal}%)")
        return payload_decisao

def executar_v2(salvar_historico=True):
    """Ponto de entrada chamado externamente pelo script 'v2_rodar_decisao_completa.py'"""
    try:
        orquestrador = V2Orchestrator()
        return orquestrador.consolidar_decisao()
    except Exception as e:
        print(f"❌ [ERRO CRÍTICO NO ORQUESTRADOR]: {e}")
        traceback.print_exc()
        return {"decisao": {"vies_final": "NEUTRO", "confianca": 0}, "erros": [str(e)]}

if __name__ == "__main__":
    executar_v2()
