"""Configuração compartilhada sem dependências de inferência."""
import os
from pathlib import Path

MODELO = 'Qwen/Qwen3-0.6B'
REVISAO = 'c1899de289a04d12100db370d81485cdf75e47ca'
PADRAO_PATH = Path(__file__).resolve().parents[1] / 'models/qwen3-0.6b'
CANDIDATO_MODELO = 'Qwen/Qwen2.5-1.5B-Instruct'
CANDIDATO_REVISAO = '989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
CANDIDATO_PATH = Path(__file__).resolve().parents[1] / 'models/qwen2.5-1.5b-instruct'
CATALOGO_MODELOS = {
    MODELO: (REVISAO, PADRAO_PATH),
    CANDIDATO_MODELO: (CANDIDATO_REVISAO, CANDIDATO_PATH),
}

def resolver_modelo(modelo=None):
    identificador = modelo or os.getenv('SANEAMENTO_LLM_MODELO', MODELO)
    if identificador not in CATALOGO_MODELOS:
        raise ValueError(f'Modelo não suportado: {identificador}.')
    revisao, padrao_path = CATALOGO_MODELOS[identificador]
    path = Path(os.getenv('SANEAMENTO_LLM_PATH', str(padrao_path)))
    return identificador, revisao, path

def opcao(nome, padrao, minimo, maximo):
    valor = int(os.getenv(nome, str(padrao)))
    if not minimo <= valor <= maximo:
        raise ValueError(f'{nome} deve estar entre {minimo} e {maximo}.')
    return valor

