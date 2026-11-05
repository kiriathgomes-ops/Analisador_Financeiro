# -*- coding: utf-8 -*-
"""
Módulo: Gerar_Resultado_Operacional_Abertura.py
Versão: 3.1 - Inteligência Operacional Completa com ORB (Op 3) mastigado.
Objetivo: Consolidar métricas e calcular a inteligência de rota (escoras/barreiras) dos 4 operacionais.
"""

import json
import os
import logging
import math
from datetime import datetime, time as dt_time
from pathlib import Path

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
from cache_candles import obter_candles

logger = logging.getLogger(__name__)

# Caminhos adicionais
FILE_SMC_M5 = COLETAS_DIR / "AnaliseGraficaSMC_Regras.json"
FILE_SMC_M15 = COLETAS_DIR / "AnaliseGraficaSMC_Regras_M15.json"
FILE_SMC_M1 = COLETAS_DIR / "AnaliseGraficaSMC_Regras_M1.json"
FILE_SMC_MTF = COLETAS_DIR / "AnaliseGraficaSMC_MTF.json"
FILE_OCR_CSV = COLETAS_DIR / "preco_teorico_win_fluxo.csv"
FILE_NOTICIAS_IMPACTO = COLETAS_DIR / "Noticias_Impacto_Dia.json"

def carregar_json_defensivo(caminho_path, default=None) -> dict:
    if default is None: default = {}
    if not caminho_path.exists(): return default
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[GERADOR_OP] Falha ao ler {caminho_path.name}: {e}")
        return default

def classificar_intensidade_sinal(valor_pct: float, limiar_ruido: float = 0.05) -> dict:
    if valor_pct is None or not isinstance(valor_pct, (int, float)):
        return {"valor_pct": 0.0, "classificacao": "INDISPONIVEL", "sinal_operacional": "NEUTRO", "rotulo_completo": "INDISPONIVEL_NEUTRO"}

    abs_valor = abs(valor_pct)
    if abs_valor < 1.5: intensidade = "LATERAL"
    elif 1.5 <= abs_valor < 2.5: intensidade = "FRACA"
    elif 2.5 <= abs_valor < 4.5: intensidade = "MODERADA"
    else: intensidade = "FORTE"

    sinal = "COMPRA" if valor_pct > limiar_ruido else ("VENDA" if valor_pct < -limiar_ruido else "NEUTRO")
    return {"valor_pct": round(valor_pct, 4), "classificacao": intensidade, "sinal_operacional": sinal, "rotulo_completo": f"{intensidade}_{sinal}"}

def ler_ultimo_ocr() -> float:
    if not FILE_OCR_CSV.exists(): return None
    try:
        with open(FILE_OCR_CSV, "r", encoding="utf-8-sig") as f:
            linhas = f.readlines()
            if linhas:
                partes = linhas[-1].strip().split(",")
                if len(partes) >= 2: return float(partes[1])
    except Exception as e:
        logger.warning(f"[GERADOR_OP] Falha ao ler OCR: {e}")
    return None

def calcular_bolas(preco_ini: float, preco_fim: float) -> list:
    if not preco_ini or not preco_fim: return []
    min_p, max_p = min(preco_ini, preco_fim), max(preco_ini, preco_fim)
    bolas = []
    ini = math.floor(min_p / 1000) * 1000
    fim = math.ceil(max_p / 1000) * 1000
    for b in range(int(ini), int(fim) + 1000, 1000):
        if min_p < b < max_p: bolas.append(b)
    return bolas

def buscar_barreiras_escoras(preco_ref: float, alvo: float, lado: str, pivots: dict, smcs: dict) -> tuple:
    escoras = []
    barreiras = []
    
    # 1. Bolas
    bolas = calcular_bolas(preco_ref, alvo)
    for b in bolas:
        barreiras.append(f"Bola em {b}")

    # 2. Pivôs
    for nome_p, val_p in pivots.items():
        if isinstance(val_p, (int, float)) and val_p > 0:
            if lado == "COMPRA" and preco_ref < val_p < alvo: barreiras.append(f"Pivô {nome_p} em {val_p:.0f}")
            elif lado == "VENDA" and alvo < val_p < preco_ref: barreiras.append(f"Pivô {nome_p} em {val_p:.0f}")
            elif lado == "COMPRA" and val_p < preco_ref: escoras.append(f"Pivô {nome_p} em {val_p:.0f}")
            elif lado == "VENDA" and val_p > preco_ref: escoras.append(f"Pivô {nome_p} em {val_p:.0f}")

    # 3. SMC (OBs)
    for tf, smc in smcs.items():
        if not smc: continue
        for ob in smc.get("order_blocks", []):
            preco_ob, tipo_ob = ob.get("preco"), ob.get("tipo")
            if not preco_ob: continue
            if lado == "COMPRA" and tipo_ob == "VENDA" and preco_ref < preco_ob < alvo: barreiras.append(f"OB de Venda ({tf}) em {preco_ob:.0f}")
            elif lado == "VENDA" and tipo_ob == "COMPRA" and alvo < preco_ob < preco_ref: barreiras.append(f"OB de Compra ({tf}) em {preco_ob:.0f}")
            elif lado == "COMPRA" and tipo_ob == "COMPRA" and preco_ob < preco_ref: escoras.append(f"OB de Compra ({tf}) em {preco_ob:.0f}")
            elif lado == "VENDA" and tipo_ob == "VENDA" and preco_ob > preco_ref: escoras.append(f"OB de Venda ({tf}) em {preco_ob:.0f}")
                
    return escoras, barreiras

