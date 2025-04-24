"""Módulo responsável pela transcrição de áudio usando a API OpenAI."""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from openai import APIError, AuthenticationError, OpenAI, RateLimitError

# Configuração inicial do logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

class Transcriber:
    """Classe para encapsular a funcionalidade de transcrição de áudio."""

    def __init__(self, api_key: Optional[str] = None):
        """Inicializa o Transcriber.

        Args:
            api_key: A chave da API OpenAI. Se None, tenta obter do ambiente.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client: Optional[OpenAI] = None

        if not self.api_key:
            logging.error(
                "Chave da API OpenAI não fornecida nem encontrada no ambiente. Transcriber não funcional."
            )
            return # Cliente permanece None

        try:
            self.client = OpenAI(api_key=self.api_key)
            logging.info("Cliente OpenAI inicializado com sucesso no Transcriber.")
        except Exception as e:
            logging.error(f"Erro ao inicializar o cliente OpenAI no Transcriber: {e}")
            # Cliente permanece None

    def transcribe_audio(self, file_path: str) -> Optional[str]:
        """Envia um arquivo de áudio para a API OpenAI Speech-to-Text e retorna a transcrição.

        Args:
            file_path: O caminho para o arquivo de áudio (esperado em formato WAV ou outro suportado).

        Returns:
            O texto transcrito pela API ou None se ocorrer um erro ou o cliente não estiver inicializado.

        Raises:
            FileNotFoundError: Se o arquivo especificado em file_path não for encontrado.
        """
        if not self.client:
            logging.error("Cliente OpenAI não inicializado no Transcriber. Transcrição abortada.")
            return None

        if not os.path.exists(file_path):
            logging.error(f"Arquivo de áudio não encontrado em: {file_path}")
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        logging.info(f"Iniciando transcrição para o arquivo: {file_path}")
        try:
            with open(file_path, "rb") as audio_file:
                # Documentação da API: https://platform.openai.com/docs/api-reference/audio/createTranscription
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",  # Modelo recomendado pela OpenAI
                    file=audio_file,
                    language="pt", # Especificar o idioma (Português)
                    # response_format="text" # Retorna apenas o texto diretamente
                )
            # A API retorna um objeto, o texto está no atributo 'text' (se response_format não for 'text')
            transcribed_text = transcript.text
            logging.info(f"Transcrição bem-sucedida para: {file_path}")
            return transcribed_text
        except FileNotFoundError:
            # Relançar a exceção capturada na verificação inicial
            logging.error(f"Erro interno: Arquivo {file_path} não encontrado durante abertura.")
            raise
        except AuthenticationError:
            logging.error(
                "Erro de autenticação com a API OpenAI. Verifique sua chave API."
            )
            return None
        except RateLimitError:
            logging.error("Limite de taxa da API OpenAI excedido. Tente novamente mais tarde.")
            return None
        except APIError as e:
            logging.error(f"Erro na API OpenAI: {e}")
            return None
        except Exception as e:
            logging.error(f"Erro inesperado durante a transcrição: {e}")
            return None

# Exemplo de uso (agora instancia a classe)
if __name__ == "__main__":
    temp_dir = "_temp"
    test_filename = "voxy_temp_recording.wav"
    test_file = os.path.join(temp_dir, test_filename)

    # Instancia o Transcriber (ele tentará pegar a chave do .env)
    transcriber_instance = Transcriber()

    if not transcriber_instance.client:
        print("Falha ao inicializar o Transcriber. Verifique a chave API e os logs.")
    elif not os.path.exists(test_file):
        print(
            f"Arquivo de teste '{test_file}' (WAV) não encontrado. "
            f"Execute audio_recorder.py ou especifique um arquivo WAV válido."
        )
    else:
        print(f"Testando a transcrição com o arquivo: {test_file}")
        result = transcriber_instance.transcribe_audio(test_file)
        if result:
            print("\n--- Transcrição ---")
            print(result)
            print("-------------------")
        else:
            print("Falha na transcrição. Verifique os logs.") 