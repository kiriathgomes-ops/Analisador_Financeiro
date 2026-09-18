#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix4.py — LeilaoService nao faz mais fallback para dias anteriores
====================================================================

Problema:
  O LeilaoService._leituras_leilao_recente() tinha um fallback que buscava
  leituras de DIAS ANTERIORES quando nao encontrava nada para hoje. Isso
  contaminava o pipeline: o NOVO_MOTOR lia um preco de leilao de ontem
  como se fosse de hoje, gerando gaps absurdos.

  Bug observado em 18/09/2026:
    - Leilao de 17/09 tinha pico de 200200 (descoberta de preco)
    - Sniper nao rodou em 18/09 (ainda nao teve leilao)
    - LeilaoService pegou 200200 do dia 17 e retornou como se fosse hoje
    - NOVO_MOTOR calculou gap = 200200 - 188280 = +11920 pts (6.33%)
    - Classificou como EXTREMO (que seria correto SE o dado fosse real)

Solucao:
  1. Remove o fallback: se nao tem leitura de HOJE, retorna indisponivel
  2. Adiciona campo 'data_leitura' no retorno (auditoria)
  3. Log explicito quando nao achar leitura do dia

Uso:
    python fix4.py --dry-run
    python fix4.py
    python fix4.py --reverter
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


ARQUIVO_ALVO = Path("v2/core/services/leilao_service.py")


# ============================================================
# PATCHES
# ============================================================
PATCH_1_METODO = (
    "Remove fallback para dias anteriores em _leituras_leilao_recente()",
    '''    def _leituras_leilao_recente(self) -> List[Dict[str, Any]]:
        """
        Retorna as leituras do leilão do dia de hoje (até 09:00:30).
        Se hoje não tiver leitura (fim de semana, feriado, OCR não rodou),
        retorna as do último dia disponível no CSV.
        """
        registros = self._ler_csv()
        if not registros:
            return []

        hoje = date.today()

        # 1. Tenta hoje
        filtrados = self._filtrar_por_dia(registros, hoje)
        if filtrados:
            return filtrados

        # 2. Fallback: último dia com leitura
        dias = sorted({r["dt"].date() for r in registros}, reverse=True)
        if dias:
            return self._filtrar_por_dia(registros, dias[0])

        return []''',
    '''    def _leituras_leilao_recente(self) -> List[Dict[str, Any]]:
        """
        Retorna as leituras do leilão do dia de hoje (até 09:00:30).

        IMPORTANTE: NÃO faz fallback para dias anteriores. Se hoje não tem
        leitura, retorna lista vazia — o caller (NOVO_MOTOR) decide o que
        fazer. Retornar dados de outro dia contamina o pipeline com preço
        de leilão obsoleto.

        Bug corrigido em 18/09/2026: gap de +11920 pts causado por leilão
        de 17/09 lido como se fosse de hoje (sniper não tinha rodado ainda).
        """
        registros = self._ler_csv()
        if not registros:
            return []

        hoje = date.today()
        return self._filtrar_por_dia(registros, hoje)''',
)


PATCH_2_RETORNO_INDISPONIVEL = (
    "Adiciona data_leitura + log no retorno indisponivel",
    '''        if not leituras_brutas:
            return {
                "disponivel": False,
                "preco": None,
                "timestamp": None,
                "fonte": "INDISPONIVEL",
                "total_leituras": 0,
                "total_leituras_brutas": 0,
                "preco_max": None,
                "preco_min": None,
                "outliers_removidos": 0,
            }''',
    '''        if not leituras_brutas:
            print(
                f"[LEILAO] Sem leituras de hoje ({date.today().isoformat()}) "
                f"no CSV. Fonte: INDISPONIVEL (nao faz fallback para dias anteriores)."
            )
            return {
                "disponivel": False,
                "preco": None,
                "timestamp": None,
                "data_leitura": None,
                "fonte": "INDISPONIVEL",
                "total_leituras": 0,
                "total_leituras_brutas": 0,
                "preco_max": None,
                "preco_min": None,
                "outliers_removidos": 0,
            }''',
)


PATCH_3_RETORNO_OUTLIERS = (
    "Adiciona data_leitura no retorno pos-filtro de outliers",
    '''        if not leituras:
            return {
                "disponivel": False,
                "preco": None,
                "timestamp": None,
                "fonte": "INDISPONIVEL",
                "total_leituras": 0,
                "total_leituras_brutas": len(leituras_brutas),
                "preco_max": None,
                "preco_min": None,
                "outliers_removidos": outliers,
            }''',
    '''        if not leituras:
            return {
                "disponivel": False,
                "preco": None,
                "timestamp": None,
                "data_leitura": None,
                "fonte": "INDISPONIVEL",
                "total_leituras": 0,
                "total_leituras_brutas": len(leituras_brutas),
                "preco_max": None,
                "preco_min": None,
                "outliers_removidos": outliers,
            }''',
)