def calcular_operacionais(agora: dt_time, ativos: dict, metricas: dict, est: dict, noticias0900: dict, smcs: dict) -> dict:
    ops = {}
    win_last = ativos.get("WIN_LAST_TICK", {}).get("preco") or ativos.get("WIN_FUT", {}).get("preco")
    win_ajuste = ativos.get("WIN_AJUSTE", {}).get("preco")
    pivots = est.get("pivot_points", {}).get("WIN_FUT", {})
    
    if not win_last or not win_ajuste: return {"erro": "Preços WIN não encontrados."}

    gap = win_last - win_ajuste
    lado_gap = "COMPRA" if gap < 0 else ("VENDA" if gap > 0 else "NEUTRO")
    ind_ext = metricas.get("indicadores_compostos", {}).get("indicador_mercado_externo", 0.0)
    ind_adrs = metricas.get("indicadores_compostos", {}).get("indicador_adrs_brasileiras", 0.0)
    tem_noticia = noticias0900.get("tem_evento_3_estrelas", False)

    # ==========================================
    # OP 1: RETORNO AO AJUSTE
    # ==========================================
    op1 = {"status": "", "detalhes": {}, "escoras": [], "barreiras": []}
    if agora < dt_time(9, 0):
        op1["status"] = "AGUARDANDO_ABERTURA"
        ocr = ler_ultimo_ocr()
        op1["detalhes"] = {"ocr_estimado": ocr, "gap_projetado": (ocr - win_ajuste) if ocr else None}
    elif dt_time(9, 0) <= agora <= dt_time(9, 15):
        op1["status"] = "ATIVO"
        alvo_op1 = win_last - 500 if lado_gap == "VENDA" else (win_last + 500 if lado_gap == "COMPRA" else win_last)
        esc, bar = buscar_barreiras_escoras(win_last, alvo_op1, lado_gap, pivots, smcs)
        if lado_gap == "COMPRA" and ind_ext < -2.5: bar.append("Contra-fluxo: Mercado Externo forte em VENDA")
        elif lado_gap == "VENDA" and ind_ext > 2.5: bar.append("Contra-fluxo: Mercado Externo forte em COMPRA")
        op1["detalhes"] = {"gap_atual": gap, "lado": lado_gap, "alvo": alvo_op1, "stop": win_last + 100 if lado_gap == "VENDA" else win_last - 100}
        op1["escoras"], op1["barreiras"] = esc, bar
        if len(bar) > 0: op1["status"] = "BLOQUEADO"
    else: op1["status"] = "ENCERRADO"
    ops["op1_retorno_ajuste"] = op1

    # ==========================================
    # OP 2: EXPLOSÃO
    # ==========================================
    op2 = {"status": "", "detalhes": {}, "escoras": [], "barreiras": []}
    driver_nome = "ADRs" if tem_noticia else "Merc. Externo"
    driver_val = ind_adrs if tem_noticia else ind_ext
    driver_class = classificar_intensidade_sinal(driver_val)
    
    if agora < dt_time(9, 0):
        op2["status"] = "AGUARDANDO_ABERTURA"
        op2["detalhes"] = {"driver": driver_nome, "valor": driver_val, "class": driver_class["rotulo_completo"]}
    elif dt_time(9, 0) <= agora <= dt_time(9, 15):
        op2["status"] = "MONITORAR"
        if driver_class["classificacao"] in ["MODERADA", "FORTE"]:
            op2["status"] = "EXPLOSAO"
            lado_exp = driver_class["sinal_operacional"]
            alvo1 = win_last + 250 if lado_exp == "COMPRA" else win_last - 250
            alvo2 = win_last + 400 if lado_exp == "COMPRA" else win_last - 400
            stop = win_last - 250 if lado_exp == "COMPRA" else win_last + 250
            esc, bar = buscar_barreiras_escoras(win_last, alvo2, lado_exp, pivots, smcs)
            op2["detalhes"] = {"driver": driver_nome, "lado": lado_exp, "alvo1": alvo1, "alvo2": alvo2, "stop": stop}
            op2["escoras"], op2["barreiras"] = esc, bar
        else: op2["detalhes"] = {"driver": driver_nome, "motivo": "Drivers sem força."}
    else: op2["status"] = "ENCERRADO"
    ops["op2_explosao"] = op2

    # ==========================================
    # OP 3: ORB 10h (Mastigado via cache_candles)
    # ==========================================
    op3 = {"status": "", "detalhes": {}, "escoras": [], "barreiras": []}
    if agora < dt_time(10, 0):
        op3["status"] = "AGUARDANDO_VELA"
        op3["detalhes"] = {"mercado_atual": f"WIN em {win_last:.0f} | Gap {gap:+.0f}"}
    elif dt_time(10, 0) <= agora <= dt_time(10, 5):
        op3["status"] = "VELA_EM_FORMACAO"
    else:
        vela_10h = None
        try:
            candles, _ = obter_candles("WIN$", 5, 50)
            for c in candles:
                if "10:00" in c['time']:
                    vela_10h = c
                    break
        except Exception as e:
            logger.warning(f"[GERADOR_OP] Falha ao ler cache de candles: {e}")
            
        if not vela_10h:
            op3["status"] = "ERRO_VELA_AUSENTE"
            op3["detalhes"] = {"motivo": "Vela das 10:00 não encontrada no MT5."}
        else:
            o, h, l, c_close = vela_10h['open'], vela_10h['high'], vela_10h['low'], vela_10h['close']
            amp = h - l
            if amp < 50 or amp > 700:
                op3["status"] = "BLOQUEADO"
                op3["detalhes"] = {"motivo": f"Amplitude fora do padrão ({amp:.0f} pts)"}
            else:
                gatilho_compra = h + 5
                gatilho_venda = l - 5
                
                if win_last > gatilho_compra:
                    op3["status"] = "COMPRA_ACIONADA"
                    alvo = win_last + amp
                    esc, bar = buscar_barreiras_escoras(win_last, alvo, "COMPRA", pivots, smcs)
                    op3["detalhes"] = {"vela": f"O={o:.0f} H={h:.0f} L={l:.0f} C={c_close:.0f}", "rompimento": "COMPRA", "alvo": alvo, "stop": l - 20}
                    op3["escoras"], op3["barreiras"] = esc, bar
                elif win_last < gatilho_venda:
                    op3["status"] = "VENDA_ACIONADA"
                    alvo = win_last - amp
                    esc, bar = buscar_barreiras_escoras(win_last, alvo, "VENDA", pivots, smcs)
                    op3["detalhes"] = {"vela": f"O={o:.0f} H={h:.0f} L={l:.0f} C={c_close:.0f}", "rompimento": "VENDA", "alvo": alvo, "stop": h + 20}
                    op3["escoras"], op3["barreiras"] = esc, bar
                else:
                    op3["status"] = "ATIVO"
                    op3["detalhes"] = {"vela": f"O={o:.0f} H={h:.0f} L={l:.0f} C={c_close:.0f}", "gatilho_compra": gatilho_compra, "gatilho_venda": gatilho_venda}
                    
    ops["op3_orb"] = op3

    # ==========================================
    # OP 4: SMC PURO
    # ==========================================
    op4 = {"status": "", "detalhes": {}, "escoras": [], "barreiras": []}
    smc_m5 = smcs.get("M5", {})
    smc_mtf = smcs.get("MTF", {})
    
    if not smc_m5: op4["status"] = "INDISPONIVEL"
    elif smc_m5.get("stale", False): op4["status"] = "INDISPONIVEL_STALE"
    else:
        entrada = smc_m5.get("entrada_sugerida")
        stop = smc_m5.get("stop_sugerido")
        alvos = smc_m5.get("alvos", [])
        
        if entrada and abs(win_last - entrada) > 500:
            op4["status"] = "ENTRADA_EXPIRADA"
            op4["detalhes"] = {"motivo": f"Preço {win_last:.0f} longe da entrada {entrada:.0f}"}
        else:
            op4["status"] = "DISPONIVEL"
            veredito_mtf = smc_mtf.get("confluencia", {}).get("veredito_mtf", "")
            if veredito_mtf in ["DIVERGENTE", "CONFLITO_MACRO"]:
                op4["status"] = "CAUTELA"
                op4["detalhes"]["alerta_mtf"] = f"MTF diz {veredito_mtf}"
            op4["detalhes"].update({"entrada": entrada, "stop": stop, "alvos": alvos})
            if entrada and alvos:
                lado_smc = "COMPRA" if alvos[0] > entrada else "VENDA"
                esc, bar = buscar_barreiras_escoras(entrada, alvos[-1], lado_smc, pivots, smcs)
                op4["escoras"], op4["barreiras"] = esc, bar

    ops["op4_smc"] = op4
    return ops

