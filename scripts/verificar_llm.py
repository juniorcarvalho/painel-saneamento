"""Verificação real separada dos testes unitários; bloqueia sockets externos."""
import json
import resource
import socket
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
from src.llm_service import ServicoResumoLocal

def bloquear(*args, **kwargs):
    raise RuntimeError('Rede bloqueada durante verificação offline')

socket.socket.connect = bloquear
torch.manual_seed(42)
torch.set_num_threads(4)
inicio = time.monotonic()
s = ServicoResumoLocal()
s.carregar()
print(json.dumps({'carregamento_s': time.monotonic()-inicio}), flush=True)
for entrada in json.loads(Path('tests/fixtures/textos_saneamento.json').read_text()):
    inicio = time.monotonic()
    try:
        resultado = s.resumir(entrada['texto'])
    except Exception as exc:
        resultado = f'{type(exc).__name__}: {exc}'
    print(json.dumps({'texto':entrada['texto'], 'resultado':resultado, 'latencia_s':time.monotonic()-inicio, 'rss_max_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}, ensure_ascii=False), flush=True)
s.fechar()
