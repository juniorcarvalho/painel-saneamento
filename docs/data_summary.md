# Data Summary Report

## 1. Fonte de dados utilizada

A fonte principal do projeto é o arquivo municipal do Sistema Nacional de
Informações sobre Saneamento (SNIS):

```text
data/br_mdr_snis_municipio_agua_esgoto.csv
```

O arquivo foi obtido a partir do dataset disponibilizado no Base dos Dados:

<https://basedosdados.org/dataset/2a543ad8-3cdb-4047-9498-efe7fb8ed697?table=df7cf198-4889-4baf-bb77-4e0e28eb90ca>

Características observadas no arquivo:

- Formato: CSV.
- Granularidade original: município e ano.
- Quantidade aproximada: 119 mil registros municipais.
- Período disponível: 1995 a 2022.
- Abrangência geográfica: 27 Unidades Federativas.
- Quantidade de colunas: 133.

O dashboard não lê o CSV diretamente durante a navegação. O arquivo é
processado por `src/data_access.py` e transformado em:

```text
data/processed/dados_saneamento.json
```

O cache atual contém 723 registros consolidados, correspondentes às
combinações válidas de UF e ano entre 1995 e 2021.

## 2. Indicadores urbanos utilizados

O projeto foi configurado para analisar cobertura urbana. A consolidação usa
os seguintes campos do CSV:

- `ano`: ano de referência do registro.
- `sigla_uf`: Unidade Federativa do município.
- `populacao_urbana_residente_agua`: população urbana residente usada como
  denominador de água.
- `populacao_urbana_atendida_agua`: população urbana atendida com água.
- `populacao_urbana_residente_esgoto`: população urbana residente usada como
  denominador de esgoto.
- `populacao_urbana_atendida_esgoto`: população urbana atendida com esgoto.

O campo original `populacao_atentida_esgoto` possui uma inconsistência de
nomenclatura, mas não é utilizado pelo pipeline urbano atual.

## 3. Transformação e agregação

As etapas executadas em `src/data_processing.py` são:

1. Ler os registros do CSV com a biblioteca padrão `csv`.
2. Converter ano e valores numéricos, ignorando células vazias ou inválidas.
3. Agrupar os municípios por `ano` e `sigla_uf`.
4. Somar separadamente as populações residentes e atendidas de água e esgoto.
5. Calcular a cobertura estadual pela razão entre as somas, evitando média
   simples dos municípios:

```text
Cobertura de água =
soma(população urbana atendida com água) /
soma(população urbana residente de água) x 100

Cobertura de esgoto =
soma(população urbana atendida com esgoto) /
soma(população urbana residente de esgoto) x 100
```

6. Calcular `Pop_Sem_Saneamento_Milhoes` usando o menor atendimento entre água
   e esgoto e o menor denominador urbano disponível.
7. Associar cada UF à sua região geográfica.
8. Persistir os registros consolidados em JSON.

## 4. Priorização

O dashboard calcula um ranking determinístico para cada ano selecionado. A
regra é:

```text
Score de prioridade =
0,4 x déficit de água + 0,6 x déficit de esgoto
```

Em que:

```text
Déficit de água = 100 - cobertura de água
Déficit de esgoto = 100 - cobertura de esgoto
```

A população sem saneamento é exibida como impacto absoluto e utilizada como
critério de desempate. Não há uso de LLM, recomendações geradas por IA ou
variáveis socioeconômicas no ranking atual.

## 5. Limitações e qualidade dos dados

Embora o arquivo contenha registros de 2022, os quatro campos urbanos
necessários estão vazios nesse ano. Por esse motivo, o pipeline não gera
registros de 2022 e utiliza 2021 como último ano válido. Os índices alternativos
disponíveis em 2022 não são misturados aos indicadores urbanos.

Registros municipais sem população residente válida para água ou esgoto não
contribuem para um indicador estadual completo. A cobertura é limitada aos
municípios com dados válidos nos denominadores correspondentes.

O cálculo representa cobertura urbana. Ele não deve ser interpretado como
cobertura total da população estadual nem como análise municipal detalhada no
dashboard final.

## 6. Cache e execução

Para regenerar o cache depois de substituir ou atualizar o CSV:

```bash
source .venv/bin/activate
python src/data_access.py
```

A API lê o JSON processado sem coletar fontes externas. O Streamlit consulta
essa API por HTTP durante a navegação (comandos em terminais separados):

```bash
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

```bash
streamlit run app.py
```

## 7. Integrações opcionais

`src/data_access.py` mantém funções genéricas para coleta via API do IBGE e de
um endpoint SNIS configurado por `SNIS_API_URL`. Essas funções não fazem parte
do fluxo principal atual, não substituem o processamento do CSV e exigem que
as respostas estejam no formato tabular esperado pelo adaptador.

## 8. Extração web de municípios

Como fonte secundária, o projeto utiliza a página
[Lista de municípios do Brasil](https://pt.wikipedia.org/wiki/Lista_de_munic%C3%ADpios_do_Brasil).
A rotina `coletar_municipios_wikipedia` baixa o HTML com uma requisição
identificada, percorre todas as tabelas alfabéticas com Beautiful Soup,
normaliza município e UF e associa o nome do estado. Registros vazios são
descartados e duplicidades por município/UF são removidas. O código IBGE é
descartado porque não está disponível nessa listagem da Wikipédia.

O resultado é salvo em
`data/processed/municipios_brasil_wikipedia.csv` por meio de uma execução
explícita (`SCRAPE_MUNICIPIOS=1 python src/data_access.py`). O dashboard lê
esse CSV local quando disponível; caso contrário, usa automaticamente a
amostra `data/municipios_brasil_wikipedia_amostra.csv`, incluída no Git, com
52 municípios dos 26 estados. O recorte contém os primeiros dois registros
de cada estado presente na coleta e é identificado na interface como amostra.
Não é uma amostra estatística representativa: a frequência de palavras
corresponde apenas ao recorte. O Distrito Federal não aparece na coleta local
usada para gerar a amostra. A origem e os critérios estão em `data/README.md`.
A fonte pode mudar de estrutura ou ficar indisponível, por isso a coleta
completa permanece explícita e fora da navegação. Reinicie o Streamlit após
coletar para renovar o cache municipal.

## 9. API e registros complementares (TP3)

`src/api.py` oferece GET e POST em `/dados`, com documentação automática em
`/docs`, `/redoc` e `/openapi.json`. A API nunca coleta dados externos durante
as requisições. O Streamlit usa `src/api_client.py`, configurado por
`SANEAMENTO_API_URL` (padrão `http://127.0.0.1:8000`).

