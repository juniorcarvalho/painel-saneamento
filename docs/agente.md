# Agente de decisão ESG (TP5)

Opção 3 do TP5: agente ReAct com ferramentas determinísticas sobre os
indicadores SNIS, usando a Groq (`openai/gpt-oss-20b`) via API compatível com OpenAI,
no padrão do projeto `dd-tp3`.

## Arquitetura

```
Streamlit (painel.py / agente.py)
   │  api_client.perguntar_agente / limpar_conversa
   ▼
FastAPI  POST /agente   DELETE /agente/{thread_id}
   │  agent_service.perguntar(agent, mensagem, thread_id)
   ▼
LangGraph create_agent (ReAct) ── InMemorySaver (memória por thread_id)
   │  ChatOpenAI → Groq
   ▼
agent_tools (7 ferramentas) → montar_registros() → cache oficial SNIS
```

- `src/agent_config.py`: `Settings` a partir do `.env`; a chave só é exigida ao construir o LLM.
- `src/agent_tools.py`: funções puras + `BaseTool` com `args_schema` Pydantic; devolvem JSON ou `ERRO: ...`.
- `src/agent_service.py`: prompt de sistema, `build_agent`, `perguntar`, `_extrair_passos`, mapeamento de erros.
- Sem chave, a API sobe normalmente (`app.state.agente = None`): `POST /agente` → 503.
- Erros: 422 validação, 429 limite da Groq, 502 outra falha do provedor, 503 sem agente, 500 interno (com novo `thread_id` sugerido, para não reutilizar um thread com `tool_call` sem resposta).

## Prompt de sistema e justificativa

| Regra | Por quê |
| --- | --- |
| Papel de analista de saneamento/ESG para gestores públicos, em pt-BR | Define tom e público |
| Nunca inventar indicadores; usar sempre as ferramentas | Evita alucinação numérica; preserva o score determinístico |
| Converter nomes de estados em siglas | As ferramentas aceitam apenas siglas de 2 letras |
| Citar ano e fonte (SNIS, cobertura urbana) | Rastreabilidade |
| Último ano válido é 2021; explicar quando o ano pedido não existe | Evita extrapolar (ex.: "2023") |
| Reutilizar UF, ano e região do histórico | Demonstra a memória conversacional |
| Formato Diagnóstico → Evidência → Recomendação → Limitações | Recomendações auditáveis |
| Fórmula do score e meta de 2033 (99% água, 90% esgoto) | Dá contexto sem o modelo calcular |
| Explicar `ERRO:` sem inventar valores | Falhas honestas |
| Perguntas conceituais sem ferramentas | Economiza chamadas |
| Texto simples, sem LaTeX | Renderização no Streamlit |
| Não substitui estudo técnico | Limite de responsabilidade |

O texto literal está em `SYSTEM_PROMPT` (`src/agent_service.py`).

## Contrato das ferramentas

| Ferramenta | Entrada | Saída |
| --- | --- | --- |
| `ranking_prioridade` | `ano?`, `regiao?`, `limite` (1–27, padrão 5) | UF, água, esgoto, score, pop. sem saneamento, posição nacional |
| `indicadores_uf` | `sigla`, `ano?` | registro + posição nacional e regional |
| `evolucao_uf` | `sigla`, `ano_inicio?`, `ano_fim?` | série anual e variação em p.p. |
| `comparar_ufs` | `siglas` (2–5), `ano?` | UFs lado a lado e diferença para a média nacional |
| `resumo_regional` | `ano?` | médias e população somada por região |
| `distancia_meta` | `sigla?` ou `regiao?`, `ano?` | lacuna até 99%/90% em 2033, ritmo exigido × histórico (5 anos), `no_ritmo_*` |
| `simular_cenario` | `sigla`, `delta_agua_pp`, `delta_esgoto_pp`, `ano?` | score e posição antes/depois (teto de 100%) |

Ano omitido = último ano oficial (2021). Só registros `Origem == "oficial"`.

## Bateria de validação

### Conferência das ferramentas contra os dados reais (executada)

Saída das ferramentas sobre o cache oficial (reprodutível com `src.agent_tools`), as mesmas que o agente consome:

