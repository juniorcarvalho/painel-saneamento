import streamlit as st

from src.data_access import MUNICIPIOS_WEB_PATH
from src.ui_helpers import carregar_referencia_municipios

st.header("Metodologia e fontes")
st.subheader("Pergunta de negócio")
st.write("Quais Unidades Federativas apresentam os maiores déficits urbanos de água e esgoto e devem ser priorizadas para alocação de recursos?")
st.subheader("Regra de priorização")
st.latex(r"Score = 0{,}4(100 - Agua) + 0{,}6(100 - Esgoto)")
st.write("A população sem saneamento representa impacto absoluto e desempata o ranking. O processamento segue as etapas de entendimento, preparação e análise do CRISP-DM e do TDSP.")
st.write("Os percentuais estaduais são calculados pela razão entre as somas das populações urbanas atendidas e residentes. O último ano válido do cache original é 2021: os campos urbanos de 2022 estão vazios. Os indicadores representam cobertura urbana e não a população estadual total.")
st.subheader("Fontes e proveniência")
st.markdown(
    "- [SNIS](https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/snis): fonte oficial dos indicadores.\n"
    "- [Base dos Dados](https://basedosdados.org/dataset/2a543ad8-3cdb-4047-9498-efe7fb8ed697?table=df7cf198-4889-4baf-bb77-4e0e28eb90ca): distribuição do CSV municipal utilizado.\n"
    "- [Wikipédia](https://pt.wikipedia.org/wiki/Lista_de_munic%C3%ADpios_do_Brasil): referência contextual de municípios, UF e estado, sem participação no score.\n"
    "- [IBGE SIDRA](https://sidra.ibge.gov.br/): integração demográfica opcional, fora do processamento principal do CSV.\n"
    "- [ODS 6 da ONU](https://brasil.un.org/pt-br/sdgs/6): contexto e metas do projeto."
)
st.info("A navegação consulta os indicadores na API local. A preparação do SNIS e a coleta da Wikipédia são executadas separadamente. Os dados complementares têm origem e data de importação próprias e não substituem registros oficiais.")
st.write("Beautiful Soup é suficiente para o HTML estático da referência municipal. Selenium só será reavaliado se uma nova fonte exigir interação ou carregamento dinâmico.")

st.subheader("Resumo com LLM local")
st.write("O Qwen3-0.6B resume textos fornecidos pelo usuário, com proveniência declarada. O limite inicial é 50–8000 caracteres e 2048 tokens no prompt completo. Textos e resumos não são persistidos pelo servidor. A saída pode conter erros e deve ser comparada ao original; não constitui indicador oficial nem altera o score determinístico.")

st.subheader("Agente inteligente (Groq)")
st.write(
    "A página \"Agente de decisão\" usa um agente ReAct (LangChain/LangGraph) com o modelo `openai/gpt-oss-20b` na Groq. "
    "O LLM só escolhe ferramentas e redige o texto; todos os números vêm de ferramentas determinísticas sobre o cache oficial SNIS: "
    "`ranking_prioridade`, `indicadores_uf`, `evolucao_uf`, `comparar_ufs`, `resumo_regional`, `distancia_meta` e `simular_cenario`. "
    "A memória da conversa é mantida por `thread_id` no servidor e se perde ao reiniciá-lo."
)
st.markdown(
    "- **Benchmark:** universalização de 2033 do Marco Legal do Saneamento (Lei 14.026/2020), com 99% de água e 90% de esgoto, alinhada às metas 6.1 e 6.2 da ODS 6. O ritmo exigido é comparado à variação média dos últimos 5 anos.\n"
    "- **Score:** o agente não altera a regra de priorização; `simular_cenario` apenas recalcula uma cópia dos dados.\n"
    "- **Privacidade:** só a pergunta e as saídas agregadas das ferramentas são enviadas à Groq; não há dados pessoais. A chave fica no `.env` da API.\n"
    "- **Limitações:** a base termina em 2021, os indicadores são urbanos, o provedor tem limite de taxa e a redação do modelo pode conter imprecisões. Confira os dados exibidos em \"Como o agente chegou a isso\"; a resposta não substitui estudo técnico."
)

with st.expander("Referência territorial extraída da Wikipédia"):
    try:
        municipios = carregar_referencia_municipios()
    except (OSError, ValueError) as exc:
        st.error(f"Não foi possível ler a referência municipal: {exc}")
    else:
        if not municipios:
            st.info("Referência municipal ainda não disponível. A coleta é uma etapa separada da navegação.")
        else:
            if not MUNICIPIOS_WEB_PATH.exists():
                st.info("Exibindo a amostra incluída no projeto: dois municípios por estado presente na coleta. A coleta completa é opcional e pode ser preparada separadamente.")
            st.write(f"{len(municipios):,} municípios disponíveis.".replace(",", "."))
            busca = st.text_input("Buscar município ou UF")
            encontrados = [item for item in municipios if not busca or busca.casefold() in item.get("municipio", "").casefold() or busca.casefold() == item.get("uf", "").casefold()]
            st.dataframe(encontrados[:1000], width="stretch", hide_index=True)
            palavras = {}
            for item in encontrados:
                for palavra in item.get("municipio", "").casefold().split():
                    if len(palavra) > 2:
                        palavras[palavra] = palavras.get(palavra, 0) + 1
            if palavras:
                st.markdown("#### Frequência de palavras nos municípios")
                st.bar_chart(dict(sorted(palavras.items(), key=lambda pair: pair[1], reverse=True)[:20]))
