graph TD
    classDef ativo fill:#0d381e,stroke:#22c55e,stroke-width:3px,color:#fff;
    classDef morto fill:#380d0d,stroke:#ff3d00,stroke-width:3px,color:#fff,stroke-dasharray: 5 5;
    classDef dado fill:#161b24,stroke:#00d4ff,stroke-width:2px,color:#fff;

    subgraph COLETA["1. COLETA (OK)"]
        C1[Coletor.py]:::ativo
        C2[Coletor_MT5_v2_2.py]:::ativo
        C3[Coleta_Noticias_Calendario.py]:::ativo
    end

    subgraph PROC["2. PROCESSAMENTO (OK)"]
        P1[Validador.py]:::ativo
        P2[Analise_Noticias.py]:::ativo
        P3[Motor_SMC_Regras.py]:::ativo
        P4[Calculadora.py]:::ativo
    end

    subgraph NOVOMOTOR["3. NOVO MOTOR (OK)"]
        N1[coletor_dados.py]:::ativo
        N2[motor_gap.py]:::ativo
        N3[motor_ajuste.py]:::ativo
        N4[motor_cenarios.py]:::ativo
        N5[motor_score.py]:::ativo
        N6[motor_previsao.py]:::ativo
    end

    subgraph ORQ["4. ORQUESTRADOR V2 (ATIVO)"]
        O1[v2_orchestrator.py]:::ativo
        O2[prediction_service.py]:::ativo
        O3[win_session_builder.py]:::ativo
        O4[opening_scenario_engine.py]:::ativo
        O5[leilao_service.py]:::ativo
        O6[session_history.py]:::ativo
    end

    subgraph MORTO["❌ CÓDIGO MORTO (NUNCA EXECUTADO)"]
        M1[confluence_engine.py]:::morto
        M2[decision_engine.py]:::morto
        M3[market_service.py]:::morto
        M4[news_service.py]:::morto
        M5[vision_service.py]:::morto
    end

    subgraph PAINEL["5. APRESENTAÇÃO"]
        V1[6_📈_Matriz_de_Influencia.py]:::ativo
        V2[Gerar_Relatorio_Mensagem.py]:::ativo
        V3[analisar_rompimento_10h.py]:::ativo
        V4[Gerar_Resultado_Operacional_Abertura.py]:::ativo
    end

    COLETA --> PROC
    PROC --> NOVOMOTOR
    NOVOMOTOR --> ORQ
    ORQ --> PAINEL

    O1 -.->|importa| M1
    O1 -.->|poderia importar| M2
    M1 -.->|NÃO É USADO| ORQ