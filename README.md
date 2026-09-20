# Saneamento em Foco

Dashboard Streamlit para análise e priorização de investimentos em saneamento
urbano por Unidade Federativa. O projeto utiliza dados municipais do Sistema
Nacional de Informações sobre Saneamento (SNIS), agregados por UF e ano.
https://basedosdados.org/dataset/2a543ad8-3cdb-4047-9498-efe7fb8ed697?table=df7cf198-4889-4baf-bb77-4e0e28eb90ca

## Requisitos

- Python 3.14 ou versão compatível com as dependências do projeto.
- Ambiente virtual Python.
- Arquivo CSV municipal do SNIS em:
  `data/br_mdr_snis_municipio_agua_esgoto.csv`.

## github: https://github.com/juniorcarvalho/painel-saneamento

## Configuração

Na raiz do projeto, crie ou ative o ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

## Atualização dos dados

O comando abaixo lê o CSV municipal, agrega os registros por ano e UF e grava o
cache utilizado pelo painel:

```bash
python src/data_access.py
```

O arquivo gerado é:

```text
data/processed/dados_saneamento.json
```

A agregação utiliza os campos urbanos:

- `populacao_urbana_residente_agua`
- `populacao_urbana_atendida_agua`
- `populacao_urbana_residente_esgoto`
- `populacao_urbana_atendida_esgoto`

Os percentuais estaduais são calculados usando a razão entre as somas das
populações atendidas e residentes. 


## Execução do painel

Com o ambiente virtual ativo e o cache gerado, execute:

```bash
streamlit run app.py
```

## Extração da referência municipal

A lista de municípios da Wikipédia é coletada separadamente e persistida em
`data/processed/municipios_brasil_wikipedia.csv`. Assim, o painel permanece
offline durante a navegação:

```bash
SCRAPE_MUNICIPIOS=1 python src/data_access.py
```

O CSV contém `municipio`, `uf` e `estado`. A página apresenta a listagem em
várias tabelas por faixa alfabética; o extrator percorre todas elas. 

O painel também permite enviar um CSV complementar pela barra lateral. O
arquivo é validado, mantido em `st.session_state` e pode ser baixado novamente;
ele não sobrescreve o cache oficial.
## Organização dos arquivos

```text
app.py                              Interface Streamlit
src/data_access.py                 Leitura, coleta e persistência do cache
src/data_processing.py             Agregação urbana e priorização
data/br_mdr_*.csv                  Base municipal de origem
data/processed/*.json              Cache consolidado do dashboard
docs/                               Contexto, escopo, dados e planos técnicos
requirements.txt                   Dependências Python
```
