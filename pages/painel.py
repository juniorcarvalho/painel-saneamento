"""Painel ESG: do dado ao insight."""

from uuid import uuid4

import streamlit as st

from src.api_client import APIError, perguntar_agente
from src.ui_helpers import carregar_registros, renderizar_passos

META_AGUA, META_ESGOTO = 99.0, 90.0

st.header("Painel ESG — do dado ao insight")
try:
    registros, fontes = carregar_registros()
except APIError as exc:
    st.error(str(exc))
    st.stop()
oficiais = [item for item in registros if item["Origem"] == "oficial"]
if not oficiais:
    st.info("Nenhum registro oficial disponível.")
    st.stop()

ano = max(item["Ano"] for item in oficiais)
do_ano = [item for item in oficiais if item["Ano"] == ano]
anos = sorted({item["Ano"] for item in oficiais})

st.subheader("Ciclo de Ciência de Dados")
etapas = st.columns(4)
with etapas[0]:
    st.markdown("**1. Coleta**")
    st.caption("SNIS/Base dos Dados, Wikipédia (scraping) e IBGE")
    st.page_link("pages/metodologia.py", label=f"{len(fontes)} fonte(s) oficiais")
with etapas[1]:
    st.markdown("**2. Processamento**")
    st.caption("Consolidação urbana por UF e ano")
    st.page_link("pages/dados.py", label=f"{len(oficiais)} registros UF×ano")
with etapas[2]:
    st.markdown("**3. Análise**")
    st.caption("Score = 40% água + 60% esgoto")
    st.page_link("pages/exploracao.py", label=f"Ranking de {ano}")
with etapas[3]:
    st.markdown("**4. IA**")
    st.caption("Agente Groq (decisão) + resumo Qwen local")
    st.page_link("pages/agente.py", label="Agente de decisão")

abaixo = [item for item in do_ano if item["Atendimento_Agua"] < META_AGUA or item["Atendimento_Esgoto"] < META_ESGOTO]
col1, col2, col3, col4 = st.columns(4)
col1.metric(f"Água (média, {ano})", f"{sum(i['Atendimento_Agua'] for i in do_ano) / len(do_ano):.1f}%")
col2.metric(f"Esgoto (média, {ano})", f"{sum(i['Atendimento_Esgoto'] for i in do_ano) / len(do_ano):.1f}%")
col3.metric("Pop. urbana sem saneamento", f"{sum(i['Pop_Sem_Saneamento_Milhoes'] for i in do_ano):.1f} M")
col4.metric("UFs abaixo da meta de 2033", f"{len(abaixo)} de {len(do_ano)}")
st.caption("Médias simples entre UFs, dados oficiais do SNIS (cobertura urbana). Meta: 99% água e 90% esgoto até 2033 (Lei 14.026/2020; ODS 6.1/6.2).")

graf1, graf2 = st.columns(2)
with graf1:
    st.subheader("Evolução nacional")
    serie = []
    for a in anos:
        grupo = [i for i in oficiais if i["Ano"] == a]
        serie.append({"Ano": a, "Água (%)": sum(i["Atendimento_Agua"] for i in grupo) / len(grupo), "Esgoto (%)": sum(i["Atendimento_Esgoto"] for i in grupo) / len(grupo)})
    st.line_chart(serie, x="Ano", y=["Água (%)", "Esgoto (%)"])
with graf2:
    st.subheader(f"Top 5 de prioridade em {ano}")
    st.bar_chart([{"UF": i["Sigla"], "Score": i["Score_Prioridade"]} for i in do_ano[:5]], x="UF", y="Score")

st.subheader("Recomendações com IA")
if st.button("Gerar recomendações com IA"):
    prompt = f"Analise o ranking de {ano} e a distância à meta de 2033 das 5 UFs prioritárias e recomende onde investir primeiro"
    try:
        with st.spinner("Consultando o agente…"):
            st.session_state["recomendacao_painel"] = perguntar_agente(prompt, uuid4().hex)
    except APIError as exc:
        if "HTTP 503" in str(exc) and "GROQ_API_KEY" in str(exc):
            st.warning("Agente não configurado. Copie `.env.example` para `.env`, preencha `GROQ_API_KEY` e reinicie a API (`make dev`). O restante do painel funciona sem a chave.")
        else:
            st.error(str(exc))
if "recomendacao_painel" in st.session_state:
    resposta = st.session_state["recomendacao_painel"]
    st.write(resposta.resposta)
    with st.expander("Dados das ferramentas que embasam a resposta"):
        renderizar_passos(resposta.passos)
    st.caption(f"{resposta.modelo} | {resposta.tempo_processamento_ms} ms. Análise assistida por IA; os números vêm das ferramentas sobre o SNIS.")
