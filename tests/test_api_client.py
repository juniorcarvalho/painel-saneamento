import pytest
from src import api_client as client

def test_contratos(monkeypatch):
    monkeypatch.setattr(client, '_requisicao', lambda *a, **k: {'resultado': 'resumo'})
    with pytest.raises(client.APIError): client.consultar_dados()
    with pytest.raises(client.APIError): client.processar_texto({})

def test_timeout(monkeypatch):
    def timeout(*a, **k): raise TimeoutError()
    monkeypatch.setattr(client, 'urlopen', timeout)
    with pytest.raises(client.APIError, match='ainda estar terminando'):
        client.processar_texto({})


def test_sucesso_caminhos_timeouts_e_proveniencia(monkeypatch):
    import io
    import json

    fonte = {'titulo': 'Teste', 'origem': 'Documento local'}
    entrada = {'texto': 'Texto de exemplo para resumir.', 'fonte': fonte}
    resumo = {'texto_processado': entrada['texto'], 'tipo_analise': 'resumo', 'resultado': 'Resumo.', 'modelo': 'teste', 'revisao': 'abc', 'fonte': fonte, 'tempo_processamento_ms': 10}
    chamadas = []

    def abrir(request, timeout):
        chamadas.append((request, timeout))
        payload = resumo if request.full_url.endswith('/processar_texto') else {'fontes': [], 'registros': []}
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setenv('SANEAMENTO_API_URL', 'http://localhost:8123/')
    monkeypatch.setenv('SANEAMENTO_LLM_TIMEOUT_SECONDS', '60')
    monkeypatch.setattr(client, 'urlopen', abrir)
    resposta = client.processar_texto(entrada)
    assert resposta.fonte.model_dump() == fonte
    assert json.loads(chamadas[0][0].data) == entrada
    assert chamadas[0][0].full_url == 'http://localhost:8123/processar_texto'
    assert chamadas[0][1] == 75
    client.consultar_dados(ano=2021)
    client.enviar_dados([])
    assert chamadas[1][0].full_url == 'http://localhost:8123/dados?ano=2021'
    assert chamadas[2][0].method == 'POST'
    assert chamadas[1][1] == chamadas[2][1] == 15


@pytest.mark.parametrize('status,detail', [
    (422, [{'loc': ['body', 'fonte', 'titulo'], 'msg': 'Field required'}]),
    (503, 'Modelo ocupado'),
    (504, 'Prazo excedido'),
    (500, 'Falha interna'),
])
def test_erros_http_estruturados(monkeypatch, status, detail):
    import io
    import json
    from urllib.error import HTTPError

    chamadas = []

    def falhar(request, timeout):
        chamadas.append(request)
        raise HTTPError(request.full_url, status, 'erro', {}, io.BytesIO(json.dumps({'detail': detail}).encode()))

    monkeypatch.setattr(client, 'urlopen', falhar)
    with pytest.raises(client.APIError, match=f'HTTP {status}') as erro:
        client.processar_texto({})
    assert str(detail) in str(erro.value)
    assert len(chamadas) == 1