| Pergunta | Ferramenta chamada | Números retornados |
| --- | --- | --- |
| Quais UFs priorizar em 2021? | `ranking_prioridade()` | AP 80,23 · RO 69,32 · PA 64,77 · AC 58,58 · AM 47,84 |
| E só no Nordeste? | `ranking_prioridade(regiao="Nordeste")` | MA 47,37 (6º nacional) · AL 47,33 · CE 44,32 · PI 36,78 · RN 36,36 |
| Como o Maranhão evoluiu desde 2010? | `evolucao_uf("MA", ano_inicio=2010)` | Água 72,53→78,47 (+5,94 p.p.); esgoto 37,18→35,41 (−1,77 p.p.); score −1,31 |
| Se o esgoto do MA subir 20 p.p., ele sai do top 5? | `simular_cenario("MA", delta_esgoto_pp=20)` | Esgoto 35,41→55,41; score 47,37→35,37; posição 6→11. MA já estava fora do top 5 |
| Qual a cobertura em 2023? (capciosa) | `ranking_prioridade(ano=2023)` | `ERRO: Sem dados oficiais para 2023. Último ano válido: 2021.` |
| Maranhão atinge a meta de 2033 no ritmo atual? | `distancia_meta("MA")` | Lacunas 20,53 (água) e 54,59 p.p. (esgoto); exigido 1,71 e 4,55 p.p./ano; histórico 0,56 e −0,90; `no_ritmo` falso nos dois |


### Respostas do LLM (executadas)

Execução de 22/11/2026 com `openai/gpt-oss-20b` (Groq, `temperature=0`) e o prompt final. As perguntas 1 a 6 foram refeitas nessa data; a 7 mantém a execução anterior, porque o limite de requisições da Groq foi atingido na nova tentativa. As 5 primeiras perguntas foram feitas em sequência no mesmo thread (memória); as duas últimas, em threads novos. Respostas completas em cada item.

#### 1. Quais UFs priorizar em 2021?

- **Ferramentas chamadas:** `ranking_prioridade({"ano": 2021})`
- **Avaliação:** **Correta.** Ranking idêntico ao da ferramenta (AP 80,23 · RO 69,32 · PA 64,77 · AC 58,58 · AM 47,84). Estrutura Diagnóstico → Evidência → Recomendação → Limitações respeitada, com ano e fonte.

<details><summary>Resposta completa</summary>

**Diagnóstico**  
Em 2021, o ranking de prioridade de investimento em saneamento (score = 0,4 × déficit de água + 0,6 × déficit de esgoto) indica que as unidades federativas com maior urgência são aquelas que apresentam os maiores déficits combinados de cobertura de água e esgoto.  

**Evidência**  
| Pos. | UF | Água (%) | Esgoto (%) | Score | População sem saneamento (milhões) | Fonte |
|------|----|----------|------------|-------|-----------------------------------|-------|
| 1 | AP | 36,0 | 8,95 | 80,23 | 0,6043 | SNIS 2021 |
| 2 | RO | 59,97 | 11,15 | 69,32 | 0,8508 | SNIS 2021 |
| 3 | PA | 60,90 | 18,11 | 64,77 | 2,936 | SNIS 2021 |
| 4 | AC | 67,11 | 24,29 | 58,58 | 0,3128 | SNIS 2021 |
| 5 | AM | 92,30 | 25,40 | 47,84 | 1,7211 | SNIS 2021 |

- **Score**: maior score indica maior prioridade (pior situação).  
- **População sem saneamento**: mostra o número de habitantes que ainda não têm acesso a serviços de água ou esgoto.  

**Recomendação**  
Priorize, em 2021, as cinco UFs listadas acima (AP, RO, PA, AC e AM).  
- **AP**: déficit de água muito alto (64 pp) e esgoto baixo, mas score elevado devido ao déficit de água.  
- **RO**: déficit de água moderado e esgoto moderado, mas score ainda alto.  
- **PA**: déficit de esgoto elevado, score alto.  
- **AC**: déficit de esgoto muito alto, score moderado.  
- **AM**: déficit de esgoto elevado, score mais baixo que as anteriores, mas ainda relevante.

Focar recursos nessas UFs maximiza o impacto na redução do déficit de cobertura e na melhoria da qualidade de vida, alinhado à meta de universalização de 2033 (99 % água, 90 % esgoto).

**Limitações**  
- Os dados são do último ano disponível (2021); não há atualização para 2022 ou 2023.  
- O ranking considera apenas cobertura de água e esgoto; outros fatores (qualidade, gestão, financiamento) não foram incluídos.  
- O score não prevê efeitos de políticas específicas; é um indicador de prioridade baseado em déficit.

</details>

#### 2. E só no Nordeste?

