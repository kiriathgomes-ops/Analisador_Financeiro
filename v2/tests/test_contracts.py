#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contratos da suíte — dataclasses core + mapas centralizados do config.py (F2)."""
import unittest

from v2.core.contracts import AtivoSnapshot, MarketContext
from config import (
    MAPEAMENTO_TICKERS,
    MAPEAMENTO_TICKERS_INVERSO,
    ADRS_COMPOSTO,
    MAPA_B3_PARA_ADR,
)


class TestContracts(unittest.TestCase):
    """Dataclasses de contrato (core)."""

    def test_ativo_snapshot(self):
        snap = AtivoSnapshot(100.5, 1.2)
        self.assertEqual(snap.preco, 100.5)
        self.assertEqual(snap.variacao_pct, 1.2)


class TestMapasCentralizados(unittest.TestCase):
    """Contratos dos mapas de ticker centralizados no config.py (F2)."""

    def test_mapa_tickers_sem_valores_duplicados(self):
        """Bijeção: nenhum id_interno pode vir de 2 tickers brutos diferentes."""
        valores = list(MAPEAMENTO_TICKERS.values())
        self.assertEqual(
            len(valores), len(set(valores)),
            "MAPEAMENTO_TICKERS contém id_interno duplicado",
        )

    def test_inverso_consistente(self):
        """INVERSO deve ser exatamente {v: k for k, v in MAPEAMENTO_TICKERS}."""
        esperado = {v: k for k, v in MAPEAMENTO_TICKERS.items()}
        self.assertEqual(MAPEAMENTO_TICKERS_INVERSO, esperado)

    def test_adrs_composto_bate_com_mapa_b3_para_adr(self):
        """ADRS_COMPOSTO e os valores de MAPA_B3_PARA_ADR são o mesmo conjunto."""
        self.assertEqual(set(ADRS_COMPOSTO), set(MAPA_B3_PARA_ADR.values()))

    def test_adrs_composto_sem_duplicatas(self):
        self.assertEqual(
            len(ADRS_COMPOSTO), len(set(ADRS_COMPOSTO)),
            "ADRS_COMPOSTO contém duplicata",
        )

    def test_adrs_composto_sao_ids_internos_validos(self):
        """Todo ADR listado deve existir como id_interno no mapa central."""
        for adr in ADRS_COMPOSTO:
            self.assertIn(adr, MAPEAMENTO_TICKERS_INVERSO, f"'{adr}' não é id_interno válido")

    def test_mapa_b3_para_adr_aponta_para_adrs(self):
        """Toda ação B3 deve apontar para um ADR presente em ADRS_COMPOSTO."""
        for b3, adr in MAPA_B3_PARA_ADR.items():
            self.assertIn(adr, ADRS_COMPOSTO, f"'{b3}' aponta para ADR inválido '{adr}'")

    def test_quantidade_minima_tickers(self):
        """Guarda contra deleção acidental em massa (mínimo conhecido)."""
        self.assertGreaterEqual(
            len(MAPEAMENTO_TICKERS), 30,
            "MAPEAMENTO_TICKERS encolheu demais — possível deleção acidental",
        )


if __name__ == "__main__":
    unittest.main()
