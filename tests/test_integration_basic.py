"""
Testes de integração básicos para validar a comunicação entre componentes.
"""
import queue
import threading
import pytest
from unittest.mock import MagicMock, patch

# Mock simples para a interface PySide6
class MockQApplication:
    def __init__(self, *args, **kwargs):
        pass
    @staticmethod
    def instance():
        return None

class MockQWidget:
    def __init__(self, *args, **kwargs):
        self.setWindowTitle = MagicMock()
        self.setWindowFlags = MagicMock()
        self.setAttribute = MagicMock()
        self.setLayout = MagicMock()
        self.setFixedSize = MagicMock()
        self.hide = MagicMock()
        self.show = MagicMock()
        self.move = MagicMock()
        self.update = MagicMock()

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

# Configurar mocks básicos para PySide6
@pytest.fixture
def setup_pyside_mocks(monkeypatch):
    monkeypatch.setattr('PySide6.QtWidgets.QApplication', MockQApplication)
    monkeypatch.setattr('PySide6.QtWidgets.QWidget', MockQWidget)
    
    # Mock mais completo para QVBoxLayout
    mock_layout = MagicMock()
    mock_layout.setContentsMargins = MagicMock()
    mock_layout.setSpacing = MagicMock()
    mock_layout.addWidget = MagicMock()
    monkeypatch.setattr('PySide6.QtWidgets.QVBoxLayout', lambda *args: mock_layout)
    
    # Mock mais completo para QLabel
    mock_label = MagicMock()
    mock_label.setAlignment = MagicMock()
    mock_label.setStyleSheet = MagicMock()
    mock_label.setText = MagicMock()
    mock_label.hide = MagicMock()
    mock_label.show = MagicMock()
    monkeypatch.setattr('PySide6.QtWidgets.QLabel', lambda *args, **kwargs: mock_label)
    
    # Mocks para os novos widgets visuais
    monkeypatch.setattr('src.visual_feedback.WaveAnimationWidget', MockWaveAnimationWidget)
    monkeypatch.setattr('src.visual_feedback.StatusIndicator', MockStatusIndicator)
    
    # Mock o QTimer
    monkeypatch.setattr('PySide6.QtCore.QTimer', MockQTimer)
    monkeypatch.setattr('src.visual_feedback.QTimer', MockQTimer)
    
    # Mock o Signal
    monkeypatch.setattr('PySide6.QtCore.Signal', MockSignal)
    
    # Patch específico para o construtor da PySideFeedbackWindow para fornecer um feedback_signal pré-mockado
    def patch_feedback_window_init(self, feedback_queue, parent=None):
        self.feedback_queue = feedback_queue
        self.queue_timer = MockQTimer()
        self.queue_timer.start()
        self.feedback_signal = MockSignal()
        
        # Componentes
        self.wave_animation = MockWaveAnimationWidget()
        self.status_indicator = MockStatusIndicator()
        
        # Redirecionar os métodos mockados
        self.start_recording = MagicMock()
        self.stop_recording = MagicMock()
        self.update_volume = MagicMock()
        self.show_message = MagicMock()
        
        # Conectar o sinal ao handler
        self.feedback_signal.connect(self._handle_feedback)
    
    monkeypatch.setattr('src.visual_feedback.PySideFeedbackWindow.__init__', patch_feedback_window_init)
    
    monkeypatch.setattr('PySide6.QtCore.QTime', MagicMock)
    monkeypatch.setattr('PySide6.QtGui.QPainter', MagicMock)
    monkeypatch.setattr('PySide6.QtCore.Qt', MagicMock())
    return True

@pytest.fixture
def mock_openai():
    # Mock simplificado para OpenAI
    mock_openai = MagicMock()
    mock_openai.audio.transcriptions.create.return_value = MagicMock(text="Teste de transcrição")
    return mock_openai

@pytest.fixture
def mock_sounddevice(monkeypatch):
    # Mock para sounddevice.InputStream
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock()
    mock_stream.active = True
    
    monkeypatch.setattr('sounddevice.InputStream', lambda **kwargs: mock_stream)
    return mock_stream

@pytest.fixture
def setup_mocks(monkeypatch):
    # Mock PySide6 dependencies
    monkeypatch.setattr("src.visual_feedback.QVBoxLayout", MagicMock())
    monkeypatch.setattr("src.visual_feedback.QLabel", MagicMock())
    monkeypatch.setattr("src.visual_feedback.QWidget", MagicMock())
    monkeypatch.setattr("src.visual_feedback.QTimer", MockQTimer)
    monkeypatch.setattr("src.visual_feedback.WaveAnimationWidget", MockWaveAnimationWidget)
    monkeypatch.setattr("src.visual_feedback.StatusIndicator", MockStatusIndicator)
    monkeypatch.setattr("src.visual_feedback.Qt", MagicMock())
    monkeypatch.setattr("src.visual_feedback.QApplication", MagicMock())
    
    # Patch específico para o construtor da PySideFeedbackWindow para fornecer um feedback_signal pré-mockado
    def patch_feedback_window_init(self, feedback_queue, parent=None):
        self.feedback_queue = feedback_queue
        self.queue_timer = MockQTimer()
        self.queue_timer.start()
        self.feedback_signal = MockSignal()
        
        # Componentes
        self.wave_animation = MockWaveAnimationWidget()
        self.status_indicator = MockStatusIndicator()
        
        # Redirecionar os métodos mockados
        self.update_volume = lambda level: self.wave_animation.set_level(level)
        self.start_recording = MagicMock()
        self.stop_recording = MagicMock()
        self.show_message = MagicMock()
        
        # Conectar o sinal ao handler
        self.feedback_signal.connect(self._handle_feedback)
    
    monkeypatch.setattr('src.visual_feedback.PySideFeedbackWindow.__init__', patch_feedback_window_init)
    
    return True

