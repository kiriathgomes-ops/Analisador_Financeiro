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