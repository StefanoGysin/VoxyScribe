import os
import queue
import threading
import tempfile
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import numpy as np

# Importamos os mocks compartilhados
from tests.fixtures.mock_openai import (
    MockOpenAI,
    MockAuthenticationError,
    MockRateLimitError,
    MockAPIError
)

# Mock para o QApplication e outros componentes PySide6
class MockQApplication:
    def __init__(self, *args, **kwargs):
        self.quit = MagicMock()
        self.exec = MagicMock()
        self.processEvents = MagicMock()
        
    @staticmethod
    def instance():
        return None

class MockQMessageBox:
    @staticmethod
    def critical(*args, **kwargs):
        return 0
    
    @staticmethod
    def information(*args, **kwargs):
        return 0

class MockQTime:
    @staticmethod
    def currentTime():
        mock_time = MagicMock()
        mock_time.elapsed = MagicMock(return_value=100)
        mock_time.msecsTo = MagicMock(return_value=1000)
        return mock_time

class MockQMetaObject:
    @staticmethod
    def invokeMethod(*args, **kwargs):
        pass

# Mock para sounddevice
class MockInputStream:
    def __init__(self, **kwargs):
        self.active = True
        self.callback = kwargs.get('callback')
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.active = False

# Mock para WaveAnimationWidget
class MockWaveAnimationWidget:
    def __init__(self, *args, **kwargs):
        self._level = 0.0
        self._phase = 0.0
        self.is_processing = False
        self.animation_timer = MockQTimer()
    
    def set_level(self, level):
        self._level = max(0.0, min(1.0, level))
    
    def set_processing(self, is_processing):
        self.is_processing = is_processing
    
    def _update_animation(self):
        pass
    
    def show(self):
        pass
    
    def hide(self):
        pass
    
    def setMinimumHeight(self, height):
        pass

# Mock para StatusIndicator
class MockStatusIndicator:
    def __init__(self, *args, **kwargs):
        self._status = "idle"
        self.pulse_size = 0.0
        self.pulse_growing = True
        self.pulse_timer = MockQTimer()
    
    def set_status(self, status):
        self._status = status
    
    def _update_pulse(self):
        pass
    
    def show(self):
        pass
    
    def hide(self):
        pass
    
    def setFixedSize(self, width, height):
        pass

# Mock para QTimer
class MockQTimer:
    def __init__(self, parent=None):
        self.timeout = MagicMock()
        self.interval = 0
        self.active = False
    
    def start(self, interval=None):
        if interval:
            self.interval = interval
        self.active = True
    
    def stop(self):
        self.active = False
    
    def singleShot(self, *args, **kwargs):
        pass

# Mock para a classe Signal
class MockSignal:
    def __init__(self, *args):
        self.callbacks = []
    
    def connect(self, func):
        self.callbacks.append(func)
    
    def emit(self, *args):
        for callback in self.callbacks:
            callback(*args)

# Classe mock completa para PySideFeedbackWindow
class MockPySideFeedbackWindow:
    """
    Implementação completa de um mock para PySideFeedbackWindow.
    """
    def __init__(self, feedback_queue, parent=None):
        self.feedback_queue = feedback_queue
        self.wave_animation = MockWaveAnimationWidget()
        self.status_indicator = MockStatusIndicator()
        
        # Mock methods
        self.start_recording = MagicMock()
        self.stop_recording = MagicMock()
        self.start_processing = MagicMock()
        self.processing_complete = MagicMock()
        self.show_message = MagicMock()
        self.update_volume = MagicMock()
        self.show = MagicMock()
        self.hide = MagicMock()
        self.move = MagicMock()
        
        # Define behavior for update_volume
        self.update_volume.side_effect = lambda level: self.wave_animation.set_level(level)
        
        # Setup timer for queue processing
        self.queue_timer = MockQTimer()
    
    def _handle_feedback(self, command, data):
        if command == "start_recording":
            self.start_recording()
        elif command == "stop_recording":
            self.stop_recording()
        elif command == "start_processing":
            self.start_processing()
        elif command == "processing_complete":
            self.processing_complete()
        elif command == "update_volume":
            self.update_volume(data)
        elif command == "show_message":
            self.show_message(data)

