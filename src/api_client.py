"""Cliente HTTP do Streamlit com configuração e tratamento de falhas centralizados."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.agent_schemas import RespostaAgenteSaida
from src.llm_schemas import TextoResposta
from src.llm_config import opcao


class APIError(RuntimeError):
    """Falha de conexão, contrato ou validação na API."""

    def __init__(self, mensagem, status=None, timeout=False):
        super().__init__(mensagem)
        self.status = status
        self.timeout = timeout


def _requisicao(method: str, registros=None, filtros=None, caminho="/dados", timeout=15):
    base = os.getenv("SANEAMENTO_API_URL", "http://127.0.0.1:8000").rstrip("/")
    url = f"{base}{caminho}"
    if filtros:
        url += "?" + urlencode({key: value for key, value in filtros.items() if value is not None})
    body = None if registros is None else json.dumps(registros, allow_nan=False).encode("utf-8")
    try:
        request = Request(url, data=body, method=method, headers={"Accept": "application/json", "Content-Type": "application/json"})
        with urlopen(request, timeout=timeout) as response:
            if getattr(response, "status", 200) == 204:
                return None
            payload = json.load(response)
        return payload
    except HTTPError as exc:
        try:
            erro = json.loads(exc.read())
            detalhe = erro.get("detail", "Erro sem detalhes.") if isinstance(erro, dict) else "Erro sem detalhes."
        except (ValueError, UnicodeError):
            detalhe = "Erro sem detalhes."
        raise APIError(f"API retornou HTTP {exc.code}: {detalhe}", status=exc.code) from exc
    except TimeoutError as exc:
        raise APIError("Tempo de transporte excedido. O processamento pode ainda estar terminando; não reenvie automaticamente.", timeout=True) from exc
    except (URLError, OSError) as exc:
        raise APIError("API indisponível. Verifique se o serviço FastAPI está em execução.") from exc
    except (ValueError, UnicodeError) as exc:
        raise APIError("A API retornou uma resposta inválida.") from exc


def consultar_dados(ano=None, regiao=None):
    return _validar_dados(_requisicao("GET", filtros={"ano": ano, "regiao": regiao}))


def enviar_dados(registros):
    return _validar_dados(_requisicao("POST", registros=registros))


def _validar_dados(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('registros'), list) or not isinstance(payload.get('fontes'), list):
        raise APIError('Resposta de dados fora do contrato.')
    return payload


def processar_texto(entrada):
    try:
        timeout = opcao('SANEAMENTO_LLM_TIMEOUT_SECONDS', 120, 1, 3600) + 15
        return TextoResposta.model_validate(_requisicao('POST', registros=entrada, caminho='/processar_texto', timeout=timeout))
    except ValueError as exc:
        raise APIError('Resposta ou configuração de resumo inválida.') from exc


def _timeout_agente():
    try:
        # pior caso do servidor: ~4 chamadas ao LLM, cada uma com 1 tentativa + 2 retentativas
        return float(os.getenv('HTTP_TIMEOUT', '30')) * 4 + 30
    except ValueError:
        return 150.0


def perguntar_agente(mensagem, thread_id):
    payload = _requisicao('POST', registros={'mensagem': mensagem, 'thread_id': thread_id}, caminho='/agente', timeout=_timeout_agente())
    try:
        return RespostaAgenteSaida.model_validate(payload)
    except ValueError as exc:
        raise APIError('Resposta do agente fora do contrato.') from exc


def limpar_conversa(thread_id):
    _requisicao('DELETE', caminho=f'/agente/{thread_id}', timeout=15)
