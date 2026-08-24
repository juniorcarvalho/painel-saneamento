import csv
import io

import streamlit as st

from src.data_access import PROCESSED_PATH, carregar_dados_processados
from src.data_processing import calcular_prioridade


st.set_page_config(
    page_title="Saneamento em Foco",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def carregar_registros():
    payload = carregar_dados_processados()
    return calcular_prioridade(payload["registros"]), payload.get("fontes", [])


def csv_bytes(registros):
    if not registros:
        return b""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(registros[0].keys()))
    writer.writeheader()
    writer.writerows(registros)
    return buffer.getvalue().encode("utf-8-sig")


st.title("Saneamento em Foco (ODS 6)")
st.subheader("Priorização de investimentos em saneamento básico por Unidade Federativa")

try:
    registros, fontes = carregar_registros()
except (FileNotFoundError, ValueError, OSError) as exc:
    st.error(f"Não foi possível carregar o cache local de dados: {exc}")
    st.stop()

ano_mais_recente = max(item.get("Ano", 0) for item in registros)
top_three = [item for item in registros if item.get("Ano", 0) == ano_mais_recente][:3]
nomes_prioritarios = ", ".join(item["UF"] for item in top_three)
st.info(
    "**Resumo Executivo:** o ranking determinístico combina 40% do déficit de água "
    "e 60% do déficit de esgoto. Com os dados carregados, as três maiores prioridades "
    f"em {ano_mais_recente} são **{nomes_prioritarios}**."
)

tab1, tab2, tab3 = st.tabs(["Aplicação", "Escopo e Metodologia", "Fontes"])

with tab1:
    st.markdown("### Exploração dos dados de saneamento")
    st.write("Os dados são carregados exclusivamente do cache processado local.")

    st.sidebar.header("Filtros")
    anos = sorted({item["Ano"] for item in registros}, reverse=True)
    ano = st.sidebar.selectbox("Ano", anos)
    registros_ano = [item for item in registros if item["Ano"] == ano]
    regioes = ["Todas"] + sorted({item["Regiao"] for item in registros_ano})
    regiao = st.sidebar.selectbox("Região geográfica", regioes)
    criterio = st.sidebar.radio(
        "Ordenar por",
        [
            "Prioridade",
            "Menor Cobertura de Água (%)",
            "Menor Cobertura de Esgoto (%)",
            "Maior População sem Saneamento (M)",
            "Alfabética (UF)",
        ],
    )

    filtrados = registros_ano if regiao == "Todas" else [item for item in registros_ano if item["Regiao"] == regiao]
    if criterio == "Menor Cobertura de Água (%)":
        filtrados = sorted(filtrados, key=lambda item: item["Atendimento_Agua"])
    elif criterio == "Menor Cobertura de Esgoto (%)":
        filtrados = sorted(filtrados, key=lambda item: item["Atendimento_Esgoto"])
    elif criterio == "Maior População sem Saneamento (M)":
        filtrados = sorted(filtrados, key=lambda item: item["Pop_Sem_Saneamento_Milhoes"], reverse=True)
    elif criterio == "Alfabética (UF)":
        filtrados = sorted(filtrados, key=lambda item: item["UF"])

    if not filtrados:
        st.warning("Nenhum dado atende aos filtros selecionados.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Média de atendimento de água", f"{sum(item['Atendimento_Agua'] for item in filtrados) / len(filtrados):.1f}%")
        col2.metric("Média de atendimento de esgoto", f"{sum(item['Atendimento_Esgoto'] for item in filtrados) / len(filtrados):.1f}%")
        col3.metric("População sem saneamento", f"{sum(item['Pop_Sem_Saneamento_Milhoes'] for item in filtrados):.2f} M")

        st.markdown("#### Cobertura por UF")
        st.bar_chart(
            {
                "Água (%)": [item["Atendimento_Agua"] for item in filtrados],
                "Esgoto (%)": [item["Atendimento_Esgoto"] for item in filtrados],
            }
        )

        col_table, col_download = st.columns([4, 1])
        with col_table:
            st.markdown("#### Ranking e dados consolidados")
            st.dataframe(filtrados, width="stretch", hide_index=True)
        with col_download:
            st.download_button(
                "Baixar CSV",
                data=csv_bytes(filtrados),
                file_name="saneamento_filtrado.csv",
                mime="text/csv",
            )

    st.caption(f"Cache: {PROCESSED_PATH}. Fontes declaradas: {', '.join(fontes) or 'não informadas'}")

with tab2:
    st.markdown("### Escopo, metas e abordagem metodológica")
    st.markdown("#### Pergunta de negócio")
    st.write(
        "Quais Unidades Federativas do Brasil apresentam os menores índices de cobertura "
        "de saneamento básico e devem ser priorizadas para alocação de recursos?"
    )
    st.markdown("#### Regra de priorização")
    st.write(
        "A prioridade é calculada de forma determinística: 40% do déficit de atendimento "
        "de água e 60% do déficit de atendimento de esgoto. A população sem saneamento "
        "é apresentada como impacto absoluto e usada como desempate."
    )
    st.markdown("#### Governança")
    st.write("A organização segue as etapas de entendimento, preparação e análise do CRISP-DM e do TDSP.")

with tab3:
    st.markdown("### Fontes de dados")
    st.markdown(
        "- [SNIS](https://www.gov.br/cidades/pt-br/acesso-a-informacao/"
        "acoes-e-programas/saneamento/snis): índices de atendimento de água e esgoto.\n"
        "- [Dataset municipal no Base dos Dados](https://basedosdados.org/dataset/"
        "2a543ad8-3cdb-4047-9498-efe7fb8ed697?table=df7cf198-4889-4baf-bb77-4e0e28eb90ca): "
        "arquivo utilizado no processamento.\n"
        "- [IBGE SIDRA](https://sidra.ibge.gov.br/): dados demográficos das Unidades Federativas.\n"
        "- [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades): "
        "referência para identificação territorial.\n"
        "- [Conecta Brasil](https://conectabrasil.org/): iniciativa de infraestrutura e inclusão.\n"
        "- [Observatório do Terceiro Setor](https://observatorio3setor.org.br/): "
        "referência em projetos sociais.\n"
        "- [ODS 6 da ONU](https://brasil.un.org/pt-br/sdgs/6): água potável e saneamento."
    )
    st.info(
        "A atualização das APIs é executada separadamente por `src/data_access.py`. "
        "O dashboard não depende de rede durante a navegação."
    )