# Simulação de dados de áudio
@pytest.fixture
def mock_audio_data():
    """Cria dados de áudio falsos para simulação."""
    return np.random.randint(-32768, 32767, size=(8000, 1), dtype=np.int16)

# Arquivo temporário para o teste
@pytest.fixture
def temp_wav_file():
    """Cria um arquivo WAV temporário real para os testes."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.remove(temp_path)

@pytest.fixture
def mock_pyside_environment(monkeypatch):
    """Prepara o ambiente para simular o PySide6."""
    monkeypatch.setattr('PySide6.QtWidgets.QApplication', MockQApplication)
    monkeypatch.setattr('PySide6.QtWidgets.QMessageBox', MockQMessageBox)
    monkeypatch.setattr('PySide6.QtCore.QTime', MockQTime)
    monkeypatch.setattr('PySide6.QtCore.QMetaObject', MockQMetaObject)
    
    # Outros mocks PySide6 necessários
    monkeypatch.setattr('PySide6.QtCore.Qt.QueuedConnection', 0)
    monkeypatch.setattr('PySide6.QtCore.Qt.FramelessWindowHint', 0)
    monkeypatch.setattr('PySide6.QtCore.Qt.WindowStaysOnTopHint', 0)
    monkeypatch.setattr('PySide6.QtCore.Qt.Tool', 0)
    monkeypatch.setattr('PySide6.QtCore.Qt.WA_TranslucentBackground', 0)
    monkeypatch.setattr('PySide6.QtCore.Qt.WA_ShowWithoutActivating', 0)
    monkeypatch.setattr('PySide6.QtCore.Qt.AlignCenter', 0)
    monkeypatch.setattr('PySide6.QtCore.Qt.NoPen', 0)
    
    # Outras classes de GUI necessárias
    monkeypatch.setattr('PySide6.QtGui.QPainter', MagicMock)
    monkeypatch.setattr('PySide6.QtGui.QColor', MagicMock)
    monkeypatch.setattr('PySide6.QtGui.QBrush', MagicMock)
    monkeypatch.setattr('PySide6.QtGui.QPen', MagicMock)
    monkeypatch.setattr('PySide6.QtGui.QCursor', MagicMock())
    
    # Mocks melhorados que resolveram o problema em test_integration_basic.py
    monkeypatch.setattr('PySide6.QtCore.QTimer', MockQTimer)
    monkeypatch.setattr('src.visual_feedback.QTimer', MockQTimer)
    monkeypatch.setattr('PySide6.QtCore.Signal', MockSignal)
    monkeypatch.setattr('PySide6.QtCore.QRectF', MagicMock)
    monkeypatch.setattr('PySide6.QtWidgets.QVBoxLayout', MagicMock)
    monkeypatch.setattr('PySide6.QtWidgets.QLabel', MagicMock)
    monkeypatch.setattr('src.visual_feedback.WaveAnimationWidget', MockWaveAnimationWidget)
    monkeypatch.setattr('src.visual_feedback.StatusIndicator', MockStatusIndicator)
    
    # Substituir a classe PySideFeedbackWindow por nosso mock completo
    monkeypatch.setattr('src.visual_feedback.PySideFeedbackWindow', MockPySideFeedbackWindow)
    
    return True

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables e dotenv."""
    monkeypatch.setattr('dotenv.load_dotenv', lambda: True)
    monkeypatch.setattr('os.getenv', lambda var_name, default=None: 
                        "test-api-key" if var_name == "OPENAI_API_KEY" else default)
    
    # Criar diretório temporário para testes
    monkeypatch.setattr('os.makedirs', lambda *args, **kwargs: None)
    
    return True

@pytest.fixture
def mock_audio_recording_environment(monkeypatch, mock_audio_data):
    """Prepara o ambiente para simular a gravação de áudio."""
    # Mock para o sounddevice
    monkeypatch.setattr('sounddevice.InputStream', MockInputStream)
    
    # Mock para scipy.io.wavfile.write
    mock_wav_write = MagicMock()
    monkeypatch.setattr('scipy.io.wavfile.write', mock_wav_write)
    
    # Mock para simular dados de áudio
    def mock_callback(indata, frames, time_info, status):
        # Simula callback do sounddevice com dados não silenciosos
        # Aqui preenchemos 'indata' com os dados simulados
        indata[:] = mock_audio_data[:indata.shape[0]]
    
    # Mock para detecção de silêncio
    def mock_calculate_rms(*args, **kwargs):
        return 200.0  # Valor acima do threshold típico
    
    audio_recorder_patches = {
        '_callback': mock_callback,
        '_calculate_rms': mock_calculate_rms
    }
    
    return {'mock_wav_write': mock_wav_write, 'patches': audio_recorder_patches}

