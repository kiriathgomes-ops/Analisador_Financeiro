"""
fix23d.py — Aplica os 5 patches do fix23 no Prompt_Rompimento_10h.txt
           com regex tolerante e verificacao pos-aplicacao.

Motivo: os fix23, fix23b e fix23c abortaram sem salvar por variacao
de espacos no arquivo. Este usa regex para casar por estrutura,
nao por texto literal.

Uso:
    python fix23d.py --dry-run
    python fix23d.py
    python fix23d.py --reverter
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "PromptIA" / "Prompt_Rompimento_10h.txt"


# --- Blocos de texto NOVOS -------------------------------------------------

REGRA_3_5_NOVO = '''Se ALINHAMENTO = DIVERGENTE, VIES FINAL = AGUARDAR (conservador).

Racional: quando 2+ blocos direcionais apontam direcoes opostas, o
sinal mecanico (inclusive gatilho ORB disparado) perde confiabilidade.
A perda potencial (stop = amplitude) nao compensa a incerteza.

A UNICA excecao e quando TODOS os 3 criterios abaixo sao verdadeiros:
    (a) Regra 10 NAO esta ativa (gap spot vs ajuste < 500 pts)
    (b) 2+ blocos direcionais apontam a MESMA direcao do gatilho
    (c) gatilho mecanico disparou ha < 150 pts do preco atual

Se a excecao valer: reporte a direcao do gatilho com confianca
reduzida em 40%, sinalize em ALERTAS o stop = amplitude (R:R ~ 1).
Na duvida, AGUARDAR.
'''

REGRA_10_NOVO = '''10. REGRA 10 - PRIORIDADE MAXIMA (sobrepoe TODAS as outras regras,
    incluindo a 3.5 e qualquer gatilho mecanico ja disparado):

    Nunca sugerir operar contra ajuste B3 em gap > 500 pts.

    Aplicacao obrigatoria ANTES do VIES FINAL:
      1. Calcule GAP = |spot MT5 - WIN_AJUSTE| (Bloco A ou E.5)
      2. Verifique o BLOCO E.5: se consta "REGRA 10 ATIVA", use como
         verdade absoluta - nao recalcule manualmente.
      3. Se GAP > 500 E direcao pretendida e contra a posicao vs ajuste:
           Preco ACIMA do ajuste -> VENDA bloqueada
           Preco ABAIXO do ajuste -> COMPRA bloqueada
           VIES FINAL = AGUARDAR
      4. Isso vale mesmo se o gatilho mecanico ORB disparou.
'''

REGRA_12_NOVO = '''11. Se o Bloco E (vela 10:00) estiver indisponivel, VIES FINAL = AGUARDAR
    independentemente de qualquer outro fator. Sem vela, sem R:R, sem trade.

12. CHECKLIST OBRIGATORIO ANTES DO VIES FINAL.
    Aplique na ordem. Se qualquer item FALHAR, VIES FINAL = AGUARDAR.

    [ ] 1. Bloco E disponivel? (regra 11)
    [ ] 2. Amplitude no filtro [50, 700]? (regra 2)
    [ ] 3. Bloco E.5 indica "REGRA 10 ATIVA"? Se SIM -> AGUARDAR.
    [ ] 4. Alinhamento geral NAO e DIVERGENTE? (regra 3.5)
    [ ] 5. R:R a mercado >= 0,9? (regra 5)
    [ ] 6. Pelo menos 3 dos 6 fatores alinhados? (regra 4)

    Se TODOS passarem -> VIES FINAL = direcao validada
    Se algum FALHAR   -> VIES FINAL = AGUARDAR
    Se regra 2 falhar -> VIES FINAL = NAO OPERAR
---
'''

SECAO_55_ITEM1_NOVO = "   Blocos A-E.5 (ativos, metricas, estimativa, SMC, vela 10:00, risco ORB).\n"

SECAO_55_PASSOS_56 = (
    "4. Nunca copiar o campo `vies_final` do Bloco F sem antes validar que os\n"
    "   Blocos A-E.5 sustentam a mesma conclusao.\n"
    "5. ANTES de emitir o VIES FINAL, aplique o checklist da regra 12.\n"
    "   Se qualquer item falhar, VIES FINAL = AGUARDAR.\n"
    "6. O campo \"Regra 10 aplicavel\" no template e OBRIGATORIO. Se voce\n"
    "   nao souber o gap exato, calcule a partir do Bloco A (WIN_AJUSTE)\n"
    "   e do Bloco E.5 (Preco spot MT5).\n"
)


# --- Helpers ----------------------------------------------------------------

def _backup(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p: Path):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def _aplicar_regex(conteudo: str, padrao: str, novo: str, flags=re.MULTILINE | re.DOTALL):
    """Aplica regex e retorna (novo_conteudo, mudou)."""
    rx = re.compile(padrao, flags)
    if not rx.search(conteudo):
        return conteudo, False
    return rx.sub(novo, conteudo, count=1), True


def aplicar(dry_run: bool) -> int:
    if not ALVO.exists():
        print(f"[ERRO] {ALVO.name} nao encontrado")
        return 1

    conteudo = ALVO.read_text(encoding="utf-8")
    novo = conteudo
    relatorio = []

    # --- Patch 1: regra 3.5 ---
    padrao_35 = (
        r"Se ALINHAMENTO = DIVERGENTE[^\n]*\n"
        r"(?:.*?\n)*?"
        r"(?=\n---|\n## )"
    )
    novo, ok = _aplicar_regex(novo, padrao_35, REGRA_3_5_NOVO + "\n", re.MULTILINE)
    relatorio.append(("regra 3.5 reescrita (conservadora)", ok))

    # --- Patch 2: regra 10 elevada ---
    padrao_r10 = (
        r"10\. Nunca sugerir operar contra ajuste B3 em gap > 500 pts\.\n"
    )
    novo, ok = _aplicar_regex(novo, padrao_r10, REGRA_10_NOVO, re.MULTILINE)
    relatorio.append(("regra 10 -> prioridade maxima", ok))

    # --- Patch 3: regra 12 (checklist) ---
    padrao_r12 = (
        r"11\. Se o Bloco E \(vela 10:00\) estiver indispon[^\n]*\n"
        r"(?:\s+[^\n]*\n)*?"
        r"---\n"
    )
    novo, ok = _aplicar_regex(novo, padrao_r12, REGRA_12_NOVO, re.MULTILINE)
    relatorio.append(("regra 12 (checklist) adicionada", ok))

    # --- Patch 4: template — campo Regra 10 aplicavel ---
    padrao_tpl = (
        r"(Posicao vs ajuste : \[ACIMA \| ABAIXO \| NO AJUSTE\]\n)"
    )
    novo, ok = _aplicar_regex(
        novo,
        padrao_tpl,
        r"\1Regra 10 aplicavel: [SIM | NAO]  (gap vs ajuste = XXX pts)\n",
        re.MULTILINE,
    )
    relatorio.append(("campo 'Regra 10 aplicavel' no template", ok))

    # --- Patch 5a: item 1 da secao 5.5 -> A-E.5 ---
    padrao_55a = (
        r"(\d+\.\s+Aplicar o framework das 6 etapas[^\n]*\n)"
        r"\s*Blocos A-E \(ativos[^\n]*\n"
    )
    novo, ok = _aplicar_regex(
        novo,
        padrao_55a,
        r"\1" + SECAO_55_ITEM1_NOVO,
        re.MULTILINE,
    )
    relatorio.append(("secao 5.5 item 1 -> Blocos A-E.5", ok))

    # --- Patch 5b: typo "oBloco" -> "o Bloco" ---
    novo, ok = _aplicar_regex(
        novo,
        r"Citar\s+o\s*Bloco\s+F",
        "Citar o Bloco F",
        re.MULTILINE,
    )
    relatorio.append(("typo 'oBloco' corrigido", ok))

    # --- Patch 5c: passos 5 e 6 na secao 5.5 ---
    padrao_55c = (
        r"4\. Nunca copiar o campo `vies_final`[^\n]*\n"
        r"(?:\s+[^\n]*\n)*?"
        r"(?=\n---)"
    )
    novo, ok = _aplicar_regex(novo, padrao_55c, SECAO_55_PASSOS_56, re.MULTILINE)
    relatorio.append(("passos 5 e 6 na secao 5.5", ok))

    # --- Relatorio ---
    print()
    for nome, ok in relatorio:
        status = "OK" if ok else "SKIP (ja aplicado ou padrao nao achado)"
        print(f"  [{status}] {nome}")

    aplicados = sum(1 for _, ok in relatorio if ok)
    print(f"\n  Total: {aplicados}/{len(relatorio)} patches aplicados")

    if novo == conteudo:
        print("\n[INFO] nada mudou — todos os patches ja estavam aplicados?")
        return 0

    if dry_run:
        print("\n[DRY-RUN] nada salvo.")
        return 0

    bak = _backup(ALVO)
    print(f"\n[BACKUP] {bak.name}")
    ALVO.write_text(novo, encoding="utf-8")
    print(f"[OK] {ALVO.name} atualizado.")
    return 0


def reverter() -> int:
    if not ALVO.exists():
        print(f"[ERRO] {ALVO.name} nao encontrado.")
        return 1
    bak = _ultimo_backup(ALVO)
    if not bak:
        print("[ERRO] nenhum backup.")
        return 1
    shutil.copy2(bak, ALVO)
    print(f"[REVERTER] {ALVO.name} restaurado de {bak.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    return reverter() if args.reverter else aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())