`GET /dados` responde com `fontes` (metadados do cache oficial) e `registros`
(oficiais e complementares). Os filtros opcionais são `ano` (inteiro entre
1 e 9999) e `regiao` (Norte, Nordeste, Sudeste, Sul ou Centro-Oeste). Resultado
vazio é uma consulta válida com lista vazia. A ausência do cache oficial
resulta em HTTP 503; formato inválido ou falha de leitura resulta em HTTP 500.

`POST /dados` recebe uma lista não vazia com sete campos obrigatórios:

| Campo | Regra |
| --- | --- |
| Ano | Inteiro JSON entre 1 e 9999 |
| UF | Nome ou identificação da UF, texto não vazio |
| Sigla | Sigla válida, normalizada para maiúsculas |
| Regiao | Região brasileira correspondente à sigla |
| Atendimento_Agua | Número finito entre 0 e 100 |
| Atendimento_Esgoto | Número finito entre 0 e 100 |
| Pop_Sem_Saneamento_Milhoes | Número finito maior ou igual a zero |

Campos adicionais e booleanos em campos numéricos são rejeitados. A API usa
`normalizar_registros` e `calcular_prioridade`; déficits e score são calculados
no servidor. O POST responde com HTTP 201 e os novos registros no envelope
`fontes`/`registros`. Payloads e filtros inválidos produzem HTTP 422. Falhas de
persistência produzem HTTP 500, preservando o arquivo anterior quando a
substituição atômica não é concluída.

O armazenamento complementar é exclusivo em
`data/processed/dados_complementares.json`, com uma lista em `registros`.
O POST acrescenta novos registros sem sobrescrever o cache SNIS. O arquivo
complementar ausente equivale a uma lista vazia; formato inválido gera erro,
sem recriação silenciosa. A API marca cada registro como `Origem: oficial`
ou `Origem: complementar`. Complementares recebem `Importado_Em` em UTC;
a data indica importação e não a data de coleta da fonte enviada pelo usuário.
Não há verificação externa de autenticidade desses dados. A fonte declarada
do cache oficial é preservada, e não é atribuída aos registros complementares.

O arquivo complementar tem gravação atômica e lock em um processo. A execução
suportada usa um worker; coordenação entre instâncias requer outra solução de
persistência. Não há deduplicação: reenvios criam novas linhas para a mesma
UF/ano. A exploração permite filtrar a origem, iniciando pela oficial. Médias
são simples sobre os registros exibidos; somas populacionais podem duplicar
pessoas se forem incluídos lotes sobrepostos.

## 10. Upload, navegação e exportação

O menu `st.navigation` separa exploração/ranking, consulta/importação e
metodologia/fontes. As consultas e os gráficos usam o GET da API; erros são
exibidos sem impedir a navegação para a metodologia.

O upload aceita CSV UTF-8 separado por vírgula, no formato consolidado acima
ou com as seis colunas municipais urbanas descritas na seção 2. O segundo
formato é agregado por UF/ano antes do envio. Preserva-se a política de
agregação: valores municipais vazios ou inválidos não contribuem e grupos
sem denominadores não geram indicadores. O CSV consolidado é validado por
`normalizar_registros`; cabeçalhos duplicados, linhas com quantidade incorreta
de células e ausência de registros válidos são rejeitados.

A prévia antecede o botão de envio. A persistência acontece somente após POST
bem-sucedido; o upload não altera diretamente os arquivos. A exportação é um
CSV UTF-8 com BOM dos dados consultados e filtrados, incluindo a origem. Na
reimportação, são enviados apenas os sete campos de entrada. A referência
municipal mantém `st.cache_data`, e as consultas de indicadores são renovadas
a cada execução da página para refletir os lotes persistidos.

## 11. Preparação para LLMs

Os dados atuais são tabulares e não contêm texto apropriado para resumo,
análise de sentimento ou Q&A. A lista municipal é uma referência de nomes,
sem conteúdo documental suficiente para essas tarefas.

Uma evolução futura exigirá relatórios ou documentos de saneamento com fonte,
data, licença e contexto territorial registrados. Será necessário limpar e
segmentar os textos, associá-los aos indicadores por UF/ano e avaliar respostas
com citações e critérios de fidelidade. Este TP3 apresenta essa preparação na
metodologia e não adiciona inferência, recomendações automáticas ou provedor.
Beautiful Soup é mantido para a fonte HTML estática; Selenium só se justifica
com uma fonte necessária que dependa de interação ou carregamento dinâmico.


## TP4 — resumo local
Textos de saneamento são fornecidos pelo usuário com título e origem declarados. Qwen3-0.6B gera resumos sem persistência de textos ou respostas no servidor. Limites padrão: 50–8000 caracteres, 2048 tokens de prompt e 256 tokens novos. A fonte não é consultada automaticamente. Os indicadores e o score determinístico permanecem independentes do resumo.
