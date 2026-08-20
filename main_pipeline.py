import json
import os
import subprocess
import sys
import time
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_COLETAS = os.path.join(BASE_DIR, "Coletas")
ARQUIVO_CALENDARIO = os.path.join(PASTA_COLETAS, "Noticias_Calendario.json")


# ============================================================
# LOG
# ============================================================


def log(msg, tipo="INFO"):
    hora = datetime.now().strftime("%H:%M:%S")
    icones = {"INFO": "ℹ️", "OK": "✅", "ALERTA": "⚠️", "ERRO": "❌"}
    print(f"[{hora}] {icones.get(tipo, '👉')} {msg}")


# ============================================================
# CHECAGEM DE CACHE DO CALENDÁRIO
# ============================================================


def calendario_ja_coletado_hoje():
    """Verifica se o calendário do dia atual já foi gerado na pasta Coletas."""
    if not os.path.exists(ARQUIVO_CALENDARIO):
        return False

    try:
        with open(ARQUIVO_CALENDARIO, "r", encoding="utf-8") as f:
            dados = json.load(f)

        data_referencia = dados.get("metadata", {}).get("data_referencia", "")
        hoje = datetime.now().strftime("%Y-%m-%d")

        if data_referencia == hoje:
            return True
    except Exception:
        pass

    return False


# ============================================================
# EXECUTOR DE SCRIPTS
# ============================================================


def executar_script(script):
    caminho = os.path.join(BASE_DIR, script)

    if not os.path.exists(caminho):
        log(f"{script} não encontrado", "ERRO")
        return False

    try:
        inicio = time.time()
        subprocess.run([sys.executable, caminho], check=True)
        tempo = round(time.time() - inicio, 2)
        log(f"{script} executado em {tempo}s", "OK")
        return True

    except subprocess.CalledProcessError as erro:
        log(
            f"Erro executando {script}: código {erro.returncode}",
            "ERRO",
        )
        return False

    except Exception as erro:
        log(f"Falha {script}: {erro}", "ERRO")
        return False


# ============================================================
# SALVAR LOG PIPELINE
# ============================================================


def salvar_log_pipeline(resultado):
    os.makedirs(PASTA_COLETAS, exist_ok=True)
    arquivo = os.path.join(PASTA_COLETAS, "Pipeline_Log.json")

    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=4, ensure_ascii=False)


# ============================================================
# PIPELINE OPERACIONAL
# ============================================================


def executar_pipeline():
    print()
    print("=" * 70)
    print("🚀 PIPELINE ANALISADOR FINANCEIRO")
    print("=" * 70)

#    ("2.1 - COLETA NOTICIAS ECONOMICAS", "MapearTendencia15Min.py"),
    etapas = [
        ("0 - LIMPEZA DE IMAGENS TRADINGVIEW", "Limpar_Imagens_TradingView.py"),
        ("1 - COLETA MERCADO GLOBAL", "Coletor.py"),
        ("2 - COLETA NOTICIAS ECONOMICAS", "Coleta_Noticias_Calendario.py"),
           
        ("3 - ANALISE IMPACTO NOTICIAS", "Analise_Noticias.py"),
        ("4 - VALIDACAO DOS DADOS", "Validador.py"),
        ("5 - CALCULOS MACRO E INDICADORES", "Calculadora.py"),
        ("6 - ESTIMATIVA ABERTURA WIN/WDO", "CalculadoraEstimativaAbertura.py"),
        ("7 - RESULTADO OPERACIONAL", "Gerar_Resultado_Operacional_Abertura.py"),
        ("8 - ENGINE DE VIES INSTITUCIONAL", "Engine_Vies.py"),
        ("8.1 - MOTOR SMC POR REGRAS (MT5)", "Rodar_SMC_Regras.py"),
        ("9 - GERADOR RELATORIO FINAL", "Gerar_Relatorio_Mensagem.py"),
        ("10 - V2 SESSAO WINFUT", "v2_gravar_sessao_win.py"),
        ("11 - V2 SESSAO + DECISAO", "v2_rodar_decisao_completa.py"),

    ]

    historico = []
    pipeline_ok = True

    for nome, script in etapas:
        log(f"Iniciando {nome}")
        inicio = datetime.now()

        # Checagem condicional: Pula a coleta do calendário se já foi realizada hoje
        if script == "Coleta_Noticias_Calendario.py" and calendario_ja_coletado_hoje():
            log("Calendário econômico de hoje já coletado. Reutilizando cache.", "OK")
            sucesso = True
        else:
            sucesso = executar_script(script)

        fim = datetime.now()

        historico.append(
            {
                "etapa": nome,
                "script": script,
                "inicio": inicio.strftime("%Y-%m-%d %H:%M:%S"),
                "fim": fim.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "OK" if sucesso else "ERRO",
            }
        )

        if not sucesso:
            pipeline_ok = False
            log("PIPELINE INTERROMPIDA", "ERRO")
            break

    salvar_log_pipeline(
        {
            "data_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status_geral": "SUCESSO" if pipeline_ok else "ERRO",
            "etapas": historico,
        }
    )

    print()
    print("=" * 70)

    if pipeline_ok:
        print("🎉 PIPELINE FINALIZADA COM SUCESSO")
    else:
        print("❌ PIPELINE FINALIZADA COM ERROS")

    print("=" * 70)


# ============================================================
# FERRAMENTAS ADMINISTRATIVAS
# EXECUÇÃO MANUAL (NÃO FAZEM PARTE DO PIPELINE OPERACIONAL)
# ============================================================

FERRAMENTAS_ADMINISTRATIVAS = [
    "Mapa_Fluxo.py",
    "Mapa_Projeto.py",
    "Gerar_ArquivosApp.py",
    "Gerar_App_Completo.py",
    "Teste_ArquivosApp.py",
]

# ALIAS DE COMPATIBILIDADE PARA IMPORTAÇÃO VIA STREAMLIT
main_pipeline = executar_pipeline


# ============================================================
# EXECUÇÃO PRINCIPAL VIA TERMINAL
# ============================================================

if __name__ == "__main__":
    executar_pipeline()
