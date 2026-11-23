import json
from functools import partial

import pytest
import torch
from fastapi.testclient import TestClient
from src import api
from src.api_data_access import adicionar_dados_complementares, carregar_dados_complementares
from src.data_access import carregar_dados_processados
from src.llm_service import Ocupado, ServicoResumoLocal, TempoExcedido, EntradaLonga

ENTRADA = {'texto': 'Em 2021, a cidade ampliou a rede de água para 200 famílias.', 'fonte': {'titulo': 'Exemplo', 'origem': 'Documento sintético local'}}

class Falso:
    modelo = 'teste'
    revisao = 'teste'
    def carregar(self): pass
    def fechar(self): pass
    def resumir(self, texto): return 'Em 2021, a rede foi ampliada para 200 famílias.'

@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(api, 'ServicoResumoLocal', Falso)
    with TestClient(api.app) as client:
        yield client

def test_contrato(cliente):
    r = cliente.post('/processar_texto', json=ENTRADA)
    assert r.status_code == 200
    assert r.json()['fonte'] == ENTRADA['fonte']
    assert r.json()['tempo_processamento_ms'] >= 0
    assert cliente.post('/processar_texto', json={**ENTRADA, 'texto': 'curto'}).status_code == 422
    assert cliente.post('/processar_texto', json={**ENTRADA, 'extra': True}).status_code == 422

@pytest.mark.parametrize('erro,status', [(Ocupado('ocupado'),503),(TempoExcedido('prazo'),504),(EntradaLonga('limite'),422),(ValueError('interno'),500)])
def test_erros(cliente, monkeypatch, erro, status):
    def falhar(self, texto): raise erro
    monkeypatch.setattr(Falso, 'resumir', falhar)
    assert cliente.post('/processar_texto', json=ENTRADA).status_code == status

def test_carga_falha(monkeypatch):
    def falhar(self): raise FileNotFoundError()
    monkeypatch.setattr(Falso, 'carregar', falhar)
    monkeypatch.setattr(api, 'ServicoResumoLocal', Falso)
    monkeypatch.setattr(api, 'carregar_dados_processados', lambda: {'fontes': [], 'registros': []})
    monkeypatch.setattr(api, 'carregar_dados_complementares', lambda: [])
    with TestClient(api.app) as client:
        assert client.post('/processar_texto', json=ENTRADA).status_code == 503
        assert client.get('/dados').status_code == 200

def test_post_dados_sem_llm(cliente, monkeypatch):
    api.app.state.llm = None
    monkeypatch.setattr(api, 'adicionar_dados_complementares', lambda registros: [])
    registro = {'Ano': 2021, 'UF': 'São Paulo', 'Sigla': 'SP', 'Regiao': 'Sudeste', 'Atendimento_Agua': 90.0, 'Atendimento_Esgoto': 80.0, 'Pop_Sem_Saneamento_Milhoes': 1.0}
    assert cliente.post('/dados', json=[registro]).status_code == 201


@pytest.mark.parametrize('erro,status', [
    (MemoryError('sem memória'), 503),
    (torch.OutOfMemoryError('sem memória'), 503),
    (RuntimeError("DefaultCPUAllocator: can't allocate memory: Error code 12"), 503),
    (RuntimeError('tensor inválido'), 500),
])
def test_memoria_servico_real(cliente, erro, status):
    class Tokenizer:
        def apply_chat_template(self, *args, **kwargs):
            return 'prompt'

        def __call__(self, *args, **kwargs):
            return {'input_ids': torch.tensor([[1]])}

    class Modelo:
        def generate(self, **kwargs):
            raise erro

    servico = ServicoResumoLocal()
    servico.tokenizer, servico.model = Tokenizer(), Modelo()
    api.app.state.llm = servico
    resposta = cliente.post('/processar_texto', json=ENTRADA)
    assert resposta.status_code == status
    if status == 503:
        assert 'Memória insuficiente' in resposta.json()['detail']
    assert not servico.lock.locked()


def test_persistencia_dados_com_falha_llm(monkeypatch, tmp_path):
    oficial, complementar = tmp_path / 'oficial.json', tmp_path / 'complementar.json'
    original = json.dumps({'fontes': ['Fixture'], 'registros': []})
    oficial.write_text(original)
    monkeypatch.setattr(api, 'carregar_dados_processados', partial(carregar_dados_processados, path=oficial))
    monkeypatch.setattr(api, 'carregar_dados_complementares', partial(carregar_dados_complementares, path=complementar))
    monkeypatch.setattr(api, 'adicionar_dados_complementares', partial(adicionar_dados_complementares, path=complementar))

    def falhar(self):
        raise FileNotFoundError('Pesos ausentes')

    monkeypatch.setattr(Falso, 'carregar', falhar)
    monkeypatch.setattr(api, 'ServicoResumoLocal', Falso)
    registro = {'Ano': 2021, 'UF': 'São Paulo', 'Sigla': 'SP', 'Regiao': 'Sudeste', 'Atendimento_Agua': 90.0, 'Atendimento_Esgoto': 80.0, 'Pop_Sem_Saneamento_Milhoes': 1.0}
    with TestClient(api.app) as client:
        assert client.post('/processar_texto', json=ENTRADA).status_code == 503
        post = client.post('/dados', json=[registro])
        assert post.status_code == 201
        get = client.get('/dados')
        assert get.status_code == 200
        assert get.json()['registros'] == post.json()['registros']
    assert oficial.read_text() == original
    assert json.loads(complementar.read_text())['registros'][0]['Sigla'] == 'SP'
