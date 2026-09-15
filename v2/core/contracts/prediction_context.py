from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime


@dataclass
class PredictionContext:
    """
    Contexto de previsão de abertura gerado pelo NOVO_MOTOR.

    Campos legados:
      timestamp, ativo, abertura_projetada, faixa_provavel_*,
      gap_*, direcao_prevista, score, score_classificacao,
      score_detalhes, analise_ajuste, cenario_*, metadados.

    Campos novos (V2):
      aberturas (OCR + calculada), fonte, divergência, score direcional,
      probabilidades de cenário.
    """
    # ---- Campos legados ----
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

    # ---- Campos novos: Score direcional ----
    score_direcao: str = "NEUTRO"
    score_forca: str = "FRACO"
    score_magnitude: float = 0.0

    # ---- Campos novos: Divergência ----
    divergencia_direcao: bool = False
    divergencia_detalhes: str = ""

    # ---- Campos novos: Aberturas ----
    abertura_leilao_real: Optional[float] = None
    abertura_leilao_timestamp: Optional[str] = None
    abertura_teorica_calculada: Optional[float] = None
    fonte_abertura: str = "DESCONHECIDA"

    # ---- Campos novos: Cenários probabilísticos ----
    cenario_principal_nome: str = ""
    cenario_principal_probabilidade: float = 0.0
    cenario_alternativo_nome: str = ""
    cenario_alternativo_probabilidade: float = 0.0