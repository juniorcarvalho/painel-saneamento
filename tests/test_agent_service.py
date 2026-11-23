import httpx
import openai
import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from src import agent_service as svc
from src.agent_config import ConfigError, ExternalServiceError, LimiteExcedido, Settings
from tests.fakes import FakeToolChatModel


def agente(respostas, tools=None):
    @tool
    def ranking_prioridade(limite: int = 5) -> str:
        """Ranking."""
        return '{"ranking":[{"sigla":"AC"}]}'

    return svc.build_agent(llm=FakeToolChatModel(messages=iter(respostas)), tools=tools or [ranking_prioridade])


def test_passos_e_resposta():
    ag = agente([
        AIMessage(content="", tool_calls=[{"name": "ranking_prioridade", "args": {"limite": 3}, "id": "c1"}]),
        AIMessage(content="Priorize o AC."),
    ])
    r = svc.perguntar(ag, "Quais UFs priorizar?", "thread-aaaa")
    assert r.texto == "Priorize o AC."
    assert len(r.passos) == 1
    p = r.passos[0]
    assert (p.ferramenta, p.entrada, p.saida) == ("ranking_prioridade", {"limite": 3}, '{"ranking":[{"sigla":"AC"}]}')


def test_memoria_por_thread():
    vistos = []

    class Modelo(FakeToolChatModel):
        def _generate(self, messages, *a, **k):
            vistos.append(sum(m.type == "human" for m in messages))
            return super()._generate(messages, *a, **k)


    @tool
    def x() -> str:
        """x"""
        return "x"

    ag = svc.build_agent(llm=Modelo(messages=iter([AIMessage(content=f"r{i}") for i in range(3)])), tools=[x])
    svc.perguntar(ag, "primeira", "thread-aaaa")
    svc.perguntar(ag, "segunda", "thread-aaaa")
    svc.perguntar(ag, "outra thread", "thread-bbbb")
    assert vistos == [1, 2, 1]
    ag.checkpointer.delete_thread("thread-aaaa")


def test_passos_so_do_turno_atual():
    ag = agente([
        AIMessage(content="", tool_calls=[{"name": "ranking_prioridade", "args": {}, "id": "c1"}]),
        AIMessage(content="um"),
        AIMessage(content="dois"),
    ])
    svc.perguntar(ag, "primeira", "thread-aaaa")
    assert svc.perguntar(ag, "segunda", "thread-aaaa").passos == []


REQ = httpx.Request("POST", "https://x")


@pytest.mark.parametrize("erro,esperado", [
    (openai.AuthenticationError("x", response=httpx.Response(401, request=REQ), body=None), ExternalServiceError),
    (openai.RateLimitError("x", response=httpx.Response(429, request=REQ), body=None), LimiteExcedido),
    (openai.APIConnectionError(request=REQ), ExternalServiceError),
    (openai.APIError("x", request=REQ, body=None), ExternalServiceError),
])
def test_mapeamento_excecoes(erro, esperado):
    class Quebrado:
        def invoke(self, *a, **k):
            raise erro

    with pytest.raises(esperado):
        svc.perguntar(Quebrado(), "oi", "thread-aaaa")


@pytest.mark.parametrize("corpo,esperado", [
    ({"message": "Rate limit reached ... on tokens per day (TPD): Limit 200000. Please try again in 3m52.848s."}, "Limite diário de tokens do provedor atingido. Tente novamente em 3m52.848s."),
    ({"message": "Rate limit reached ... on tokens per minute (TPM): Limit 8000. Please try again in 2.5s."}, "Limite de tokens por minuto do provedor atingido. Tente novamente em 2.5s."),
    (None, "Limite de requisições do provedor atingido. Tente novamente em instantes."),
])
def test_mensagem_de_limite_detalhada(corpo, esperado):
    class Limitado:
        def invoke(self, *a, **k):
            raise openai.RateLimitError("x", response=httpx.Response(429, request=REQ), body=corpo)

    with pytest.raises(LimiteExcedido) as info:
        svc.perguntar(Limitado(), "oi", "thread-aaaa")
    assert str(info.value) == esperado


def test_chave_ausente(monkeypatch):
    cfg = Settings("", "m", "http://x", 0, 1)
    with pytest.raises(ConfigError):
        svc.build_llm(cfg)
    assert "groq_api_key" not in repr(cfg)


def test_resposta_vazia_vira_erro():
    ag = agente([AIMessage(content="")])
    with pytest.raises(ExternalServiceError, match="vazia"):
        svc.perguntar(ag, "oi", "thread-aaaa")
