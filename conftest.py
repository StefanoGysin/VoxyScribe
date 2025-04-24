import sys
import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Classes mocadas para OpenAI que serão usadas automaticamente nos testes
class MockAudioResponse:
    """Mock para resposta de transcrição de áudio"""
    def __init__(self, text="Isso é um teste de transcrição."):
        self.text = text

# Mock global para o método transcribe_audio
@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    """Patch global para a biblioteca OpenAI em todos os testes."""
    # Mock para criar_transcrição que retorna uma resposta fixa
    mock_create = MagicMock(return_value=MockAudioResponse())
    
    # Mock para o objeto transcriptions
    mock_transcriptions = MagicMock()
    mock_transcriptions.create = mock_create
    
    # Mock para o objeto audio
    mock_audio = MagicMock()
    mock_audio.transcriptions = mock_transcriptions
    
    # Mock para a classe OpenAI
    mock_openai = MagicMock()
    mock_openai.return_value.audio = mock_audio
    
    # Definir o mock para a classe OpenAI
    monkeypatch.setattr('openai.OpenAI', mock_openai)
    
    # Também mock para os erros específicos da OpenAI
    class MockAuthenticationError(Exception):
        """Mock para OpenAI AuthenticationError"""
        pass
    
    class MockRateLimitError(Exception):
        """Mock para OpenAI RateLimitError"""
        pass
    
    class MockAPIError(Exception):
        """Mock para OpenAI APIError"""
        pass
    
    monkeypatch.setattr('openai.AuthenticationError', MockAuthenticationError)
    monkeypatch.setattr('openai.RateLimitError', MockRateLimitError)
    monkeypatch.setattr('openai.APIError', MockAPIError)
    
    return {
        'client': mock_openai,
        'create': mock_create,
        'AuthenticationError': MockAuthenticationError,
        'RateLimitError': MockRateLimitError,
        'APIError': MockAPIError
    } 