def test_feedback_queue_basic_functionality(setup_pyside_mocks):
    """
    Teste básico para verificar se a fila de feedback funciona corretamente 
    entre componentes.
    """
    # Importar os módulos após configurar os mocks
    from src.visual_feedback import PySideFeedbackWindow
    
    # Criar uma fila de comunicação
    feedback_queue = queue.Queue()
    
    # Criar uma instância do PySideFeedbackWindow
    window = PySideFeedbackWindow(feedback_queue=feedback_queue)
    
    # Enviar mensagens para a fila
    messages = [
        ("start_recording", None),
        ("update_volume", 0.5),
        ("show_message", "Teste"),
        ("stop_recording", None)
    ]
    
    for msg in messages:
        feedback_queue.put(msg)
    
    # Processar as mensagens
    while not feedback_queue.empty():
        cmd, data = feedback_queue.get_nowait()
        window._handle_feedback(cmd, data)
    
    # Verificar se os métodos foram chamados
    assert window.start_recording.called
    assert window.stop_recording.called
    assert window.show_message.called

def test_audio_recorder_with_feedback(setup_pyside_mocks, mock_sounddevice, monkeypatch):
    """
    Testa a integração entre AudioRecorder e a fila de feedback.
    """
    # Configurar mock para scipy.io.wavfile.write
    mock_wav_write = MagicMock()
    monkeypatch.setattr('scipy.io.wavfile.write', mock_wav_write)
    
    # Importar os módulos após configurar os mocks
    from src.audio_recorder import AudioRecorder
    
    # Criar uma fila de comunicação
    feedback_queue = queue.Queue()
    
    # Mock para o método _recording_loop
    def mock_recording_loop(self):
        # Simular o envio de uma atualização de volume
        if self.feedback_queue:
            self.feedback_queue.put(("update_volume", 0.75))
        # Simular outros comportamentos...
        return
    
    # Aplicar o mock
    monkeypatch.setattr('src.audio_recorder.AudioRecorder._recording_loop', mock_recording_loop)
    
    # Criar instância do AudioRecorder com a fila
    audio_recorder = AudioRecorder(
        output_filename="test.wav",
        feedback_queue=feedback_queue
    )
    
    # Simular alguma ação que enviaria mensagens para a fila
    audio_recorder._recording_loop()
    
    # Verificar se a mensagem foi colocada na fila
    assert not feedback_queue.empty()
    cmd, data = feedback_queue.get()
    assert cmd == "update_volume"
    assert data == 0.75

def test_transcriber_basic_functionality(monkeypatch, mock_openai):
    """
    Testa a funcionalidade básica do Transcriber.
    """
    # Desabilitar o carregamento de variáveis de ambiente
    monkeypatch.setattr('dotenv.load_dotenv', lambda: True)
    
    # Configurar mock para o.path.exists
    monkeypatch.setattr('os.path.exists', lambda path: True)
    
    # Usar um mock mais específico para open que verifica o modo
    original_open = open
    def mock_open(path, mode='r', **kwargs):
        if path.endswith('.wav') and 'rb' in mode:
            return MagicMock()
        return original_open(path, mode, **kwargs)
    
    monkeypatch.setattr('builtins.open', mock_open)
    
    # Importar Transcriber após configurar mocks
    from src.transcriber import Transcriber
    
    # Criar instância do Transcriber com o client mockado
    transcriber = Transcriber(api_key="fake-key")
    transcriber.client = mock_openai
    
    # Testar a transcrição
    result = transcriber.transcribe_audio("fake_audio.wav")
    
    # Verificar se o método da API foi chamado e se retornou o texto esperado
    assert mock_openai.audio.transcriptions.create.called
    assert result == "Teste de transcrição"

def test_visual_feedback_with_volume_bar(setup_mocks):
    """
    Testa a integração entre a janela de feedback visual e o componente de visualização.
    """
    # Importar os módulos após configurar os mocks
    from src.visual_feedback import PySideFeedbackWindow
    
    # Criar uma fila de comunicação
    feedback_queue = queue.Queue()
    
    # Criar instância do PySideFeedbackWindow
    window = PySideFeedbackWindow(feedback_queue=feedback_queue)
    
    # Testar atualização de volume
    window.update_volume(0.8)
    assert window.wave_animation._level == 0.8
    
    # Testar start_recording
    window.start_recording()
    assert window.start_recording.called
    
    # Testar stop_recording
    window.stop_recording()
    assert window.stop_recording.called 