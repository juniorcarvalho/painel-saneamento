# 1. Título do Projeto e ODS Vinculada

Título do Projeto: Saneamento em Foco: Priorização de Investimentos em
Saneamento Básico por Unidade Federativa

Objetivo de Desenvolvimento Sustentável (ODS): ODS 6 - Água Potável e
Saneamento, especialmente as metas 6.1, de acesso universal e equitativo à
água potável segura, e 6.2, de acesso a saneamento e higiene adequados.

Justificativa: O Brasil apresenta disparidades regionais na cobertura de
saneamento. O projeto consolida dados urbanos do SNIS por Unidade Federativa
para apoiar a identificação de estados com maiores déficits de água e esgoto.

# 2. Problema de Negócio

Pergunta principal: "Quais Unidades Federativas do Brasil apresentam os
menores índices de cobertura urbana de saneamento básico e devem ser
priorizadas para alocação de recursos?"

Contexto: Decisores públicos, organizações sociais e analistas de impacto
precisam comparar indicadores de saneamento de diferentes anos e estados sem
consolidar manualmente milhares de registros municipais. O projeto transforma
essa base municipal em indicadores estaduais comparáveis e exportáveis.

# 3. Escopo e Objetivos

## No Escopo

- Utilizar o arquivo municipal do SNIS
  `data/br_mdr_snis_municipio_agua_esgoto.csv`.
- Processar dados de cobertura urbana de água e esgoto.
- Agregar registros municipais por Unidade Federativa e ano.
- Calcular percentuais estaduais com ponderação pela população urbana
  residente.
- Criar um cache local em `data/processed/dados_saneamento.json`.
- Disponibilizar aplicação Streamlit com menu multipágina e integração HTTP
  a uma API FastAPI local.
- Consultar indicadores oficiais e complementares por ano e região.
- Importar CSV via POST, com persistência complementar e proveniência explícita.
- Documentar a preparação futura de fontes textuais para LLMs.
- Permitir filtros por ano, região e critério de ordenação.
- Exibir métricas, ranking, gráfico comparativo, tabela e download dos dados.
- Calcular uma prioridade determinística com base nos déficits de água e
  esgoto.
- Organizar o desenvolvimento com práticas de CRISP-DM e TDSP.

## Fora do Escopo

- Análise municipal detalhada no dashboard final.
- Análise de bairros ou localidades específicas.
- Cobertura total não urbana; o foco é exclusivamente urbano.
- Uso de LLM, provedor de IA ou recomendações geradas automaticamente.
- Variáveis socioeconômicas, como PIB, IDH ou renda, no score atual.
- Coleta de dados em tempo real durante a navegação do painel.
- Implementação de transações financeiras ou contratos.
- Hospedagem em nuvem como requisito da versão atual.

Os municípios são a granularidade da fonte de origem, mas o processamento e a
apresentação final são feitos por UF e ano.

# 4. Dados e Pipeline

O pipeline é dividido entre:

- `src/data_access.py`: leitura do CSV, atualização do cache e suporte
  opcional a fontes via API.
- `src/data_processing.py`: conversão numérica, agregação urbana, associação
  regional e cálculo dos indicadores.
- `src/api_data_access.py`: arquivo complementar separado, importação datada e
  substituição atômica.
- `src/api.py`: GET/POST `/dados`, contratos e validação com FastAPI.
- `src/api_client.py`: cliente HTTP e configuração por `SANEAMENTO_API_URL`.
- `app.py` e `pages/`: navegação Streamlit, exploração, consulta/importação e
  metodologia/fontes; funções compartilhadas em `src/ui_helpers.py`.

Os campos urbanos principais são:

- `populacao_urbana_residente_agua`;
- `populacao_urbana_atendida_agua`;
- `populacao_urbana_residente_esgoto`;
- `populacao_urbana_atendida_esgoto`.

O CSV é agrupado por `ano` e `sigla_uf`. Os percentuais são calculados pela
razão entre as somas das populações atendidas e residentes. Registros sem
denominador urbano válido não geram um indicador completo para aquela UF e ano.

O arquivo contém linhas de 2022, mas os campos urbanos utilizados estão vazios
nesse ano. Portanto, o cache atual utiliza 2021 como último ano válido.

# 5. Regra de Priorização

O ranking é determinístico e transparente:

```text
Score de prioridade =
0,4 x déficit de água + 0,6 x déficit de esgoto
```

Os déficits são calculados como `100 - cobertura`. A população sem saneamento é
exibida como impacto absoluto e usada como critério de desempate. O painel não
gera recomendações textuais por IA até o TP4; no TP5, o agente (seção 11) as redige sem alterar o score.

# 6. Metas e Indicadores

