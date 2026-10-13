# Guia de Execucao - Analisador Financeiro

Ultima atualizacao: 2026-10-13

---

## Antes de comecar - 3 regras universais

1. Sempre comece pelo smoke test quando mexer em config/pipeline.

2. Sempre faca dry-run antes de aplicar em scripts de fix.

3. Nao cole blocos com markdown no terminal. PowerShell tenta interpretar.


## 1. Entradas principais

### 1.1 UI (Streamlit)

    python -m streamlit run Home.py

- Abre em http://localhost:8501
- Para parar: Ctrl+C

### 1.2 Agendador

    python Agendador.py            # loop continuo, roda em :05s de cada grade
    python Agendador.py --once     # roda 1x (debug)

### 1.3 Pipeline completo

    python main_pipeline.py

- 7 fases em sequencia, duracao ~15s

### 1.4 Orquestrador V2

    python -m v2.core.engines.v2_orchestrator


## 2. Diagnostico e auditoria

### 2.1 Diagnostico geral (recomendado)

    python ferramentas/auditoria/diagnostico.py --full
    python ferramentas/auditoria/diagnostico.py --inventario
    python ferramentas/auditoria/diagnostico.py --integridade
    python ferramentas/auditoria/diagnostico.py --freshness

### 2.2 Auditoria em 2 camadas (legado)

    python ferramentas/auditoria/audit_camada1.py
    python ferramentas/auditoria/audit_camada2.py

### 2.3 Smoke test

    python Temp_Validacao_Smoke.py

### 2.4 Limpeza de lixo

    python ferramentas/auditoria/limpar_lixo.py              # dry-run
    python ferramentas/auditoria/limpar_lixo.py --aplicar


## 3. Fix scripts

    python ferramentas/fixes/fixNN.py              # dry-run
    python ferramentas/fixes/fixNN.py --aplicar    # aplica + backup
    python ferramentas/fixes/fixNN.py --reverter   # restaura backup

Backups em ferramentas/fixes/backups/


## 4. Ferramentas de mapeamento

    python ferramentas/mapear_dados.py
    python ferramentas/mapear_fluxo.py
    python ferramentas/mapas/Gerar_Mapa_Fluxo.py
    python ferramentas/mapas/Gerar_Mapa_Projeto.py
    python ferramentas/mapas/Gerar_Mapa_Inventario_Tecnico.py


## 5. Motores individuais (debug fino)

### 5.1 Coleta

    python Coletor.py
    python Coletor_MT5_v2_2.py

### 5.2 Validacao e noticias

    python Coleta_Noticias_Calendario.py
    python Analise_Noticias.py
    python Validador.py

### 5.3 Motores tecnicos

    python Rodar_SMC_Regras.py
    python MapearTendencia15Min.py

### 5.4 Calculadoras

    python Calculadora.py
    python CalculadoraEstimativaAbertura.py
    python Gerar_Resultado_Operacional_Abertura.py

### 5.5 Decisao e relatorios

    python v2_rodar_decisao_completa.py
    python v2_gravar_sessao_win.py
    python Gerar_Relatorio_Mensagem.py


## 6. Consultas rapidas

### Ver estado de um JSON

    python -c "import json; d=json.load(open('Coletas/Decisao_V2.json',encoding='utf-8')); print(json.dumps(d, indent=2, ensure_ascii=False)[:1500])"

### Contar arquivos numa pasta

    (Get-ChildItem "Coletas\Historico_MT5" -File).Count

### Freshness de todos os JSONs

    Get-ChildItem "Coletas\*.json" | Select-Object Name, LastWriteTime | Sort-Object LastWriteTime -Descending


## 7. Fluxos recomendados

### Vou mexer em config.py

    python Temp_Validacao_Smoke.py    # antes
    # ... editar ...
    python Temp_Validacao_Smoke.py    # depois
    python ferramentas/auditoria/diagnostico.py --integridade

### Pipeline parou de gerar um JSON

    python main_pipeline.py
    python <motor-especifico>.py
    python ferramentas/auditoria/diagnostico.py --freshness

### Vou aplicar um fix

    python ferramentas/fixes/fixNN.py              # dry-run
    python ferramentas/fixes/fixNN.py --aplicar
    python Temp_Validacao_Smoke.py
    # se quebrou:
    python ferramentas/fixes/fixNN.py --reverter

### Antes de commitar

    python Temp_Validacao_Smoke.py
    python ferramentas/auditoria/diagnostico.py --integridade
    git status
    git add <arquivos>
    git commit -m "..."
    git push


## 8. Armadilhas conhecidas

| Armadilha | Como evitar |
|---|---|
| Agendador rodando durante teste | Ctrl+C no terminal dele antes |
| Colar markdown no PowerShell | Copiar so texto puro |
| Rodar --aplicar sem ver dry-run | Sempre rodar dry-run primeiro |
| Esquecer --reverter existe | Todo fixNN tem |
| Cache do Streamlit nao invalida | Tecla C no browser ou reinicia servidor |
| MT5 desconectado | Coletor retorna OFFLINE, nao trava |


## 9. Mapa de pastas

    Analisador_Financeiro/
    |-- Home.py                    entrypoint Streamlit
    |-- Agendador.py               loop de producao
    |-- main_pipeline.py           pipeline de 7 fases
    |-- config.py                  constantes centrais
    |-- pages/                     UI principal
    |-- v2/                        arquitetura V2 oficial
    |   |-- core/engines/
    |   |-- core/services/
    |   |-- core/contracts/
    |   +-- pages/
    |-- Coletas/                   dados (gitignored)
    |   |-- *.json                 JSONs de producao
    |   |-- Historico_MT5/         snapshots MT5 (rotacionado)
    |   |-- Historico_Aberturas/   sessoes diarias
    |   +-- Historico_Decisoes_V2/ decisoes historicas
    |-- ferramentas/
    |   |-- fixes/
    |   |-- auditoria/
    |   |-- analises/
    |   |-- mapas/
    |   +-- docs/
    +-- docs/                      documentacao


## 10. Comandos de referencia rapida

### Rodar tudo

    python Temp_Validacao_Smoke.py
    python ferramentas/auditoria/diagnostico.py --full
    python main_pipeline.py
    python -m streamlit run Home.py
    python Agendador.py

### Parar tudo

    Ctrl+C em cada terminal aberto

### Verificar estado

    git status
    git log --oneline -5
    python ferramentas/auditoria/diagnostico.py --freshness

### Limpar

    python ferramentas/auditoria/limpar_lixo.py
    python ferramentas/auditoria/limpar_lixo.py --aplicar


---

Fim do guia. Se descobrir um comando novo que vale a pena, adiciona aqui.
