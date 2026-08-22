# Importação do módulo 'json' para manipulação, leitura e escrita de arquivos no formato JSON.
import json

# Importação do módulo 'os' para interação com o sistema operacional (caminhos de pastas, verificação de arquivos, etc.).
import os

# Importação do módulo 'subprocess' para executar outros scripts Python/comandos externos em processos independentes.
import subprocess

# Importação do módulo 'sys' para acessar variáveis e funções do sistema Python (como 'sys.executable' para garantir a versão correta do interpretador).
import sys

# Importação do módulo 'time' para medição de tempos de execução e pausas programadas.
import time

# Importação da classe 'datetime' do módulo 'datetime' para capturar e formatar datas e horas.
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO DE CAMINHOS E DIRETÓRIOS
# ============================================================

# Captura o diretório absoluto onde este script principal está localizado no sistema.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define o caminho absoluto para a pasta 'Coletas' dentro do diretório base do projeto.
PASTA_COLETAS = os.path.join(BASE_DIR, "Coletas")

# Define o caminho completo do arquivo JSON onde fica armazenado o cache do calendário de notícias econômicas.
ARQUIVO_CALENDARIO = os.path.join(PASTA_COLETAS, "Noticias_Calendario.json")


# ============================================================
# SISTEMA DE LOGS FORMATADOS
# ============================================================


def log(msg, tipo="INFO"):
    """Exibe mensagens no terminal com timestamp e ícones para facilitar a leitura dos logs.

    :param msg: Mensagem de texto a ser exibida.
    :param tipo: Categoria da mensagem ('INFO', 'OK', 'ALERTA', 'ERRO').
    """
    # Formata o horário atual no padrão Hora:Minuto:Segundo (ex: 14:30:15)
    hora = datetime.now().strftime("%H:%M:%S")

    # Dicionário que mapeia o tipo de log para o seu respectivo emoji visual
    icones = {"INFO": "ℹ️", "OK": "✅", "ALERTA": "⚠️", "ERRO": "❌"}

    # Imprime no terminal a hora, o ícone correspondente (ou '👉' caso o tipo não seja mapeado) e a mensagem
    print(f"[{hora}] {icones.get(tipo, '👉')} {msg}")


# ============================================================
# CHECAGEM DE CACHE DO CALENDÁRIO ECONÔMICO
# ============================================================


def calendario_ja_coletado_hoje():
    """Verifica se o arquivo de calendário de notícias já foi baixado e processado no dia de hoje.

    Retorna True se o arquivo existir e contiver a data de hoje nos metadados. Retorna
    False em caso contrário ou em caso de erro na leitura do JSON.
    """
    # Se o arquivo JSON do calendário não existir na pasta de coletas, indica que ainda não foi coletado hoje
    if not os.path.exists(ARQUIVO_CALENDARIO):
        return False

    try:
        # Abre o arquivo JSON do calendário para leitura no formato UTF-8
        with open(ARQUIVO_CALENDARIO, "r", encoding="utf-8") as f:
            dados = json.load(f)

        # Extrai a data de referência gravada dentro do bloco 'metadata' do JSON
        data_referencia = dados.get("metadata", {}).get("data_referencia", "")

        # Obtém a data de hoje no formato ANO-MÊS-DIA (ex: 2026-08-22)
        hoje = datetime.now().strftime("%Y-%m-%d")

        # Se a data salva no arquivo for exatamente a data de hoje, retorna True para reutilizar o cache
        if data_referencia == hoje:
            return True
    except Exception:
        # Se ocorrer qualquer erro ao ler ou decodificar o arquivo JSON, ignora e força uma nova coleta
        pass

    # Caso a data de referência seja diferente de hoje ou tenha havido falha na leitura, retorna False
    return False


# ============================================================
# EXECUTOR DE SCRIPTS PYTHON EXTERNOS
# ============================================================


def executar_script(script):
    """Executa um script Python filho via linha de comando/subprocesso e monitora erros e tempo de execução.

    :param script: Nome do arquivo Python (ex: 'Coletor.py')
    :return: True se a execução foi bem-sucedida, False caso contrário.
    """
    # Monta o caminho completo até o script filho no diretório base
    caminho = os.path.join(BASE_DIR, script)

    # Verifica se o arquivo do script realmente existe no disco antes de tentar rodar
    if not os.path.exists(caminho):
        log(f"{script} não encontrado", "ERRO")
        return False

    try:
        # Registra o timestamp inicial para calcular o tempo total de execução
        inicio = time.time()

        # Executa o script utilizando o mesmo interpretador Python atual (sys.executable)
        # check=True faz com que o Python lance uma exceção caso o script retorne código de erro diferente de 0
        subprocess.run([sys.executable, caminho], check=True)

        # Arredonda e calcula a duração da execução em segundos (2 casas decimais)
        tempo = round(time.time() - inicio, 2)

        # Registra no log o sucesso da execução
        log(f"{script} executado em {tempo}s", "OK")
        return True

    except subprocess.CalledProcessError as erro:
        # Captura erros ocorridos dentro do script executado (ex: exceção não tratada no script filho)
        log(
            f"Erro executando {script}: código {erro.returncode}",
            "ERRO",
        )
        return False

    except Exception as erro:
        # Captura falhas genéricas (ex: falta de permissão ou problemas do sistema operacional)
        log(f"Falha {script}: {erro}", "ERRO")
        return False


# ============================================================
# GRAVAÇÃO DO LOG DE EXECUÇÃO DA PIPELINE
# ============================================================


