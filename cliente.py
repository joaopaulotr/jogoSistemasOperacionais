import socket
import json
import threading
import time
import queue
import os

# Configurações de conexão
HOST = 'localhost'
PORTA = 5555

# Variáveis globais do cliente
numero_jogador = None
meu_tabuleiro = {}
tabuleiro_inimigo = {}
jogo_ativo = True
prompt_ativo = ""  # Armazena o prompt atual para reimpressão

# Eventos para sincronização entre threads
evento_posicionar = threading.Event()
evento_jogo_iniciado = threading.Event()
evento_sua_vez = threading.Event()

# Queue para respostas de posicionamento
respostas_queue = queue.Queue()

# Lock para variáveis compartilhadas
lock = threading.Lock()


def limpar_tela():
    """Limpa a tela do terminal"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def desenhar_tabuleiro(tabuleiro, titulo):
    """Desenha um tabuleiro formatado no terminal"""
    print(f"\n{titulo}")
    print("   1  2  3  4  5 6 7 8")
    linhas = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    
    for linha in linhas:
        print(f"{linha} ", end="")
        for coluna in range(1, 6):
            posicao = f"{linha}{coluna}"
            simbolo = tabuleiro.get(posicao, '~')
            
            if simbolo == 'T':
                print(f" T ", end="")
            elif simbolo == 'X':
                print(f" X ", end="")
            elif simbolo == 'O':
                print(f" O ", end="")
            else:
                print(f" ~ ", end="")
        print()


def enviar_mensagem(sock, mensagem):
    try:
        dados = json.dumps(mensagem) + "\n"
        sock.sendall(dados.encode('utf-8'))
    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
        print("⚠ conexão perdida com o servidor. encerrando jogo...")
        global jogo_ativo
        jogo_ativo = False
    except Exception as erro:
        print(f"erro ao enviar mensagem: {erro}")


def receber_mensagens(sock):
    """Thread que fica recebendo mensagens do servidor continuamente"""
    global jogo_ativo, meu_tabuleiro, tabuleiro_inimigo, numero_jogador, prompt_ativo
    
    buffer = ""
    
    while jogo_ativo:
        try:
            chunk = sock.recv(2048).decode('utf-8')
            if not chunk:
                break
            
            buffer += chunk
            
           
            while "\n" in buffer:
                linha, buffer = buffer.split("\n", 1)
                
                if not linha.strip():
                    continue
                
                try:
                    mensagem = json.loads(linha)
                    
                    tipo = mensagem.get("tipo")
                    
                    if tipo == "BEM_VINDO":
                        with lock:
                            numero_jogador = mensagem.get("numero_jogador")
                        print(f"\n{mensagem.get('mensagem')}")
                        print("Aguardando outro jogador...\n")
                    
                    elif tipo == "POSICIONAR":
                        print(f"\n{mensagem.get('mensagem')}")
                        print("Digite as posições uma por vez (ex: A1, B3, E5)\n")
                        evento_posicionar.set()
                    
                    elif tipo == "OK":
                        print(f"✓ {mensagem.get('mensagem')}")
                        respostas_queue.put(mensagem)
                    
                    elif tipo == "ERRO":
                        erro_msg = mensagem.get('mensagem')
                        print(f"\n✗ ERRO: {erro_msg}")
                        respostas_queue.put(mensagem)
                        # Se é durante o jogo e ainda é sua vez, mantém evento ativo e pede nova entrada
                        if prompt_ativo and evento_sua_vez.is_set():
                            print("Tente novamente!")
                            print(prompt_ativo, end="", flush=True)
                    
                    elif tipo == "JOGO_INICIADO":
                        limpar_tela()
                        print("\n" + "=" * 50)
                        print("      A BATALHA COMEÇOU!")
                        print("=" * 50)
                        print(f"\nVocê é o Jogador {numero_jogador}")
                        print("\nLegenda:")
                        print("  T = Seu tanque")
                        print("  X = Acerto")
                        print("  O = Erro (água)")
                        print("  ~ = Desconhecido\n")
                        evento_jogo_iniciado.set()
                    
                    elif tipo == "ATUALIZAR":
                        with lock:
                            meu_tabuleiro = mensagem.get("meu_tabuleiro", {})
                            tabuleiro_inimigo = mensagem.get("tabuleiro_inimigo", {})
                        
                        limpar_tela()
                        print("\n" + "=" * 50)
                        desenhar_tabuleiro(meu_tabuleiro, "MEU CAMPO")
                        desenhar_tabuleiro(tabuleiro_inimigo, "CAMPO INIMIGO")
                        print("=" * 50)
                        
                        tanques_meus = mensagem.get("tanques_meus", 0)
                        tanques_inimigo = mensagem.get("tanques_inimigo", 0)
                        print(f"\nTanques restantes: Você = {tanques_meus} | Inimigo = {tanques_inimigo}")
                    
                    elif tipo == "SUA_VEZ":
                        prompt_ativo = "Sua jogada (ex: B4): "
                        print(f"\n>>> Sua vez de atacar!")
                        print(prompt_ativo, end="", flush=True)
                        evento_sua_vez.set()
                    
                    elif tipo == "RESULTADO":
                        resultado = mensagem.get("mensagem")
                        if resultado == "ACERTOU":
                            print(f"\n🎯 ACERTOU! Você destruiu um tanque inimigo!")
                        else:
                            print(f"\n💧 ERROU! Seu tiro caiu na água...")
                        print("Aguarde a jogada do adversário...")
                        # Limpa o evento pois a vez passou para o outro jogador
                        evento_sua_vez.clear()
                    
                    elif tipo == "FIM_DE_JOGO":
                        limpar_tela()
                        desenhar_tabuleiro(meu_tabuleiro, "MEU CAMPO")
                        desenhar_tabuleiro(tabuleiro_inimigo, "CAMPO INIMIGO")
                        
                        vencedor = mensagem.get("vencedor")
                        print("\n" + "=" * 50)
                        if vencedor == f"Jogador {numero_jogador}":
                            print("     🏆 VITÓRIA! VOCÊ VENCEU A BATALHA! 🏆")
                        else:
                            print(f"     💀 DERROTA! Seus {tanques_meus} tanques foram destruídos!")
                        print("=" * 50)
                        print("\nPressione Enter para sair...")
                        
                        jogo_ativo = False
                        evento_sua_vez.set()  # Libera input() se estiver bloqueado
                        break
                
                except json.JSONDecodeError as e:
                    print(f"JSON inválido recebido: {e}")
                    continue
        
        except socket.timeout:
            print("\nTimeout - servidor não respondeu. Encerrando conexão...")
            jogo_ativo = False
            break
        except Exception as erro:
            if jogo_ativo:
                print(f"\nErro na conexão: {erro}")
            break


def posicionar_tanques(sock):
    """Solicita ao usuário o posicionamento dos tanques"""
    
    # Aguarda a mensagem "POSICIONAR" do servidor
    evento_posicionar.wait()
    
    tanques_posicionados = 0
    
    while tanques_posicionados < 3:0
        try:
            posicao = input(f"Tanque {tanques_posicionados + 1}/3: ").strip().upper()
            
            # Envia a posição para o servidor
            mensagem = {
                "tipo": "POSICAO_TANQUE",
                "posicao": posicao
            }
            enviar_mensagem(sock, mensagem)
            
            # Aguarda resposta do servidor (OK ou ERRO)
            try:
                resposta = respostas_queue.get(timeout=5)
            except queue.Empty:
                print("⚠ Sem resposta do servidor, tente novamente")
                continue
            
            # Só incrementa se recebeu OK
            if resposta.get("tipo") == "OK":
                tanques_posicionados += 1
            # Se ERRO, a mensagem já foi impressa por receber_mensagens
            
        except KeyboardInterrupt:
            print("\nSaindo do jogo...")
            return False
    
    print("\nTodos os tanques posicionados! Aguardando adversário finalizar...\n")
    return True


def jogar(sock):
    """Loop principal do jogo onde o jogador pode atacar"""
    global jogo_ativo
    
    # Aguarda o jogo começar
    evento_jogo_iniciado.wait()
    
    while jogo_ativo:
        try:
            # Bloqueia até ser sua vez
            evento_sua_vez.wait()
            
            # Verifica se o jogo ainda está ativo após espera
            if not jogo_ativo:
                break
            
            entrada = input().strip().upper()
            
            # Se jogo terminou enquanto aguardava input, sai
            if not jogo_ativo:
                break
            
            if entrada:
                mensagem = {
                    "tipo": "ATAQUE",
                    "posicao": entrada
                }
                enviar_mensagem(sock, mensagem)
                # NÃO limpa o evento aqui - só limpa quando receber RESULTADO válido
        
        except KeyboardInterrupt:
            print("\nSaindo do jogo...")
            jogo_ativo = False
            break


def conectar_ao_servidor():
    """Conecta ao servidor e inicia o jogo"""
    global jogo_ativo
   
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Define timeout de 60 segundos para detectar servidor travado
        sock.settimeout(60.0)
        sock.connect((HOST, PORTA))
       
        print("=" * 50)
        print("    BATTLE MEMORY - BATALHA DE TANQUES")
        print("=" * 50)
        print(f"Conectado ao servidor {HOST}:{PORTA}\n")
       
        # Inicia a thread que recebe mensagens do servidor
        thread_receber = threading.Thread(target=receber_mensagens, args=(sock,))
        thread_receber.daemon = True
        thread_receber.start()
       
        # Fase de posicionamento dos tanques
        if not posicionar_tanques(sock):
            return
       
        # Aguarda o jogo começar e entra no loop principal
        jogar(sock)
        
        # Encerra a conexão de forma limpa
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except:
            pass
        sock.close()
   
    except ConnectionRefusedError:
        print("Erro: Não foi possível conectar ao servidor.")
        print("Verifique se o servidor está rodando!")
    except Exception as erro:
        print(f"Erro inesperado: {erro}")
    finally:
        jogo_ativo = False


if __name__ == "__main__":
    conectar_ao_servidor()