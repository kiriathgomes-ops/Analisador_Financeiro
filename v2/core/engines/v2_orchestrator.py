# -*- coding: utf-8 -*-
"""
Módulo: v2/core/engines/v2_orchestrator.py
Versão: 3.4.1 - Stale Gate + Pepita Reportada

Lógica:
  - SMC fornece direção técnica + níveis operacionais.
  - NOVO_MOTOR fornece direção macro + gap + cenário + aberturas.
  - Visão C: divergência interna do NOVO_MOTOR bloqueia.
  - Pepita (v3.3): SMC conf ajustada < 85% bloqueia.
  - Stale (v3.4): SMC sobre candle com idade > 15 min bloqueia.
  - v3.4.1: pepita_passou é calculado antes do gate stale. Quando stale
    dispara, o campo reflete o que a Pepita TERIA decidido (True/False),
    não o default enganoso. Quando não stale, comportamento idêntico.
"""

import os
import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from v2.core.services.win_session_builder import build_win_session
from v2.core.engines.opening_scenario_engine import gerar_cenario_abertura

from config import (
    FILE_DECISAO_V2,
    FILE_UNIFICADO,
    FILE_SMC_REGRAS,
    FILE_SMC_MTF,
    MODIFICADOR_MTF,
    CONFIANCA_MINIMA_FINAL,
    FILE_ESTIMATIVA_ABERTURA,
    FILE_NOTICIAS_IMPACTO,
    HISTORICO_DECISOES_V2_DIR,
)


MAPA_DIRECAO = {
    "ALTA": "COMPRA",
    "BAIXA": "VENDA",
    "COMPRA": "COMPRA",
    "VENDA": "VENDA",
    "NEUTRO": "NEUTRO",
    "LATERAL": "NEUTRO",
}

PESO_SMC = 0.60
PESO_NOVO_MOTOR = 0.40
CONFIANCA_MINIMA_CONFLUENCIA = 55.0
CONFIANCA_MINIMA_SMC_PEPITA = 85.0


