import queue
import logging
import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QApplication, 
                             QGraphicsOpacityEffect, QHBoxLayout)
from PySide6.QtCore import (Qt, QTimer, Signal, Slot, QElapsedTimer, QRectF, 
                          QPropertyAnimation, QEasingCurve, QSize, QPoint, Property)
from PySide6.QtGui import (QPainter, QColor, QBrush, QPen, QCursor, QFont, 
                         QFontMetrics, QPixmap, QRadialGradient, QLinearGradient,
                         QPainterPath)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constantes de Design ---
BRAND_COLOR = QColor(128, 100, 255)  # Cor principal - roxo suave
ACCENT_COLOR = QColor(120, 210, 255)  # Cor de destaque - azul claro
DARK_BG = QColor(30, 30, 38)  # Fundo escuro com tom levemente azulado
LIGHT_TEXT = QColor(240, 240, 255)  # Texto claro com tom suave
STATUS_LISTENING = QColor(100, 220, 120)  # Verde para gravação
STATUS_PROCESSING = QColor(245, 158, 66)  # Laranja para processamento
WINDOW_WIDTH = 220
WINDOW_HEIGHT = 150
BORDER_RADIUS = 12

# --- Wave Animation Widget ---
class WaveAnimationWidget(QWidget):
    """Widget animado que mostra ondas de áudio com efeito de pulso e reação ao volume."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0
        self._phase = 0.0
        self._processing_phase = 0.0
        self.is_processing = False
        self.setMinimumHeight(36)
        
        # Configurar timer de animação
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(16)  # ~60 FPS
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start()
        
        # Efeito de "respiração" suave
        self.pulse_effect = 0.0
        self.pulse_direction = 0.01

    def set_level(self, level: float):
        """Define o nível de volume (0.0 a 1.0) e atualiza a visualização."""
        self._level = max(0.0, min(1.0, level))
        self.update()

    def set_processing(self, is_processing: bool):
        """Alterna entre o modo de gravação e o modo de processamento."""
        self.is_processing = is_processing
        self.update()

    def _update_animation(self):
        """Atualiza os parâmetros de animação para criar movimento."""
        # Animação de fase para ondas em movimento
        self._phase += 0.05
        if self._phase > math.pi * 2:
            self._phase -= math.pi * 2
            
        # Animação circular para o modo de processamento
        if self.is_processing:
            self._processing_phase += 0.1
            if self._processing_phase > math.pi * 2:
                self._processing_phase -= math.pi * 2
                
        # Efeito de "respiração" suave
        self.pulse_effect += self.pulse_direction
        if self.pulse_effect > 1.0 or self.pulse_effect < 0.0:
            self.pulse_direction *= -1
            self.pulse_effect = max(0.0, min(1.0, self.pulse_effect))
        
        self.update()

    def paintEvent(self, event):
        """Renderiza a visualização animada das ondas de áudio."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # Fundo transparente
        painter.setPen(Qt.NoPen)
        
        if self.is_processing:
            self._draw_processing_animation(painter)
        else:
            self._draw_wave_animation(painter)

    def _draw_wave_animation(self, painter):
        """Desenha a animação de ondas de áudio durante a gravação."""
        width = self.width()
        height = self.height()
        
        # Número de barras
        num_bars = 24
        bar_width = width / (num_bars * 1.3)
        space_width = bar_width / 3
        
        # Criar gradiente para as barras
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(BRAND_COLOR.red(), BRAND_COLOR.green(), BRAND_COLOR.blue(), 230))
        gradient.setColorAt(1, QColor(ACCENT_COLOR.red(), ACCENT_COLOR.green(), ACCENT_COLOR.blue(), 180))
        
        # Criar efeito de "respiração" para as barras inativas
        base_level = 0.15 + (0.05 * self.pulse_effect)
        
        # Desenhar cada barra com efeito de onda
        for i in range(num_bars):
            # Calcular altura variável com base na posição, fase e nível de áudio
            normalized_pos = i / num_bars
            
            # Altura da onda: combina o padrão senoidal com o nível de áudio e o efeito de pulso
            wave_height = self._create_wave_pattern(normalized_pos, self._phase)
            
            # Aplicar o nível de áudio e garantir um mínimo para visual
            bar_height_percentage = base_level + wave_height * (0.2 + self._level * 0.8)
            bar_height = height * bar_height_percentage
            
            # Posição X da barra
            x = i * (bar_width + space_width)
            
            # Posição Y (a partir da parte inferior)
            y = height - bar_height
            
            # Desenhar a barra com gradiente
            painter.setBrush(QBrush(gradient))
            
            # Desenhar a barra com bordas arredondadas
            bar_rect = QRectF(x, y, bar_width, bar_height)
            painter.drawRoundedRect(bar_rect, 2, 2)

    def _draw_processing_animation(self, painter):
        """Desenha a animação de processamento circular."""
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2
        
        # Tamanho base do círculo
        radius = min(width, height) * 0.3
        
        # Gradiente para os pontos
        gradient = QRadialGradient(center_x, center_y, radius)
        gradient.setColorAt(0, STATUS_PROCESSING)
        gradient.setColorAt(1, QColor(STATUS_PROCESSING.red(), 
                                      STATUS_PROCESSING.green(), 
                                      STATUS_PROCESSING.blue(), 0))
        
        # Quantidade de pontos na animação circular
        num_dots = 8
        
        # Tamanho dos pontos
        dot_radius = radius * 0.20
        
        # Desenhar os pontos em círculo com opacidade variável
        for i in range(num_dots):
            # Calcular ângulo para distribuição circular
            angle = (i / num_dots) * math.pi * 2 + self._processing_phase
            
            # Coordenadas do ponto
            dot_x = center_x + math.cos(angle) * radius
            dot_y = center_y + math.sin(angle) * radius
            
            # Opacidade variável baseada na posição na sequência
            opacity = 0.3 + 0.7 * (((i / num_dots + 0.5) % 1.0) * 0.8)
            
            # Cor com opacidade variável
            dot_color = QColor(STATUS_PROCESSING.red(), 
                              STATUS_PROCESSING.green(), 
                              STATUS_PROCESSING.blue(), 
                              int(255 * opacity))
            
            # Desenhar o ponto como um círculo preenchido
            painter.setBrush(QBrush(dot_color))
            painter.drawEllipse(QRectF(dot_x - dot_radius, 
                                      dot_y - dot_radius, 
                                      dot_radius * 2, 
                                      dot_radius * 2))

    def _create_wave_pattern(self, pos, phase):
        """Cria um padrão de onda mais orgânico para as barras."""
        # Combinar múltiplas ondas com frequências e fases diferentes para maior naturalidade
        wave1 = 0.5 * math.sin(math.pi * pos * 3.1 + phase)
        wave2 = 0.3 * math.sin(math.pi * pos * 5.3 + phase * 0.7)
        wave3 = 0.2 * math.sin(math.pi * pos * 7.5 + phase * 1.3)
        
        return 0.3 + 0.7 * abs(wave1 + wave2 + wave3) / 1.0

