import unittest
from datetime import datetime
from v2.core.contracts import AtivoSnapshot, MarketContext

class TestContracts(unittest.TestCase):
    def test_ativo_snapshot(self):
        snap = AtivoSnapshot(100.5, 1.2)
        self.assertEqual(snap.preco, 100.5)
        self.assertEqual(snap.variacao_pct, 1.2)

if __name__ == "__main__":
    unittest.main()