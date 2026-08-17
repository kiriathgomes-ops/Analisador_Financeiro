# ============================================================
# ARQUIVO: v2/core/engines/opening_scenario_engine.py
# FASE 6 (inicial) — Motor de Cenários de Abertura WINFUT
#
# Consome WinSession e produz OpeningScenario.
# Não gera ordem. Não afirma certeza.
# Linguagem: cenário provável, probabilidade relativa, invalidação.
# ============================================================

from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

from v2.core.contracts.win_session import (
    WinSession,
    OpeningScenario,
    RelacaoComAjuste,
    ComportamentosPossiveis,
)


class OpeningScenarioEngine:
    """
    Motor de cenários de abertura em relação ao ajuste.

    Regras iniciais (heurísticas — serão refinadas com histórico na FASE 5/6):
      - Distância last × ajuste define a "força" do posicionamento.
      - Gap projetado reforça ou suaviza a direção.
      - Contexto (VIX, ES, ADRs) qualifica o cenário, não decide sozinho.
    """

    # Limiares em pontos de WIN (ajustáveis depois)
    LIMIAR_PROXIMO = 50          # até 50 pts → perto do ajuste
    LIMIAR_MODERADO = 150        # 50–150 → moderado
    LIMIAR_DISTANTE = 300        # > 300 → gap grande / excesso

    def processar(self, session: WinSession) -> OpeningScenario:
        cenario = OpeningScenario()

        dist = session.distancias.last_vs_ajuste_pts
        gap_pts = session.gap.gap_projetado_pts
        gap_dir = session.gap.direcao_gap
        posicao = session.cenario.relacao_com_ajuste.posicao

        # --------------------------------------------------------
        # 1. Posição em relação ao ajuste
        # --------------------------------------------------------
        if not posicao and dist is not None:
            if dist > 0:
                posicao = "ACIMA"
            elif dist < 0:
                posicao = "ABAIXO"
            else:
                posicao = "NO_AJUSTE"

        cenario.relacao_com_ajuste = RelacaoComAjuste(posicao=posicao)

        # --------------------------------------------------------
        # 2. Direção provável (gap + posição)
        # --------------------------------------------------------
        direcao = self._definir_direcao(posicao, gap_dir, dist)
        cenario.direcao_provavel = direcao

        # --------------------------------------------------------
        # 3. Intensidade da distância
        # --------------------------------------------------------
        intensidade = self._classificar_intensidade(dist)

        # --------------------------------------------------------
        # 4. Comportamentos possíveis (heurística inicial)
        # --------------------------------------------------------
        comportamentos = self._estimar_comportamentos(
            posicao=posicao,
            intensidade=intensidade,
            dist=dist,
            gap_pts=gap_pts,
            session=session,
        )
        cenario.comportamentos = comportamentos

        # --------------------------------------------------------
        # 5. Cenário principal (texto)
        # --------------------------------------------------------
        cenario.relacao_com_ajuste.cenario_principal = self._texto_cenario_principal(
            posicao, intensidade, direcao, dist
        )
        cenario.relacao_com_ajuste.probabilidade_cenario = self._prob_cenario_principal(
            comportamentos
        )

        # --------------------------------------------------------
        # 6. Cenário alternativo
        # --------------------------------------------------------
        cenario.cenario_alternativo = self._texto_cenario_alternativo(
            posicao, intensidade, comportamentos
        )

        # --------------------------------------------------------
        # 7. Probabilidade de direção (heurística)
        # --------------------------------------------------------
        cenario.probabilidade_direcao = self._prob_direcao(
            intensidade, session
        )

        # --------------------------------------------------------
        # 8. Confiança geral e contexto
        # --------------------------------------------------------
        cenario.confianca_geral = self._confianca_geral(session, intensidade)
        cenario.contexto_resumo = self._montar_contexto_resumo(session)
        cenario.niveis_observacao = dict(session.cenario.niveis_observacao or {})

        if session.precos.ajuste is not None:
            cenario.niveis_observacao.setdefault("ajuste", session.precos.ajuste)
        if session.precos.last_mt5 is not None:
            cenario.niveis_observacao.setdefault("last_mt5", session.precos.last_mt5)
        if dist is not None:
            cenario.niveis_observacao["distancia_ajuste_pts"] = dist

        return cenario

    # ============================================================
    # Regras internas
    # ============================================================

    def _definir_direcao(
        self,
        posicao: Optional[str],
        gap_dir: Optional[str],
        dist: Optional[float],
    ) -> str:
        if gap_dir in ("ALTA", "BAIXA", "NEUTRO"):
            return gap_dir
        if posicao == "ACIMA":
            return "ALTA"
        if posicao == "ABAIXO":
            return "BAIXA"
        return "NEUTRO"

    def _classificar_intensidade(self, dist: Optional[float]) -> str:
        if dist is None:
            return "INDEFINIDO"
        ad = abs(dist)
        if ad <= self.LIMIAR_PROXIMO:
            return "PROXIMO"
        if ad <= self.LIMIAR_MODERADO:
            return "MODERADO"
        if ad <= self.LIMIAR_DISTANTE:
            return "DISTANTE"
        return "EXCESSO"

    def _estimar_comportamentos(
        self,
        posicao: Optional[str],
        intensidade: str,
        dist: Optional[float],
        gap_pts: Optional[float],
        session: WinSession,
    ) -> ComportamentosPossiveis:
        """
        Heurística inicial (não estatística).

        Ideia geral:
          - Perto do ajuste → maior chance de teste / rejeição / retorno
          - Distante / excesso → maior chance de rompimento ou falso rompimento
          - Contexto adverso (VIX alto, ES fraco) reduz continuidade
        """
        cb = ComportamentosPossiveis()

        # Base neutra
        base = {
            "romper_e_continuar": 25.0,
            "testar_e_rejeitar": 25.0,
            "testar_e_recuperar": 15.0,
            "retornar_ao_ajuste": 20.0,
            "falso_rompimento": 15.0,
        }

        if intensidade == "PROXIMO":
            base = {
                "romper_e_continuar": 15.0,
                "testar_e_rejeitar": 30.0,
                "testar_e_recuperar": 20.0,
                "retornar_ao_ajuste": 25.0,
                "falso_rompimento": 10.0,
            }
        elif intensidade == "MODERADO":
            base = {
                "romper_e_continuar": 30.0,
                "testar_e_rejeitar": 25.0,
                "testar_e_recuperar": 15.0,
                "retornar_ao_ajuste": 15.0,
                "falso_rompimento": 15.0,
            }
        elif intensidade == "DISTANTE":
            base = {
                "romper_e_continuar": 35.0,
                "testar_e_rejeitar": 15.0,
                "testar_e_recuperar": 10.0,
                "retornar_ao_ajuste": 15.0,
                "falso_rompimento": 25.0,
            }
        elif intensidade == "EXCESSO":
            base = {
                "romper_e_continuar": 25.0,
                "testar_e_rejeitar": 10.0,
                "testar_e_recuperar": 10.0,
                "retornar_ao_ajuste": 20.0,
                "falso_rompimento": 35.0,
            }

        # Ajuste leve por contexto (VIX alto reduz continuidade)
        vix = session.contexto.vix.preco
        if vix is not None and vix >= 25:
            base["romper_e_continuar"] = max(5.0, base["romper_e_continuar"] - 8)
            base["falso_rompimento"] = min(45.0, base["falso_rompimento"] + 5)
            base["retornar_ao_ajuste"] = min(40.0, base["retornar_ao_ajuste"] + 3)

        # ES negativo forte reduz rompimento de alta
        es_var = session.contexto.sp500_fut.variacao_pct
        if posicao == "ACIMA" and es_var is not None and es_var < -0.5:
            base["romper_e_continuar"] = max(5.0, base["romper_e_continuar"] - 7)
            base["testar_e_rejeitar"] = min(40.0, base["testar_e_rejeitar"] + 5)

        if posicao == "ABAIXO" and es_var is not None and es_var > 0.5:
            base["romper_e_continuar"] = max(5.0, base["romper_e_continuar"] - 7)
            base["testar_e_recuperar"] = min(35.0, base["testar_e_recuperar"] + 5)

        # Calendário econômico de alto impacto → mais cautela (menos continuidade)
        news = session.noticias
        if news and news.disponivel:
            if news.risco_abertura_win or news.tem_3_estrelas_brasil_0900:
                base["romper_e_continuar"] = max(5.0, base["romper_e_continuar"] - 10)
                base["falso_rompimento"] = min(45.0, base["falso_rompimento"] + 8)
                base["retornar_ao_ajuste"] = min(40.0, base["retornar_ao_ajuste"] + 5)
            elif news.classificacao_risco in ("ALTO", "EXTREMO"):
                base["romper_e_continuar"] = max(5.0, base["romper_e_continuar"] - 6)
                base["falso_rompimento"] = min(40.0, base["falso_rompimento"] + 5)

        # Normaliza para ~100
        total = sum(base.values()) or 1.0
        fator = 100.0 / total
        cb.romper_e_continuar = round(base["romper_e_continuar"] * fator, 1)
        cb.testar_e_rejeitar = round(base["testar_e_rejeitar"] * fator, 1)
        cb.testar_e_recuperar = round(base["testar_e_recuperar"] * fator, 1)
        cb.retornar_ao_ajuste = round(base["retornar_ao_ajuste"] * fator, 1)
        cb.falso_rompimento = round(base["falso_rompimento"] * fator, 1)

        return cb

    def _prob_cenario_principal(self, cb: ComportamentosPossiveis) -> float:
        vals = [
            cb.romper_e_continuar or 0,
            cb.testar_e_rejeitar or 0,
            cb.testar_e_recuperar or 0,
            cb.retornar_ao_ajuste or 0,
            cb.falso_rompimento or 0,
        ]
        return round(max(vals), 1)

    def _prob_direcao(self, intensidade: str, session: WinSession) -> float:
        base = {
            "PROXIMO": 52.0,
            "MODERADO": 58.0,
            "DISTANTE": 62.0,
            "EXCESSO": 55.0,
            "INDEFINIDO": 50.0,
        }.get(intensidade, 50.0)

        # Contexto alinhado aumenta um pouco
        es = session.contexto.sp500_fut.variacao_pct
        adrs = session.contexto.indicador_adrs
        if es is not None and adrs is not None:
            if (es > 0 and adrs > 0) or (es < 0 and adrs < 0):
                base = min(70.0, base + 5)
        return round(base, 1)

    def _confianca_geral(self, session: WinSession, intensidade: str) -> float:
        conf = 50.0
        if session.precos.ajuste is not None and session.precos.last_mt5 is not None:
            conf += 15
        if session.gap.gap_projetado_pts is not None:
            conf += 10
        if session.contexto.vix.preco is not None:
            conf += 5
        if session.contexto.sp500_fut.preco is not None:
            conf += 5
        if intensidade in ("MODERADO", "DISTANTE"):
            conf += 5
        if intensidade == "EXCESSO":
            conf -= 5  # gap extremo = mais incerteza de continuidade
        # Notícias de alto impacto reduzem confiança na continuidade
        news = session.noticias
        if news and news.disponivel:
            if news.risco_abertura_win or news.tem_3_estrelas_brasil_0900:
                conf -= 12
            elif news.classificacao_risco == "EXTREMO":
                conf -= 10
            elif news.classificacao_risco == "ALTO":
                conf -= 6
            elif news.classificacao_risco == "ATENÇÃO":
                conf -= 3
        return round(min(85.0, max(30.0, conf)), 1)

    def _texto_cenario_principal(
        self,
        posicao: Optional[str],
        intensidade: str,
        direcao: str,
        dist: Optional[float],
    ) -> str:
        dist_txt = f"{dist:+.0f} pts" if dist is not None else "n/d"

        if posicao == "ACIMA":
            if intensidade == "PROXIMO":
                return (
                    f"Preço pouco acima do ajuste ({dist_txt}). "
                    "Cenário mais provável: teste do ajuste com possível rejeição ou retorno."
                )
            if intensidade == "MODERADO":
                return (
                    f"Abertura/preço moderadamente acima do ajuste ({dist_txt}). "
                    "Cenário principal: tentar continuidade de alta, com risco de teste do ajuste."
                )
            if intensidade in ("DISTANTE", "EXCESSO"):
                return (
                    f"Preço bem acima do ajuste ({dist_txt}). "
                    "Cenário principal: risco elevado de excesso de gap — "
                    "continuidade possível, mas falso rompimento e retorno ao ajuste ganham peso."
                )
        if posicao == "ABAIXO":
            if intensidade == "PROXIMO":
                return (
                    f"Preço pouco abaixo do ajuste ({dist_txt}). "
                    "Cenário mais provável: teste do ajuste com possível recuperação ou rejeição."
                )
            if intensidade == "MODERADO":
                return (
                    f"Preço moderadamente abaixo do ajuste ({dist_txt}). "
                    "Cenário principal: pressão vendedora com risco de teste de recuperação do ajuste."
                )
            if intensidade in ("DISTANTE", "EXCESSO"):
                return (
                    f"Preço bem abaixo do ajuste ({dist_txt}). "
                    "Cenário principal: gap de baixa relevante — continuidade possível, "
                    "mas falso rompimento e busca do ajuste ganham peso."
                )
        return "Posição indefinida em relação ao ajuste. Aguardando definição."

    def _texto_cenario_alternativo(
        self,
        posicao: Optional[str],
        intensidade: str,
        cb: ComportamentosPossiveis,
    ) -> str:
        # Pega o segundo maior comportamento
        itens = [
            ("rompimento e continuidade", cb.romper_e_continuar or 0),
            ("teste e rejeição", cb.testar_e_rejeitar or 0),
            ("teste e recuperação", cb.testar_e_recuperar or 0),
            ("retorno ao ajuste", cb.retornar_ao_ajuste or 0),
            ("falso rompimento", cb.falso_rompimento or 0),
        ]
        itens_ord = sorted(itens, key=lambda x: x[1], reverse=True)
        if len(itens_ord) < 2:
            return "Cenário alternativo não calculado."
        alt_nome, alt_pct = itens_ord[1]
        return f"Alternativo: {alt_nome} (~{alt_pct:.0f}%). Monitorar invalidação do cenário principal."

    def _montar_contexto_resumo(self, session: WinSession) -> List[str]:
        linhas: List[str] = []
        ctx = session.contexto

        if ctx.vix.preco is not None:
            linhas.append(f"VIX {ctx.vix.preco:.1f}" + (
                f" ({ctx.vix.variacao_pct:+.2f}%)" if ctx.vix.variacao_pct is not None else ""
            ))
        if ctx.sp500_fut.variacao_pct is not None:
            linhas.append(f"ES {ctx.sp500_fut.variacao_pct:+.2f}%")
        if ctx.nasdaq_fut.variacao_pct is not None:
            linhas.append(f"NQ {ctx.nasdaq_fut.variacao_pct:+.2f}%")
        if ctx.dxy.variacao_pct is not None:
            linhas.append(f"DXY {ctx.dxy.variacao_pct:+.2f}%")
        if ctx.usd_brl.variacao_pct is not None:
            linhas.append(f"USD/BRL {ctx.usd_brl.variacao_pct:+.2f}%")
        if ctx.indicador_adrs is not None:
            linhas.append(f"ADRs BR {ctx.indicador_adrs:+.2f}%")
        if ctx.iron_ore.variacao_pct is not None:
            linhas.append(f"Minério {ctx.iron_ore.variacao_pct:+.2f}%")
        if ctx.crude_oil.variacao_pct is not None:
            linhas.append(f"Petróleo {ctx.crude_oil.variacao_pct:+.2f}%")

        news = session.noticias
        if news and news.disponivel:
            if news.classificacao_risco:
                linhas.append(f"Calendário: {news.classificacao_risco} (impacto {news.impacto_total})")
            if news.risco_abertura_win:
                linhas.append("⚠️ Risco elevado na abertura WIN (notícias)")
            if news.tem_3_estrelas_brasil_0900:
                linhas.append("⭐⭐⭐ Brasil 09:00")

        return linhas[:10]


