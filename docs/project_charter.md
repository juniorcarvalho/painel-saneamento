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
- Disponibilizar dashboard interativo em Streamlit.
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
- `app.py`: carregamento exclusivo do cache local e apresentação no Streamlit.

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
gera recomendações textuais por IA.

# 6. Metas e Indicadores

## Entregas técnicas

- Dashboard interativo executável localmente com Streamlit.
- Pipeline Python nativo para transformação do CSV municipal.
- Cache JSON consolidado por UF e ano.
- Ranking determinístico com os componentes do cálculo visíveis.
- Tabela e download dos dados filtrados.
- Testes automatizados para processamento, cache e compilação da aplicação.

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

Mitigação: o dashboard utiliza o cache local e não depende de rede durante a
navegação. A atualização principal usa o CSV local.

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