# --- Status Indicator ---
class StatusIndicator(QWidget):
    """Indicador visual de status com efeito pulsante."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = "idle"  # idle, recording, processing
        self.pulse_size = 0.0
        self.pulse_growing = True
        
        # Timer para animação de pulso
        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(30)
        self.pulse_timer.timeout.connect(self._update_pulse)
        self.pulse_timer.start()
        
        # Tamanho fixo
        self.setFixedSize(24, 24)

    def set_status(self, status):
        """Define o status atual: 'idle', 'recording', 'processing'."""
        self._status = status
        self.update()

    def _update_pulse(self):
        """Atualiza o efeito de pulso."""
        pulse_step = 0.05
        if self.pulse_growing:
            self.pulse_size += pulse_step
            if self.pulse_size >= 1.0:
                self.pulse_size = 1.0
                self.pulse_growing = False
        else:
            self.pulse_size -= pulse_step
            if self.pulse_size <= 0.0:
                self.pulse_size = 0.0
                self.pulse_growing = True
        
        self.update()

    def paintEvent(self, event):
        """Desenha o indicador de status com efeito de pulso."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2
        
        # Raio do círculo principal
        inner_radius = min(width, height) * 0.3
        
        # Determinar cor com base no status
        if self._status == "recording":
            color = STATUS_LISTENING
        elif self._status == "processing":
            color = STATUS_PROCESSING
        else:
            color = QColor(150, 150, 150)  # Cinza para idle
        
        # Desenhar círculo de fundo (efeito de pulso)
        if self._status != "idle":
            # Raio do pulso externo
            pulse_radius = inner_radius * (1.0 + self.pulse_size * 0.7)
            
            # Cor com transparência para o pulso
            pulse_color = QColor(color)
            pulse_color.setAlpha(int(100 * (1.0 - self.pulse_size)))
            
            # Desenhar pulso
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(pulse_color))
            painter.drawEllipse(QRectF(center_x - pulse_radius, 
                                      center_y - pulse_radius, 
                                      pulse_radius * 2, 
                                      pulse_radius * 2))
        
        # Desenhar círculo principal
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QRectF(center_x - inner_radius, 
                                  center_y - inner_radius, 
                                  inner_radius * 2, 
                                  inner_radius * 2))