# ------------------------------------------------------------
# Atalho
# ------------------------------------------------------------

def gerar_cenario_abertura(session: WinSession) -> OpeningScenario:
    return OpeningScenarioEngine().processar(session)


# ------------------------------------------------------------
# Debug
# ------------------------------------------------------------

if __name__ == "__main__":
    from v2.core.services.win_session_builder import build_win_session

    print("=" * 60)
    print(" OPENING SCENARIO ENGINE — debug")
    print("=" * 60)

    session = build_win_session()
    cenario = gerar_cenario_abertura(session)

    # Anexa ao session para visualização
    session.cenario = cenario

    print(f"Contrato        : {session.metadata.contrato_principal}")
    print(f"Ajuste          : {session.precos.ajuste}")
    print(f"Last MT5        : {session.precos.last_mt5}")
    print(f"Distância       : {session.distancias.last_vs_ajuste_pts} pts")
    print(f"Posição         : {cenario.relacao_com_ajuste.posicao}")
    print(f"Direção         : {cenario.direcao_provavel} ({cenario.probabilidade_direcao}%)")
    print(f"Confiança       : {cenario.confianca_geral}%")
    print()
    print("Cenário principal:")
    print(f"  {cenario.relacao_com_ajuste.cenario_principal}")
    print()
    print("Comportamentos:")
    cb = cenario.comportamentos
    print(f"  Romper e continuar : {cb.romper_e_continuar}%")
    print(f"  Testar e rejeitar  : {cb.testar_e_rejeitar}%")
    print(f"  Testar e recuperar : {cb.testar_e_recuperar}%")
    print(f"  Retornar ao ajuste : {cb.retornar_ao_ajuste}%")
    print(f"  Falso rompimento   : {cb.falso_rompimento}%")
    print()
    print(f"Alternativo: {cenario.cenario_alternativo}")
    print()
    print("Contexto:", " | ".join(cenario.contexto_resumo))
    print("=" * 60)
