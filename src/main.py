import keyboard
import threading
import time
import os
import logging
from dotenv import load_dotenv
import queue
import sys

# Importar nossos módulos
from audio_recorder import AudioRecorder
from transcriber import Transcriber
from text_injector import TextInjector
# from visual_feedback import FeedbackWindow # Old Tkinter version
from visual_feedback import PySideFeedbackWindow # Task 4.3.7: Import new window

# Importar PySide6 para QApplication e QMessageBox
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QMetaObject, Qt # Para invocar quit na thread principal

# --- Configuração ---
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)

# Constantes e Configurações
HOTKEY = os.getenv("VOXY_HOTKEY", "alt+shift+s")
AUDIO_TEMP_DIR = "_temp"
AUDIO_TEMP_FILENAME = "voxy_temp_recording.wav"
AUDIO_TEMP_PATH = os.path.join(AUDIO_TEMP_DIR, AUDIO_TEMP_FILENAME)
MODEL = os.getenv("OPENAI_MODEL", "whisper-1")

os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)

# Variáveis globais (inicializadas em __main__)
audio_recorder = None
transcriber = None
text_injector = None
feedback_window = None # This will be the PySideFeedbackWindow instance
feedback_queue = None # Task 4.3.7: Queue for feedback
is_processing = None
app = None # Referência para a QApplication
hotkey_listener_thread = None # Task 4.3.7: Thread for keyboard listener

# --- Lógica Principal do Workflow ---

