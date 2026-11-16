"""Formulário de resumo com proveniência declarada."""

import streamlit as st

from src.api_client import APIError, processar_texto

st.header("Resumo com IA local")
st.info(
    "Cole de 50 a 8000 caracteres. O prompt completo aceita até 2048 tokens por padrão. "
    "Confira o resumo com o original; ele não altera os indicadores oficiais."
)

with st.form("resumo"):
    texto = st.text_area("Texto de saneamento", max_chars=8000, height=220)
    titulo = st.text_input("Título", max_chars=200)
    origem = st.text_input("Origem (URL ou identificação do documento local)", max_chars=500)
    enviar = st.form_submit_button("Gerar resumo")

if enviar:
    try:
        with st.spinner("Gerando resumo localmente…"):
            resposta = processar_texto({
                "texto": texto,
                "fonte": {
                    "titulo": titulo,
                    "origem": origem,
                },
            })
        st.session_state["resumo_local"] = resposta
    except APIError as exc:
        st.error(str(exc))

if "resumo_local" in st.session_state:
    resposta = st.session_state["resumo_local"]
    st.subheader("Último resumo gerado")
    st.text(resposta.resultado)
    st.text(f"Fonte declarada: {resposta.fonte.titulo} — {resposta.fonte.origem}")
    st.caption(f"{resposta.modelo} | {resposta.tempo_processamento_ms} ms")
    with st.expander("Texto original"):
        st.text(resposta.texto_processado)
