import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
# from pydub import AudioSegment # Comentado - Conversão não é mais responsabilidade direta aqui
import queue
import os
import time
import threading
import logging
from typing import Optional # Added Optional

# Configuração do Logging (pode ser configurado externamente no futuro)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')

# Rough maximum expected RMS value for normalization (adjust based on testing)
# This depends heavily on microphone sensitivity and input gain.
# A value of 500-1000 might be a reasonable starting point for int16 data.
MAX_EXPECTED_RMS = 700 # Heuristic value, needs tuning

class AudioRecorder:
    """Gerencia a gravação de áudio com detecção de silêncio em uma thread separada."""

    def __init__(
        self,
        output_filename: str,
        samplerate: int = 44100,
        channels: int = 1,
        blocksize: int = 1024,
        dtype: str = 'int16',
        silence_threshold: float = 50, # Keep this in the original scale
        silence_stop_duration: float = 1.5,
        feedback_queue: Optional[queue.Queue] = None # Task 4.3.6: Add feedback queue
    ):
        """Inicializa o gravador de áudio.

        Args:
            output_filename: Caminho completo para salvar o arquivo WAV final.
            samplerate: Taxa de amostragem.
            channels: Número de canais.
            blocksize: Tamanho do bloco para processamento.
            dtype: Tipo de dado das amostras.
            silence_threshold: Limiar RMS para detectar silêncio (na escala original dos dados).
            silence_stop_duration: Duração em segundos de silêncio contínuo para parar.
            feedback_queue: Fila opcional para enviar atualizações de feedback (e.g., volume).
        """
        self.output_filename = output_filename
        self.samplerate = samplerate
        self.channels = channels
        self.blocksize = blocksize
        self.dtype = dtype
        self.silence_threshold = silence_threshold
        self.silence_stop_duration = silence_stop_duration
        self.feedback_queue = feedback_queue # Task 4.3.6

        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._recording_thread: threading.Thread | None = None
        self._audio_data = []
        self._recording_started_flag = False
        self._silent_frames = 0
        self._total_frames = 0

        logging.info(f"AudioRecorder inicializado para salvar em: {self.output_filename}")
        if self.feedback_queue:
            logging.info("Fila de feedback habilitada.")

    def _calculate_rms(self, data: np.ndarray) -> float:
        """Calcula o valor RMS (Root Mean Square) de um bloco de áudio."""
        if data.size == 0:
            return 0.0
        # Ensure data is float64 for calculation to avoid overflow/underflow
        data_float = data.astype(np.float64)
        # Use np.mean directly on the squared data
        rms_val = np.sqrt(np.mean(np.square(data_float)))
        return rms_val

    def _normalize_rms(self, rms_value: float) -> float:
        """Normalizes the RMS value to a 0.0-1.0 range based on MAX_EXPECTED_RMS."""
        # Simple linear scaling, clamped
        normalized = rms_value / MAX_EXPECTED_RMS
        return max(0.0, min(1.0, normalized))

    def _callback(self, indata, frames, time_info, status):
        """Callback chamado pelo sounddevice para cada bloco de áudio."""
        if status:
            logging.warning(f"Status da gravação Sounddevice: {status}")

        rms = self._calculate_rms(indata)

        # Task 4.3.6: Send normalized RMS to feedback queue
        if self.feedback_queue:
            try:
                rms_normalized = self._normalize_rms(rms)
                # Use put_nowait to avoid blocking the audio callback thread
                self.feedback_queue.put_nowait(("update_volume", rms_normalized))
            except queue.Full:
                # This should ideally not happen if the GUI processes the queue fast enough
                logging.warning("Feedback queue is full. Discarding volume update.")
            except Exception as q_err:
                 logging.error(f"Error putting item in feedback queue: {q_err}")

        # logging.debug(f"RMS: {rms:.2f}") # Debug pode ser muito verboso

        frames_per_second = self.samplerate / self.blocksize
        silent_frames_needed = int(self.silence_stop_duration * frames_per_second)

        if rms > self.silence_threshold:
            if not self._recording_started_flag:
                logging.info("Som detectado, gravação efetivamente iniciada.")
                self._recording_started_flag = True
            self._queue.put(indata.copy())
            self._silent_frames = 0
            self._total_frames += frames
        elif self._recording_started_flag:
            self._queue.put(indata.copy())
            self._silent_frames += 1
            self._total_frames += frames
            if self._silent_frames >= silent_frames_needed:
                logging.info(f"Silêncio detectado por {self.silence_stop_duration}s, sinalizando parada.")
                self._stop_event.set()
        # else: Não grava nada antes da primeira detecção de som

    def _recording_loop(self):
        """Loop principal de gravação executado em uma thread separada."""
        logging.info("Thread de gravação iniciada.")
        self._audio_data = []
        self._recording_started_flag = False
        self._silent_frames = 0
        self._total_frames = 0
        stream = None # Inicializar stream como None

        try:
            logging.info("Iniciando stream de áudio...")
            stream = sd.InputStream(
                samplerate=self.samplerate,
                blocksize=self.blocksize,
                channels=self.channels,
                dtype=self.dtype,
                callback=self._callback
            )
            with stream:
                logging.info("Stream de áudio iniciado. Aguardando dados ou sinal de parada...")
                while not self._stop_event.is_set():
                    try:
                        # Consome da fila. Timeout curto para não bloquear indefinidamente
                        # se a callback parar por algum motivo antes do stop_event.
                        data_block = self._queue.get(timeout=0.5)
                        self._audio_data.append(data_block)
                    except queue.Empty:
                        # Se a fila está vazia, apenas continua checando o stop_event
                        # ou se o stream ainda está ativo.
                        if not stream.active:
                            logging.warning("Stream se tornou inativo inesperadamente.")
                            break
                        pass
                logging.info("Sinal de parada recebido ou stream inativo, saindo do loop de gravação.")

        except sd.PortAudioError as e:
            logging.error(f"Erro de áudio PortAudioError: {e}. Verifique o dispositivo de entrada.")
            # Considerar sinalizar erro para a thread principal?
            # Task 4.3.6: Send error message to feedback queue if available
            if self.feedback_queue:
                 try:
                     self.feedback_queue.put_nowait(("show_message", "Erro no dispositivo de áudio!"))
                 except queue.Full:
                     logging.warning("Feedback queue full when trying to send audio device error.")
        except Exception as e:
            logging.exception("Erro inesperado dentro da thread de gravação.")
            # Task 4.3.6: Send generic error message
            if self.feedback_queue:
                 try:
                     self.feedback_queue.put_nowait(("show_message", "Erro na gravação!"))
                 except queue.Full:
                     logging.warning("Feedback queue full when trying to send generic recording error.")
        finally:
            # Garante que o stop_event seja setado caso a saída seja por exceção
            self._stop_event.set()
            if stream and stream.active:
                logging.info("Fechando stream de áudio.")
                # stream.stop() # stream.close() é chamado pelo __exit__ do context manager

            # Processamento e salvamento do áudio
            if not self._audio_data:
                logging.warning("Nenhum dado de áudio foi gravado.")
            else:
                try:
                    recording_np = np.concatenate(self._audio_data, axis=0)
                    duration_sec = len(recording_np) / self.samplerate
                    logging.info(f"Gravação finalizada. Duração total: {duration_sec:.2f} segundos.")

                    # Garante que o diretório de saída exista
                    output_dir = os.path.dirname(self.output_filename)
                    if output_dir:
                        os.makedirs(output_dir, exist_ok=True)

                    # Salva como WAV
                    logging.info(f"Salvando gravação WAV em {self.output_filename}...")
                    wav.write(self.output_filename, self.samplerate, recording_np)
                    logging.info("Arquivo WAV salvo com sucesso.")
                except Exception as save_e:
                    logging.exception(f"Erro ao processar ou salvar o arquivo WAV: {save_e}")
                    # Task 4.3.6: Send save error message
                    if self.feedback_queue:
                         try:
                             self.feedback_queue.put_nowait(("show_message", "Erro ao salvar áudio!"))
                         except queue.Full:
                             logging.warning("Feedback queue full when trying to send save error.")

            logging.info("Thread de gravação finalizada.")

    def start_recording(self) -> threading.Thread | None:
        """Inicia o processo de gravação em uma nova thread.

        Returns:
            O objeto Thread da gravação iniciada, ou None se já estiver gravando.
        """
        if self._recording_thread and self._recording_thread.is_alive():
            logging.warning("Tentativa de iniciar gravação enquanto outra já está em andamento.")
            return None

        logging.info("Solicitação para iniciar gravação recebida.")
        self._stop_event.clear() # Reseta o evento de parada
        self._queue = queue.Queue() # Cria uma nova fila para esta gravação

        self._recording_thread = threading.Thread(target=self._recording_loop, name="AudioRecordThread", daemon=True)
        self._recording_thread.start()
        logging.info(f"Thread de gravação iniciada: {self._recording_thread.name}")
        return self._recording_thread

    def stop_recording(self):
        """Força a parada da gravação (se estiver ocorrendo)."""
        if self._recording_thread and self._recording_thread.is_alive():
            logging.info("Solicitação manual para parar a gravação recebida.")
            self._stop_event.set()
            # O join pode ser feito pela thread que chamou start_recording
            # self._recording_thread.join(timeout=1)
        else:
            logging.info("Solicitação para parar, mas nenhuma gravação ativa encontrada.")

    def is_recording(self) -> bool:
        """Verifica se a gravação está ativa."""
        return bool(self._recording_thread and self._recording_thread.is_alive())

