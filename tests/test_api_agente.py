import pytest
from fastapi.testclient import TestClient

from src import api
from src.agent_config import ConfigError, ExternalServiceError, LimiteExcedido
from src.agent_service import Passo, RespostaAgente

ENTRADA = {"mensagem": "Quais UFs priorizar em 2021?", "thread_id": "thread-12345678"}


class FakeSaver:
    def __init__(self):
        self.apagados = []

    def delete_thread(self, thread_id):
        self.apagados.append(thread_id)


class FakeAgente:
    checkpointer = FakeSaver()


class Falso:
    modelo = "teste"
    revisao = "teste"

    def carregar(self): pass
    def fechar(self): pass


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(api, "ServicoResumoLocal", Falso)
    monkeypatch.setattr(api, "build_agent", lambda: FakeAgente())
    monkeypatch.setattr(api, "perguntar", lambda ag, m, t: RespostaAgente("Priorize o AC.", [Passo("ranking_prioridade", {"limite": 5}, "{}")]))
    FakeAgente.checkpointer = FakeSaver()
    with TestClient(api.app) as client:
        yield client


def test_contrato(cliente):
    r = cliente.post("/agente", json=ENTRADA)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["resposta"] == "Priorize o AC."
    assert corpo["passos"] == [{"ferramenta": "ranking_prioridade", "entrada": {"limite": 5}, "saida": "{}"}]
    assert corpo["thread_id"] == ENTRADA["thread_id"] and corpo["tempo_processamento_ms"] >= 0


@pytest.mark.parametrize("corpo", [
    {**ENTRADA, "mensagem": " "},
    {**ENTRADA, "thread_id": "inválido!!"},
    {**ENTRADA, "thread_id": "curto"},
    {**ENTRADA, "extra": 1},
])
def test_422(cliente, corpo):
    assert cliente.post("/agente", json=corpo).status_code == 422


def test_503_sem_agente(monkeypatch):
    monkeypatch.setattr(api, "ServicoResumoLocal", Falso)

    def sem_chave():
        raise ConfigError("sem chave")

    monkeypatch.setattr(api, "build_agent", sem_chave)
    with TestClient(api.app) as client:
        r = client.post("/agente", json=ENTRADA)
        assert r.status_code == 503 and "GROQ_API_KEY" in r.json()["detail"]
        assert client.delete("/agente/thread-12345678").status_code == 503


@pytest.mark.parametrize("erro,status", [(ExternalServiceError("x"), 502), (LimiteExcedido("x"), 429), (RuntimeError("x"), 500)])
def test_erros(cliente, monkeypatch, erro, status):
    def falhar(*a):
        raise erro

    monkeypatch.setattr(api, "perguntar", falhar)
    r = cliente.post("/agente", json=ENTRADA)
    assert r.status_code == status
    if status == 500:
        assert "thread_id sugerido" in r.json()["detail"]


def test_delete_limpa_thread(cliente):
    assert cliente.delete("/agente/thread-12345678").status_code == 204
    assert FakeAgente.checkpointer.apagados == ["thread-12345678"]
    assert cliente.delete("/agente/curto").status_code == 422