class V2Orchestrator:
    def __init__(self):
        self.timestamp_inicio = time.time()
        self.erros_acumulados = []
        self._debug_confluencia = {}

        self.contextos_status = {
            "market_ok": False,
            "prediction_ok": False,
            "news_ok": False,
            "vision_ok": False,
            "session_ok": False,
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

    def _normalizar_direcao(self, bruta: Optional[str]) -> str:
        if not bruta:
            return "NEUTRO"
        return MAPA_DIRECAO.get(str(bruta).upper().strip(), "NEUTRO")

    def _ler_smc(self, smc_dados: dict, mtf_dados: Optional[dict] = None) -> Dict[str, Any]:
        if not smc_dados:
            return {
                "direcao": "NEUTRO", "confianca": 0, "entrada": None,
                "stop": None, "alvos": [], "poc": 0.0, "vwap": 0.0,
                "ob_alinhado": False, "order_blocks": [], "fvgs": [],
                "veredito_mtf": None,
                "stale": False, "stale_motivo": None, "candle_idade_min": None,
            }

        niveis = smc_dados.get("niveis_institucionais", {}) or {}
        metadados = smc_dados.get("metadados", {}) or {}
        stale = smc_dados.get("stale", metadados.get("stale", False))
        stale_motivo = smc_dados.get("stale_motivo", metadados.get("stale_motivo"))
        candle_idade_min = smc_dados.get("candle_idade_min", metadados.get("candle_idade_min"))

        return {
            "direcao": self._normalizar_direcao(smc_dados.get("bias_direcional")),
            "confianca": float(smc_dados.get("confianca_visual", 0) or 0),
            "entrada": smc_dados.get("entrada_sugerida"),
            "stop": smc_dados.get("stop_sugerido"),
            "alvos": smc_dados.get("alvos", []) or [],
            "poc": float(niveis.get("poc_ontem", 0.0) or 0.0),
            "vwap": float(niveis.get("vwap_ontem", 0.0) or 0.0),
            "ob_alinhado": bool(niveis.get("ob_alinhado_com_poc", False)),
            "order_blocks": smc_dados.get("order_blocks", []) or [],
            "fvgs": smc_dados.get("fair_value_gaps", []) or [],
            "veredito_mtf": (
                ((mtf_dados or {}).get("confluencia") or {}).get("veredito_mtf")
            ),
            "stale": bool(stale),
            "stale_motivo": stale_motivo,
            "candle_idade_min": candle_idade_min,
        }

    def _ler_novo_motor(self) -> Optional[Dict[str, Any]]:
        try:
            from v2.core.services.prediction_service import PredictionService
            svc = PredictionService()
            prediction = svc.get_prediction()
            if not prediction:
                return None

            return {
                "direcao": self._normalizar_direcao(prediction.direcao_prevista),
                "confianca": float(prediction.score or 0.0),
                "gap_pontos": float(prediction.gap_pontos or 0.0),
                "gap_pct": float(prediction.gap_percentual or 0.0),
                "gap_intensidade": prediction.gap_intensidade,
                "faixa_inf": float(prediction.faixa_provavel_inferior or 0.0),
                "faixa_sup": float(prediction.faixa_provavel_superior or 0.0),
                "abertura_projetada": float(prediction.abertura_projetada or 0.0),
                "cenario_nome": (prediction.cenario_principal or {}).get("nome"),
                "cenario_desc": (prediction.cenario_principal or {}).get("descricao"),
                "score_direcao": prediction.score_direcao,
                "score_forca": prediction.score_forca,
                "score_magnitude": float(prediction.score_magnitude or 0.0),
                "divergencia_direcao": bool(prediction.divergencia_direcao),
                "divergencia_detalhes": prediction.divergencia_detalhes,
                "abertura_leilao_real": prediction.abertura_leilao_real,
                "abertura_leilao_timestamp": prediction.abertura_leilao_timestamp,
                "abertura_teorica_calculada": prediction.abertura_teorica_calculada,
                "fonte_abertura": prediction.fonte_abertura,
                "gap_fonte": getattr(prediction, "gap_fonte", "DESCONHECIDO"),
                "cenario_principal_nome": prediction.cenario_principal_nome,
                "cenario_principal_probabilidade": prediction.cenario_principal_probabilidade,
                "cenario_alternativo_nome": prediction.cenario_alternativo_nome,
                "cenario_alternativo_probabilidade": prediction.cenario_alternativo_probabilidade,
            }
        except Exception as e:
            self.erros_acumulados.append(f"Falha no NOVO_MOTOR: {str(e)}")
            return None

    def _verificar_confluencia(
        self, smc: Dict[str, Any], novo_motor: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str, Optional[str], float, list, list]:
        motivos = []
        riscos = []

        smc_dir = smc["direcao"]
        smc_conf_bruta = smc["confianca"]
        _delta_mtf = MODIFICADOR_MTF.get(smc.get("veredito_mtf") or "", 0)
        smc_conf = max(0.0, min(100.0, smc_conf_bruta + _delta_mtf))

        # v3.4.1: calcula pepita ANTES de qualquer gate, para reportar corretamente
        # mesmo quando outro gate (stale, smc_neutro) disparar primeiro.
        pepita_avaliada = bool(smc_conf >= CONFIANCA_MINIMA_SMC_PEPITA)

        self._debug_confluencia = {
            "smc_conf_bruto": float(smc_conf_bruta),
            "mtf_veredito": smc.get("veredito_mtf"),
            "mtf_delta": float(_delta_mtf),
            "smc_conf_ajustado": float(smc_conf),
            "smc_direcao": smc_dir,
            "nm_conf": None,
            "peso_smc": float(PESO_SMC),
            "peso_nm": float(PESO_NOVO_MOTOR),
            "confianca_final": None,
            "motivo_saida": None,
            "nm_magnitude": None,
            "nm_direcao_score": None,
            "nm_divergencia_interna": None,
            "score_magnitude": None,
            "score_direcao": None,
            "passou_gate_confluencia": (
                smc_conf >= CONFIANCA_MINIMA_CONFLUENCIA
            ),
            "passou_gate_final": False,
            "pepita_minimo": float(CONFIANCA_MINIMA_SMC_PEPITA),
            "pepita_smc_conf_bruto": float(smc_conf_bruta),
            "pepita_smc_conf_ajustado": float(smc_conf),
            "pepita_passou": pepita_avaliada,
            "smc_stale": bool(smc.get("stale", False)),
            "smc_stale_motivo": smc.get("stale_motivo"),
            "candle_idade_min": smc.get("candle_idade_min"),
        }
        if _delta_mtf:
            motivos.append(
                f"MTF [{smc.get('veredito_mtf')}]: confianca SMC "
                f"{smc_conf_bruta:.0f}% -> {smc_conf:.0f}% ({_delta_mtf:+d})"
            )

        # ============================================================
        # v3.4 — STALE GATE
        # ============================================================
        if smc.get("stale"):
            idade_txt = (
                f"{smc.get('candle_idade_min')}min"
                if smc.get("candle_idade_min") is not None
                else "?"
            )
            pepita_txt = "passaria" if pepita_avaliada else "reprovaria"
            motivos.append(
                f"🚫 SMC STALE: {smc.get('stale_motivo') or 'candle antigo'} "
                f"(idade={idade_txt}; Pepita {pepita_txt})"
            )
            riscos.append(
                "SMC está sobre candle congelado (fora do pregão ou MT5 travado). "
                "Decisão não operacional."
            )
            self._debug_confluencia["motivo_saida"] = "smc_stale"
            self._debug_confluencia["confianca_final"] = 0.0
            return False, "NEUTRO", None, 0.0, motivos, riscos

        if smc_dir == "NEUTRO":
            motivos.append("SMC sem direção definida (LATERAL/NEUTRO)")
            self._debug_confluencia["motivo_saida"] = "smc_neutro"
            self._debug_confluencia["confianca_final"] = 0.0
            return False, "NEUTRO", None, 0.0, motivos, riscos

        if not pepita_avaliada:
            motivos.append(
                f"🚫 PEPITA: SMC conf. {smc_conf:.0f}% "
                f"(bruto {smc_conf_bruta:.0f}%, MTF {_delta_mtf:+d}) "
                f"< mínimo {CONFIANCA_MINIMA_SMC_PEPITA:.0f}%"
            )
            riscos.append(
                "Confiança SMC abaixo do limiar de lucratividade (Pepita). "
                "Histórico: sistema cego = -30 pts/trade, WR 48%."
            )
            self._debug_confluencia["motivo_saida"] = "pepita_smc_abaixo_minimo"
            self._debug_confluencia["confianca_final"] = float(smc_conf)
            return False, "NEUTRO", None, smc_conf, motivos, riscos

        if smc_conf < CONFIANCA_MINIMA_CONFLUENCIA:
            motivos.append(
                f"SMC com confiança baixa ({smc_conf:.0f}% < {CONFIANCA_MINIMA_CONFLUENCIA:.0f}%)"
            )
            self._debug_confluencia["motivo_saida"] = "smc_conf_baixa"
            self._debug_confluencia["confianca_final"] = float(smc_conf)
            return False, "NEUTRO", None, smc_conf, motivos, riscos

        if not novo_motor:
            motivos.append("NOVO_MOTOR indisponível — sem confluência")
            riscos.append("NOVO_MOTOR não retornou previsão")
            self._debug_confluencia["motivo_saida"] = "nm_indisponivel"
            self._debug_confluencia["confianca_final"] = float(smc_conf * 0.5)
            return False, "NEUTRO", None, smc_conf * 0.5, motivos, riscos

        nm_dir = novo_motor["direcao"]
        nm_score_dir = novo_motor.get("score_direcao", "NEUTRO")
        nm_conf = novo_motor["confianca"]
        self._debug_confluencia["nm_conf"] = float(nm_conf)
        self._debug_confluencia["nm_magnitude"] = float(nm_conf)
        self._debug_confluencia["nm_direcao_score"] = nm_score_dir
        self._debug_confluencia["score_magnitude"] = float(nm_conf)
        self._debug_confluencia["score_direcao"] = nm_score_dir
        self._debug_confluencia["nm_divergencia_interna"] = bool(
            novo_motor.get("divergencia_direcao")
        )
        gap = novo_motor["gap_pontos"]

        motivos.append(f"SMC: {smc_dir} (conf. {smc_conf:.0f}%)")
        motivos.append(f"NOVO_MOTOR: {nm_dir} (score {nm_conf:.1f}, gap {gap:+.0f} pts)")

        if novo_motor.get("divergencia_direcao"):
            motivos.append(
                f"⚠️ NOVO_MOTOR em CONFLITO INTERNO: "
                f"gap diz {nm_dir}, score agregado diz {nm_score_dir}"
            )
            riscos.append(
                f"Motor interno divergente ({nm_dir} vs {nm_score_dir}). "
                "Sem convicção — não operar."
            )
            self._debug_confluencia["motivo_saida"] = "nm_divergencia_interna"
            self._debug_confluencia["confianca_final"] = 0.0
            return False, "NEUTRO", None, 0.0, motivos, riscos

        if smc_dir == nm_dir and nm_dir != "NEUTRO":
            confianca_final = (smc_conf * PESO_SMC) + (nm_conf * PESO_NOVO_MOTOR)
            confianca_final = round(min(100.0, confianca_final), 1)
            self._debug_confluencia["confianca_final"] = float(confianca_final)
            self._debug_confluencia["passou_gate_final"] = (
                confianca_final >= CONFIANCA_MINIMA_FINAL
            )

            if confianca_final < CONFIANCA_MINIMA_FINAL:
                motivos.append(
                    f"⚠️ Confiança final {confianca_final:.1f}% < "
                    f"mínimo {CONFIANCA_MINIMA_FINAL:.0f}% — não opera"
                )
                self._debug_confluencia["motivo_saida"] = "confianca_final_abaixo_minimo"
                return False, "NEUTRO", None, confianca_final, motivos, riscos

            motivos.append(f"✅ Confluência confirmada em {smc_dir}")
            self._debug_confluencia["motivo_saida"] = "ok"
            return True, smc_dir, smc_dir, confianca_final, motivos, riscos

        motivos.append(f"⚠️ DIVERGÊNCIA: SMC diz {smc_dir}, NOVO_MOTOR diz {nm_dir}")
        riscos.append(
            f"Motores divergem (SMC={smc_dir}, NovoMotor={nm_dir}). "
            "Aguardar alinhamento antes de operar."
        )
        self._debug_confluencia["motivo_saida"] = "divergencia_smc_nm"
        self._debug_confluencia["confianca_final"] = 0.0
        return False, "NEUTRO", None, 0.0, motivos, riscos

    def _serializar_cenario(self) -> Optional[Dict[str, Any]]:
        c = getattr(self, "_cenario_abertura", None)
        if not c:
            return None
        try:
            rel = getattr(c, "relacao_com_ajuste", None)
            return {
                "direcao_provavel": c.direcao_provavel,
                "probabilidade_direcao": c.probabilidade_direcao,
                "confianca_geral": c.confianca_geral,
                "relacao_com_ajuste": {
                    "posicao": rel.posicao if rel else None,
                    "cenario_principal": rel.cenario_principal if rel else None,
                    "probabilidade_cenario": rel.probabilidade_cenario if rel else None,
                },
                "cenario_alternativo": c.cenario_alternativo,
                "niveis_observacao": c.niveis_observacao or {},
                "contexto_resumo": c.contexto_resumo or [],
            }
        except Exception as e:
            print(f"[AVISO] fix83: falha ao serializar cenario: {e}")
            return None

    def consolidar_decisao(self) -> dict:
        ativos_dados = self._carregar_json_defensivo(FILE_UNIFICADO)
        smc_dados = self._carregar_json_defensivo(FILE_SMC_REGRAS)
        mtf_dados = self._carregar_json_defensivo(FILE_SMC_MTF)
        estimativas = self._carregar_json_defensivo(FILE_ESTIMATIVA_ABERTURA)
        noticias = self._carregar_json_defensivo(FILE_NOTICIAS_IMPACTO)

        if ativos_dados.get("ativos"):
            self.contextos_status["market_ok"] = True
        if estimativas:
            self.contextos_status["prediction_ok"] = True
        if noticias:
            self.contextos_status["news_ok"] = True
        if smc_dados:
            self.contextos_status["vision_ok"] = True
            self.contextos_status["session_ok"] = True

        smc = self._ler_smc(smc_dados, mtf_dados)
        novo_motor = self._ler_novo_motor()

        ativos = ativos_dados.get("ativos", {}) if isinstance(ativos_dados, dict) else {}
        win_fut = ativos.get("WIN_FUT", {}) or {}
        win_last_tick = ativos.get("WIN_LAST_TICK", {}) or {}
        win_ajuste_obj = ativos.get("WIN_AJUSTE", {}) or {}

        win_last = (
            win_fut.get("preco")
            or win_last_tick.get("preco")
            or win_ajuste_obj.get("preco")
            or 0.0
        )
        win_ajuste = float(win_ajuste_obj.get("preco", 0.0) or 0.0)

        pivots = estimativas.get("pivot_points", {}).get("WIN_FUT", {}) or {}

        operar, vies_final, direcao_motores, confianca, motivos, riscos = \
            self._verificar_confluencia(smc, novo_motor)

        self._cenario_abertura = None
        try:
            _session = build_win_session()
            self._cenario_abertura = gerar_cenario_abertura(_session)
        except Exception as _e:
            print(f"[AVISO] fix83: falha ao gerar cenario: {_e}")

        entrada = None
        stop = None
        alvo_1 = None
        alvo_2 = None
        invalidacao = "Aguardando confluência"

        if operar:
            entrada = smc["entrada"]
            stop = smc["stop"]
            alvos = smc["alvos"]
            alvo_1 = alvos[0] if len(alvos) > 0 else None
            alvo_2 = alvos[1] if len(alvos) > 1 else None

            if vies_final == "COMPRA":
                invalidacao = f"Fechamento abaixo de {stop:.0f}" if stop else "Fechamento abaixo do stop"
            elif vies_final == "VENDA":
                invalidacao = f"Fechamento acima de {stop:.0f}" if stop else "Fechamento acima do stop"

        gap_pts = float((novo_motor or {}).get("gap_pontos", 0.0))

        payload_decisao = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "versao": "V3.4.1-StaleGate",
                "fonte": "v2_orchestrator",
                "latencia_ms": round((time.time() - self.timestamp_inicio) * 1000, 2),
            },
            "contextos": self.contextos_status,
            "decisao": {
                "timestamp": datetime.now().isoformat(),
                "ativo": "WIN",
                "vies_final": vies_final,
                "confianca": confianca,
                "entrada": entrada,
                "stop_loss": stop,
                "alvo_1": alvo_1,
                "alvo_2": alvo_2,
                "invalidacao": invalidacao,
                "motivos": motivos,
                "riscos": riscos,
                "metadados": {
                    "pivots": {
                        "pp": float(pivots.get("PP", 0) or 0),
                        "r1": float(pivots.get("R1", 0) or 0),
                        "r2": float(pivots.get("R2", 0) or 0),
                        "s1": float(pivots.get("S1", 0) or 0),
                        "s2": float(pivots.get("S2", 0) or 0),
                    },
                    "smc": {
                        "poc_ontem": smc["poc"],
                        "vwap_ontem": smc["vwap"],
                        "ob_alinhado_com_poc": smc["ob_alinhado"],
                        "order_blocks": smc["order_blocks"],
                        "fvgs": smc["fvgs"],
                        "entrada_sugerida": smc["entrada"],
                        "stop_sugerido": smc["stop"],
                        "alvos": smc["alvos"],
                    },
                    "novo_motor": novo_motor or {},
                    "confluencia": getattr(self, "_debug_confluencia", {}),
                    "precificacao_teorica": {
                        "abertura_teorica": (novo_motor or {}).get("abertura_teorica_calculada", 0.0),
                        "gap_fonte": (novo_motor or {}).get("gap_fonte", "DESCONHECIDO"),
                    },
                    "gap_pts": gap_pts,
                    "ajuste": win_ajuste,
                    "last": float(win_last or 0.0),
                    "opening_scenario": self._serializar_cenario(),
                },
            },
            "erros": self.erros_acumulados,
        }

        with open(FILE_DECISAO_V2, "w", encoding="utf-8") as f:
            json.dump(payload_decisao, f, indent=4, ensure_ascii=False)

        HISTORICO_DECISOES_V2_DIR.mkdir(parents=True, exist_ok=True)
        data_hoje = datetime.now().strftime("%Y%m%d")
        hora_agora = datetime.now().strftime("%H%M%S")
        nome_hist = f"{data_hoje}_{hora_agora}.json"
        with open(HISTORICO_DECISOES_V2_DIR / nome_hist, "w", encoding="utf-8") as f:
            json.dump(payload_decisao, f, indent=4, ensure_ascii=False)

        print(
            f"✅ [V2 ORCHESTRATOR] Decisão consolidada: "
            f"{vies_final} ({confianca:.0f}%) | operar={operar} | "
            f"motivo={self._debug_confluencia.get('motivo_saida')}"
        )
        return payload_decisao


def executar_v2(salvar_historico=True):
    try:
        orquestrador = V2Orchestrator()
        return orquestrador.consolidar_decisao()
    except Exception as e:
        print(f"❌ [ERRO CRÍTICO NO ORQUESTRADOR]: {e}")
        traceback.print_exc()
        return {"decisao": {"vies_final": "NEUTRO", "confianca": 0}, "erros": [str(e)]}


if __name__ == "__main__":
    executar_v2()