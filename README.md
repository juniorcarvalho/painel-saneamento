# Saneamento em Foco

Aplicação Streamlit multipágina integrada a uma API FastAPI para análise e
priorização de investimentos em saneamento urbano por Unidade Federativa.
Os dados municipais do SNIS são agregados por UF e ano. A prioridade combina
40% do déficit de água e 60% do déficit de esgoto.

O projeto também integra dois usos de LLM: um **agente de decisão** (Groq) com
ferramentas determinísticas e memória de conversa, e um **resumo de textos** com
modelo local (Qwen3-0.6B). Nenhum deles altera o score de prioridade.

| Caminho | Conteúdo |
| --- | --- |
| `app.py`, `pages/` | Painel Streamlit (6 páginas) |
| `src/api.py` | API FastAPI (`/dados`, `/processar_texto`, `/agente`) |
| `src/agent_*.py` | Agente: configuração, ferramentas, serviço e contratos |
| `src/llm_*.py` | Resumo local com Qwen |
| `src/data_*.py`, `src/api_data_access.py` | Coleta, agregação, score e dados complementares |
| `tests/` | Testes sem rede, sem chave e sem download de modelos |
| `docs/` | `project_charter.md`, `data_summary.md`, `agente.md`, `llm_local.md` |

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
mesmo comando de instalação. FastAPI, Uvicorn, LangChain/LangGraph e as
bibliotecas do modelo local estão incluídos no arquivo. A primeira instalação
baixa o PyTorch (CPU) e é demorada.

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
| `make download-model` | Baixar o modelo local do resumo (Qwen3-0.6B) |
| `make test` | Executar os testes (sem rede e sem chave) |

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

O menu lateral possui seis páginas:

- **Painel ESG (inicial):** ciclo coleta → processamento → análise → IA, KPIs do
  último ano, evolução nacional, Top 5 de prioridade e o botão "Gerar
  recomendações com IA" (requer `GROQ_API_KEY`).
- **Exploração e ranking:** ano, região, origem, ordenação, métricas, gráfico
  identificado por UF, tabela e exportação dos registros filtrados.
- **Agente de decisão (IA):** chat com memória por conversa, sugestões de
  perguntas e a explicação "Como o agente chegou a isso" (ferramentas e dados).
- **Resumo com IA local:** resumo de textos com o Qwen3-0.6B.
- **Consulta e importação:** GET filtrado na API, download CSV, validação e
  prévia de upload, seguido de envio explícito de um lote via POST.
- **Metodologia e fontes:** regra de prioridade, limitações, proveniência,
  referência municipal local, resumo local e agente.

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

Os endpoints `POST /processar_texto` e `POST /agente` (e `DELETE /agente/{thread_id}`)
têm contratos próprios, descritos nas seções de IA abaixo e em `/docs`.

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

## Agente de decisão (Groq)

A página **Agente de decisão (IA)** e o botão "Gerar recomendações com IA" do **Painel ESG**
usam um agente ReAct (Groq, `openai/gpt-oss-20b`) com ferramentas determinísticas sobre o SNIS.
Detalhes e prompt em [`docs/agente.md`](docs/agente.md).

```sh
cp .env.example .env   # preencha GROQ_API_KEY
make dev               # API + painel; a API lê o .env ao iniciar
```

Sem a chave, o painel e as demais páginas funcionam; a API responde 503 em `POST /agente`
e a página do agente orienta a configuração. A memória da conversa é mantida em RAM por
`thread_id` (`DELETE /agente/{thread_id}` a descarta) e se perde ao reiniciar a API.
Só a pergunta e as saídas agregadas das ferramentas são enviadas à Groq.

Configuração no `.env` (modelo em `.env.example`): `GROQ_API_KEY`, `MODEL_NAME`
(padrão `openai/gpt-oss-20b`), `GROQ_BASE_URL`, `LLM_TEMPERATURE` e `HTTP_TIMEOUT`
(o cliente do Streamlit espera `HTTP_TIMEOUT` + 30 s).

Rota `POST /agente` (`{"mensagem": "...", "thread_id": "..."}`): 200 com `resposta`, `passos`
(ferramenta, entrada e saída), `modelo` e `tempo_processamento_ms`; 422 entrada inválida;
429 limite do provedor; 502 falha do provedor ou resposta vazia do modelo; 503 agente não
configurado; 500 falha interna (a mensagem sugere um novo `thread_id`).

**Limite do plano gratuito da Groq:** cerca de 8000 tokens por minuto para o `gpt-oss-20b`.
Conversas longas ou respostas com séries históricas podem retornar 429; aguarde alguns
segundos e reenvie, ou inicie uma "Nova conversa", que zera o histórico e reduz o consumo.
Se o modelo devolver uma resposta vazia (acontece ocasionalmente), a API responde 502; reenvie a pergunta.

## Resumo com IA local

A página **Resumo com IA local**, usa Qwen3-0.6B via POST `/processar_texto`.

```sh
make setup
make download-model  # requer internet apenas na preparação
make dev
make test             # testes com modelos falsos, sem download
.venv/bin/python scripts/verificar_llm.py             # avaliação real offline do padrão (Qwen3-0.6B)
.venv/bin/python scripts/baixar_modelo.py --todos     # opcional: baixa Qwen3-0.6B e Qwen2.5-1.5B-Instruct
.venv/bin/python scripts/verificar_llm.py --comparar  # opcional: comparação empírica offline dos dois candidatos
```

## Testes

```sh
make test
```

Cobre ferramentas do agente (dados sintéticos), agente com modelo falso (passos,
memória por `thread_id`, erros do provedor), rotas da API, cliente HTTP e páginas
Streamlit. Não requer rede, `GROQ_API_KEY` nem download de modelos.

# Uso de IA

Usado claude code modelo opus 5.5 para planejamento das tarefas e revisão do que foi implementado