- **Ferramentas chamadas:** `ranking_prioridade({"ano": 2021, "regiao": "Nordeste"})`
- **Avaliação:** **Correta; a memória funcionou.** Reutilizou 2021 sem o usuário citá-lo e passou `regiao=Nordeste`. Os números batem (MA 47,37 · AL 47,33 · CE 44,32 · PI 36,78 · RN 36,36). A coluna "Pos." é regional (1–5); a nacional do MA é 6ª.

<details><summary>Resposta completa</summary>

**Diagnóstico**  
Para a região Nordeste, o ranking de prioridade de investimento em saneamento de 2021 indica que as unidades federativas com maior déficit combinado de água e esgoto (e, consequentemente, maior score) são as que mais necessitam de atenção imediata.

**Evidência (2021 – SNIS)**  

| Pos. | UF | Água (%) | Esgoto (%) | Score | População sem saneamento (milhões) |
|------|----|----------|------------|-------|-----------------------------------|
| 1 | MA | 78,47 | 35,41 | 47,37 | 1,3962 |
| 2 | AL | 88,16 | 29,01 | 47,33 | 1,3605 |
| 3 | CE | 74,26 | 43,29 | 44,32 | 3,521 |
| 4 | PI | 93,44 | 43,08 | 36,78 | 0,7371 |
| 5 | RN | 95,35 | 42,50 | 36,36 | 1,2994 |

- **Score**: maior score = maior prioridade (pior situação).  
- **População sem saneamento**: número de habitantes que ainda não têm acesso a água ou esgoto.

**Recomendação**  
Priorize, em 2021, as UFs do Nordeste listadas acima, em ordem de score:

1. **Maranhão (MA)** – score 47,37, déficit de água e esgoto relativamente alto.  
2. **Alagoas (AL)** – score 47,33, déficit de água moderado e esgoto mais baixo.  
3. **Ceará (CE)** – score 44,32, déficit de esgoto elevado.  
4. **Piauí (PI)** – score 36,78, déficit de esgoto elevado, mas score menor que CE.  
5. **Rio Grande do Norte (RN)** – score 36,36, déficit de esgoto elevado, score mais baixo que PI.

Focar recursos nessas UFs maximiza o impacto na redução do déficit de cobertura e na melhoria da qualidade de vida, alinhado à meta de universalização de 2033 (99 % água, 90 % esgoto).

**Limitações**  
- Dados correspondem ao último ano disponível (2021); não há atualização para 2022 ou 2023.  
- O ranking considera apenas cobertura de água e esgoto; outros fatores (qualidade, gestão, financiamento) não foram incluídos.  
- O score não prevê efeitos de políticas específicas; é um indicador de prioridade baseado em déficit.

</details>

#### 3. Como o Maranhão evoluiu desde 2010?

- **Ferramentas chamadas:** `evolucao_uf({"ano_fim": 2021, "ano_inicio": 2010, "sigla": "MA"})`
- **Avaliação:** **Números corretos; duas falhas de leitura.** Variações corretas (+5,94 / −1,77 / −1,31 p.p.) e o diagnóstico agora reconhece a queda do esgoto. Porém diz que o score "piorou ligeiramente", quando a variação de −1,31 indica melhora (score menor = menor prioridade), e a recomendação ainda faz inferência causal ("os investimentos em esgoto não acompanharam").

<details><summary>Resposta completa</summary>

**Diagnóstico**  
Desde 2010 até 2021, o Maranhão apresentou avanços moderados na cobertura de água, mas um declínio no abastecimento de esgoto, resultando em um score de prioridade que se manteve relativamente estável, mas ligeiramente piorado.

**Evidência (SNIS 2010‑2021)**  

| Ano | Água (%) | Esgoto (%) | Score |
|-----|----------|------------|-------|
| 2010 | 72,53 | 37,18 | 48,68 |
| 2011 | 73,56 | 38,03 | 47,76 |
| 2012 | 73,79 | 35,50 | 49,18 |
| 2013 | 75,72 | 36,97 | 47,53 |
| 2014 | 73,65 | 36,84 | 48,44 |
| 2015 | 77,51 | 38,18 | 46,09 |
| 2016 | 75,69 | 39,90 | 45,78 |
| 2017 | 73,83 | 42,61 | 44,90 |
| 2018 | 76,35 | 39,79 | 45,59 |
| 2019 | 75,44 | 35,96 | 48,25 |
| 2020 | 76,29 | 36,92 | 47,33 |
| 2021 | 78,47 | 35,41 | 47,37 |

- **Variação de água (2010‑2021)**: +5,94 pp (melhora).  
- **Variação de esgoto (2010‑2021)**: –1,77 pp (declínio).  
- **Variação do score (2010‑2021)**: –1,31 pp (score piorou ligeiramente).