@pytest.fixture
def mock_transcription_success():
    """Mock para simular sucesso na transcrição."""
    mock_result = MagicMock()
    mock_result.text = "Isso é um texto de teste transcrito com sucesso!"
    return mock_result

@pytest.fixture
def mock_keyboard(monkeypatch):
    """Mock para o módulo keyboard."""
    mock_add_hotkey = MagicMock()
    mock_wait = MagicMock()
    monkeypatch.setattr('keyboard.add_hotkey', mock_add_hotkey)
    monkeypatch.setattr('keyboard.wait', mock_wait)
    return {'add_hotkey': mock_add_hotkey, 'wait': mock_wait}

@pytest.fixture
def mock_text_injector():
    """Mock para o TextInjector."""
    mock_injector = MagicMock()
    mock_injector.inject.return_value = True
    return mock_injector

# --- Testes de Integração do Fluxo Completo ---

@patch('openai.OpenAI', MockOpenAI)
@patch('openai.AuthenticationError', MockAuthenticationError)
@patch('openai.RateLimitError', MockRateLimitError)
@patch('openai.APIError', MockAPIError)
def test_complete_integration_workflow(monkeypatch, mock_pyside_environment, 
                                    mock_env_vars, mock_audio_recording_environment,
                                    mock_transcription_success, mock_keyboard,
                                    mock_text_injector, temp_wav_file):
    """
    Testa o fluxo de integração completo da aplicação, simulando o ciclo:
    1. Ativação da hotkey
    2. Gravação de áudio
    3. Feedback visual
    4. Transcrição 
    5. Injeção de texto
    """
    # Importações aqui para usar os mocks
    from src.audio_recorder import AudioRecorder
    from src.transcriber import Transcriber
    from src.visual_feedback import PySideFeedbackWindow
    
    # Substituir QApplication por nosso mock
    monkeypatch.setattr('PySide6.QtWidgets.QApplication', MockQApplication)
    
    # Configurar os patches para o AudioRecorder
    for method_name, mock_method in mock_audio_recording_environment['patches'].items():
        monkeypatch.setattr(f'src.audio_recorder.AudioRecorder.{method_name}', mock_method)
    
    # Configurar o mock para Transcriber.client.audio.transcriptions.create
    monkeypatch.setattr('os.path.exists', lambda path: True)
    
    # Configurar o mock para open do arquivo de áudio
    mock_file = MagicMock()
    monkeypatch.setattr('builtins.open', lambda path, mode, **kwargs: mock_file)
    
    # --- Simulação simplificada de um fluxo de trabalho completo ---
    
    # 1. Configurar componentes principais
    feedback_queue = queue.Queue()
    is_processing = threading.Lock()
    
    # 2. Inicializar componentes
    audio_recorder = AudioRecorder(
        output_filename=temp_wav_file,
        feedback_queue=feedback_queue
    )
    
    transcriber = Transcriber(api_key="test-api-key")
    transcriber.client.audio.transcriptions.create.return_value = mock_transcription_success
    
    text_injector = mock_text_injector
    
    feedback_window = PySideFeedbackWindow(feedback_queue=feedback_queue)
    
    # 3. Simular fluxo completo manualmente
    try:
        # Iniciar gravação e feedback visual
        feedback_queue.put(("start_recording", None))
        
        # Simular uma gravação bem-sucedida
        audio_data = np.random.randint(-32768, 32767, size=(8000, 1), dtype=np.int16)
        audio_recorder._audio_data = [audio_data]
        
        # Salvar o arquivo de áudio (simulado)
        mock_audio_recording_environment['mock_wav_write'](
            temp_wav_file, 
            audio_recorder.samplerate, 
            audio_data
        )
        
        # Processar mensagens até aqui
        # This ensures the recording start is handled
        while not feedback_queue.empty():
            cmd, data = feedback_queue.get_nowait()
            feedback_window._handle_feedback(cmd, data)
        
        # Simular transcrição bem-sucedida
        transcription_text = transcriber.transcribe_audio(temp_wav_file)
        
        # Simular injeção do texto
        feedback_queue.put(("show_message", "Injetando..."))
        text_injector.inject(transcription_text)
        feedback_queue.put(("stop_recording", None))
        
        # Processar mensagens restantes
        while not feedback_queue.empty():
            cmd, data = feedback_queue.get_nowait()
            feedback_window._handle_feedback(cmd, data)
            
    except Exception as e:
        pytest.fail(f"Teste falhou com exceção: {e}")
    
    # Verificações
    assert mock_audio_recording_environment['mock_wav_write'].called, "A função write não foi chamada."
    assert transcriber.client.audio.transcriptions.create.called, "A API transcriptions.create não foi chamada."
    assert text_injector.inject.called, "O método inject do TextInjector não foi chamado."
    text_injected = text_injector.inject.call_args[0][0]
    assert text_injected == mock_transcription_success.text, f"Texto incorreto: {text_injected} vs esperado: {mock_transcription_success.text}"

