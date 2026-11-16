from streamlit.testing.v1 import AppTest
from src.llm_schemas import TextoResposta
from src import api_client

def test_formulario_e_rerun(monkeypatch):
    chamadas = []
    def resumir(entrada):
        chamadas.append(entrada)
        return TextoResposta(texto_processado=entrada['texto'], resultado='Resumo de teste.', modelo='falso', revisao='teste', fonte=entrada['fonte'], tempo_processamento_ms=1)
    monkeypatch.setattr(api_client, 'processar_texto', resumir)
    app = AppTest.from_file('pages/resumo.py').run()
    app.text_area[0].set_value('Texto de saneamento fornecido pelo usuário para teste do formulário.')
    app.text_input[0].set_value('Documento')
    app.text_input[1].set_value('Arquivo local')
    app.button[0].click().run()
    assert not app.exception
    assert len(chamadas) == 1
    assert chamadas[0]['fonte'] == {'titulo': 'Documento', 'origem': 'Arquivo local'}
    app.run()
    assert len(chamadas) == 1
    assert app.text[0].value == 'Resumo de teste.'


def test_erros_interface(monkeypatch):
    for mensagem in ['API retornou HTTP 503: Modelo indisponível.', 'API indisponível. Verifique se o serviço FastAPI está em execução.']:
        chamadas = []

        def falhar(entrada):
            chamadas.append(entrada)
            raise api_client.APIError(mensagem)

        monkeypatch.setattr(api_client, 'processar_texto', falhar)
        app = AppTest.from_file('pages/resumo.py').run()
        app.button[0].click().run()
        assert not app.exception
        assert app.error[0].value == mensagem
        app.run()
        assert len(chamadas) == 1