def salvar_log_pipeline(resultado):
    """Grava o relatório de execução do pipeline em formato JSON dentro da pasta 'Coletas'.

    :param resultado: Dicionário contendo o status global e os dados de cada
    etapa executada.
    """
    # Garante que o diretório 'Coletas' exista; se não existir, ele é criado automaticamente
    os.makedirs(PASTA_COLETAS, exist_ok=True)

    # Define o caminho completo para salvar o log do pipeline
    arquivo = os.path.join(PASTA_COLETAS, "Pipeline_Log.json")

    # Abre e grava o dicionário como um arquivo JSON formatado com identação e caracteres UTF-8 preservados
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=4, ensure_ascii=False)


# ============================================================
# GERENCIADOR DA PIPELINE OPERACIONAL
# ============================================================


def executar_pipeline():
    """Função principal que coordena o fluxo sequencial de execução dos scripts da análise financeira."""
    # Exibe cabeçalho no terminal
    print()
    print("=" * 70)
    print("🚀 PIPELINE ANALISADOR FINANCEIRO")
    print("=" * 70)

    # Lista de tuplas contendo ("Nome do Passo no Log", "Nome do Arquivo Script Python")
    # Nota: A linha comentada abaixo foi mantida conforme o script original:
    #    ("2.1 - COLETA NOTICIAS ECONOMICAS", "MapearTendencia15Min.py"),
    etapas = [
        ("0 - LIMPEZA DE IMAGENS TRADINGVIEW" , "Limpar_Imagens_TradingView.py"),
        ("1 - COLETA MERCADO GLOBAL", "Coletor.py"),
        ("2 - COLETA NOTICIAS ECONOMICAS", "Coleta_Noticias_Calendario.py"),
        ("3 - ANALISE IMPACTO NOTICIAS", "Analise_Noticias.py"),
        ("4 - VALIDACAO DOS DADOS", "Validador.py"),
        ("5 - CALCULOS MACRO E INDICADORES", "Calculadora.py"),
        ("6 - ESTIMATIVA ABERTURA WIN/WDO", "CalculadoraEstimativaAbertura.py"),
        ("7 - RESULTADO OPERACIONAL","Gerar_Resultado_Operacional_Abertura.py"),
        ("8 - ENGINE DE VIES INSTITUCIONAL", "Engine_Vies.py"),
        ("8.1 - MOTOR SMC POR REGRAS (MT5)", "Rodar_SMC_Regras.py"),
        ("9 - GERADOR RELATORIO FINAL", "Gerar_Relatorio_Mensagem.py"),
        ("10 - V2 SESSAO WINFUT", "v2_gravar_sessao_win.py"),
        ("11 - V2 SESSAO + DECISAO", "v2_rodar_decisao_completa.py"),
    ]

    # Lista para armazenar os detalhes de início, fim e status de cada etapa
    historico = []

    # Flag booleana para acompanhar a integridade de todo o pipeline
    pipeline_ok = True

    # Iteração sequencial sobre cada etapa registrada na lista de etapas
    for nome, script in etapas:
        # Notifica o início do processamento da etapa no terminal
        log(f"Iniciando {nome}")

        # Registra o horário de início da etapa atual
        inicio = datetime.now()

        # Regra condicional especial: Pula a execução do script de calendário se ele já tiver sido coletado hoje
        if (
            script == "Coleta_Noticias_Calendario.py"
            and calendario_ja_coletado_hoje()
        ):
            log(
                "Calendário econômico de hoje já coletado. Reutilizando cache.",
                "OK",
            )
            sucesso = True
        else:
            # Caso contrário, executa o script normalmente através da função auxiliar
            sucesso = executar_script(script)

        # Registra o horário de conclusão da etapa atual
        fim = datetime.now()

        # Adiciona os detalhes da etapa ao histórico de execução
        historico.append(
            {
                "etapa": nome,
                "script": script,
                "inicio": inicio.strftime("%Y-%m-%d %H:%M:%S"),
                "fim": fim.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "OK" if sucesso else "ERRO",
            }
        )

        # Se o script falhar, interrompe o fluxo sequencial do pipeline (Circuit Breaker)
        if not sucesso:
            pipeline_ok = False
            log("PIPELINE INTERROMPIDA", "ERRO")
            break

    # Grava no arquivo JSON 'Pipeline_Log.json' o resultado compilado da execução
    salvar_log_pipeline(
        {
            "data_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status_geral": "SUCESSO" if pipeline_ok else "ERRO",
            "etapas": historico,
        }
    )

    # Exibe o rodapé do resultado no terminal
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

# Lista de scripts de suporte/administração que são rodados manualmente e não entram no loop automático
FERRAMENTAS_ADMINISTRATIVAS = [
    "Mapa_Fluxo.py",
    "Mapa_Projeto.py",
    "Gerar_ArquivosApp.py",
    "Gerar_App_Completo.py",
    "Teste_ArquivosApp.py",
]

# Alias de compatibilidade para permitir a importação/chamada direta da função 'executar_pipeline' por interfaces como o Streamlit
main_pipeline = executar_pipeline


# ============================================================
# PONTO DE ENTRADA DO SCRIPT VIA TERMINAL
# ============================================================

# Garante que o pipeline só seja executado se este arquivo for rodado diretamente (ex: python script.py)
# e previne execuções indesejadas caso ele seja importado como módulo por outro arquivo.
if __name__ == "__main__":
    executar_pipeline()