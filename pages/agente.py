"""Chat com o agente de decisão ESG (Groq), com memória por conversa."""

from uuid import uuid4

import streamlit as st

from src.api_client import APIError, limpar_conversa, perguntar_agente
from src.ui_helpers import renderizar_passos

AVISO = "Análise assistida por IA; os números vêm das ferramentas sobre o SNIS."
SUGESTOES = [
    "Quais UFs priorizar em 2021?",
    "E só no Nordeste?",
    "Como o Maranhão evoluiu desde 2010?",
    "Se o esgoto do MA subir 20 p.p., ele sai do top 5?",
]

st.header("Agente de decisão ESG")
st.info(
    "Pergunte em linguagem natural. O agente consulta ferramentas determinísticas sobre os indicadores SNIS e "
    "lembra o contexto da conversa (UF, ano, região). Ele não altera o score de prioridade."
)

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = uuid4().hex
    st.session_state["mensagens_agente"] = []
mensagens = st.session_state["mensagens_agente"]

if st.button("Nova conversa"):
    try:
        limpar_conversa(st.session_state["thread_id"])
    except APIError:
        pass  # a memória do servidor é volátil; descartar o thread é só higiene
    st.session_state["thread_id"] = uuid4().hex
    st.session_state["mensagens_agente"] = mensagens = []

st.caption("Sugestões (use em sequência para ver a memória):")
colunas = st.columns(len(SUGESTOES))
clicada = None
for coluna, texto in zip(colunas, SUGESTOES):
    if coluna.button(texto, key=f"sug_{texto}", width="stretch"):
        clicada = texto

for item in mensagens:
    with st.chat_message(item["papel"]):
        st.write(item["texto"])
        if item["papel"] == "assistant":
            if item["passos"]:
                with st.expander("Como o agente chegou a isso"):
                    renderizar_passos(item["passos"])
            st.caption(f"{item['modelo']} | {item['tempo_ms']} ms. {AVISO}")

pergunta = st.chat_input("Pergunte sobre prioridades, evolução, metas ou cenários") or clicada
if pergunta:
    mensagens.append({"papel": "user", "texto": pergunta})
    with st.chat_message("user"):
        st.write(pergunta)
    try:
        with st.chat_message("assistant"):
            with st.spinner("Consultando o agente…"):
                resposta = perguntar_agente(pergunta, st.session_state["thread_id"])
            st.write(resposta.resposta)
            if resposta.passos:
                with st.expander("Como o agente chegou a isso", expanded=True):
                    renderizar_passos(resposta.passos)
            st.caption(f"{resposta.modelo} | {resposta.tempo_processamento_ms} ms. {AVISO}")
        mensagens.append({"papel": "assistant", "texto": resposta.resposta, "passos": resposta.passos, "modelo": resposta.modelo, "tempo_ms": resposta.tempo_processamento_ms})
    except APIError as exc:
        mensagens.pop()
        if exc.status == 503:
            st.error("Agente não configurado. Copie `.env.example` para `.env`, preencha `GROQ_API_KEY` e reinicie a API (`make dev`).")
        else:
            st.error(str(exc))
        if exc.status == 500 or exc.timeout:
            # a memória do servidor pode estar inconsistente com o histórico visível: recomeça
            st.session_state["thread_id"] = uuid4().hex
            st.session_state["mensagens_agente"] = []
            st.warning("A conversa foi reiniciada para evitar um histórico inconsistente. Refaça a pergunta.")