PATCH_4_RETORNO_OK = (
    "Adiciona data_leitura no retorno OK",
    '''        return {
            "disponivel": True,
            "preco": float(ultima["preco"]),
            "timestamp": ultima["dt"].isoformat(),
            "fonte": "OCR_LEILAO",
            "total_leituras": len(leituras),
            "total_leituras_brutas": len(leituras_brutas),
            "preco_max": float(max(precos)),
            "preco_min": float(min(precos)),
            "outliers_removidos": outliers,
        }''',
    '''        data_leitura = ultima["dt"].date().isoformat()
        print(
            f"[LEILAO] Leitura de hoje ({data_leitura}): "
            f"{ultima['preco']:.0f} pts (fonte OCR_LEILAO)"
        )
        return {
            "disponivel": True,
            "preco": float(ultima["preco"]),
            "timestamp": ultima["dt"].isoformat(),
            "data_leitura": data_leitura,
            "fonte": "OCR_LEILAO",
            "total_leituras": len(leituras),
            "total_leituras_brutas": len(leituras_brutas),
            "preco_max": float(max(precos)),
            "preco_min": float(min(precos)),
            "outliers_removidos": outliers,
        }''',
)


PATCHES = [
    PATCH_1_METODO,
    PATCH_2_RETORNO_INDISPONIVEL,
    PATCH_3_RETORNO_OUTLIERS,
    PATCH_4_RETORNO_OK,
]


# ============================================================
# LOGICA
# ============================================================
def _backup_mais_recente():
    backups = sorted(
        ARQUIVO_ALVO.parent.glob(f"{ARQUIVO_ALVO.name}.bak_*"),
        reverse=True,
    )
    return backups[0] if backups else None


def reverter() -> int:
    backup = _backup_mais_recente()
    if not backup:
        print(f"[ERRO] Nenhum backup encontrado para {ARQUIVO_ALVO}")
        return 1
    print(f"[INFO] Restaurando de: {backup.name}")
    shutil.copy2(backup, ARQUIVO_ALVO)
    print(f"[OK] {ARQUIVO_ALVO} restaurado")
    return 0


def _validar_sintaxe_py(caminho: Path) -> tuple[bool, str]:
    import ast
    try:
        ast.parse(caminho.read_text(encoding="utf-8"))
        return True, "OK"
    except SyntaxError as e:
        return False, f"SyntaxError linha {e.lineno}: {e.msg}"


def aplicar(dry_run: bool = False) -> int:
    if not ARQUIVO_ALVO.exists():
        print(f"[ERRO] Arquivo nao encontrado: {ARQUIVO_ALVO.resolve()}")
        print("       Rode a partir da raiz do projeto.")
        return 1

    conteudo_original = ARQUIVO_ALVO.read_text(encoding="utf-8")

    faltando = [nome for nome, antigo, _ in PATCHES if antigo not in conteudo_original]
    if faltando:
        print("[FALHA] Os seguintes patches nao encontraram o padrao esperado:")
        for nome in faltando:
            print(f"   - {nome}")
        print("\nNenhuma alteracao foi feita.")
        return 2

    if not dry_run:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = ARQUIVO_ALVO.with_suffix(f".py.bak_{timestamp}")
        shutil.copy2(ARQUIVO_ALVO, backup_path)
        print(f"[OK] Backup: {backup_path.name}")
    else:
        print("[DRY-RUN] Backup nao sera criado")

    conteudo = conteudo_original
    for i, (nome, antigo, novo) in enumerate(PATCHES, start=1):
        if antigo in conteudo:
            conteudo = conteudo.replace(antigo, novo, 1)
            print(f"[OK] Patch {i}/{len(PATCHES)}: {nome}")
        else:
            print(f"[AVISO] Patch {i}/{len(PATCHES)}: {nome} — nao encontrado apos patch anterior")
            return 3

    if not dry_run:
        ARQUIVO_ALVO.write_text(conteudo, encoding="utf-8")
        ok, msg = _validar_sintaxe_py(ARQUIVO_ALVO)
        if not ok:
            print(f"[ERRO] Sintaxe invalida: {msg}")
            return 4
        print(f"[OK] Sintaxe validada")
        print(f"\n[OK] {ARQUIVO_ALVO} atualizado com sucesso")
    else:
        print(f"\n[DRY-RUN] Simulacao concluida — arquivo NAO foi salvo")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LeilaoService nao faz fallback para dias anteriores"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simula sem salvar")
    parser.add_argument("--reverter", action="store_true", help="Restaura do backup")
    args = parser.parse_args()

    print("=" * 60)
    print(" fix4.py — LeilaoService sem fallback entre dias")
    print("=" * 60)

    if args.reverter:
        return reverter()
    return aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())