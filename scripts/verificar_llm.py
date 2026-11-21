"""Verificação real separada dos testes unitários; bloqueia sockets externos."""
import argparse
import json
import resource
import socket
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
from src.llm_config import CATALOGO_MODELOS
from src.llm_service import ServicoResumoLocal

def bloquear(*args, **kwargs):
    raise RuntimeError('Rede bloqueada durante verificação offline')

def avaliar_modelo(modelo=None):
    socket.socket.connect = bloquear
    torch.manual_seed(42)
    torch.set_num_threads(4)
    inicio = time.monotonic()
    s = ServicoResumoLocal(modelo=modelo)
    s.carregar()
    print(json.dumps({'modelo': s.modelo, 'revisao': s.revisao, 'carregamento_s': time.monotonic() - inicio, 'rss_carregamento_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}), flush=True)
    for entrada in json.loads(Path('tests/fixtures/textos_saneamento.json').read_text()):
        inicio = time.monotonic()
        try:
            resultado = s.resumir(entrada['texto'])
        except Exception as exc:
            resultado = f'{type(exc).__name__}: {exc}'
        print(json.dumps({'modelo': s.modelo, 'texto': entrada['texto'], 'resultado': resultado, 'latencia_s': time.monotonic() - inicio, 'rss_max_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}, ensure_ascii=False), flush=True)
    s.fechar()

def main():
    parser = argparse.ArgumentParser(description='Avalia modelos locais offline nas fixtures de saneamento.')
    parser.add_argument('--modelo', choices=list(CATALOGO_MODELOS), default=None)
    parser.add_argument('--comparar', action='store_true', help='Executa cada candidato em subprocesso isolado para medir RSS independente.')
    args = parser.parse_args()
    if args.comparar:
        for item in CATALOGO_MODELOS:
            subprocess.run([sys.executable, __file__, '--modelo', item], check=True)
    else:
        avaliar_modelo(args.modelo)

if __name__ == '__main__':
    main()