**Recomendação**  
1. **Fortalecer programas de coleta e tratamento de esgoto** – a queda de 1,77 pp indica que os investimentos em esgoto não acompanharam a expansão da cobertura de água.  
2. **Manter e ampliar os esforços de expansão de água** – a melhoria de quase 6 pp demonstra eficácia, mas ainda há espaço para atingir a meta de 99 % até 2033.  
3. **Avaliar a integração de sistemas** – projetos que combinem expansão de água e esgoto tendem a reduzir o score de prioridade mais rapidamente.  

**Limitações**  
- Os dados são do último ano disponível (2021); não há atualização para 2022 ou 2023.  
- O score de prioridade não reflete fatores qualitativos (qualidade da água, eficiência operacional, financiamento).  
- A variação negativa de esgoto pode ser influenciada por mudanças metodológicas de coleta de dados; não se pode afirmar causalidade apenas com esses números.

</details>

#### 4. Se o esgoto do MA subir 20 p.p., ele sai do top 5?

- **Ferramentas chamadas:** `simular_cenario({"ano": 2021, "delta_agua_pp": 0, "delta_esgoto_pp": 20, "sigla": "MA"})`
- **Avaliação:** **Evidência correta; premissa ainda não corrigida.** A tabela está certa (MA 6ª → 11ª, score 47,37 → 35,37) e o diagnóstico agora fala em cobertura, sem inverter déficit e cobertura. Mas a resposta afirma que o MA "sai do top 5", quando ele já estava fora (6º). Cita a limitação de que a população sem saneamento não é recalculada.

<details><summary>Resposta completa</summary>

**Diagnóstico**  
Um ganho hipotético de 20 pontos percentuais na cobertura de esgoto do Maranhão (MA) alteraria significativamente seu score de prioridade e sua posição no ranking nacional de 2021.

**Evidência (simulação 2021)**  

| Antes | Depois |
|-------|--------|
| Água | 78,47 % |
| Esgoto | 35,41 % |
| Score | 47,37 |
| Posição nacional | 6 |
| **Esgoto +20 pp** | 55,41 % |
| Score | **35,37** |
| Posição nacional | **11** |

- O score diminui de 47,37 para 35,37, refletindo a redução do déficit combinado.  
- A posição nacional passa de 6ª para 11ª, saindo do top 5.

**Recomendação**  
- Se o objetivo for retirar o Maranhão do top 5 de prioridade, um aumento de 20 pp em esgoto seria suficiente.  
- Contudo, a meta de universalização de 2033 (99 % água, 90 % esgoto) ainda exige avanços adicionais, especialmente na cobertura de água, que permanece abaixo da meta.  
- Investimentos simultâneos em expansão de água e esgoto garantirão uma melhoria mais equilibrada e reduzirão a necessidade de grandes ajustes pontuais.

**Limitações**  
- A simulação assume que o ganho de esgoto não excede 100 % e não recalcula a população sem saneamento.  
- Não considera efeitos de financiamento, governança ou qualidade do serviço.  
- O resultado depende apenas da variação de cobertura; outros fatores que influenciam o score não foram modelados.

</details>

#### 5. Maranhão atinge a meta de 2033 no ritmo atual?

- **Ferramentas chamadas:** `distancia_meta({"ano": 2021, "regiao": null, "sigla": "MA"})`
- **Avaliação:** **Correta.** Todos os números batem com `distancia_meta` (lacunas 20,53 e 54,59 p.p.; exigido 1,71 e 4,55; histórico 0,56 e −0,90). A recomendação usa só os ritmos exigidos, sem metas inventadas.

<details><summary>Resposta completa</summary>

**Diagnóstico**  
O Maranhão não alcançará a meta de universalização de 2033 (99 % água e 90 % esgoto) se continuar no ritmo atual de expansão de cobertura.

**Evidência (SNIS 2021 – Meta 2033)**  

| Indicador | 2021 | Lacuna até 2033 | Anos restantes | Ritmo exigido (pp/ano) | Ritmo histórico (pp/ano) | Cumprimento |
|-----------|------|-----------------|----------------|------------------------|--------------------------|-------------|
| Água | 78,47 % | 20,53 pp | 12 | 1,71 pp | 0,56 pp | **Não** |
| Esgoto | 35,41 % | 54,59 pp | 12 | 4,55 pp | –0,90 pp | **Não** |

