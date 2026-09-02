import asyncio
import importlib
import logging
import time
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

# Configuração detalhada de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Imports dos módulos operacionais do pipeline
import Limpar_Imagens_TradingView
import Coletor
import Coleta_Noticias_Calendario
import Analise_Noticias
import Validador
import Calculadora
import CalculadoraEstimativaAbertura
import Gerar_Resultado_Operacional_Abertura
import Rodar_SMC_Regras
import Gerar_Relatorio_Mensagem
import v2_gravar_sessao_win
import v2_rodar_decisao_completa


def run_sync_module(module_object, name: str):
    """
    Executor dinâmico para módulos síncronos.
    Tenta invocar .main(), .executar(), .run(). Caso o script execute o código
    diretamente no bloco `if __name__ == '__main__'`, ele roda via subprocess.
    """
    start = time.perf_counter()
    logging.info(f"🚀 Iniciando: {name}")
    try:
        if hasattr(module_object, "main") and callable(module_object.main):
            module_object.main()
        elif hasattr(module_object, "executar") and callable(module_object.executar):
            module_object.executar()
        elif hasattr(module_object, "run") and callable(module_object.run):
            module_object.run()
        else:
            # Caso o script dependa do bloco if __name__ == '__main__' (como Coletor.py)
            script_path = getattr(module_object, "__file__", None)
            if script_path:
                subprocess.run([sys.executable, script_path], check=True)
            else:
                importlib.reload(module_object)
            
        elapsed = time.perf_counter() - start
        logging.info(f"✅ Concluído: {name} em {elapsed:.2f}s")
    except Exception as e:
        logging.error(f"❌ Erro crítico na execução de {name}: {e}", exc_info=True)
        raise e


async def main_pipeline_async():
    pipeline_start = time.perf_counter()
    logging.info("=== INICIANDO PIPELINE V2 (ASSÍNCRONO / PARALELO) ===")

    loop = asyncio.get_running_loop()
    
    # Pool de threads para executar scripts síncronos sem bloquear o Event Loop
    with ThreadPoolExecutor(max_workers=6) as pool:

        # -------------------------------------------------------------
        # FASE 1: Limpeza e Preparação (Sequencial)
        # -------------------------------------------------------------
        await loop.run_in_executor(pool, run_sync_module, Limpar_Imagens_TradingView, "Limpeza de Imagens")

        # -------------------------------------------------------------
        # FASE 2: Coletas de Dados Em Paralelo (APIs + Web Scraping)
        # -------------------------------------------------------------
        logging.info("📡 Disparando coletas paralelas (APIs/MT5 + Notícias/Calendário)...")
        
        task_coletor = loop.run_in_executor(pool, run_sync_module, Coletor, "Coletor Cotações/APIs")
        task_noticias = loop.run_in_executor(pool, run_sync_module, Coleta_Noticias_Calendario, "Coleta Notícias/Calendário")

        # Aguarda a finalização das duas coletas
        await asyncio.gather(task_coletor, task_noticias)

        # -------------------------------------------------------------
        # FASE 3: Processamento e Sanitização dos Dados
        # -------------------------------------------------------------
        await loop.run_in_executor(pool, run_sync_module, Analise_Noticias, "Análise Quantitativa de Notícias")
        await loop.run_in_executor(pool, run_sync_module, Validador, "Validador de Dados (32 Ativos)")

        # -------------------------------------------------------------
        # FASE 4: Motores de Cálculo Em Paralelo
        # -------------------------------------------------------------
        logging.info("🧮 Processando calculadoras em paralelo...")

        task_calc_macro = loop.run_in_executor(pool, run_sync_module, Calculadora, "Calculadora (Spreads/DI/Macro)")
        task_calc_abertura = loop.run_in_executor(pool, run_sync_module, CalculadoraEstimativaAbertura, "Estimativa de Abertura & Pivôs")

        # Aguarda o término de ambos os cálculos
        await asyncio.gather(task_calc_macro, task_calc_abertura)

        # -------------------------------------------------------------
        # FASE 5: Consolidação Operacional e Regras SMC
        # -------------------------------------------------------------
        await loop.run_in_executor(pool, run_sync_module, Gerar_Resultado_Operacional_Abertura, "Consolidação de Payload")
        await loop.run_in_executor(pool, run_sync_module, Rodar_SMC_Regras, "Motor SMC & ICT Regras")

        # -------------------------------------------------------------
        # FASE 6: Relatórios, Gravação de Histórico e Decisão Final V2
        # -------------------------------------------------------------
        logging.info("📝 Gerando relatórios e registrando sessão...")

        task_relatorio = loop.run_in_executor(pool, run_sync_module, Gerar_Relatorio_Mensagem, "Relatório em Markdown")
        task_sessao = loop.run_in_executor(pool, run_sync_module, v2_gravar_sessao_win, "Gravação Histórica da Sessão")

        await asyncio.gather(task_relatorio, task_sessao)

        # Decisão V2 Unificada (Consolida Decisao_V2.json)
        await loop.run_in_executor(pool, run_sync_module, v2_rodar_decisao_completa, "Orquestrador Final Decisao_V2")

    total_time = time.perf_counter() - pipeline_start
    logging.info(f"🎉 PIPELINE V2 CONCLUÍDO COM SUCESSO EM {total_time:.2f} SEGUNDOS!")


if __name__ == "__main__":
    try:
        asyncio.run(main_pipeline_async())
    except Exception as e:
        logging.critical(f"💥 Falha fatal na execução do pipeline: {e}")