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

O Streamlit consome somente o JSON processado e não realiza chamadas de rede
durante a navegação:

```bash
streamlit run app.py
```

## 7. Integrações opcionais

`src/data_access.py` mantém funções genéricas para coleta via API do IBGE e de
um endpoint SNIS configurado por `SNIS_API_URL`. Essas funções não fazem parte
do fluxo principal atual, não substituem o processamento do CSV e exigem que
as respostas estejam no formato tabular esperado pelo adaptador.