- **Água**: Para fechar 20,53 pp em 12 anos, seria necessário um aumento médio de 1,71 pp/ano, enquanto o ritmo histórico foi de apenas 0,56 pp/ano.  
- **Esgoto**: A lacuna de 54,59 pp exigiria 4,55 pp/ano, mas o histórico mostra uma queda de –0,90 pp/ano.

**Recomendação**  
1. **Acelerar a expansão de esgoto** – é o indicador mais crítico, com lacuna de 54,59 pp e ritmo histórico negativo.  
2. **Revisar e intensificar programas de abastecimento de água** – aumentar o ritmo de 0,56 pp/ano para pelo menos 1,71 pp/ano.  
3. **Integração de políticas** – projetos que combinem expansão de água e esgoto tendem a reduzir a lacuna de forma mais eficiente.  
4. **Monitoramento contínuo** – atualizar os indicadores anualmente para avaliar se os ajustes estão gerando o ritmo exigido.

**Limitações**  
- Os dados são do último ano disponível (2021); não há atualização para 2022 ou 2023.  
- O cálculo assume que a meta de 2033 será mantida em 99 % água e 90 % esgoto; variações na meta ou no marco legal não foram consideradas.  
- Não foram incluídos fatores de financiamento, governança ou qualidade do serviço que podem influenciar a taxa de crescimento real.

</details>

#### 6. Qual a cobertura de água e esgoto em 2023? (capciosa; thread novo)

- **Ferramentas chamadas:** `resumo_regional({"ano": 2021})`
- **Avaliação:** **Correta quanto à premissa; um número calculado pelo modelo.** Em thread novo, sem UF, respondeu no nível nacional (`resumo_regional`) e disse que 2023 não existe e que o último ano é 2021 (pendência anterior resolvida). Porém os valores 91,1% e 59,9% são médias das cinco médias regionais, calculadas pelo modelo e não retornadas pela ferramenta (aritmética conferida, mas contraria a regra "não calcule números").

<details><summary>Resposta completa</summary>

**Cobertura de água e esgoto no Brasil – 2021 (último ano disponível)**  

| Indicador | Cobertura | Fonte | Observação |
|-----------|-----------|-------|------------|
| Água | **≈ 91,1 %** | SNIS 2021 | Média simples das cinco regiões (Norte, Nordeste, Sudeste, Sul, Centro‑Oeste). |
| Esgoto | **≈ 59,9 %** | SNIS 2021 | Média simples das cinco regiões. |

> **Nota:** Não há dados publicados para 2023; o último ano com informações completas na base é 2021.  

Esses valores refletem a situação geral do país em 2021, antes da meta de universalização de 2033 (99 % água, 90 % esgoto). Se precisar de dados por estado ou região, posso consultar as ferramentas específicas.

</details>

#### 7. Qual a UF com maior cobertura de esgoto em 2021 e quanto precisa melhorar para 2033? (thread novo)

- **Ferramentas chamadas:** `indicadores_uf({"ano": 2021, "sigla": "AC"})`; `ranking_prioridade({"ano": 2021, "limite": 27})`
- **Avaliação:** **Correta.** SP tem a maior cobertura de esgoto (94,73%), confirmado por `ranking_prioridade(limite=27)`, e já cumpre a meta de 90%. Chamou antes `indicadores_uf` para o AC, que era desnecessária.

<details><summary>Resposta completa</summary>

**Diagnóstico**  
A cobertura de esgoto em 2021 foi a mais alta do país na Unidade Federativa (UF) de São Paulo (SP), com 94,73 % de cobertura urbana.

**Evidência**  
- **UF:** SP  
- **Ano:** 2021  
- **Cobertura de esgoto:** 94,73 %  
- **Meta de 2033 (Marco Legal do Saneamento – Lei 14.026/2020):** 90 %  
- **Fonte:** SNIS, cobertura urbana por UF 2021  

**Recomendação**  
- **Manter e consolidar** a cobertura já existente, garantindo a qualidade e a expansão de serviços de tratamento e coleta.  
- **Focar em áreas urbanas de menor cobertura** dentro de SP, se houver variações regionais.  
- **Monitorar a evolução** até 2023/2024 para confirmar a continuidade do desempenho.

**Limitações**  
- Os dados são do último ano disponível (2021); não há atualização para 2023.  
- A análise considera apenas cobertura urbana; não inclui cobertura rural ou qualidade do serviço.  
- A meta de 2033 já está atendida, portanto não há necessidade de melhoria percentual em esgoto, mas pode haver necessidade de ajustes em outras dimensões do saneamento.

</details>