# --- Feedback Window Class ---
class PySideFeedbackWindow(QWidget):
    """
    Fornece feedback visual durante a gravação de áudio usando PySide6.
    Exibe status de gravação, tempo decorrido e visualização de volume.
    Aparece próximo ao cursor do mouse quando ativo.
    """
    feedback_signal = Signal(str, object)  # Signal para comunicação a partir da fila

    def __init__(self, feedback_queue: queue.Queue, parent=None):
        super().__init__(parent)
        self.feedback_queue = feedback_queue
        self.is_recording = False
        self.is_processing = False
        self.recording_elapsed_timer = QElapsedTimer()  # Timer para rastrear tempo
        self.elapsed_display_timer = QTimer(self)  # Timer para atualizar o display
        self.position_update_timer = QTimer(self)  # Timer para seguir o cursor
        
        # Estado da animação
        self.current_state = "idle"  # idle, recording, processing
        
        # Timer de alta prioridade para seguir o cursor
        self.position_update_timer.setTimerType(Qt.PreciseTimer)
        self.position_update_timer.setInterval(5)  # Atualização ultra-rápida (5ms)
        self.position_update_timer.timeout.connect(self._update_position)

        self._init_ui()
        self._setup_queue_timer()

        # Conectar o sinal ao slot de processamento
        self.feedback_signal.connect(self._handle_feedback)
        # Conectar o timer de tempo decorrido
        self.elapsed_display_timer.timeout.connect(self._update_timer_display)
        
        # Efeito de fade para mostrar/ocultar a janela
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Animação de fade-in
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(250)
        self.fade_animation.setEasingCurve(QEasingCurve.OutCubic)

    def _init_ui(self):
        """Inicializa os componentes da interface."""
        self.setWindowTitle("Voxy AI Transcription")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        self.main_layout.setContentsMargins(12, 12, 12, 10)
        self.main_layout.setSpacing(8)
        
        # Área de cabeçalho (ícone + status)
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(8)
        
        # Ícone da aplicação
        self.app_icon = QLabel(self)
        self.app_icon.setAlignment(Qt.AlignCenter)
        self.app_icon.setStyleSheet("""
            QLabel {
                color: #a080ff;
                background-color: transparent;
                font-size: 16px;
            }
        """)
        self.app_icon.setText("🎙️")
        self.header_layout.addWidget(self.app_icon)
        
        # Indicador de status
        self.status_indicator = StatusIndicator(self)
        self.header_layout.addWidget(self.status_indicator)
        
        # Texto de status
        self.status_text = QLabel("Idle", self)
        self.status_text.setStyleSheet("""
            QLabel {
                color: #b8b8d0;
                background-color: transparent;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
        """)
        self.header_layout.addWidget(self.status_text)
        
        # Espaçador
        self.header_layout.addStretch(1)
        
        # Timer Label
        self.timer_label = QLabel("00:00", self)
        self.timer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.timer_label.setStyleSheet("""
            QLabel {
                color: #d0d0e8;
                background-color: transparent;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.header_layout.addWidget(self.timer_label)
        
        # Adicionar header ao layout principal
        self.main_layout.addLayout(self.header_layout)
        
        # Mensagem de status/fase
        self.phase_label = QLabel("AI Transcription Ready", self)
        self.phase_label.setAlignment(Qt.AlignCenter)
        self.phase_label.setStyleSheet("""
            QLabel {
                color: #d0d0e8;
                background-color: transparent;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        self.main_layout.addWidget(self.phase_label)
        
        # Visualização de ondas
        self.wave_widget = WaveAnimationWidget(self)
        self.main_layout.addWidget(self.wave_widget)
        
        # Rodapé / Nome da aplicação
        self.footer_label = QLabel("Voxy AI", self)
        self.footer_label.setAlignment(Qt.AlignRight)
        self.footer_label.setStyleSheet("""
            QLabel {
                color: #808090;
                background-color: transparent;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10px;
                font-style: italic;
            }
        """)
        self.main_layout.addWidget(self.footer_label)

        # Definir tamanho fixo para a janela
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Iniciar oculto
        self.hide()

    def _setup_queue_timer(self):
        """Configura um timer para verificar periodicamente a fila de feedback."""
        self.queue_timer = QTimer(self)
        self.queue_timer.timeout.connect(self._process_queue)
        self.queue_timer.start(50)  # Verificar a fila a cada 50ms

    def _process_queue(self):
        """Processa mensagens da fila de feedback na thread principal da GUI."""
        try:
            while not self.feedback_queue.empty():
                command, data = self.feedback_queue.get_nowait()
                # Emitir sinal para lidar com o comando na thread principal
                self.feedback_signal.emit(command, data)
                self.feedback_queue.task_done()
        except queue.Empty:
            pass
        except Exception as e:
            logging.error(f"Erro ao processar fila de feedback: {e}")

    def _show_with_animation(self):
        """Mostra a janela com uma animação de fade-in."""
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.show()
        self.fade_animation.start()

    def _hide_with_animation(self):
        """Oculta a janela com uma animação de fade-out."""
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self._finish_hide)
        self.fade_animation.start()
    
    def _finish_hide(self):
        """Completa a operação de ocultação após a animação."""
        if self.opacity_effect.opacity() == 0:
            self.hide()
        # Desconectar para evitar múltiplas conexões
        try:
            self.fade_animation.finished.disconnect(self._finish_hide)
        except:
            pass

    @Slot(str, object)
    def _handle_feedback(self, command: str, data: object):
        """Processa comandos recebidos da fila via feedback_signal."""
        logging.debug(f"Janela de Feedback recebeu comando: {command} com dados: {data}")
        if command == "start_recording":
            self.start_recording()
        elif command == "stop_recording":
            self.stop_recording()
        elif command == "update_volume":
            self.update_volume(data)  # data deve ser o nível RMS
        elif command == "start_processing":
            self.start_processing()
        elif command == "processing_complete":
            self.processing_complete()
        elif command == "show_message":
            self.show_message(data)  # data deve ser a string da mensagem
        else:
            logging.warning(f"Comando desconhecido recebido: {command}")

    def _update_position(self):
        """Atualiza a posição da janela para ficar próxima ao cursor do mouse."""
        if not QApplication.instance():
            return

        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()
            if not screen:
                return

        # Cálculo simplificado para maior performance
        window_width = self.width()
        window_height = self.height()
        
        # Posição abaixo do cursor
        target_x = cursor_pos.x() - (window_width / 2)  # Centralizado horizontalmente
        target_y = cursor_pos.y() + 20  # Abaixo do cursor
        
        # Ajustes para evitar sair da tela
        screen_geometry = screen.availableGeometry()
        if target_x + window_width > screen_geometry.right():
            target_x = screen_geometry.right() - window_width
        if target_x < screen_geometry.left():
            target_x = screen_geometry.left()
        
        if target_y + window_height > screen_geometry.bottom():
            target_y = cursor_pos.y() - window_height - 5  # Mover para cima do cursor
            
        # Mover diretamente para máxima performance
        self.move(target_x, target_y)

    @Slot()
    def _update_timer_display(self):
        """Atualiza o rótulo do timer com o tempo decorrido de gravação."""
        if self.is_recording and self.recording_elapsed_timer.isValid():
            elapsed_msecs = self.recording_elapsed_timer.elapsed()
            seconds = int(elapsed_msecs / 1000) % 60
            minutes = int(elapsed_msecs / 60000) % 60
            self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")
        else:
            self.timer_label.setText("00:00")

    def _update_status_display(self, status, message):
        """Atualiza o display de status com uma nova mensagem e estado."""
        self.current_state = status
        self.status_indicator.set_status(status)
        
        if status == "recording":
            self.status_text.setText("Gravando")
            self.status_text.setStyleSheet("color: #70dd78; font-weight: bold; font-size: 12px;")
            self.wave_widget.set_processing(False)
        elif status == "processing":
            self.status_text.setText("Processando")
            self.status_text.setStyleSheet("color: #f59e42; font-weight: bold; font-size: 12px;")
            self.wave_widget.set_processing(True)
        else:
            self.status_text.setText("Inativo")
            self.status_text.setStyleSheet("color: #b8b8d0; font-size: 12px;")
            self.wave_widget.set_processing(False)
        
        self.phase_label.setText(message)

    def paintEvent(self, event):
        """Desenha o fundo personalizado com bordas arredondadas e gradiente."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # Criar caminho para bordas arredondadas
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), BORDER_RADIUS, BORDER_RADIUS)
        
        # Gradiente de fundo
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(DARK_BG.red(), DARK_BG.green(), DARK_BG.blue(), 240))
        gradient.setColorAt(1, QColor(DARK_BG.red() - 5, DARK_BG.green() - 5, DARK_BG.blue(), 240))
        
        # Desenhar fundo com bordas arredondadas
        painter.fillPath(path, gradient)
        
        # Borda sutil
        painter.setPen(QPen(QColor(70, 70, 80, 100), 1))
        painter.drawPath(path)

    # --- Métodos Públicos ---

    def start_recording(self):
        """Chamado quando a gravação inicia."""
        logging.info("Janela de feedback: Gravação iniciada.")
        self.is_recording = True
        self.is_processing = False
        self.recording_elapsed_timer.start()  # Iniciar o timer
        self.elapsed_display_timer.start(100)  # Atualizar display a cada 100ms
        
        # Iniciar timer de alta prioridade para seguir o mouse
        self.position_update_timer.start()
        
        # Atualizar interface
        self._update_status_display("recording", "Ouvindo sua voz...")
        
        # Posição inicial e mostrar com animação
        self._update_position()
        self._show_with_animation()

    def stop_recording(self):
        """Chamado quando a gravação para."""
        logging.info("Janela de feedback: Gravação parada.")
        self.is_recording = False
        self.elapsed_display_timer.stop()
        self.recording_elapsed_timer.invalidate()  # Limpar timer
        
        if not self.is_processing:
            # Se não estiver processando, ocultar após um delay
            self.position_update_timer.stop()
            self._update_status_display("idle", "Processamento concluído") # Mensagem genérica
            QTimer.singleShot(1000, self._hide_with_animation)

    def start_processing(self):
        """Indica que o processamento de IA começou."""
        logging.info("Janela de feedback: Processamento iniciado.")
        self.is_processing = True
        self.elapsed_display_timer.stop()
        
        # Manter a janela visível e atualizar status
        self._update_status_display("processing", "IA transcrevendo áudio...")

    def processing_complete(self):
        """Indica que o processamento de IA foi concluído."""
        logging.info("Janela de feedback: Processamento concluído.")
        self.is_processing = False
        
        # Ocultar após um delay se também não estiver gravando
        if not self.is_recording:
            self.position_update_timer.stop()
            self._update_status_display("idle", "Transcrição concluída")
            QTimer.singleShot(1500, self._hide_with_animation)

    def update_volume(self, level: float):
        """Atualiza o indicador de volume."""
        if self.is_recording and hasattr(self, 'wave_widget'):
            try:
                float_level = float(level)
                self.wave_widget.set_level(float_level)
            except (ValueError, TypeError):
                 logging.warning(f"Nível de volume inválido recebido: {level}. Esperado float.")
                 self.wave_widget.set_level(0.0)

    def show_message(self, message: str):
        """Exibe uma mensagem temporária."""
        logging.info(f"Janela de feedback exibindo mensagem: {message}")
        self._update_status_display("idle", message)
        self._update_position()
        self._show_with_animation()
        QTimer.singleShot(3000, self._hide_with_animation)


# Exemplo de uso (para fins de teste, comentar ou remover em produção)
if __name__ == '__main__':
    import sys
    import time
    import threading

    app = QApplication(sys.argv)
    q = queue.Queue()
    window = PySideFeedbackWindow(q)

    # Simular comandos de outras threads
    def simulate_commands():
        time.sleep(1)
        q.put(("start_recording", None))
        
        for i in range(25):
            time.sleep(0.2)
            # Volume variando em padrão senoidal
            volume = 0.2 + 0.8 * abs(math.sin(i * 0.25))
            q.put(("update_volume", volume))
        
        time.sleep(0.5)
        q.put(("stop_recording", None))
        
        time.sleep(0.5)
        q.put(("start_processing", None))
        
        time.sleep(3)
        q.put(("processing_complete", None))
        
        time.sleep(2)
        q.put(("show_message", "Texto transcrito com sucesso!"))
        
        time.sleep(4)
        app.quit()  # Sair após simulação

    thread = threading.Thread(target=simulate_commands, daemon=True)
    thread.start()

    sys.exit(app.exec()) 