# --- Bloco de Teste --- 
if __name__ == "__main__":
    print("--- Teste do AudioRecorder Refatorado ---")
    
    # Criar diretório _temp se não existir para o teste
    temp_dir_test = "_temp"
    os.makedirs(temp_dir_test, exist_ok=True)
    test_filename = os.path.join(temp_dir_test, "test_audio_recorder_output.wav")

    # --- Teste COM feedback queue ---
    print("\n--- Teste com Feedback Queue ---")
    feedback_q_test = queue.Queue()
    recorder_with_feedback = AudioRecorder(
        output_filename=test_filename.replace(".wav", "_feedback.wav"),
        silence_stop_duration=2.0,
        feedback_queue=feedback_q_test
    )

    # Thread para consumir e imprimir da fila de feedback
    def feedback_consumer(q: queue.Queue, stop_event: threading.Event):
        print("[Feedback Consumer Thread] Iniciado")
        while not stop_event.is_set() or not q.empty():
            try:
                cmd, data = q.get(timeout=0.1)
                if cmd == "update_volume":
                    # Simple text representation of volume
                    bar_len = int(data * 20) # Scale to 20 chars
                    volume_bar = '#' * bar_len + '-' * (20 - bar_len)
                    print(f"[Feedback] Volume: [{volume_bar}] {data:.2f}", end='\r')
                else:
                    print(f"\n[Feedback] Comando: {cmd}, Dados: {data}")
                q.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                 print(f"\n[Feedback Consumer Thread] Erro: {e}")
                 break
        print("\n[Feedback Consumer Thread] Finalizado")

    consumer_stop_event = threading.Event()
    consumer_thread = threading.Thread(target=feedback_consumer, args=(feedback_q_test, consumer_stop_event), daemon=True)
    consumer_thread.start()

    print("Iniciando gravação com feedback em 2 segundos... Fale algo!")
    time.sleep(2)
    recording_thread_fb = recorder_with_feedback.start_recording()

    if recording_thread_fb:
        print("Gravação iniciada. Esperando silêncio...")
        try:
            recording_thread_fb.join() # Espera a thread de gravação terminar
            print("\nThread de gravação com feedback finalizada.")
        except KeyboardInterrupt:
            print("\nCtrl+C pressionado. Parando gravação com feedback...")
            recorder_with_feedback.stop_recording()
            recording_thread_fb.join(timeout=2)
        finally:
            print("Sinalizando parada para thread consumidora de feedback...")
            consumer_stop_event.set() # Sinaliza para a thread consumidora parar
            consumer_thread.join(timeout=1) # Espera a consumidora terminar
    else:
        print("Falha ao iniciar gravação com feedback.")
        consumer_stop_event.set()
        consumer_thread.join(timeout=1)

    print("-----------------------------------------")


    # --- Teste SEM feedback queue (original) ---
    # print("\n--- Teste Sem Feedback Queue ---")
    # recorder = AudioRecorder(output_filename=test_filename, silence_stop_duration=2.0)
    # print("Iniciando gravação em 2 segundos... Fale algo!")
    # time.sleep(2)
    # recording_thread = recorder.start_recording()
    # if recording_thread:
    #     print("Gravação iniciada em background. Esperando a detecção de silêncio...")
    #     try:
    #         recording_thread.join()
    #         print("\nThread de gravação finalizada.")
    #         # ... (rest of the original test code) ...
    #     except KeyboardInterrupt:
    #         print("\nCtrl+C pressionado. Tentando parar a gravação...")
    #         recorder.stop_recording()
    #         recording_thread.join(timeout=2)
    #         print("Gravação interrompida.")
    # else:
    #     print("Não foi possível iniciar a thread de gravação.")
    # print("-----------------------------------------")

    # O código original que fazia a conversão foi movido para dentro de uma função separada
    # ou pode ser removido/comentado se não for mais necessário para execução direta.

    # Exemplo de como chamar de outro módulo (mantido para referência):
    # wav_path = record_with_silence_detection()
    # if wav_path:
    #     mp3_path = convert_to_mp3(wav_path, "_temp/output_final.mp3") # Ajustar path se necessário
    #     if mp3_path:
    #         print(f"Arquivo MP3 final: {mp3_path}")
    #         os.remove(wav_path) # Limpar WAV temporário 