# ============================================================
# ARQUIVO: Validador.py
# DATA: 30/07/2026 | Atualizado 29/10/2026
# MOTIVO: Fase 3 - Validação, sanitização e padronização dos
#         33 ativos (com WIN e WDO Ajustes separados).
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
    ativo_raw = item.get("ativo")
    status_fonte = item.get("status")
    dados = item.get("dados_reais")

    _status_ok = isinstance(status_fonte, str) and status_fonte.startswith("OK")
    if not _status_ok or not dados:
        return False, f"Status de coleta inválido: {status_fonte}", None

    close = dados.get("close")

    if close is None or not isinstance(close, (int, float)) or close <= 0:
        return False, f"Preço/Taxa de fechamento inválido ou zerado: {close}", None

    nome_padronizado = MAPEAMENTO_TICKERS.get(ativo_raw, ativo_raw)

    # INCLUINDO OS NOVOS CAMPOS AQUI
    dados_sanitizados = {
        "ativo_id": nome_padronizado,
        "ticker_original": ativo_raw,
        "fonte": item.get("fonte"),
        "timestamp_coleta": item.get("timestamp"),
        "close": float(close),
        "previous_close": _to_float_safe(dados.get("fechamento_anterior")),
        "open": _to_float_safe(dados.get("open")),
        "high": _to_float_safe(dados.get("high")),
        "low": _to_float_safe(dados.get("low")),
        "change_percent": _to_float_safe(dados.get("change_percent")),
        "volume": _to_float_safe(dados.get("volume")),
        
        # NOVOS CAMPOS (Pré e Diário)
        "change_daily": _to_float_safe(dados.get("change_daily")),
        "premarket_change": _to_float_safe(dados.get("premarket_change")),
        "premarket_close": _to_float_safe(dados.get("premarket_close")),
    }

    for chave_extra in ("var_abs", "fechamento_real", "preco_medio"):
        if chave_extra in dados and dados[chave_extra] is not None:
            dados_sanitizados[chave_extra] = _to_float_safe(dados[chave_extra])

    return True, "Aprovado", dados_sanitizados


# ------------------------------------------------------------
# ORQUESTRAÇÃO
# ------------------------------------------------------------
def executar_validacao() -> bool:
    if not FILE_INPUT.exists():
        print(f"[ERRO] Arquivo de entrada não encontrado: {FILE_INPUT}")
        return False

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Lendo {FILE_INPUT.name}...")

    with open(FILE_INPUT, "r", encoding="utf-8") as f:
        coleta = json.load(f)

    itens = coleta.get("coletas", [])
    aprovados = []
    rejeitados = []

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
    print(" FASE 3: ENGINE DE VALIDAÇÃO E SANITIZAÇÃO DE DADOS (33 ATIVOS)")
    print("=" * 60)
    executar_validacao()