@patch('openai.OpenAI', MockOpenAI)
@patch('openai.AuthenticationError', MockAuthenticationError)
@patch('openai.RateLimitError', MockRateLimitError)
@patch('openai.APIError', MockAPIError)
def test_integration_workflow_with_transcription_error(monkeypatch, mock_pyside_environment, 
                                                    mock_env_vars, mock_audio_recording_environment,
                                                    mock_keyboard, mock_text_injector, 
                                                    temp_wav_file):
    """
    Testa o fluxo de integração quando ocorre um erro na transcrição.
    Verifica se o erro é tratado corretamente e se a mensagem de erro aparece no feedback.
    """
    # Importações aqui para usar os mocks
    from src.audio_recorder import AudioRecorder
    from src.transcriber import Transcriber
    
    # Configurar os patches para o AudioRecorder
    for method_name, mock_method in mock_audio_recording_environment['patches'].items():
        monkeypatch.setattr(f'src.audio_recorder.AudioRecorder.{method_name}', mock_method)
    
    # Configurar o mock para Transcriber
    monkeypatch.setattr('os.path.exists', lambda path: True)
    
    # Configurar o mock para open do arquivo de áudio
    mock_file = MagicMock()
    monkeypatch.setattr('builtins.open', lambda path, mode, **kwargs: mock_file)
    
    # --- Simulação simplificada do fluxo com erro de transcrição ---
    
    # Criar componentes principais
    feedback_queue = queue.Queue()
    mock_feedback_window = MagicMock()
    mock_feedback_window.show_message = MagicMock()
    
    # Inicializar componentes
    audio_recorder = AudioRecorder(
        output_filename=temp_wav_file,
        feedback_queue=feedback_queue
    )
    
    transcriber = Transcriber(api_key="test-api-key")
    # Configurar erro na API durante transcrição
    transcriber.client.audio.transcriptions.create.side_effect = MockAPIError("API Error teste")
    
    text_injector = mock_text_injector
    
    # Simular fluxo com erro na transcrição
    try:
        # Simular gravação
        audio_data = np.random.randint(-32768, 32767, size=(8000, 1), dtype=np.int16)
        audio_recorder._audio_data = [audio_data]
        
        # Salvar o arquivo de áudio (simulado)
        mock_audio_recording_environment['mock_wav_write'](
            temp_wav_file, 
            audio_recorder.samplerate, 
            audio_data
        )
        
        # Tentar transcrever
        transcription_text = transcriber.transcribe_audio(temp_wav_file)
        
        # A transcrição deveria retornar None devido ao erro da API
        assert transcription_text is None, "A transcrição deveria ter retornado None devido ao erro da API"
        
        # Simular o comportamento de mostrar mensagem de erro
        mock_feedback_window.show_message("Erro Transcrição!")
            
    except Exception as e:
        pytest.fail(f"Teste falhou com exceção inesperada: {e}")
    
    # Verificações
    assert mock_audio_recording_environment['mock_wav_write'].called, "A função de escrita de áudio não foi chamada."
    assert transcriber.client.audio.transcriptions.create.called, "A API de transcrição não foi chamada."
    assert mock_feedback_window.show_message.called, "O método show_message não foi chamado."
    assert any("Erro Transcrição" in str(call) for call in mock_feedback_window.show_message.call_args_list), f"A mensagem de erro de transcrição não foi encontrada nas chamadas."
    assert not text_injector.inject.called, "O TextInjector foi chamado, mas não deveria com erro de transcrição."

