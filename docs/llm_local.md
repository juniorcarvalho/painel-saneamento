# Resumo local — TP4

O [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) é causal,
multilíngue e disponibilizado sob Apache-2.0. Foi escolhido pelo menor custo
em CPU, pela menor latência e pelo modo `enable_thinking=False`. A alternativa
[Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
oferece português e mais parâmetros, mas exige cerca de 6,1 GiB de RSS em FP32
apenas para carregar (pressionando swap no host de 7,6 GiB de RAM), contra
3,4–4,0 GiB do 0,6B, além de apresentar latências de 2,5x a 5,7x maiores e
extrapolar juízos subjetivos no ensaio empírico abaixo. BERT é um modelo
encoder voltado a representação/classificação e não gera resumos diretamente.

Revisões fixadas em `src/llm_config.py`:
- `Qwen/Qwen3-0.6B`: `c1899de289a04d12100db370d81485cdf75e47ca` (`models/qwen3-0.6b`, padrão da API).
- `Qwen/Qwen2.5-1.5B-Instruct`: `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` (`models/qwen2.5-1.5b-instruct`, candidato alternativo para benchmark).

O download explícito (`scripts/baixar_modelo.py`, com suporte a `--modelo` e
`--todos`) grava um manifesto conferido no carregamento. A API
usa apenas arquivos locais, sem código remoto. Não há embeddings, RAG,
treinamento nem persistência dos documentos. A proveniência é declarada,
não verificada automaticamente.

Ambiente validado: Python 3.14.2, torch 2.10.0+cpu, Transformers 4.57.6,
huggingface_hub 0.36.2, Pydantic 2.12.5, Linux x86_64 (7,6 GiB de RAM, 2,0 GiB de swap). Instalação das wheels
e testes realizados neste ambiente. Inferência em CPU FP32, até 256 tokens
novos, amostragem com temperature=0.7, top_p=0.8 e top_k=20.
O script de avaliação usa seed 42 e quatro threads, sem prometer reprodução
idêntica entre ambientes. A aplicação não fixa a seed de cada requisição.

Execute `make download-model`, depois `make dev`. A API usa um worker.
Sem manifesto/pesos válidos, `/processar_texto` retorna 503 e `/dados`
permanece disponível. Consulte README para opções e exemplo HTTP.
O limite de tokens considera todo o prompt, sem truncamento silencioso.
O prazo é cooperativo entre passos: operações nativas podem ultrapassá-lo.
A trava permanece adquirida até o término real, inclusive após timeout do cliente.

## Verificações

`make test`: 25 testes passaram. Cobrem contrato 200, validação,
503 de carga/ocupação, 422 por tokens, 504, 500, extração da continuação,
saída vazia, liberação da trava, GET/POST de dados sem LLM, cliente, formulário
e resolução do catálogo de modelos candidatos.
Os testes adicionais cobrem proveniência com título e origem, falta de memória do Python/PyTorch e
do alocador de CPU, parada cooperativa, concorrência entre threads, persistência
em arquivos temporários, caminhos/timeouts HTTP e mensagens de falha na interface.
O AppTest confirma que reruns preservam o resultado sem regenerar.
Há aviso de depreciação do transporte httpx pelo TestClient do FastAPI.

`scripts/verificar_llm.py` (com `--modelo` ou `--comparar` em subprocessos isolados)
executa três fixtures sintéticas autorais CC0 (`tests/fixtures/textos_saneamento.json`),
sem alegar que representam documentos oficiais. Bloqueia conexões por socket
antes do carregamento e registra latência e pico de RSS. Esse ensaio mede o
processo de inferência isolado; a medição com API e Streamlit juntos e a
navegação manual completa ainda não foram realizadas. A validação estrutural
não assegura fidelidade; todo resumo deve ser conferido com seu original.

### Resultado inicial do Qwen3-0.6B em 16/11/2026

Carregamento offline: **6,15 s**; pico de RSS: **4134,6 MiB**.
Latências dos casos 1, 2 e 3: **9,20 s**, **7,72 s** e **7,96 s**.

### Comparação empírica entre candidatos em 21/11/2026

Executada com `.venv/bin/python scripts/verificar_llm.py --comparar` (mesmo prompt de sistema, seed 42, 4 threads, FP32 em CPU, nas três fixtures de `tests/fixtures/textos_saneamento.json`):

| Métrica | `Qwen/Qwen3-0.6B` | `Qwen/Qwen2.5-1.5B-Instruct` | Razão (1.5B / 0.6B) |
| --- | --- | --- | --- |
| Pesos em disco (`model.safetensors`) | 1,40 GiB (1,50 GB) | 2,88 GiB (3,09 GB) | 2,06x |
| Carregamento offline | **7,73 s** | **134,82 s** (com paginação/swap) | 17,45x |
| RSS após carregamento | **3436,7 MiB** | **6090,5 MiB** | 1,77x |
| Pico de RSS na inferência | **3436,7 MiB** | **6251,1 MiB** | 1,82x |
| Latência — Caso 1 | **7,03 s** | **24,44 s** | 3,48x |
| Latência — Caso 2 | **6,43 s** | **16,39 s** | 2,55x |
| Latência — Caso 3 | **7,25 s** | **41,64 s** | 5,74x |
| Latência média por resumo | **6,90 s** | **27,49 s** | 3,98x |

#### Comparação qualitativa das saídas por texto

1. **Caso 1** (*"Em 2021, o município fictício de Vila Clara ampliou a rede de água para 200 famílias. A obra terminou em 15 de dezembro de 2021."*):
   - **Qwen3-0.6B (7,03 s):** *"Em 2021, o município fictício de Vila Clara ampliou a rede de água para 200 famílias. A obra terminou em 15 de dezembro de 2021."* — Preservou integralmente os fatos (nomes, 200 famílias, 15 de dezembro de 2021) sem inventar informações, embora tenha repetido o trecho original por já ser curto.
   - **Qwen2.5-1.5B-Instruct (24,44 s):** *"Em 2021, o município fictício de Vila Clara implementou uma expansão na infraestrutura de água potável, beneficiando 200 famílias da comunidade. Esta obra foi concluída no dia 15 de dezembro do mesmo ano."* — Parafraseou com maior fluidez em português e manteve números e datas, porém acrescentou qualificadores ausentes no original (*"água potável"*, *"da comunidade"*).

2. **Caso 2** (*"Em 2022, Vila Clara iniciou a construção de 3 estações de tratamento de esgoto. Duas foram concluídas em 2023; a terceira segue em obras."*):
   - **Qwen3-0.6B (6,43 s):** *"Em 2022, Vila Clara iniciou a construção de 3 estações de tratamento de esgoto. Duas foram concluídas em 2023, e a terceira segue em obras."* — Conservador e fiel aos números e datas, trocando apenas o ponto e vírgula por conjunção.
   - **Qwen2.5-1.5B-Instruct (16,39 s):** *"Vila Clara começou a construir 3 estações de tratamento de esgoto em 2022. As duas primeiras foram concluídas no ano seguinte, em 2023. A terceira está em obras ainda."* — Boa reformulação sintática e preservação exata dos fatos, mas introduziu a inferência não declarada de que as concluídas foram *"as duas primeiras"*.

3. **Caso 3** (*"O relatório de 2024 de Vila Clara registra 80% de cobertura de água e 60% de esgoto. Os números são fictícios e servem apenas para testar resumos."*):
   - **Qwen3-0.6B (7,25 s):** *"O relatório de 2024 de Vila Clara apresenta 80% de cobertura de água e 60% de esgoto, sendo os números fictícios e servem apenas para testar resumos."* — Preservou os percentuais e o aviso de que os números são fictícios, sem extrapolação factual, com leve perda de paralelismo gramatical (*"sendo os números fictícios e servem…"*).
   - **Qwen2.5-1.5B-Instruct (41,64 s):** *"O relatório de 2024 da cidade de Vila Clara apresenta uma situação bastante promissora em termos de infraestrutura hídrica e sanitária. A cidade tem conseguido atingir o objetivo de 80% de cobertura de água potável e 60% de tratamento do esgoto residencial. Essas figuras são altamente positivas e demonstram que a administração municipal está avançando na implementação de sistemas de abastecimento de água e esgotamento sanitário eficientes. As metas alcançadas representam progresso significativo no campo das infraestruturas básicas de saúde pública e segurança ambiental."* — Apesar de mais fluente, violou a instrução negativa do sistema (*"Não acrescente fatos nem recomendações"*): omitiu que os dados eram fictícios, expandiu o texto em vez de comprimir, converteu *"60% de esgoto"* em *"60% de tratamento do esgoto residencial"* e adicionou juízos de valor e fatos não presentes no documento (*"situação bastante promissora"*, *"atingir o objetivo"*, *"administração municipal está avançando"*).

#### Conclusão da justificativa

A comparação empírica confirma a escolha do **Qwen/Qwen3-0.6B** para a aplicação local:
- **Custo computacional e estabilidade:** em CPU FP32, o `Qwen2.5-1.5B-Instruct` atinge **6251,1 MiB de RSS**, ultrapassando a memória livre típica do ambiente de 7,6 GiB de RAM (quando somado ao sistema operacional, FastAPI e Streamlit) e forçando paginação em swap, o que elevou seu carregamento a **134,82 s** contra **7,73 s** do `Qwen3-0.6B` (**3436,7 MiB de RSS**).
- **Latência:** o `Qwen3-0.6B` respondeu em média em **6,90 s** (máximo 7,25 s), enquanto o `Qwen2.5-1.5B-Instruct` levou em média **27,49 s** (chegando a 41,64 s no Caso 3).
- **Qualidade e fidelidade:** embora o `Qwen3-0.6B` seja excessivamente extrativo em textos de duas frases (baixa compressão), ele respeitou estritamente a restrição de não inventar fatos nos três casos. Já o `Qwen2.5-1.5B-Instruct`, com `temperature=0.7`, apresentou melhor paráfrase nos Casos 1 e 2, mas alucinou adjetivações e omitiu a ressalva de dados fictícios no Caso 3.
