"""
Mock implementations for OpenAI APIs and classes
"""
from unittest.mock import MagicMock

class MockAuthenticationError(Exception):
    """Mock for OpenAI AuthenticationError"""
    pass

class MockRateLimitError(Exception):
    """Mock for OpenAI RateLimitError"""
    pass

class MockAPIError(Exception):
    """Mock for OpenAI APIError"""
    pass

class MockAudioResponse:
    """Mock for audio transcription response"""
    def __init__(self, text="Isso é um teste de transcrição."):
        self.text = text

class MockTranscriptionCreate(MagicMock):
    """Mock para o método create de transcriptions"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.return_value = MockAudioResponse()

class MockTranscriptions(MagicMock):
    """Mock para o objeto transcriptions"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create = MockTranscriptionCreate()

class MockAudio(MagicMock):
    """Mock para o objeto audio"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transcriptions = MockTranscriptions()

class MockOpenAI:
    """Mock for the main OpenAI class"""
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.audio = MockAudio()
        
    def __call__(self, *args, **kwargs):
        # Permite que a classe seja usada como um método (para ser compatível com decoradores @patch)
        return self
        
    def set_success_response(self, text="Isso é um teste de transcrição."):
        """Configure a successful response text"""
        self.audio.transcriptions.create.return_value = MockAudioResponse(text)
        
    def set_error_response(self, error_type="api_error"):
        """Configure an error response"""
        if error_type == "authentication":
            self.audio.transcriptions.create.side_effect = MockAuthenticationError("Invalid API key")
        elif error_type == "rate_limit":
            self.audio.transcriptions.create.side_effect = MockRateLimitError("Rate limit exceeded")
        else:
            self.audio.transcriptions.create.side_effect = MockAPIError("General API error") 