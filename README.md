# Saneamento em Foco

Aplicação Streamlit multipágina integrada a uma API FastAPI para análise e
priorização de investimentos em saneamento urbano por Unidade Federativa.
Os dados municipais do SNIS são agregados por UF e ano. A prioridade combina
40% do déficit de água e 60% do déficit de esgoto.

## Instalação local

Use Python 3.11 ou superior (incluindo 3.14). Os comandos abaixo são para
Linux/macOS e devem ser executados na raiz do repositório.
O atalho de desenvolvimento também requer GNU Make (`make`).

Se ainda não tiver o projeto localmente:

```bash
git clone https://github.com/juniorcarvalho/painel-saneamento.git
cd painel-saneamento
```

Para criar o ambiente virtual e instalar as dependências:

```bash
make setup
```

Também é possível configurar manualmente:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Se o ambiente já existir, basta ativá-lo e atualizar as dependências com o
mesmo comando de instalação. FastAPI e Uvicorn estão incluídos no arquivo.

## Preparação dos dados

Obtenha o CSV municipal do SNIS no
[Base dos Dados](https://basedosdados.org/dataset/2a543ad8-3cdb-4047-9498-efe7fb8ed697?table=df7cf198-4889-4baf-bb77-4e0e28eb90ca)
e salve em `data/br_mdr_snis_municipio_agua_esgoto.csv`. Execute:

```bash
python src/data_access.py
```

O comando gera `data/processed/dados_saneamento.json`, com fontes e registros.
Os percentuais urbanos estaduais usam a razão entre as somas das populações
atendidas e residentes de água e esgoto. No arquivo original, 2021 é o último
ano com os denominadores urbanos necessários; os campos de 2022 estão vazios.
A API não inicia coleta nem processamento da fonte durante uma requisição.
Se o cache oficial já estiver disponível, é possível iniciar os serviços
diretamente. O CSV original só é necessário para gerar ou atualizar esse cache.
Os arquivos de dados processados são locais e não são incluídos no Git.

A referência contextual de municípios inclui uma amostra em
[`data/municipios_brasil_wikipedia_amostra.csv`](data/municipios_brasil_wikipedia_amostra.csv),
com 52 registros cobrindo os 26 estados (dois municípios por estado).
Ao clonar o projeto, a página **Metodologia e fontes** usa essa amostra
automaticamente se a coleta completa não estiver disponível e identifica
o recorte na tela. A referência pode ser consultada sem executar o scraper
ou iniciar a API.

Para obter a referência completa, execute a coleta opcional separadamente:

```bash
SCRAPE_MUNICIPIOS=1 python src/data_access.py
```

O HTML estático da Wikipédia é extraído com Beautiful Soup e salvo em
`data/processed/municipios_brasil_wikipedia.csv`, com município, UF e estado.
Esse arquivo completo tem preferência sobre a amostra e permanece ignorado
pelo Git. Reinicie o Streamlit após gerar a coleta para renovar o cache da
referência municipal. A origem e os critérios do recorte estão em
[`data/README.md`](data/README.md).
Essa fonte não fornece o score. Selenium não é necessário para a fonte atual;
será reavaliado caso outra fonte exija interação ou carregamento dinâmico.

## Executar API e painel

Para preparar o ambiente e iniciar API e Streamlit em um único comando:

```bash
make dev
```

O comando cria `.venv` se necessário, instala as dependências na primeira
execução ou quando `requirements.txt` mudar e gera o cache oficial a partir
do CSV municipal local se o cache ainda não existir. Não é necessário ativar
o ambiente virtual. O CSV municipal deve estar no caminho da seção de dados;
se ele e o cache estiverem ausentes, o comando informa como proceder.
A coleta da Wikipédia é opcional e não é executada durante a inicialização.

A API inicia com recarga automática ao alterar arquivos em `src/`. O
Streamlit mantém seu comportamento de recarga. Os logs de ambos aparecem no
terminal; **Ctrl+C encerra os dois serviços**, incluindo o processo de recarga
da API. Se um serviço encerrar, o outro também será encerrado.
`make up` é um alias de `make dev`.

Para mudar as portas:

```bash
make dev API_PORT=8001 WEB_PORT=8502
```

O endereço da API no Streamlit é ajustado automaticamente. Para aceitar
conexões externas ao ambiente local, configure os endereços de escuta:

```bash
make dev API_HOST=0.0.0.0 WEB_HOST=0.0.0.0
```

Outros comandos disponíveis:

| Comando | Finalidade |
| --- | --- |
| `make help` | Listar comandos e opções de configuração |
| `make setup` | Criar o ambiente e instalar dependências |
| `make api` | Iniciar somente a API, preparando o cache se necessário |
| `make web` | Iniciar somente o painel; requer API em execução |
| `make data` | Regenerar o cache oficial a partir do CSV municipal local |
| `make scrape` | Executar a coleta opcional da Wikipédia |

Também é possível iniciar os serviços manualmente em dois terminais, ambos
na raiz do projeto:

**Terminal 1 — API FastAPI:**

```bash
source .venv/bin/activate
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — painel Streamlit:**

```bash
source .venv/bin/activate
python -m streamlit run app.py
```

Abra o painel em [localhost:8501](http://localhost:8501) e a documentação da
API em [127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
Use `Ctrl+C` em cada terminal para encerrar os serviços.

Para verificar a consulta após iniciar a API:

```bash
curl 'http://127.0.0.1:8000/dados?ano=2021&regiao=Norte'
```

Para usar outro endereço da API, defina a variável no processo do Streamlit:

```bash
SANEAMENTO_API_URL=http://127.0.0.1:8000 python -m streamlit run app.py
```

Por exemplo, se iniciar o Uvicorn com `--port 8001`, use
`SANEAMENTO_API_URL=http://127.0.0.1:8001`. O endereço é acessado pelo servidor
Streamlit, portanto deve ser alcançável a partir do ambiente onde ele executa.

## Navegação e uso

O menu lateral possui três páginas:

- **Exploração e ranking:** ano, região, origem, ordenação, métricas, gráfico
  identificado por UF, tabela e exportação dos registros filtrados.
- **Consulta e importação:** GET filtrado na API, download CSV, validação e
  prévia de upload, seguido de envio explícito de um lote via POST.
- **Metodologia e fontes:** regra de prioridade, limitações, proveniência,
  referência municipal local e preparação conceitual para uma futura LLM.

A exploração inicia com origem oficial. Dados complementares podem repetir
UF/ano e alterar médias e somas quando incluídos. A interface informa essa
limitação. A indisponibilidade da API aparece nas páginas de dados e mantém
a navegação para a metodologia disponível.

### Importar e exportar dados

1. Abra **Consulta e importação** e selecione o CSV em **CSV complementar**.
2. Confira a prévia dos registros normalizados e agregados por UF/ano.
3. Clique em **Enviar à API** e aguarde a mensagem de sucesso. A seleção do
   arquivo, por si só, não grava dados.
4. Consulte o ano e a região desejados e use **Baixar CSV da consulta**.
5. Em **Exploração e ranking**, selecione a origem **complementar** ou
   **Todas** para incluir os registros importados. Use **Baixar CSV filtrado**
   para exportar o recorte exibido.

## Dev Container e GitHub Codespaces

A configuração em `.devcontainer/devcontainer.json` instala as dependências
e inicia API e Streamlit ao conectar ao ambiente. As portas encaminhadas são
8000 (API) e 8501 (painel). Abra a porta 8501 na visualização do editor ou no
navegador. A comunicação entre os serviços usa o endereço local dentro do
container; não é necessário configurar a URL pública da API no Streamlit.

O cache oficial ainda precisa ser preparado conforme a seção de dados. Se
um serviço não estiver em execução, use os comandos dos terminais acima no
ambiente do container, evitando iniciar outra instância na mesma porta.

## Contrato da API

Documentação interativa em `http://127.0.0.1:8000/docs`, alternativa em `/redoc`
e contrato em `/openapi.json`.

```bash
curl 'http://127.0.0.1:8000/dados?ano=2021&regiao=Norte'
```

`GET /dados` retorna `{"fontes": [...], "registros": [...]}`. `ano` é opcional,
inteiro entre 1 e 9999; `regiao` é opcional e aceita `Norte`, `Nordeste`,
`Sudeste`, `Sul` ou `Centro-Oeste`. Sem filtros, retorna todos os registros.
Cada registro contém `Origem` (`oficial` ou `complementar`), déficits e score;
os complementares também contêm `Importado_Em` em UTC.
`fontes` mantém os metadados do cache oficial; a origem complementar é
identificada em cada registro, sem atribuição ao SNIS.

```bash
curl -X POST 'http://127.0.0.1:8000/dados' \
  -H 'Content-Type: application/json' \
  -d '[{"Ano":2021,"UF":"Acre","Sigla":"AC","Regiao":"Norte","Atendimento_Agua":75,"Atendimento_Esgoto":30,"Pop_Sem_Saneamento_Milhoes":0.2}]'
```

`POST /dados` recebe uma lista não vazia com as sete colunas do exemplo.
Percentuais são números entre 0 e 100; população é um número finito não
negativo, em milhões. O ano JSON deve ser inteiro. A sigla é normalizada para
maiúsculas e deve corresponder à região. Campos adicionais são rejeitados;
score, déficits e proveniência são definidos pelo servidor. Resposta `201`
retorna somente os registros recém-importados no mesmo envelope do GET.

| Situação | HTTP |
| --- | --- |
| Consulta válida, inclusive sem resultados | 200 |
| Lote complementar persistido | 201 |
| Payload ou parâmetros inválidos | 422 |
| Cache oficial ausente no GET | 503 |
| Arquivo inválido ou falha de leitura/escrita | 500 |

Os lotes são acrescentados em `data/processed/dados_complementares.json`.
Arquivo ausente representa uma lista vazia; arquivo corrompido provoca erro,
sem descarte silencioso. O POST não modifica `dados_saneamento.json`.
A gravação complementar usa substituição atômica e exclusão mútua dentro de
um único processo. Execute com **um worker**: múltiplos processos ou instâncias
exigem um banco de dados ou coordenação adicional. Envios repetidos criam
novos registros; não existe deduplicação nem atualização automática.
O serviço é destinado ao uso local acadêmico e não possui autenticação.

## Upload CSV

Use UTF-8 (BOM opcional), separador vírgula e ponto decimal. Vírgula decimal
é aceita em células entre aspas. O formato consolidado é:

```csv
Ano,UF,Sigla,Regiao,Atendimento_Agua,Atendimento_Esgoto,Pop_Sem_Saneamento_Milhoes
2021,Acre,AC,Norte,75,30,0.2
```

Também são aceitas as seis colunas municipais urbanas:
`ano`, `sigla_uf`, `populacao_urbana_residente_agua`,
`populacao_urbana_atendida_agua`, `populacao_urbana_residente_esgoto` e
`populacao_urbana_atendida_esgoto`. A agregação ocorre antes do envio à API.
Na agregação municipal, células numéricas vazias ou inválidas não contribuem;
combinações sem denominadores válidos são descartadas. A prévia mostra o
resultado consolidado. CSVs exportados podem ser reimportados: somente os
sete campos de entrada são enviados; score e origem são recalculados.

## Uso de LLM

Codex modelo Sol 6.1 para revisao do código e geração da documentação

## Resumo com IA local

A quarta página, **Resumo com IA local**, usa Qwen3-0.6B via POST `/processar_texto`.
É independente do uso de Codex no desenvolvimento e não altera o ranking.

```sh
make setup
make download-model  # requer internet apenas na preparação
make dev
make test             # testes com modelos falsos, sem download
.venv/bin/python scripts/verificar_llm.py  # avaliação real offline
```

Python 3.14.2 teve instalação e testes verificados. `PYTHON` e `VENV` configuram
um ambiente novo no Makefile (ex.: `make setup PYTHON=python3.12 VENV=.venv312`).
Use um único worker da API. Pesos ficam em `models/qwen3-0.6b/`, fora do Git.
`SANEAMENTO_LLM_PATH` muda esse diretório; `SANEAMENTO_LLM_TIMEOUT_SECONDS`
(padrão 120, intervalo 1–3600) e `SANEAMENTO_LLM_MAX_INPUT_TOKENS`
(padrão 2048, intervalo 128–8192) configuram limites. Configure o mesmo prazo
na API e no Streamlit; o cliente adiciona 15 segundos ao timeout.

```sh
curl http://127.0.0.1:8000/processar_texto -H 'Content-Type: application/json' \
  -d '{"texto":"Em 2021, a cidade ampliou a rede de água para 200 famílias.","fonte":{"titulo":"Exemplo","origem":"Documento local"}}'
```

A fonte exige apenas título e origem. Esses metadados são preservados na resposta.

A resposta contém `texto_processado`, `tipo_analise`, `resultado`, `modelo`,
`revisao`, `fonte` e `tempo_processamento_ms`. Erros usam `detail`: 422 para
entrada inválida, 503 para modelo ausente/ocupado, 504 para prazo excedido e
500 para falha interna. Modelo ausente não impede acesso a `/dados`.
O startup não baixa arquivos e usa `HF_HUB_OFFLINE=1`. Textos e resumos não
são gravados pelo servidor; o último resultado permanece na sessão da interface.
Veja [configuração e avaliação](docs/llm_local.md).
