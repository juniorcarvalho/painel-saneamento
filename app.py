import streamlit as st

st.set_page_config(page_title="Saneamento em Foco", layout="wide", initial_sidebar_state="expanded")
st.title("Saneamento em Foco (ODS 6)")
st.caption("Priorização de investimentos em saneamento urbano por Unidade Federativa")

pagina = st.navigation([
    st.Page("pages/painel.py", title="Painel ESG", default=True),
    st.Page("pages/exploracao.py", title="Exploração e ranking"),
    st.Page("pages/agente.py", title="Agente de decisão (IA)"),
    st.Page("pages/resumo.py", title="Resumo com IA local"),
    st.Page("pages/dados.py", title="Consulta e importação"),
    st.Page("pages/metodologia.py", title="Metodologia e fontes"),
])
pagina.run()
