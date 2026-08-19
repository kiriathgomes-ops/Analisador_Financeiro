# Analisador_Financeiro/testar_coletor.py
import json
from pprint import pprint
from NOVO_MOTOR_PREVISAO_ABERTURA.dados.coletor_dados import coletar_dados_entrada

def main():
    print("=" * 50)
    print("INICIANDO TESTE DO COLETOR DE DADOS...")
    print("=" * 50)

    # Executa a coleta
    dados = coletar_dados_entrada()

    if dados is None:
        print("\n❌ [ERRO] O coletor retornou None.")
        return

    print("\n✅ [SUCESSO] Dados coletados com êxito!")
    print(f"Timestamp: {dados.timestamp}\n")

    # Exibe resumo das principais variáveis lidas
    print("--- RESUMO DOS DADOS COLETADOS ---")
    print(f"Preço Atual WIN:     {dados.preco_atual_win}")
    print(f"Ajuste WIN:          {dados.ajuste_win}")
    print(f"Fechamento Anterior: {dados.fechamento_anterior_win}")
    print(f"Abertura Teórica:    {dados.abertura_teorica.abertura_teorica_pontos if dados.abertura_teorica else 'N/A'}")
    
    if dados.contexto:
        print("\n--- CONTEXTO EXTERNO ---")
        print(f"S&P 500 Futuro:      {dados.contexto.sp500} ({dados.contexto.sp500_var}%)")
        print(f"EWZ (ETF Brasil):    {dados.contexto.ewz} ({dados.contexto.ewz_var}%)")
        print(f"VIX (Índice do Medo):{dados.contexto.vix}")
        print(f"Qtd ADRs lidas:      {len(dados.contexto.adrs)}")

    if dados.noticias:
        print("\n--- NOTÍCIAS ---")
        print(f"Impacto Noticias:    {dados.noticias.classificacao_impacto}")
        print(f"Risco Abertura WIN:  {dados.noticias.risco_abertura_win}")

    # Exibe o dicionário completo em formato formatado (JSON)
    print("\n" + "=" * 50)
    print("ESTRUTURA COMPLETA (to_dict):")
    print("=" * 50)
    pprint(dados.to_dict())

if __name__ == "__main__":
    main()