def trigger_voxy_workflow():
    """Função chamada pela hotkey para iniciar o fluxo de gravação/transcrição/injeção."""
    global feedback_queue # Ensure we use the global queue

    if not is_processing.acquire(blocking=False):
        logging.warning("Hotkey pressionada, mas um processo já está em andamento. Ignorando.")
        return

    logging.info(f"Hotkey '{HOTKEY}' detectada! Iniciando fluxo...")

    result_queue = queue.Queue()
    recording_thread = None
    transcription_thread = None

    try:
        # --- 1. Feedback Visual Inicial e Gravação ---
        try:
            # Task 4.3.7: Use queue to start feedback
            if feedback_queue:
                feedback_queue.put(("start_recording", None))
            logging.info("Comando 'start_recording' enviado para feedback visual.")

            # A gravação agora recebe a fila na inicialização
            recording_thread = audio_recorder.start_recording()
            if not recording_thread:
                raise RuntimeError("Falha ao iniciar a thread de gravação.")
            logging.info("Gravação iniciada.")

            recording_thread.join()
            logging.info("Gravação concluída.")

            # Task 4.3.7: Feedback window automatically shows "Processing..." on stop_recording
            # No need to explicitly send stop here unless we want immediate hide

        except Exception as e_rec:
            logging.exception("Erro durante a gravação ou feedback inicial.")
            # Task 4.3.7: Use queue for error message
            if feedback_queue:
                feedback_queue.put(("show_message", "Erro Gravação!"))
            time.sleep(2) # Keep message visible briefly
            return

        # --- 2. Feedback Visual - Transcrevendo e Transcrição ---
        try:
            # Task 4.3.7: Feedback window should show "Processing..." from stop_recording.
            # logging.info("Feedback visual 'Processando...' (implícito).")

            def transcribe_task(audio_path, output_queue):
                """Tarefa para ser executada em uma thread separada."""
                try:
                    text = transcriber.transcribe_audio(audio_path)
                    output_queue.put(text if text else "")
                except Exception as e_task:
                    logging.exception("Erro na thread de transcrição.")
                    output_queue.put(None)

            transcription_thread = threading.Thread(
                target=transcribe_task,
                args=(AUDIO_TEMP_PATH, result_queue),
                daemon=True,
                name="TranscribeThread"
            )
            transcription_thread.start()
            logging.info("Thread de transcrição iniciada.")

            transcription_thread.join()
            logging.info("Thread de transcrição concluída.")

            transcribed_text = result_queue.get()

            if transcribed_text is None:
                logging.error("Falha na transcrição (erro na thread).")
                # Task 4.3.7: Use queue for error message
                if feedback_queue:
                    feedback_queue.put(("show_message", "Erro Transcrição!"))
                time.sleep(2)
                return
            elif not transcribed_text:
                 logging.info("Transcrição retornou texto vazio.")
                 # Task 4.3.7: Send stop_recording which hides the window after delay
                 if feedback_queue:
                     feedback_queue.put(("stop_recording", None))
            else:
                 logging.info(f"Texto transcrito obtido: {transcribed_text[:50]}...")

        except Exception as e_trans:
            logging.exception("Erro durante a etapa de transcrição.")
            # Task 4.3.7: Use queue for error message
            if feedback_queue:
                feedback_queue.put(("show_message", "Erro Transcrição!"))
            time.sleep(2)
            return

        # --- 3. Injeção de Texto (se houver) ---
        if transcribed_text:
            try:
                # Task 4.3.7: Show injecting message
                if feedback_queue:
                    feedback_queue.put(("show_message", "Injetando..."))
                logging.info("Feedback visual 'Injetando...' exibido.")
                injection_success = text_injector.inject(transcribed_text)
                if not injection_success:
                    logging.error("Falha ao injetar o texto (retorno False do injector).")
                    # Task 4.3.7: Use queue for error message
                    if feedback_queue:
                        feedback_queue.put(("show_message", "Erro Injeção!"))
                    time.sleep(2)
                else:
                    # Task 4.3.7: Success! Tell feedback window to hide (via stop_recording)
                    if feedback_queue:
                        feedback_queue.put(("stop_recording", None))
            except Exception as e_inj:
                logging.exception("Erro durante a injeção de texto.")
                # Task 4.3.7: Use queue for error message
                if feedback_queue:
                    feedback_queue.put(("show_message", "Erro Injeção!"))
                time.sleep(2)
        # else: (No text) stop_recording was already called

    except Exception as e_main:
        logging.exception("Ocorreu um erro inesperado durante o workflow Voxy.")
        try:
            # Task 4.3.7: Use queue for error message
            if feedback_queue:
                feedback_queue.put(("show_message", "Erro Inesperado!"))
            time.sleep(2)
        except Exception as e_fb_err:
             logging.error(f"Erro adicional ao tentar mostrar feedback de erro inesperado: {e_fb_err}")

    finally:
        # --- 4. Limpeza Final ---
        # Task 4.3.7: Hiding is handled by stop_recording or show_message timeouts
        # logging.info("Feedback visual escondido (implicitamente via stop/message).")

        if is_processing.locked():
             is_processing.release()
             logging.info("Workflow concluído, lock liberado.")
        else:
             logging.warning("Tentativa de liberar lock no finally, mas não estava adquirido.")

        try:
            if os.path.exists(AUDIO_TEMP_PATH):
                os.remove(AUDIO_TEMP_PATH)
                logging.info(f"Arquivo temporário {AUDIO_TEMP_PATH} removido.")
        except Exception as e_clean:
            logging.error(f"Erro ao tentar remover arquivo temporário {AUDIO_TEMP_PATH}: {e_clean}")


# --- Configuração e Loop Principal --- 

def quit_app():
    """Safely request the QApplication to quit from any thread."""
    logging.info("Solicitando encerramento da aplicação Qt...")
    # Use invokeMethod to ensure quit() is called in the main GUI thread
    QMetaObject.invokeMethod(app, "quit", Qt.QueuedConnection)

