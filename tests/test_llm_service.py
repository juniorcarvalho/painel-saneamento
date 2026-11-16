import pytest
import torch
from src.llm_service import ServicoResumoLocal, EntradaLonga, TempoExcedido, Ocupado

class Tokenizer:
    def apply_chat_template(self, messages, **kwargs):
        assert kwargs['enable_thinking'] is False
        return 'prompt'
    def __call__(self, prompt, **kwargs): return {'input_ids': torch.tensor([[1,2,3]])}
    def decode(self, tokens, **kwargs):
        assert tokens.tolist() == [4]
        return self.output
    output = 'Resumo válido'

class Model:
    def generate(self, **kwargs): return torch.tensor([[1,2,3,4]])

def test_inferencia_e_trava():
    s = ServicoResumoLocal()
    s.tokenizer, s.model = Tokenizer(), Model()
    assert s.resumir('texto') == 'Resumo válido'
    s.max_tokens = 2
    with pytest.raises(EntradaLonga): s.resumir('texto')
    assert not s.lock.locked()
    s.max_tokens = 2048
    s.tokenizer.output = ''
    with pytest.raises(ValueError): s.resumir('texto')
    assert not s.lock.locked()
    s.lock.acquire()
    with pytest.raises(Ocupado): s.resumir('texto')
    s.lock.release()
    s.timeout = -1
    with pytest.raises(TempoExcedido): s.resumir('texto')
    assert not s.lock.locked()


def test_prazo_cooperativo(monkeypatch):
    from src import llm_service

    agora = [100.0]
    monkeypatch.setattr(llm_service.time, 'monotonic', lambda: agora[0])
    s = ServicoResumoLocal()
    s.tokenizer = Tokenizer()

    class Cooperativo:
        def generate(self, **kwargs):
            criterio = kwargs['stopping_criteria']
            ids = kwargs['input_ids']
            assert not criterio(ids, None).all()
            agora[0] += s.timeout
            assert criterio(ids, None).all()
            return torch.tensor([[1, 2, 3, 4]])

    s.model = Cooperativo()
    with pytest.raises(TempoExcedido):
        s.resumir('texto')
    assert not s.lock.locked()


def test_concorrencia_mantem_trava_ate_terminar():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    iniciou, terminar = Event(), Event()
    s = ServicoResumoLocal()
    s.tokenizer = Tokenizer()

    class Lento:
        def generate(self, **kwargs):
            iniciou.set()
            assert terminar.wait(5)
            return torch.tensor([[1, 2, 3, 4]])

    s.model = Lento()
    with ThreadPoolExecutor(max_workers=1) as executor:
        trabalho = executor.submit(s.resumir, 'texto')
        try:
            assert iniciou.wait(5)
            with pytest.raises(Ocupado):
                s.resumir('outro texto')
            assert s.lock.locked()
            assert not trabalho.cancel()
            assert s.lock.locked()
        finally:
            terminar.set()
        assert trabalho.result(timeout=5) == 'Resumo válido'
    assert not s.lock.locked()
