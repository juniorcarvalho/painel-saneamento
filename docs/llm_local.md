# Resumo local — TP4

O [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) é causal,
multilíngue e disponibilizado sob Apache-2.0. Foi escolhido pelo menor custo
em CPU e pelo modo `enable_thinking=False`. A alternativa
[Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
oferece português e mais parâmetros, mas exige aproximadamente 6 GB apenas
para pesos FP32, contra cerca de 2,4 GB estimados para 0,6B. Não foi feita
comparação empírica entre os modelos. BERT não gera resumos diretamente.

Revisão fixada: `c1899de289a04d12100db370d81485cdf75e47ca`.
O download explícito grava um manifesto conferido no carregamento. A API
usa apenas arquivos locais, sem código remoto. Não há embeddings, RAG,
treinamento nem persistência dos documentos. A proveniência é declarada,
não verificada automaticamente.

Ambiente validado: Python 3.14.2, torch 2.10.0+cpu, Transformers 4.57.6,
huggingface_hub 0.36.2, Pydantic 2.12.5, Linux x86_64. Instalação das wheels
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

`make test`: 24 testes passaram após as correções da revisão 0004. Cobrem contrato 200, validação,
503 de carga/ocupação, 422 por tokens, 504, 500, extração da continuação,
saída vazia, liberação da trava, GET/POST de dados sem LLM, cliente e formulário.
Os testes adicionais cobrem proveniência com título e origem, falta de memória do Python/PyTorch e
do alocador de CPU, parada cooperativa, concorrência entre threads, persistência
em arquivos temporários, caminhos/timeouts HTTP e mensagens de falha na interface.
O AppTest confirma que reruns preservam o resultado sem regenerar.
Há aviso de depreciação do transporte httpx pelo TestClient do FastAPI.

`scripts/verificar_llm.py` executa três fixtures sintéticas autorais CC0,
sem alegar que representam documentos oficiais. Bloqueia conexões por socket
antes do carregamento e registra latência e pico de RSS. Esse ensaio mede o
processo de inferência isolado; a medição com API e Streamlit juntos e a
navegação manual completa ainda não foram realizadas. A validação estrutural
não assegura fidelidade; todo resumo deve ser conferido com seu original.

### Resultado real em 16/11/2026

Carregamento offline: **6,15 s**; pico de RSS: **4134,6 MiB**.
Latências dos casos 1, 2 e 3: **9,20 s**, **7,72 s** e **7,96 s**.
Os três resultados preservaram nomes, datas, quantidades e percentuais.
Não foram observados fatos inventados nem omissões nesses trechos curtos.
O primeiro resultado repetiu integralmente o original; o segundo apenas
reformulou a pontuação e o terceiro apresentou concordância pouco natural
(“sendo os números fictícios e servem…”). Portanto, este ensaio demonstra
execução local e preservação factual nesses casos, mas não comprova boa
compressão ou qualidade geral em documentos maiores. Os limites iniciais
permanecem provisórios até avaliação representativa e medição conjunta.
