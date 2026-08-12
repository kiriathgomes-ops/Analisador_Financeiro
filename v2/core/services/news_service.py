import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from ..contracts import NewsContext

class NewsService:
    def __init__(self, coletas_dir: Optional[Path] = None):
        if coletas_dir is None:
            self.coletas_dir = Path(__file__).resolve().parent.parent.parent.parent / "Coletas"
        else:
            self.coletas_dir = coletas_dir

    def _carregar_json(self, nome: str) -> Dict[str, Any]:
        caminho = self.coletas_dir / nome
        if not caminho.exists():
            return {}
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def get_news(self) -> Optional[NewsContext]:
        dados = self._carregar_json("Noticias_Impacto_Dia.json")
        if not dados:
            return None
        resumo = dados.get("resumo", {})
        alertas = dados.get("alertas", {})
        return NewsContext(
            timestamp=datetime.now(),
            impacto_total=resumo.get("impacto_total", 0),
            classificacao_risco=resumo.get("classificacao", "BAIXO"),
            tem_3_estrelas_brasil_0900=alertas.get("tem_3_estrelas_brasil_0900", False),
            tem_3_estrelas_outros_horarios=alertas.get("tem_3_estrelas_outros_horarios", False),
            tem_multiplas_2_estrelas_mesmo_horario=alertas.get("tem_multiplas_2_estrelas_mesmo_horario", False),
            risco_abertura_win=alertas.get("risco_abertura_WIN", False),
            eventos_3_estrelas=alertas.get("noticias_3_estrelas_outros_horarios", []),
            horarios_multiplas_2_estrelas=alertas.get("horarios_multiplas_2_estrelas", []),
            metadados={"fonte": "Noticias_Impacto_Dia.json"}
        )