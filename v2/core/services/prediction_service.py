import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from NOVO_MOTOR_PREVISAO_ABERTURA.core.motor_previsao import executar_previsao
    NOVO_MOTOR_DISPONIVEL = True
except ImportError:
    NOVO_MOTOR_DISPONIVEL = False

try:
    from Engine_Vies import executar_core
    LEGADO_DISPONIVEL = True
except ImportError:
    LEGADO_DISPONIVEL = False

from ..contracts import PredictionContext

class PredictionService:
    def get_prediction(self) -> Optional[PredictionContext]:
        # Novo Motor
        if NOVO_MOTOR_DISPONIVEL:
            try:
                dados = executar_previsao()
                if dados and dados.get("score", {}).get("valor", 0) > 20:
                    return self._criar_contexto_novo_motor(dados)
                else:
                    print("⚠️ PredictionService: Novo Motor retornou score baixo ou vazio.")
            except Exception as e:
                print(f"⚠️ PredictionService: erro no Novo Motor: {e}")

        # Fallback Engine_Vies
        if LEGADO_DISPONIVEL:
            try:
                dados_legado = executar_core()
                if dados_legado:
                    win = dados_legado.get("analise_operacional", {}).get("WIN_INDICE", {})
                    vies = win.get("vies_final", "NEUTRO")
                    score = win.get("score_numeric", 0)
                    if "COMPRA" in vies.upper() and score > 1.0:
                        direcao = "COMPRA"
                    elif "VENDA" in vies.upper() and score < -1.0:
                        direcao = "VENDA"
                    else:
                        print("⚠️ PredictionService: Fallback retornou NEUTRO ou score baixo.")
                        return None
                    score_norm = min(100, max(30, abs(score) * 20))
                    return PredictionContext(
                        timestamp=datetime.now(),
                        ativo="WIN",
                        abertura_projetada=0.0,
                        faixa_provavel_inferior=0.0,
                        faixa_provavel_superior=0.0,
                        gap_pontos=0.0,
                        gap_percentual=0.0,
                        gap_intensidade="N/A",
                        classificacao_gap="N/A",
                        direcao_prevista=direcao,
                        score=score_norm,
                        score_classificacao="FORTE" if score_norm > 70 else "MODERADO",
                        score_detalhes={"legado_score": score},
                        analise_ajuste={},
                        cenario_principal={},
                        cenario_alternativo={},
                        metadados={"fonte": "Engine_Vies (fallback)"}
                    )
            except Exception as e:
                print(f"⚠️ PredictionService: erro no fallback: {e}")

        return None

    def _criar_contexto_novo_motor(self, dados: Dict) -> PredictionContext:
        return PredictionContext(
            timestamp=datetime.fromisoformat(dados.get("timestamp", datetime.now().isoformat())),
            ativo=dados.get("ativo", "WIN"),
            abertura_projetada=dados.get("abertura_projetada", 0.0),
            faixa_provavel_inferior=dados["faixa_provavel"][0] if dados.get("faixa_provavel") else 0.0,
            faixa_provavel_superior=dados["faixa_provavel"][1] if dados.get("faixa_provavel") else 0.0,
            gap_pontos=dados.get("gap", {}).get("pontos", 0.0),
            gap_percentual=dados.get("gap", {}).get("percentual", 0.0),
            gap_intensidade=dados.get("gap", {}).get("intensidade", "N/A"),
            classificacao_gap=dados.get("gap", {}).get("classificacao", "N/A"),
            direcao_prevista=dados.get("direcao_prevista", "NEUTRO"),
            score=dados.get("score", {}).get("valor", 0.0),
            score_classificacao=dados.get("score", {}).get("classificacao", "N/A"),
            score_detalhes=dados.get("score", {}).get("detalhes", {}),
            analise_ajuste=dados.get("analise_ajuste", {}),
            cenario_principal=dados.get("cenario_principal", {}),
            cenario_alternativo=dados.get("cenario_alternativo", {}),
            metadados=dados.get("metadados", {})
        )