import socket
import json
import threading
import time

# Configurações de conexão
HOST = 'localhost'
PORTA = 5555

# Variáveis globais do cliente
numero_jogador = None
meu_tabuleiro = {}
tabuleiro_inimigo = {}
jogo_ativo = True


def limpar_tela():
    """Limpa a tela do terminal"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def desenhar_tabuleiro(tabuleiro, titulo):
    """Desenha um tabuleiro formatado no terminal"""
    print(f"\n{titulo}")
    print("   1  2  3  4  5")
    linhas = ['A', 'B', 'C', 'D', 'E']
    
    for linha in linhas:
        print(f"{linha} ", end="")
        for coluna in range(1, 6):
            posicao = f"{linha}{coluna}"
            simbolo = tabuleiro.get(posicao, '~')
            
            # Adiciona cores para melhor visualização
            if simbolo == 'T':
                print(f" T ", end="")  # Tanque
            elif simbolo == 'X':
                print(f" X ", end="")  # Acerto
            elif simbolo == 'O':
                print(f" O ", end="")  # Erro
            else:
                print(f" ~ ", end="")  # Água
        print()


def enviar_mensagem(sock, mensagem):
    """Envia uma mensagem JSON para o servidor"""
    try:
        dados = json.dumps(mensagem)
        sock.send(dados.encode('utf-8'))
    except Exception as erro:
        print(f"Erro ao enviar mensagem: {erro}")


def receber_mensagens(sock):
    """Thread que fica recebendo mensagens do servidor continuamente"""
    global jogo_ativo, meu_tabuleiro, tabuleiro_inimigo
    
    while jogo_ativo:
        try:
            dados = sock.recv(2048).decode('utf-8')
            if not dados:
                break
            
            mensagem = json.loads(dados)
            tipo = mensagem.get("tipo")
            
            # Processa diferentes tipos de mensagens
            if tipo == "BEM_VINDO":
                global numero_jogador
                numero_jogador = mensagem.get("numero_jogador")
                print(f"\n{mensagem.get('mensagem')}")
                print("Aguardando outro jogador...\n")
            
            elif tipo == "POSICIONAR":
                print(f"\n{mensagem.get('mensagem')}")
                print("Digite as posições uma por vez (ex: A1, B3, E5)\n")
            
            elif tipo == "OK":
                print(f"✓ {mensagem.get('mensagem')}")
            
            elif tipo == "ERRO":
                print(f"✗ ERRO: {mensagem.get('mensagem')}")
            
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
            
            elif tipo == "ATUALIZAR":
                # Atualiza os tabuleiros
                meu_tabuleiro = mensagem.get("meu_tabuleiro", {})
                tabuleiro_inimigo = mensagem.get("tabuleiro_inimigo", {})
                
                # Mostra os tabuleiros atualizados
                limpar_tela()
                print("\n" + "=" * 50)
                desenhar_tabuleiro(meu_tabuleiro, "MEU CAMPO")
                desenhar_tabuleiro(tabuleiro_inimigo, "CAMPO INIMIGO")
                print("=" * 50)
                
                tanques_meus = mensagem.get("tanques_meus", 0)
                tanques_inimigo = mensagem.get("tanques_inimigo", 0)
                print(f"\nTanques restantes: Você = {tanques_meus} | Inimigo = {tanques_inimigo}")
            
            elif tipo == "SUA_VEZ":
                print(f"\n>>> {mensagem.get('mensagem')}")
                print("Digite a posição para atacar (ex: B4): ", end="", flush=True)
            
            elif tipo == "RESULTADO":
                resultado = mensagem.get("mensagem")
                if resultado == "ACERTOU":
                    print(f"\n🎯 ACERTOU! Você destruiu um tanque inimigo!")
                else:
                    print(f"\n💧 ERROU! Seu tiro caiu na água...")
                print("\nAguardando jogada do adversário...")
            
            elif tipo == "FIM_DE_JOGO":
                limpar_tela()
                desenhar_tabuleiro(meu_tabuleiro, "MEU CAMPO")
                desenhar_tabuleiro(tabuleiro_inimigo, "CAMPO INIMIGO")
                
                vencedor = mensagem.get("vencedor")
                print("\n" + "=" * 50)
                if vencedor == f"Jogador {numero_jogador}":
                    print("     🏆 VITÓRIA! VOCÊ VENCEU A BATALHA! 🏆")
                else:
                    print("     💀 DERROTA! Seus tanques foram destruídos!")
                print("=" * 50)
                
                jogo_ativo = False
                break
        
        except Exception as erro:
            if jogo_ativo:
                print(f"\nErro na conexão: {erro}")
            break


def posicionar_tanques(sock):
    """Solicita ao usuário o posicionamento dos tanques"""
    tanques_posicionados = 0
    
    while tanques_posicionados < 3:
        try:
            posicao = input(f"Tanque {tanques_posicionados + 1}/3: ").strip().upper()
            
            # Envia a posição para o servidor
            mensagem = {
                "tipo": "POSICAO_TANQUE",
                "posicao": posicao
            }
            enviar_mensagem(sock, mensagem)
            
            # Aguarda resposta (a thread de receber vai processar)
            time.sleep(0.2)
            
            # Verifica se foi aceito (de forma simplificada)
            tanques_posicionados += 1
            
        except KeyboardInterrupt:
            print("\nSaindo do jogo...")
            return False
    
    print("\nTodos os tanques posicionados! Aguardando adversário finalizar...\n")
    return True


def jogar(sock):
    """Loop principal do jogo onde o jogador pode atacar"""
    global jogo_ativo
    
    # Aguarda o jogo começar
    time.sleep(1)
    
    while jogo_ativo:
        try:
            # Lê a entrada do jogador
            entrada = input().strip().upper()
            
            if entrada:
                # Envia o ataque
                mensagem = {
                    "tipo": "ATAQUE",
                    "posicao": entrada
                }
                enviar_mensagem(sock, mensagem)
        
        except KeyboardInterrupt:
            print("\nSaindo do jogo...")
            jogo_ativo = False
            break