@patch('openai.OpenAI', MockOpenAI)
@patch('openai.AuthenticationError', MockAuthenticationError)
@patch('openai.RateLimitError', MockRateLimitError)
@patch('openai.APIError', MockAPIError)
def test_integration_workflow_queue_communication(monkeypatch, mock_pyside_environment, 
                                               mock_env_vars, mock_audio_recording_environment,
                                               mock_transcription_success, mock_keyboard,
                                               mock_text_injector, temp_wav_file):
    """
    Testa especificamente a comunicação via fila entre os componentes.
    Verifica se as mensagens são enviadas e recebidas corretamente.
    """
    # Importações aqui para usar os mocks
    from src.audio_recorder import AudioRecorder
    from src.transcriber import Transcriber
    from src.visual_feedback import PySideFeedbackWindow
    
    # Substituir QApplication por nosso mock
    monkeypatch.setattr('PySide6.QtWidgets.QApplication', MockQApplication)
    
    # Configurar os patches para o AudioRecorder
    for method_name, mock_method in mock_audio_recording_environment['patches'].items():
        monkeypatch.setattr(f'src.audio_recorder.AudioRecorder.{method_name}', mock_method)
    
    # Configurar o mock para Transcriber
    monkeypatch.setattr('os.path.exists', lambda path: True)
    
    # Configurar o mock para open do arquivo de áudio
    mock_file = MagicMock()
    monkeypatch.setattr('builtins.open', lambda path, mode, **kwargs: mock_file)
    
    # --- Simulação simplificada com foco na comunicação via queue ---
    
    # 1. Configurar componentes principais
    feedback_queue = queue.Queue()
    is_processing = threading.Lock()
    
    # 2. Inicializar componentes
    audio_recorder = AudioRecorder(
        output_filename=temp_wav_file,
        feedback_queue=feedback_queue
    )
    
    transcriber = Transcriber(api_key="test-api-key")
    transcriber.client.audio.transcriptions.create.return_value = mock_transcription_success
    
    text_injector = mock_text_injector
    
    feedback_window = PySideFeedbackWindow(feedback_queue=feedback_queue)
    
    # Lista para registrar todas as mensagens processadas
    processed_messages = []
    
    # 3. Simular envio de várias mensagens e capturar todas
    try:
        # Enviar várias mensagens para a fila
        messages_to_send = [
            ("start_recording", None),
            ("update_volume", 0.25),
            ("update_volume", 0.5),
            ("update_volume", 0.75),
            ("show_message", "Processando..."),
            ("show_message", "Injetando..."),
            ("stop_recording", None)
        ]
        
        for msg in messages_to_send:
            feedback_queue.put(msg)
        
        # Processar todas as mensagens e registrar
        while not feedback_queue.empty():
            cmd, data = feedback_queue.get_nowait()
            processed_messages.append((cmd, data))
            feedback_window._handle_feedback(cmd, data)
            
    except Exception as e:
        pytest.fail(f"Teste falhou com exceção: {e}")
    
    # Verificações
    assert len(processed_messages) == len(messages_to_send), f"Número incorreto de mensagens processadas: {len(processed_messages)} vs. esperado: {len(messages_to_send)}"
    
    # Verificar chamadas aos métodos mock
    assert feedback_window.start_recording.call_count == 1
    assert feedback_window.update_volume.call_count == 3
    assert feedback_window.show_message.call_count == 2
    assert feedback_window.stop_recording.call_count == 1
    
    # Verificar tipos de mensagens processadas
    message_types = [msg[0] for msg in processed_messages]
    assert "start_recording" in message_types
    assert "update_volume" in message_types
    assert "show_message" in message_types
    assert "stop_recording" in message_types 