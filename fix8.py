#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix8.py — Deteccao de leilao por cor de fundo (azul)
=====================================================

Problema:
  A regiao do OCR le corretamente durante o leilao (fundo azul), mas
  quando o leilao fecha e a barra azul some, a mesma regiao passa a
  capturar lixo do grafico (ex: '6.760').

  A heuristica de horario (08:50-09:05) e fragil: o leilao pode fechar
  antes ou depois.

Solucao:
  Detectar a cor de fundo da regiao. A barra de leilao do Profit tem
  fundo AZUL caracteristico. Se a regiao nao for predominantemente azul,
  o leilao nao esta ativo — pula OCR.

Alteracoes em win_abertura_sniper.py:
  1. Adiciona helper _regiao_e_azul_leilao()
  2. Adiciona log de transicao (so quando muda de estado)
  3. No main(), so roda OCR quando a regiao tem fundo azul
  4. Contador separado de ciclos fora do leilao

Uso:
    python fix8.py --dry-run
    python fix8.py
    python fix8.py --reverter
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


ARQUIVO_ALVO = Path("win_abertura_sniper.py")


# ============================================================
# PATCHES
# ============================================================
PATCH_1_HELPER = (
    "Adiciona helper _regiao_e_azul_leilao()",
    '''def capturar_regiao(regiao):
    with mss.MSS() as sct:
        img = sct.grab(regiao)
        return Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")''',
    '''def capturar_regiao(regiao):
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
        return False''',
)


PATCH_2_MAIN_LOOP = (
    "main(): so roda OCR quando a regiao tem fundo azul",
    '''    try:
        while True:
            img = capturar_regiao(regiao)
            preco, conf = extrair_numero(img)
            agora_dt = datetime.now()
            agora = agora_dt.strftime('%H:%M:%S')

            total_tentativas += 1

            if preco:''',
    '''    # Contador de ciclos fora do leilao (para relatorio final)
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
                print(f"[{agora}] Fora do leilao (sem fundo azul)", end="\\r")
                time.sleep(INTERVALO)
                continue

            # ---- Leilao ativo: roda OCR normal ----
            preco, conf = extrair_numero(img)
            total_tentativas += 1

            if preco:''',
)


PATCH_3_RELATORIO = (
    "Relatorio final: adiciona contador de ciclos fora do leilao",
    '''        print(f"  Rejeitadas pelo filtro  : {total_rejeitadas_filtro}")
        print(f"      ├─ fora faixa abs.  : {filtro.rejeicoes_absoluta}")
        print(f"      └─ salto vs mediana : {filtro.rejeicoes_mediana}")
        print(f"  Gravações por mudança   : {total_mudanca}")''',
    '''        print(f"  Rejeitadas pelo filtro  : {total_rejeitadas_filtro}")
        print(f"      ├─ fora faixa abs.  : {filtro.rejeicoes_absoluta}")
        print(f"      └─ salto vs mediana : {filtro.rejeicoes_mediana}")
        print(f"  Ciclos fora do leilao   : {total_fora_leilao}")
        print(f"  Gravações por mudança   : {total_mudanca}")''',
)


PATCHES = [
    PATCH_1_HELPER,
    PATCH_2_MAIN_LOOP,
    PATCH_3_RELATORIO,
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
            print(f"[AVISO] Patch {i}/{len(PATCHES)}: {nome} — nao encontrado")
            return 3

    if not dry_run:
        ARQUIVO_ALVO.write_text(conteudo, encoding="utf-8")
        ok, msg = _validar_sintaxe_py(ARQUIVO_ALVO)
        if not ok:
            print(f"[ERRO] Sintaxe invalida: {msg}")
            return 4
        print(f"[OK] Sintaxe validada")
        print(f"\n[OK] {ARQUIVO_ALVO} atualizado com sucesso")
        print(f"     {len(PATCHES)} patches aplicados")
    else:
        print(f"\n[DRY-RUN] Simulacao concluida — arquivo NAO foi salvo")
        print(f"          {len(PATCHES)} patches seriam aplicados")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deteccao de leilao por cor de fundo (azul)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simula sem salvar")
    parser.add_argument("--reverter", action="store_true", help="Restaura do backup")
    args = parser.parse_args()

    print("=" * 60)
    print(" fix8.py — Deteccao de leilao por cor de fundo")
    print("=" * 60)

    if args.reverter:
        return reverter()
    return aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())