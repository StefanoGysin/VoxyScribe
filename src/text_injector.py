import pyautogui
import time
import logging

# Configuração básica do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Intervalo padrão entre as teclas (em segundos)
DEFAULT_TYPE_INTERVAL = 0.01

class TextInjector:
    """Encapsula a lógica para injetar texto usando pyautogui."""

    def __init__(self, interval: float = DEFAULT_TYPE_INTERVAL):
        """Inicializa o injetor.

        Args:
            interval: O intervalo (delay) entre a digitação de cada caractere.
        """
        self.type_interval = interval
        logging.info(f"TextInjector inicializado com intervalo: {self.type_interval}s")

    def inject(self, text: str):
        """Simula a digitação do texto fornecido na posição atual do cursor.

        Args:
            text: O texto a ser digitado.

        Returns:
            bool: True se a injeção foi (aparentemente) bem-sucedida, False caso contrário.
        """
        if not text:
            logging.warning("Tentativa de injetar texto vazio.")
            return True # Considera sucesso, pois não há nada a fazer

        try:
            logging.info(f"Injetando texto (primeiros 50 chars): {text[:50]}...")
            # O pyautogui.write pode ter problemas com certos caracteres/layouts.
            # Alternativa seria usar o clipboard:
            # import pyperclip
            # pyperclip.copy(text)
            # pyautogui.hotkey('ctrl', 'v')
            pyautogui.write(text, interval=self.type_interval)
            logging.info("Texto injetado com sucesso.")
            return True
        except pyautogui.FailSafeException:
            logging.error("Falha de segurança do PyAutoGUI ativada (mouse no canto?). Injeção cancelada.")
            return False
        except Exception as e:
            logging.error(f"Erro inesperado ao injetar texto: {e}", exc_info=True)
            # Considerar relançar a exceção ou retornar False dependendo do fluxo desejado
            return False

# Bloco de teste
if __name__ == "__main__":
    print("--- Teste do TextInjector Refinado ---")
    injector = TextInjector(interval=0.02) # Intervalo um pouco maior para visualização

    test_text = "Olá, mundo! Este é um teste do injetor de texto refinado. 123 @#$%^&*()"

    print(f"\nAguardando 3 segundos... Posicione o cursor onde o texto deve ser inserido.")
    time.sleep(3)

    print(f"Injetando: '{test_text}'")
    success = injector.inject(test_text)

    if success:
        print("\nInjeção concluída com sucesso (verifique o resultado).")
    else:
        print("\nFalha ao injetar o texto.")

    print("-------------------------------------") 