def setup_and_run_hotkey_listener():
    """Configura e inicia o listener da hotkey em uma thread separada."""
    global app
    logging.info(f"Configurando listener para a hotkey: {HOTKEY}")

    try:
        # Usar threading para não bloquear a execução principal ao chamar o workflow
        keyboard.add_hotkey(HOTKEY, lambda: threading.Thread(target=trigger_voxy_workflow, daemon=True, name="WorkflowTriggerThread").start())

        logging.info("Listener da hotkey iniciado. Pressione ESC para sair.")
        # Mantém esta thread rodando esperando ESC
        keyboard.wait('esc')
        logging.info("Tecla ESC pressionada na thread do listener.")
        quit_app() # Solicita o encerramento da aplicação Qt
    except ImportError:
        logging.error("Erro ao importar 'keyboard'. Certifique-se de que está instalado e rodando com privilégios (sudo no Linux).")
        quit_app() # Tenta sair mesmo assim
    except Exception as e_kb:
        logging.exception("Erro inesperado na thread do listener de hotkey.")
        quit_app() # Tenta sair
    finally:
        logging.info("Thread do listener de hotkey finalizada.")

# --- Ponto de Entrada Principal ---

if __name__ == "__main__":
    logging.info("Iniciando Voxy Tool...")

    # --- Inicialização da Aplicação Qt --- # Task 4.3.7
    # QApplication DEVE ser instanciada antes de qualquer widget
    app = QApplication.instance() or QApplication(sys.argv)
    if not app:
         logging.critical("Falha ao criar QApplication!")
         sys.exit(1)

    # --- Declaração de Variáveis Globais ---
    openai_api_key = None
    feedback_queue = queue.Queue() # Task 4.3.7
    is_processing = threading.Lock()

    try:
        # --- Inicialização dos Componentes ---
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            error_message = "Chave da API OpenAI (OPENAI_API_KEY) não encontrada no arquivo .env!\nA aplicação será encerrada."
            logging.error(error_message)
            # Task 4.3.7: Show message box directly
            QMessageBox.critical(None, "Erro de Configuração", error_message)
            sys.exit(1)

        # Task 4.3.7: Instanciar com a fila
        audio_recorder = AudioRecorder(output_filename=AUDIO_TEMP_PATH, feedback_queue=feedback_queue)
        transcriber = Transcriber(api_key=openai_api_key)
        text_injector = TextInjector()
        feedback_window = PySideFeedbackWindow(feedback_queue) # Task 4.3.7
        # A janela PySide não precisa ser "iniciada" como a Tkinter, ela é gerenciada pelo app.exec()

        # --- Iniciar Listener em Thread Separada ---
        logging.info("Iniciando thread do listener de hotkey...")
        hotkey_listener_thread = threading.Thread(target=setup_and_run_hotkey_listener, name="HotkeyListenerThread", daemon=False) # Não daemon
        hotkey_listener_thread.start()

        # --- Executar Loop de Eventos Qt --- # Task 4.3.7
        logging.info("Iniciando loop de eventos principal (Qt Application exec)...")
        exit_code = app.exec() # Bloqueia até app.quit() ser chamado
        logging.info(f"Loop de eventos Qt finalizado com código: {exit_code}")

        # Esperar a thread do listener terminar após o app.quit()
        logging.info("Aguardando finalização da thread do listener...")
        hotkey_listener_thread.join(timeout=2)
        if hotkey_listener_thread.is_alive():
             logging.warning("Thread do listener não finalizou após timeout.")

    except Exception as e_init:
        logging.critical(f"Erro crítico durante a inicialização: {e_init}", exc_info=True)
        # Tentar mostrar mensagem de erro se possível
        try:
            QMessageBox.critical(None, "Erro Crítico", f"Erro inesperado na inicialização:\n{e_init}")
        except Exception:
             pass # Se nem isso funcionar, apenas logamos
        sys.exit(1)
    finally:
        logging.info("Encerrando Voxy Tool.")
        # Limpeza adicional se necessário (ex: fechar outros recursos)
        # keyboard.remove_all_hotkeys() # Desregistrar hotkeys se necessário/possível
        # print("Hotkeys removidas.")
        logging.shutdown() # Garante que todos os logs sejam escritos

    sys.exit(0) # Saída limpa