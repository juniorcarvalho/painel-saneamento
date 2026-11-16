"""Configuração compartilhada sem dependências de inferência."""
import os
from pathlib import Path

MODELO = 'Qwen/Qwen3-0.6B'
REVISAO = 'c1899de289a04d12100db370d81485cdf75e47ca'
PADRAO_PATH = Path(__file__).resolve().parents[1] / 'models/qwen3-0.6b'

def opcao(nome, padrao, minimo, maximo):
    valor = int(os.getenv(nome, str(padrao)))
    if not minimo <= valor <= maximo:
        raise ValueError(f'{nome} deve estar entre {minimo} e {maximo}.')
    return valor

