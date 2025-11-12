SERVIDOR:

import socket
import threading
import json
import time

# Configurações do servidor
HOST = 'localhost'
PORTA = 5555

tabuleiro_jogador1 = {}  
tabuleiro_jogador2 = {}  
ataques_jogador1 = []    
ataques_jogador2 = []    
tanques_restantes = {1: 3, 2: 3}  
vez_do_jogador = 1       
jogadores_prontos = 0    

lock_jogo = threading.Lock()

# Armazena as conexoes dos clientes
conexoes = {1: None, 2: None}

# Variável para controlar se o jogo já começou
jogo_iniciado = False


def criar_tabuleiro_vazio():
    """Cria um tabuleiro 5x5 vazio para visualização"""
    tabuleiro = {}
    linhas = ['A', 'B', 'C', 'D', 'E']
    for linha in linhas:
        for coluna in range(1, 6):
            posicao = f"{linha}{coluna}"
            tabuleiro[posicao] = '~'  # Água (vazio)
    return tabuleiro


def validar_posicao(posicao):
    """Verifica se uma posição é válida no tabuleiro"""
    if len(posicao) < 2:
        return False
    linha = posicao[0].upper()
    try:
        coluna = int(posicao[1:])
        return linha in ['A', 'B', 'C', 'D', 'E'] and 1 <= coluna <= 5
    except:
        return False


def enviar_mensagem(conexao, mensagem):
    """Envia uma mensagem JSON para o cliente"""
    try:
        dados = json.dumps(mensagem)
        conexao.send(dados.encode('utf-8'))
    except Exception as erro:
        print(f"Erro ao enviar mensagem: {erro}")


def receber_mensagem(conexao):
    """Recebe e decodifica uma mensagem JSON do cliente"""
    try:
        dados = conexao.recv(1024).decode('utf-8')
        if dados:
            return json.loads(dados)
        return None
    except Exception as erro:
        print(f"Erro ao receber mensagem: {erro}")
        return None


def montar_visao_tabuleiro(numero_jogador):
    """Monta a visão dos tabuleiros para um jogador específico"""
    # Meu tabuleiro completo (mostra meus tanques)
    meu_tabuleiro = criar_tabuleiro_vazio()
   
    if numero_jogador == 1:
        # Coloca meus tanques
        for pos in tabuleiro_jogador1:
            if pos in ataques_jogador2:
                meu_tabuleiro[pos] = 'X'  # Tanque atingido
            else:
                meu_tabuleiro[pos] = 'T'  # Tanque intacto
       
        # Mostra meus erros
        for pos in ataques_jogador2:
            if pos not in tabuleiro_jogador1:
                meu_tabuleiro[pos] = 'O'  # Tiro na água
       
        # Tabuleiro do inimigo (só mostra acertos e erros)
        tabuleiro_inimigo = criar_tabuleiro_vazio()
        for pos in ataques_jogador1:
            if pos in tabuleiro_jogador2:
                tabuleiro_inimigo[pos] = 'X'  # Acertou tanque inimigo
            else:
                tabuleiro_inimigo[pos] = 'O'  # Errou
    else:
        # Jogador 2 - mesma lógica invertida
        for pos in tabuleiro_jogador2:
            if pos in ataques_jogador1:
                meu_tabuleiro[pos] = 'X'
            else:
                meu_tabuleiro[pos] = 'T'
       
        for pos in ataques_jogador1:
            if pos not in tabuleiro_jogador2:
                meu_tabuleiro[pos] = 'O'
       
        tabuleiro_inimigo = criar_tabuleiro_vazio()
        for pos in ataques_jogador2:
            if pos in tabuleiro_jogador1:
                tabuleiro_inimigo[pos] = 'X'
            else:
                tabuleiro_inimigo[pos] = 'O'
   
    return meu_tabuleiro, tabuleiro_inimigo


def atualizar_visao_jogadores():
    """Envia atualização dos tabuleiros para ambos jogadores"""
    for num_jogador in [1, 2]:
        if conexoes[num_jogador]:
            meu_tab, inimigo_tab = montar_visao_tabuleiro(num_jogador)
            mensagem = {
                "tipo": "ATUALIZAR",
                "meu_tabuleiro": meu_tab,
                "tabuleiro_inimigo": inimigo_tab,
                "tanques_meus": tanques_restantes[num_jogador],
                "tanques_inimigo": tanques_restantes[3 - num_jogador]
            }
            enviar_mensagem(conexoes[num_jogador], mensagem)


def processar_ataque(numero_jogador, posicao):
    """Processa um ataque de um jogador"""
    global vez_do_jogador, tanques_restantes
   
    # Usar lock para exclusão mútua - apenas uma thread por vez
    with lock_jogo:
        # Verifica se é a vez deste jogador
        if vez_do_jogador != numero_jogador:
            return {"tipo": "ERRO", "mensagem": "Não é a sua vez!"}
       
        # Verifica se a posição é válida
        if not validar_posicao(posicao):
            return {"tipo": "ERRO", "mensagem": "Posição inválida!"}
       
        posicao = posicao.upper()
       
        # Determina qual tabuleiro inimigo atacar
        if numero_jogador == 1:
            tabuleiro_inimigo = tabuleiro_jogador2
            lista_ataques = ataques_jogador1
        else:
            tabuleiro_inimigo = tabuleiro_jogador1
            lista_ataques = ataques_jogador2
       
        # Verifica se já atacou essa posição
        if posicao in lista_ataques:
            return {"tipo": "ERRO", "mensagem": "Você já atacou essa posição!"}
       
        # Registra o ataque
        lista_ataques.append(posicao)
       
        # Verifica se acertou
        if posicao in tabuleiro_inimigo:
            resultado = "ACERTOU"
            tanques_restantes[3 - numero_jogador] -= 1
            print(f"Jogador {numero_jogador} ACERTOU em {posicao}!")
        else:
            resultado = "ERROU"
            print(f"Jogador {numero_jogador} errou em {posicao}")
       
        # Alterna a vez para o outro jogador
        vez_do_jogador = 3 - numero_jogador
       
        # Atualiza a visão de ambos os jogadores
        atualizar_visao_jogadores()
       
        # Verifica se alguém ganhou
        if tanques_restantes[3 - numero_jogador] == 0:
            return {"tipo": "FIM_DE_JOGO", "resultado": resultado, "vencedor": f"Jogador {numero_jogador}"}
       
        return {"tipo": "RESULTADO", "mensagem": resultado}


