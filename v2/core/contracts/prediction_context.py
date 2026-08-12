from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime

@dataclass
class PredictionContext:
    timestamp: datetime
    ativo: str
    abertura_projetada: float
    faixa_provavel_inferior: float
    faixa_provavel_superior: float
    gap_pontos: float
    gap_percentual: float
    gap_intensidade: str
    classificacao_gap: str
    direcao_prevista: str
    score: float
    score_classificacao: str
    score_detalhes: Dict[str, float] = field(default_factory=dict)
    analise_ajuste: Dict = field(default_factory=dict)
    cenario_principal: Dict = field(default_factory=dict)
    cenario_alternativo: Dict = field(default_factory=dict)
    metadados: Dict = field(default_factory=dict)