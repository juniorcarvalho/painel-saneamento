from streamlit.testing.v1 import AppTest

from src import api_client, ui_helpers
from src.agent_schemas import PassoSaida, RespostaAgenteSaida
from src.data_access import carregar_dados_processados
from src.data_processing import calcular_prioridade

SAIDA = '{"ano":2021,"regiao":null,"ranking":[{"sigla":"AC","agua":50,"esgoto":10,"score":74}]}'


def resposta(texto="Priorize o AC."):
    return RespostaAgenteSaida(resposta=texto, passos=[PassoSaida(ferramenta="ranking_prioridade", entrada={"limite": 5}, saida=SAIDA)], modelo="m", thread_id="x" * 8, tempo_processamento_ms=3)


def test_chat_envia_mesmo_thread_e_nova_conversa(monkeypatch):
    chamadas, limpas = [], []
    monkeypatch.setattr(api_client, "perguntar_agente", lambda m, t: chamadas.append((m, t)) or resposta())
    monkeypatch.setattr(api_client, "limpar_conversa", lambda t: limpas.append(t))
    app = AppTest.from_file("pages/agente.py", default_timeout=15).run()
    app.chat_input[0].set_value("Quais UFs priorizar em 2021?").run()
    app.chat_input[0].set_value("E só no Nordeste?").run()
    assert not app.exception
    assert len(chamadas) == 2 and chamadas[0][1] == chamadas[1][1]
    assert len(app.session_state["mensagens_agente"]) == 4
    antigo = chamadas[0][1]
    next(b for b in app.button if b.label == "Nova conversa").click().run()
    assert limpas == [antigo] and app.session_state["thread_id"] != antigo
    assert app.session_state["mensagens_agente"] == []


def test_503_orienta_configuracao(monkeypatch):
    def falhar(m, t):
        raise api_client.APIError("API retornou HTTP 503: Configure GROQ_API_KEY no .env e reinicie a API.", status=503)

    monkeypatch.setattr(api_client, "perguntar_agente", falhar)
    app = AppTest.from_file("pages/agente.py", default_timeout=15).run()
    app.chat_input[0].set_value("Olá agente").run()
    assert any(".env.example" in e.value for e in app.error)
    assert app.session_state["mensagens_agente"] == []


def test_painel_kpis_e_recomendacao_em_cache(monkeypatch):
    registros = calcular_prioridade(carregar_dados_processados()["registros"])
    for item in registros:
        item["Origem"] = "oficial"

    monkeypatch.setattr(ui_helpers, "consultar_dados", lambda ano=None, regiao=None: {"fontes": ["SNIS"], "registros": registros})
    chamadas = []
    monkeypatch.setattr(api_client, "perguntar_agente", lambda m, t: chamadas.append(m) or resposta())
    app = AppTest.from_file("app.py", default_timeout=20).run()
    assert not app.exception
    assert any("UFs abaixo da meta" in m.label for m in app.metric)
    next(b for b in app.button if b.label == "Gerar recomendações com IA").click().run()
    assert not app.exception and len(chamadas) == 1 and "ranking de 2021" in chamadas[0]
    app.run()
    assert len(chamadas) == 1


def test_500_reinicia_o_thread(monkeypatch):
    def falhar(m, t):
        raise api_client.APIError("API retornou HTTP 500: Falha interna no agente.", status=500)

    monkeypatch.setattr(api_client, "perguntar_agente", falhar)
    app = AppTest.from_file("pages/agente.py", default_timeout=15).run()
    antigo = app.session_state["thread_id"]
    app.chat_input[0].set_value("Olá agente").run()
    assert app.session_state["thread_id"] != antigo
    assert app.session_state["mensagens_agente"] == []
    assert any("reiniciada" in w.value for w in app.warning)
