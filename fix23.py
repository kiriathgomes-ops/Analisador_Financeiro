"""
fix23.py — Prompt ORB: regra 10 como prioridade MAXIMA + checklist

Contexto (teste comparativo 21/09):
    4 IAs (ChatGPT, MyHUB, Claude, Grok) receberam o mesmo snapshot.
    Resultado real: LOSS de 540 pts na VENDA.
    - ChatGPT e MyHUB: AGUARDAR (correto)
    - Claude e Grok:   VENDA (loss)

    Claude e Grok seguiram o fix22 (regra 3.5 permissiva) e ignoraram
    a regra 10 (gap vs ajuste > 500). O fix22 tornou o prompt
    permissivo demais para operar em divergencia.

Fix:
    A) Prompt_Rompimento_10h.txt
       1) Regra 3.5 volta a ser conservadora:
          DIVERGENTE -> AGUARDAR, com excecao restrita.
       2) Regra 10 elevada a PRIORIDADE MAXIMA (sobrepoe 3.5 e
          qualquer gatilho mecanico).
       3) Nova regra 12: checklist obrigatorio antes do VIES FINAL.
       4) Output template ganha campo "Regra 10 aplicavel".
       5) Secao 5.5 ganha passo final de checklist.

    B) analisar_rompimento_10h.py
       bloco_risco_orb() passa a receber o ajuste B3 e imprime o
       status da regra 10 no proprio Bloco E.5 (para a IA nao
       precisar calcular gap manualmente).

Uso:
    python fix23.py --dry-run
    python fix23.py
    python fix23.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO_PY = ROOT / "analisar_rompimento_10h.py"
ALVO_PROMPT = ROOT / "PromptIA" / "Prompt_Rompimento_10h.txt"

# ---------------------------------------------------------------------------
# PATCHES no analisar_rompimento_10h.py
# ---------------------------------------------------------------------------

PY_ASSIN_ANTIGO = (
    'def bloco_risco_orb(vela: dict, spot: dict) -> str:\n'
)

PY_ASSIN_NOVO = (
    'def bloco_risco_orb(vela: dict, spot: dict, ajuste: float = None) -> str:\n'
)

# 2) Insere bloco Regra 10 apos logica de Rompimento REAL
PY_REGRA10_ANTIGO = (
    '        else:\n'
    '            linhas.append("  Rompimento REAL    : NAO OCORREU (preco dentro da faixa)")\n'
    '\n'
    '    if A > 400:\n'
)

PY_REGRA10_NOVO = '''        else:
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
'''

# 3) Adiciona extracao do ajuste B3 em montar_snapshot
PY_SPOT_ANTIGO = (
    '    # Spot real do MT5 no instante da geracao (contorna defasagem do Bloco A)\n'
    '    spot = _obter_spot_mt5()\n'
    '    if spot:\n'
    '        print(f"[DIAG] Spot MT5: {spot[\'simbolo\']} last={spot[\'last\']} "\n'
    '              f"bid={spot[\'bid\']} ask={spot[\'ask\']}")\n'
    '\n'
    '    # Le o prompt do arquivo (se existir)\n'
)

PY_SPOT_NOVO = '''    # Spot real do MT5 no instante da geracao (contorna defasagem do Bloco A)
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

    # Le o prompt do arquivo (se existir)
'''

# 4) Chama bloco_risco_orb com ajuste
PY_CALL_ANTIGO = (
    '        bloco_vela10(vela),\n'
    '        "",\n'
    '        bloco_risco_orb(vela, spot),\n'
    '        "",\n'
    '        bloco_decisao(decisao),\n'
)

PY_CALL_NOVO = '''        bloco_vela10(vela),
        "",
        bloco_risco_orb(vela, spot, ajuste_b3),
        "",
        bloco_decisao(decisao),
'''

PATCHES_PY = [
    ("bloco_risco_orb aceita ajuste", PY_ASSIN_ANTIGO, PY_ASSIN_NOVO),
    ("insere checagem da regra 10 no Bloco E.5", PY_REGRA10_ANTIGO, PY_REGRA10_NOVO),
    ("montar_snapshot extrai ajuste B3", PY_SPOT_ANTIGO, PY_SPOT_NOVO),
    ("chama bloco_risco_orb com ajuste", PY_CALL_ANTIGO, PY_CALL_NOVO),
]

# ---------------------------------------------------------------------------
# PATCHES no Prompt_Rompimento_10h.txt
# ---------------------------------------------------------------------------

# P1) Regra 3.5 — volta a ser conservadora
P_3_5_ANTIGO = '''Se ALINHAMENTO = DIVERGENTE:
    - Se o preco esta DENTRO da faixa ORB (sem gatilho): VIES FINAL = AGUARDAR.
    - Se o preco JA ROMPEU e a distancia do gatilho > 150 pts:
      VIES FINAL = AGUARDAR (entrada tardia inviavel).
    - Se o preco ACABOU de romper (distancia < 150 pts do gatilho):
      o gatilho mecanico ORB permanece VALIDO. Reporte com confianca
      reduzida em 40% e sinalize em ALERTAS que o stop = amplitude da
      vela 10:00 (R:R ≈ 1 por design). Nao force AGUARDAR.
'''

P_3_5_NOVO = '''Se ALINHAMENTO = DIVERGENTE, VIES FINAL = AGUARDAR (conservador).

Racional: quando 2+ blocos direcionais apontam direcoes opostas, o
sinal mecanico (inclusive gatilho ORB disparado) perde confiabilidade.
A perda potencial (stop = amplitude) nao compensa a incerteza.

A UNICA excecao e quando TODOS os 3 criterios abaixo sao verdadeiros:
    (a) Regra 10 NAO esta ativa (gap spot vs ajuste < 500 pts)
    (b) 2+ blocos direcionais apontam a MESMA direcao do gatilho
    (c) gatilho mecanico disparou ha < 150 pts do preco atual

Se a excecao valer: reporte a direcao do gatilho com confianca
reduzida em 40%, sinalize em ALERTAS o stop = amplitude (R:R ≈ 1).
Na duvida, AGUARDAR.
'''

# P2) Regra 10 — prioridade maxima
P_R10_ANTIGO = '''10. Nunca sugerir operar contra ajuste B3 em gap > 500 pts.
'''

P_R10_NOVO = '''10. REGRA 10 — PRIORIDADE MAXIMA (sobrepoe TODAS as outras regras,
    incluindo a 3.5 e qualquer gatilho mecanico ja disparado):

    Nunca sugerir operar contra ajuste B3 em gap > 500 pts.

    Aplicacao obrigatoria ANTES do VIES FINAL:
      1. Calcule GAP = |spot MT5 - WIN_AJUSTE| (Bloco A ou E.5)
      2. Verifique o BLOCO E.5: se consta "REGRA 10 ATIVA", use como
         verdade absoluta — nao recalcule manualmente.
      3. Se GAP > 500 E direcao pretendida e contra a posicao vs ajuste:
           Preco ACIMA do ajuste -> VENDA bloqueada
           Preco ABAIXO do ajuste -> COMPRA bloqueada
           VIES FINAL = AGUARDAR
      4. Isso vale mesmo se o gatilho mecanico ORB disparou.
'''

# P3) Adiciona regra 12 (checklist)
P_R11_ANTIGO = '''11. Se o Bloco E (vela 10:00) estiver indisponível, VIES FINAL = AGUARDAR
    independentemente de qualquer outro fator. Sem vela, sem R:R, sem trade.
---
'''

P_R11_NOVO = '''11. Se o Bloco E (vela 10:00) estiver indisponível, VIES FINAL = AGUARDAR
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

# P4) Output template ganha campo "Regra 10 aplicavel"
P_TEMPLATE_ANTIGO = '''Posicao vs ajuste : [ACIMA | ABAIXO | NO AJUSTE]

Alinhamento geral : [ALINHADO | DIVERGENTE | NEUTRO]
'''

P_TEMPLATE_NOVO = '''Posicao vs ajuste : [ACIMA | ABAIXO | NO AJUSTE]
Regra 10 aplicavel: [SIM | NAO]  (gap vs ajuste = XXX pts)

Alinhamento geral : [ALINHADO | DIVERGENTE | NEUTRO]
'''

# P5) Secao 5.5 — adiciona passo 5
P_55_ANTIGO = '''4. Nunca copiar o campo `vies_final` do Bloco F sem antes validar que os
   Blocos A-E.5 sustentam a mesma conclusao.
'''

P_55_NOVO = '''4. Nunca copiar o campo `vies_final` do Bloco F sem antes validar que os
   Blocos A-E.5 sustentam a mesma conclusao.
5. ANTES de emitir o VIES FINAL, aplique o checklist da regra 12.
   Se qualquer item falhar, VIES FINAL = AGUARDAR.
6. O campo "Regra 10 aplicavel" no template e OBRIGATORIO. Se voce
   nao souber o gap exato, calcule a partir do Bloco A (WIN_AJUSTE)
   e do Bloco E.5 (Preco spot MT5).
'''

PATCHES_PROMPT = [
    ("reescreve regra 3.5 (conservadora + excecao restrita)", P_3_5_ANTIGO, P_3_5_NOVO),
    ("eleva regra 10 a prioridade maxima", P_R10_ANTIGO, P_R10_NOVO),
    ("adiciona regra 12 (checklist obrigatorio)", P_R11_ANTIGO, P_R11_NOVO),
    ("adiciona campo 'Regra 10 aplicavel' no template", P_TEMPLATE_ANTIGO, P_TEMPLATE_NOVO),
    ("secao 5.5 ganha passo de checklist", P_55_ANTIGO, P_55_NOVO),
]

IGNORAR = {"fix23.py"}

# ---------------------------------------------------------------------------


def _backup(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p: Path):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def _aplicar_patches(alvo: Path, patches, dry_run: bool) -> int:
    if not alvo.exists():
        print(f"[ERRO] {alvo.name} nao encontrado em {alvo.parent}")
        return 1

    conteudo = alvo.read_text(encoding="utf-8")
    novo = conteudo

    faltando = []
    for nome, old, new in patches:
        if old not in novo:
            faltando.append(nome)
            continue
        novo = novo.replace(old, new, 1)
        print(f"  [PATCH OK] {nome}")

    if faltando:
        print(f"\n[ABORT] {alvo.name} — padroes nao encontrados:")
        for f in faltando:
            print(f"    - {f}")
        return 2

    if novo == conteudo:
        print(f"  [INFO] {alvo.name}: nada mudou.")
        return 0

    if dry_run:
        print(f"  [DRY-RUN] {alvo.name}: nao salvo.")
        return 0

    bak = _backup(alvo)
    print(f"  [BACKUP] {bak.name}")
    alvo.write_text(novo, encoding="utf-8")
    print(f"  [OK] {alvo.name} atualizado.")
    return 0


def aplicar(dry_run: bool) -> int:
    print(f"\n[ALVO 1] {ALVO_PY.name}")
    r1 = _aplicar_patches(ALVO_PY, PATCHES_PY, dry_run)

    print(f"\n[ALVO 2] {ALVO_PROMPT}")
    r2 = _aplicar_patches(ALVO_PROMPT, PATCHES_PROMPT, dry_run)

    if r1 == 0 and r2 == 0:
        print("\n[SUCESSO] Todos os patches aplicados.")
        return 0
    return max(r1, r2)


def reverter() -> int:
    for alvo in (ALVO_PY, ALVO_PROMPT):
        if not alvo.exists():
            print(f"[ERRO] {alvo.name} nao encontrado.")
            continue
        bak = _ultimo_backup(alvo)
        if not bak:
            print(f"[ERRO] {alvo.name}: nenhum backup.")
            continue
        shutil.copy2(bak, alvo)
        print(f"[REVERTER] {alvo.name} restaurado de {bak.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    return reverter() if args.reverter else aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())