def gerenciar_cliente(conexao, numero_jogador):
    """Thread que gerencia a comunicação com um cliente"""
    global jogadores_prontos, jogo_iniciado
   
    print(f"Jogador {numero_jogador} conectado!")
   
    # Envia mensagem de boas-vindas
    mensagem_boas_vindas = {
        "tipo": "BEM_VINDO",
        "mensagem": f"Bem-vindo! Você é o Jogador {numero_jogador}",
        "numero_jogador": numero_jogador
    }
    enviar_mensagem(conexao, mensagem_boas_vindas)
   
    # Aguarda o outro jogador se conectar
    while not all(conexoes.values()):
        time.sleep(0.5)
   
    # Solicita posicionamento dos tanques
    mensagem_posicionar = {
        "tipo": "POSICIONAR",
        "mensagem": "Posicione seus 3 tanques (formato: A1, B3, E5)"
    }
    enviar_mensagem(conexao, mensagem_posicionar)
   
    # Recebe as posições dos tanques
    posicoes_recebidas = []
    while len(posicoes_recebidas) < 3:
        resposta = receber_mensagem(conexao)
        if resposta and resposta.get("tipo") == "POSICAO_TANQUE":
            pos = resposta.get("posicao", "").upper()
           
            if not validar_posicao(pos):
                enviar_mensagem(conexao, {"tipo": "ERRO", "mensagem": "Posição inválida!"})
                continue
           
            if pos in posicoes_recebidas:
                enviar_mensagem(conexao, {"tipo": "ERRO", "mensagem": "Posição já ocupada!"})
                continue
           
            posicoes_recebidas.append(pos)
            enviar_mensagem(conexao, {"tipo": "OK", "mensagem": f"Tanque {len(posicoes_recebidas)}/3 posicionado em {pos}"})
   
    # Salva as posições no tabuleiro correspondente (exclusão mútua)
    with lock_jogo:
        if numero_jogador == 1:
            for pos in posicoes_recebidas:
                tabuleiro_jogador1[pos] = True
        else:
            for pos in posicoes_recebidas:
                tabuleiro_jogador2[pos] = True
       
        jogadores_prontos += 1
        print(f"Jogador {numero_jogador} finalizou posicionamento: {posicoes_recebidas}")
   
    # Aguarda ambos jogadores finalizarem o posicionamento
    while jogadores_prontos < 2:
        time.sleep(0.5)
   
    # Inicia o jogo
    if not jogo_iniciado:
        jogo_iniciado = True
        print("\n=== JOGO INICIADO ===\n")
   
    enviar_mensagem(conexao, {"tipo": "JOGO_INICIADO", "mensagem": "O jogo começou!"})
    atualizar_visao_jogadores()
   
    # Loop principal do jogo
    while tanques_restantes[1] > 0 and tanques_restantes[2] > 0:
        # Informa de quem é a vez
        if vez_do_jogador == numero_jogador:
            enviar_mensagem(conexao, {"tipo": "SUA_VEZ", "mensagem": "É a sua vez de atacar!"})
       
        # Recebe ações do cliente
        mensagem = receber_mensagem(conexao)
       
        if not mensagem:
            break
       
        if mensagem.get("tipo") == "ATAQUE":
            posicao = mensagem.get("posicao", "")
            resultado = processar_ataque(numero_jogador, posicao)
            enviar_mensagem(conexao, resultado)
           
            # Se o jogo terminou, notifica o outro jogador
            if resultado.get("tipo") == "FIM_DE_JOGO":
                outro_jogador = 3 - numero_jogador
                if conexoes[outro_jogador]:
                    enviar_mensagem(conexoes[outro_jogador], resultado)
                break
   
    print(f"Jogador {numero_jogador} desconectado")
    conexao.close()


def iniciar_servidor():
    """Função principal que inicia o servidor"""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORTA))
    servidor.listen(2)
   
    print("=" * 50)
    print("    BATTLE MEMORY - SERVIDOR DE BATALHA")
    print("=" * 50)
    print(f"Servidor ouvindo em {HOST}:{PORTA}")
    print("Aguardando 2 jogadores se conectarem...\n")
   
    # Aceita conexões dos dois jogadores
    for numero_jogador in [1, 2]:
        conexao, endereco = servidor.accept()
        conexoes[numero_jogador] = conexao
       
        # Cria uma thread para gerenciar este cliente (concorrência)
        thread_cliente = threading.Thread(target=gerenciar_cliente, args=(conexao, numero_jogador))
        thread_cliente.start()
   
    print("Dois jogadores conectados! Partida em andamento...\n")


if _name_ == "_main_":
    iniciar_servidor()