## Entregas técnicas

- Aplicação multipágina executável localmente com Streamlit.
- API FastAPI com GET e POST documentados em `/docs`.
- Armazenamento complementar isolado do cache oficial, com origem e data.
- Consulta por HTTP, prévia de CSV, importação explícita e exportação filtrada.
- Pipeline Python nativo para transformação do CSV municipal.
- Cache JSON consolidado por UF e ano.
- Ranking determinístico com os componentes do cálculo visíveis.
- Tabela e download dos dados filtrados.

## Indicadores de uso

- Reduzir o trabalho manual de consolidação dos dados municipais.
- Permitir identificar e justificar as três maiores prioridades de cada ano
  selecionado.
- Permitir comparação histórica de cobertura urbana entre as UFs.

As metas de impacto devem ser avaliadas posteriormente com usuários do painel;
nenhuma redução percentual de tempo é considerada comprovada sem medição
comparativa.

# 7. Público-Alvo

- Tomadores de decisão: visualizam o resumo executivo e o ranking estadual.
- Analistas de impacto: comparam anos, regiões, coberturas e déficits.
- Usuários técnicos: consultam a tabela e exportam os registros filtrados.

# 8. Riscos e Mitigações

## Risco 1: arquivo CSV ausente ou alterado

Mitigação: validar as colunas obrigatórias, informar erro de leitura e manter o
último cache válido. A aplicação não deve processar dados incompletos sem
sinalização.

## Risco 2: campos urbanos vazios em determinados anos

Mitigação: ignorar combinações sem denominadores válidos, registrar a limitação
no Data Summary Report e não misturar indicadores de definições diferentes.

## Risco 3: indisponibilidade de APIs opcionais

Mitigação: a preparação principal usa o CSV local, sem coleta externa durante
requisições. O painel depende da API local para indicadores e exibe erros de
conexão ou validação; a metodologia e referência municipal continuam acessíveis.

## Risco 4: inconsistência entre municípios

Mitigação: converter valores com validação, rejeitar valores negativos ou
inválidos e calcular os percentuais por soma ponderada, evitando médias
municipais simples.

# 9. Evolução TP2 e governança

O TP2 amplia o produto do TP1 sem alterar a fonte oficial nem a regra de
priorização. A camada de dados continua separada da interface: a atualização
do cache JSON e a extração web são tarefas explícitas de preparação, enquanto
o Streamlit navega apenas por arquivos locais.

Stakeholders adicionais são estudantes e professores que avaliam
reprodutibilidade, além de analistas que precisam consultar referências
municipais. A Wikipédia é uma fonte contextual, não substitui o SNIS e não
participa do cálculo do score. A listagem municipal fornece município, UF e
estado, mas não código IBGE; por isso esse campo não é esperado no artefato.
A origem, data de coleta e limitações devem ser registradas quando o CSV for
atualizado.

As entregas do TP2 incluem filtros reativos, estado de sessão, cache de dados,
upload/download de CSV, referência territorial extraída com Beautiful Soup e
relatórios atualizados. A organização permanece compatível com CRISP-DM:
entendimento do negócio, preparação e governança dos dados, modelagem dos
indicadores, avaliação por validações e disponibilização no dashboard.

# 10. Evolução TP3: API, navegação e preparação para LLM

O TP3 responde à necessidade de consultar e incorporar dados de forma
reutilizável. O fluxo principal passa a ser CSV municipal → processamento
explícito → cache oficial → API FastAPI → páginas Streamlit. Um segundo fluxo
recebe CSV consolidado ou municipal na interface → normalização/agregação →
POST `/dados` → `data/processed/dados_complementares.json`. O GET combina as
origens com identificação em cada linha, preservando as fontes do cache SNIS.

A navegação oferece exploração/ranking, consulta/importação/exportação e
metodologia/fontes. O cálculo de prioridade mantém os pesos de água e esgoto.
Os dados complementares são identificados como fornecidos pelo usuário,
recebem data de importação UTC e não substituem evidências oficiais.
A visualização inicia pelo recorte oficial. Envios repetidos são aditivos,
podendo sobrepor UF/ano; a interface informa o risco de dupla contagem.

A API valida campos obrigatórios, ano, sigla/região, números finitos,
percentuais entre 0 e 100 e população não negativa. Entrada inválida resulta
em 422, cache oficial ausente em 503 e falha de armazenamento/formato em 500.
A preparação das fontes continua sendo explícita, fora das requisições.
A persistência complementar usa lock no processo e substituição atômica;
o uso suportado é uma instância com um worker. Escalar o serviço exigirá
banco de dados ou coordenação de escrita. O serviço local não tem autenticação.

