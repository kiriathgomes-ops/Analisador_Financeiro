#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rodar_SMC_Regras.py
===================
Wrapper chamado pelo main_pipeline.

1. Descobre o contrato WIN no MT5 (Dados_MT5.json ou busca)
2. Executa Motor_SMC_Regras.analisar_smc
3. Salva Coletas/AnaliseGraficaSMC_Regras.json

Não interrompe o pipeline se MT5 estiver offline (só registra aviso).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
COLETAS = BASE_DIR / "Coletas"
SAIDA = COLETAS / "AnaliseGraficaSMC_Regras.json"

# garante import do motor na raiz do projeto
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def log(msg: str, ok: bool = True):
    icone = "[Ok]" if ok else "[ERRO]"
     # Remove qualquer caractere não-ASCII para evitar UnicodeEncodeError
    safe_msg = msg.encode('ascii', 'ignore').decode('ascii')
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {icone} {msg}")


def descobrir_simbolo_win() -> str:
    """Prioridade: Dados_MT5.json → env → default WINV26."""
    caminho = COLETAS / "Dados_MT5.json"
    if caminho.exists():
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                data = json.load(f)
            # layouts possíveis
            for chave in ("contrato_win", "win", "WIN", "symbol_win"):
                if chave in data and data[chave]:
                    return str(data[chave])
            contratos = data.get("contratos") or data.get("ativos") or {}
            if isinstance(contratos, dict):
                for k, v in contratos.items():
                    ku = str(k).upper()
                    if "WIN" in ku and "AJUSTE" not in ku:
                        if isinstance(v, dict) and v.get("symbol"):
                            return str(v["symbol"])
                        return str(k)
            # last ticks
            lasts = data.get("lasts") or data.get("ultimos") or {}
            if isinstance(lasts, dict):
                for k in lasts:
                    if "WIN" in str(k).upper():
                        return str(k)
        except Exception as e:
            log(f"Falha lendo Dados_MT5.json: {e}", ok=False)

    env = os.getenv("SMC_SYMBOL_WIN", "").strip()
    if env:
        return env
    return "WINV26"


def main() -> int:
    log("Iniciando Motor SMC por regras...")
    try:
        from Motor_SMC_Regras import analisar_smc, salvar_resultado, carregar_mt5
    except ImportError as e:
        log(f"Motor_SMC_Regras não encontrado: {e}", ok=False)
        return 0  # não quebra pipeline

    symbol = descobrir_simbolo_win()
    log(f"Símbolo alvo: {symbol}")

    try:
        candles, simbolo_usado = carregar_mt5(symbol, timeframe_min=5, qtd=120)
    except Exception as e:
        log(f"MT5 indisponível ou sem rates ({e}). Pipeline segue sem SMC regras.", ok=False)
        # grava stub para a UI saber que falhou
        stub = {
            "timestamp": datetime.now().isoformat(),
            "ativo": "WIN",
            "timeframe": "5m",
            "fonte": "regras_smc",
            "erro": str(e),
            "bias_direcional": "LATERAL",
            "direcao_estrutura": "LATERAL",
            "bos": False,
            "choch": False,
            "confianca_visual": 0,
            "estruturas_coletadas": [],
            "liquidez_relevante": [],
            "zonas_de_interesse_e_cenarios": ["SMC regras indisponível nesta execução."],
        }
        COLETAS.mkdir(parents=True, exist_ok=True)
        with open(SAIDA, "w", encoding="utf-8") as f:
            json.dump(stub, f, indent=2, ensure_ascii=False)
        return 0

    resultado = analisar_smc(candles, ativo="WIN", timeframe="5m")
    resultado["simbolo_mt5"] = simbolo_usado
    path = salvar_resultado(resultado, SAIDA)
    log(
        f"SMC regras OK | bias={resultado.get('bias_direcional')} "
        f"conf={resultado.get('confianca_visual')} → {path.name}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
