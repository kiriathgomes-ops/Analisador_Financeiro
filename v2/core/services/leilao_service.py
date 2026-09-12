# ============================================================
# v2/core/services/leilao_service.py
# Lê o CSV do OCR (preco_teorico_win_fluxo.csv) e extrai
# o preço teórico do leilão para uso no NOVO_MOTOR.
#
# SEMÂNTICA:
#   - O OCR roda durante o leilão (08:55 → 09:00) e para quando o leilão fecha.
#   - Consideramos "preço do leilão" = ÚLTIMA leitura antes de 09:00:30.
#   - Se o OCR não rodou no dia, retorna indisponível → caller decide fallback.
#
# NOTAS:
#   - O CSV NÃO tem header (linhas: "YYYY-MM-DD HH:MM:SS.mmm,preco,conf").
#   - Por isso NÃO usamos csv.DictReader — leitura linha por linha.
# ============================================================

from __future__ import annotations

import csv
from datetime import datetime, date, time
from pathlib import Path
from typing import Optional, Dict, Any, List


class LeilaoService:
    """Extrai o preço teórico do leilão a partir do CSV gerado pelo OCR."""

    # Corte do leilão: última leitura considerada (09:00:30)
    HORA_CORTE_LEILAO = time(9, 0, 30)

    # Formatos de data aceitos (com e sem milissegundos)
    FORMATOS_DATA = (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    )

    def __init__(self, coletas_dir: Optional[Path] = None):
        if coletas_dir is None:
            # Este arquivo: v2/core/services/leilao_service.py
            # Raiz: 4 níveis acima
            self.coletas_dir = Path(__file__).resolve().parent.parent.parent.parent / "Coletas"
        else:
            self.coletas_dir = Path(coletas_dir)

        self.csv_path = self.coletas_dir / "preco_teorico_win_fluxo.csv"

    # ------------------------------------------------------------
    # Parser de data
    # ------------------------------------------------------------
    def _parse_dt(self, texto: str) -> Optional[datetime]:
        """Tenta todos os formatos aceitos. Retorna None se nenhum funcionar."""
        texto = texto.strip()
        for fmt in self.FORMATOS_DATA:
            try:
                return datetime.strptime(texto, fmt)
            except ValueError:
                continue
        return None

    # ------------------------------------------------------------
    # Leitura do CSV
    # ------------------------------------------------------------
    def _ler_csv(self) -> List[Dict[str, Any]]:
        """
        Lê o CSV linha por linha (SEM DictReader, pois não há header).
        Aceita datas com e sem milissegundos. Ignora linhas inválidas.
        """
        if not self.csv_path.exists():
            return []

        registros: List[Dict[str, Any]] = []

        try:
            # utf-8-sig remove BOM automaticamente se existir
            with open(self.csv_path, "r", encoding="utf-8-sig") as f:
                for linha in f:
                    linha = linha.strip()
                    if not linha:
                        continue

                    # Pula header (se existir)
                    if not linha[0].isdigit():
                        continue

                    partes = linha.split(",")
                    if len(partes) < 2:
                        continue

                    dt = self._parse_dt(partes[0])
                    if dt is None:
                        continue

                    try:
                        preco = float(partes[1])
                        conf = float(partes[2]) if len(partes) > 2 else 0.0
                    except ValueError:
                        continue

                    if preco > 0:
                        registros.append({
                            "dt": dt,
                            "preco": preco,
                            "confianca": conf,
                        })
        except Exception:
            return []

        return registros

    # ------------------------------------------------------------
    # Filtros de dia/leilão
    # ------------------------------------------------------------
    def _filtrar_por_dia(
        self, registros: List[Dict[str, Any]], dia: date
    ) -> List[Dict[str, Any]]:
        """Filtra registros de um dia específico, até 09:00:30."""
        return [
            r for r in registros
            if r["dt"].date() == dia and r["dt"].time() <= self.HORA_CORTE_LEILAO
        ]

    def _leituras_leilao_recente(self) -> List[Dict[str, Any]]:
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

        return []

    # ------------------------------------------------------------
    # Filtro de outliers (glitches do OCR)
    # ------------------------------------------------------------
    def _filtrar_outliers(
        self, leituras: List[Dict[str, Any]], tolerancia: float = 2000.0
    ) -> List[Dict[str, Any]]:
        """
        Remove leituras absurdas (glitches do OCR).
        Considera outlier se o preço estiver a mais de `tolerancia` pts
        da MEDIANA das leituras.

        Ex.: leitura 199900 com mediana 190500 → outlier (9400 pts de diferença).
        """
        if len(leituras) < 3:
            return leituras

        precos = sorted(r["preco"] for r in leituras)
        n = len(precos)
        mediana = precos[n // 2] if n % 2 == 1 else (precos[n // 2 - 1] + precos[n // 2]) / 2

        return [
            r for r in leituras
            if abs(r["preco"] - mediana) <= tolerancia
        ]

    # ------------------------------------------------------------
    # API principal
    # ------------------------------------------------------------
    def obter_preco_leilao(self) -> Dict[str, Any]:
        """
        Retorna o preço do leilão do dia mais recente com dados.

        Chaves:
          disponivel: bool
          preco: float | None            ← última leitura antes de 09:00:30 (após filtro de outliers)
          timestamp: str | None          ← do preço retornado
          fonte: "OCR_LEILAO" | "INDISPONIVEL"
          total_leituras: int            ← após filtro de outliers
          total_leituras_brutas: int     ← antes do filtro
          preco_max: float | None
          preco_min: float | None
          outliers_removidos: int
        """
        leituras_brutas = self._leituras_leilao_recente()

        if not leituras_brutas:
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
            }

        leituras = self._filtrar_outliers(leituras_brutas)
        outliers = len(leituras_brutas) - len(leituras)

        if not leituras:
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
            }

        # Última leitura ANTES do corte (09:00:30)
        ultima = max(leituras, key=lambda r: r["dt"])
        precos = [r["preco"] for r in leituras]

        return {
            "disponivel": True,
            "preco": float(ultima["preco"]),
            "timestamp": ultima["dt"].isoformat(),
            "fonte": "OCR_LEILAO",
            "total_leituras": len(leituras),
            "total_leituras_brutas": len(leituras_brutas),
            "preco_max": float(max(precos)),
            "preco_min": float(min(precos)),
            "outliers_removidos": outliers,
        }


# ------------------------------------------------------------
# Atalho
# ------------------------------------------------------------
def obter_preco_leilao_hoje(coletas_dir: Optional[Path] = None) -> Dict[str, Any]:
    return LeilaoService(coletas_dir).obter_preco_leilao()


# ------------------------------------------------------------
# Debug
# ------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print(" LEILÃO SERVICE — debug")
    print("=" * 60)

    svc = LeilaoService()
    print(f"CSV path: {svc.csv_path}")
    print(f"CSV existe: {svc.csv_path.exists()}")
    print()

    resultado = svc.obter_preco_leilao()

    for k, v in resultado.items():
        print(f"  {k}: {v}")

    print("=" * 60)