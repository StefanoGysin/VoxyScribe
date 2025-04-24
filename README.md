# VoxyScribe

**Status:** Em Desenvolvimento 🚧 (Atualizado em 23/04/2025)

Este projeto é um agente de ditado (Speech-to-Text) para desktop chamado VoxyScribe, ativado por uma tecla de atalho global. Ele grava o áudio do microfone, utiliza a API Whisper da OpenAI para transcrevê-lo e, em seguida, injeta o texto resultante na aplicação ativa no local do cursor.

## Funcionalidades Implementadas ✨

*   **Ativação por Hotkey:** Inicia a gravação com uma combinação de teclas configurável (Padrão: `Alt+Shift+S`).
*   **Gravação de Áudio:** Grava áudio do microfone padrão.
*   **Detecção de Silêncio:** Para a gravação automaticamente após um período de silêncio.
*   **Feedback Visual (PySide6):** Exibe uma janela de feedback moderna e animada que mostra:
    *   Status atual: "Ouvindo...", "Processando...", "Inativo".
    *   Visualização de ondas sonoras durante a gravação.
    *   Indicador de processamento.
*   **Transcrição (OpenAI Whisper):** Envia o áudio gravado para a API Whisper para obter a transcrição.
*   **Injeção de Texto:** Insere o texto transcrito na posição atual do cursor do sistema.
*   **Configurável:** Permite definir a chave da API OpenAI e a hotkey via arquivo `.env`.

## Requisitos

*   Python 3.12.8
*   Conta OpenAI com chave de API configurada.
*   Dependências listadas em `requirements.txt`.
*   Microfone funcionando.

## Instalação (Ambiente de Desenvolvimento)

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/StefanoGysin/VoxyScribe.git
    cd VoxyScribe
    ```
2.  **Crie e ative um ambiente virtual (recomendado):**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure as variáveis de ambiente:**
    *   Crie um arquivo chamado `.env` na raiz do projeto.
    *   Copie o conteúdo de `.env.example` para o seu `.env`.
    *   Edite o arquivo `.env` e adicione sua chave da API OpenAI:
        ```dotenv
        OPENAI_API_KEY=sua_chave_api_aqui
        # Opcional: Mude a hotkey (padrão é Alt+Shift+S)
        # Veja a documentação do pynput para formatos válidos:
        # https://pynput.readthedocs.io/en/latest/keyboard.html#monitor-the-keyboard
        HOTKEY_COMBINATION="<alt>+<shift>+s"
        ```

## Uso

1.  **Certifique-se de que seu ambiente virtual está ativado.**
2.  **Execute o script principal:**
    ```bash
    python src/main.py
    ```
3.  A aplicação iniciará em segundo plano. Pressione a combinação de teclas de atalho configurada (padrão: `Alt+Shift+S`) para começar a gravar.
4.  Fale no microfone. A janela de feedback visual aparecerá.
5.  Pare de falar. A gravação será interrompida automaticamente após um período de silêncio e a janela indicará "Processando...".
6.  O texto transcrito será inserido na posição atual do cursor.

## Executando os Testes

O projeto utiliza `pytest` para testes unitários e de integração.

1.  **Certifique-se de que seu ambiente virtual está ativado.**
2.  **Execute os testes:**
    ```bash
    pytest
    ```
3.  **Para verificar a cobertura de testes:**
    ```bash
    pytest --cov=src
    ```
    *(Nota: A cobertura atual é de 36%. Aumentar a cobertura é uma tarefa prioritária.)*

## Problemas Conhecidos e Próximos Passos

*   **Baixa Cobertura de Testes:** A cobertura geral (36%) precisa ser aumentada, especialmente nos módulos `main.py` e `text_injector.py` (0%).
*   **Testes da GUI:** Os testes unitários para `visual_feedback.py` (62% cobertura) podem precisar de revisão adicional para garantir cobertura adequada dos novos comportamentos.
*   **Empacotamento:** A criação de um executável independente (.exe para Windows) ainda não foi implementada.
*   **Ajuste Fino:** A sensibilidade da detecção de silêncio pode precisar de ajustes.
*   **Testes no Windows:** Testes mais extensivos em diferentes cenários do Windows são necessários.

## Contribuição

Contribuições são bem-vindas! Por favor, siga as convenções de código (PEP8, docstrings Google) e adicione testes para novas funcionalidades.

## Autor

**Stefano Gysin** - [GitHub](https://github.com/StefanoGysin)
- Email: stefano.gysin@gmail.com

--- 