A análise das fontes mantém SNIS/Base dos Dados como base oficial. IBGE é
integração opcional e a Wikipédia é contexto territorial. Beautiful Soup atende
ao HTML estático atual; não há justificativa para adicionar Selenium sem uma
fonte pertinente que exija interação ou carregamento assíncrono.

A preparação para LLM exige uma fonte textual nova: os indicadores e nomes
municipais atuais são tabulares e não sustentam resumo, sentimento ou Q&A.
Uma próxima etapa deverá selecionar documentos de saneamento, registrar fonte,
data e licença, segmentar os textos e relacioná-los a UF/ano. Respostas futuras
precisarão de avaliação de fidelidade e citações. Este TP3 apenas documenta
essa evolução, mantendo inferência e recomendações automáticas fora do escopo.

Os riscos adicionais são indisponibilidade da API local, arquivos
complementares corrompidos e sobreposição de lotes. As mitigações são mensagens
na interface, erros HTTP documentados, gravação atômica e filtros por origem.
A avaliação técnica inclui consultas filtradas, importação válida e inválida,
preservação do cache oficial e navegação com API indisponível.


## TP4 — resumo local
Textos de saneamento são fornecidos pelo usuário com título e origem declarados. Qwen3-0.6B gera resumos sem persistência de textos ou respostas no servidor. Limites padrão: 50–8000 caracteres, 2048 tokens de prompt e 256 tokens novos. A fonte não é consultada automaticamente. Os indicadores e o score determinístico permanecem independentes do resumo.


# 11. TP5 — Agente inteligente e dashboard final

## Alinhamento entre dados, IA e engenharia de prompts

A pergunta de negócio permanece: "Quais Unidades Federativas apresentam os
maiores déficits urbanos de água e esgoto e devem ser priorizadas para
alocação de recursos?". O TP5 a responde de ponta a ponta: os **dados**
(723 registros SNIS por UF e ano, 1995–2021) alimentam **ferramentas
determinísticas**; um **agente** de IA as orquestra e redige recomendações; e a
**engenharia de prompts** (`docs/agente.md`) impõe papel, formato
(Diagnóstico → Evidência → Recomendação → Limitações) e a proibição de inventar
números. O painel final mostra o ciclo coleta → processamento → análise → IA.

## Por que a Opção 3 (agentes) e não as Opções 1 e 2

- O ativo do projeto são **indicadores estruturados**, não um corpus textual.
  Sumarizar relatórios (Opção 2) já existe no TP4, com texto colado pelo usuário.
- Um agente com ferramentas automatiza a análise dos indicadores e sugere
  recomendações com base em um benchmark de governança: a universalização de
  2033 do Marco Legal do Saneamento (Lei 14.026/2020; 99% água, 90% esgoto).
- A memória conversacional (Opção 1) vem sem custo extra: a memória por
  `thread_id` do LangGraph permite perguntas de acompanhamento ("E só no Nordeste?").

## Groq/`gpt-oss-20b` em vez do Qwen local

O agente exige *tool calling* confiável, que o Qwen3-0.6B em CPU não entrega
com latência aceitável (limites documentados em `docs/llm_local.md`). A Groq,
via API compatível com OpenAI, oferece tool calling, baixa latência e custo
zero no plano gratuito. O resumo local do TP4 permanece como está.

## ODS e pilares ESG

- ODS 6.1 e 6.2: cobertura de água e esgoto; o benchmark de 2033 operacionaliza as metas.
- **G (governança):** priorizar a alocação de recurso público com critério transparente e rastreável.
- **E/S (ambiental e social):** saúde, dignidade e proteção de corpos hídricos.

## Metas e indicadores adicionais

- Toda resposta do agente deve citar números retornados por ferramentas, e a
  interface expõe os passos e os dados usados ("Como o agente chegou a isso").
- As 4 perguntas sugeridas e 2 perguntas capciosas são validadas contra o
  `GET /dados` (`docs/agente.md`).
- `make test` roda sem rede e sem chave.

## Riscos adicionais

| Risco | Mitigação |
| --- | --- |
| Indisponibilidade ou limite de taxa da Groq | Erros 502/429 com mensagem clara; o restante do painel funciona sem o agente |
| Alucinação de números | O LLM não calcula: usa ferramentas; o prompt proíbe inventar; os dados da ferramenta ficam visíveis |
| Envio de dados a terceiros | Só a pergunta e saídas agregadas das ferramentas saem da máquina; sem dados pessoais; chave no `.env` |
| Chave ausente | A API sobe sem o agente; `POST /agente` responde 503 e a página orienta a configuração |
| Memória volátil | `InMemorySaver` perde o histórico ao reiniciar a API; "Nova conversa" descarta o thread |