def processar_resultado_operacional():
    print("=" * 70)
    print(" 📊 COMPILADOR INTELIGENTE OPERACIONAL — V3.1")
    print("=" * 70)
    print(f"🕒 Execução: {datetime.now().strftime('%H:%M:%S')}")

    metricas = carregar_json_defensivo(FILE_METRICAS)
    estimativa = carregar_json_defensivo(FILE_ESTIMATIVA_ABERTURA)
    decisao_v2 = carregar_json_defensivo(FILE_DECISAO_V2)
    unificado = carregar_json_defensivo(FILE_UNIFICADO)
    tendencias = carregar_json_defensivo(FILE_TENDENCIAS)
    not_0900 = carregar_json_defensivo(FILE_NOTICIAS_CALENDARIO_0900).get("alerta_noticia_0900", {})
    smcs = {
        "M5": carregar_json_defensivo(FILE_SMC_M5),
        "M15": carregar_json_defensivo(FILE_SMC_M15),
        "M1": carregar_json_defensivo(FILE_SMC_M1),
        "MTF": carregar_json_defensivo(FILE_SMC_MTF)
    }

    ativos = unificado.get("ativos", {})
    decisao_data = decisao_v2.get("decisao", {})
    vies_final = decisao_data.get("vies_final", "NEUTRO")
    confianca = decisao_data.get("confianca", 0)
    
    score = (confianca / 100) * 10 if "COMPRA" in vies_final or "ALTA" in vies_final else \
            -((confianca / 100) * 10) if "VENDA" in vies_final or "BAIXA" in vies_final else 0.0

    ops_calculados = calcular_operacionais(datetime.now().time(), ativos, metricas, estimativa, not_0900, smcs)

    payload = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "origem": "Pipeline_Completo_V2",
            "versao": "3.1_V2_OPERACIONAL",
            "integridade_fontes": {
                "metricas": FILE_METRICAS.exists(),
                "estimativa": FILE_ESTIMATIVA_ABERTURA.exists(),
                "decisao": FILE_DECISAO_V2.exists(),
                "smc_m5": FILE_SMC_M5.exists()
            }
        },
        "alerta_calendario_0900": not_0900,
        "indicadores_compostos": {
            "indicador_mercado_externo": classificar_intensidade_sinal(metricas.get("indicadores_compostos", {}).get("indicador_mercado_externo", 0.0)),
            "indicador_adrs_brasileiras": classificar_intensidade_sinal(metricas.get("indicadores_compostos", {}).get("indicador_adrs_brasileiras", 0.0))
        },
        "analise_tendencias": tendencias,
        "estimativa_abertura": {"WIN_INDICE": estimativa.get("estimativa_abertura", {}).get("WIN_INDICE", {})},
        "pivot_points": {"WIN_FUT": estimativa.get("pivot_points", {}).get("WIN_FUT", {})},
        "decisao_core": {
            "win": {
                "vies_final": vies_final,
                "score_numeric": round(score, 2),
                "confianca": confianca,
                "fatores_relevantes": decisao_data.get("motivos", []),
                "operacionais": ops_calculados
            }
        }
    }

    try:
        COLETAS_DIR.mkdir(parents=True, exist_ok=True)
        with open(FILE_RESULTADO_OPERACIONAL, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            
        print("\n📊 Operacionais Consolidados com Sucesso:")
        for op_nome, op_dados in ops_calculados.items():
            print(f"  • {op_nome.upper()} : {op_dados.get('status')}")
        print(f"\n✅ Arquivo gravado: {FILE_RESULTADO_OPERACIONAL.name}\n")
        
    except Exception as e:
        print(f"❌ [ERRO AO SALVAR]: {e}")

if __name__ == "__main__":
    processar_resultado_operacional()