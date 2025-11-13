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

# Armazena as conexões dos clientes
conexoes = {1: None, 2: None}

# Buffers de recebimento por conexão
buffers_conexao = {}

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
        dados = json.dumps(mensagem) + "\n"
        conexao.sendall(dados.encode('utf-8'))
        return True
    except Exception as erro:
        print(f"Erro ao enviar mensagem (cliente desconectou?): {erro}")
        return False


def limpar_conexao_jogador(numero_jogador):
    """Remove conexão de jogador desconectado e notifica o outro"""
    with lock_jogo:
        if conexoes[numero_jogador]:
            conn_id = id(conexoes[numero_jogador])
            buffers_conexao.pop(conn_id, None)
            try:
                conexoes[numero_jogador].close()
            except:
                pass
            conexoes[numero_jogador] = None
        
        # Notifica o outro jogador
        outro_jogador = 3 - numero_jogador
        conexao_outro = conexoes.get(outro_jogador)
    
    if conexao_outro:
        enviar_mensagem(conexao_outro, {
            "tipo": "ERRO",
            "mensagem": f"Jogador {numero_jogador} desconectou. Jogo encerrado."
        })


def receber_mensagem(conexao):
    """Recebe e decodifica uma mensagem JSON do cliente"""
    # Usa id da conexão como chave para o buffer
    conn_id = id(conexao)
    buffer = buffers_conexao.get(conn_id, '')
    
    try:
        while "\n" not in buffer:
            chunk = conexao.recv(1024).decode('utf-8')
            if not chunk:
                # Limpa buffer ao desconectar
                buffers_conexao.pop(conn_id, None)
                return None
            buffer += chunk
        
        linha, buffer = buffer.split("\n", 1)
        buffers_conexao[conn_id] = buffer
        
        if linha.strip():
            return json.loads(linha)
        return None
    except socket.timeout:
        print(f"Timeout ao receber mensagem - cliente inativo")
        return None
    except Exception as erro:
        print(f"Erro ao receber mensagem: {erro}")
        buffers_conexao.pop(conn_id, None)
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
    # Copia conexões sob lock para evitar condição de corrida
    with lock_jogo:
        conexoes_copy = dict(conexoes)
    
    for num_jogador in [1, 2]:
        if conexoes_copy[num_jogador]:
            meu_tab, inimigo_tab = montar_visao_tabuleiro(num_jogador)
            mensagem = {
                "tipo": "ATUALIZAR",
                "meu_tabuleiro": meu_tab,
                "tabuleiro_inimigo": inimigo_tab,
                "tanques_meus": tanques_restantes[num_jogador],
                "tanques_inimigo": tanques_restantes[3 - num_jogador]
            }
            enviar_mensagem(conexoes_copy[num_jogador], mensagem)


def processar_ataque(numero_jogador, posicao):
    """Processa um ataque de um jogador"""
    global vez_do_jogador, tanques_restantes
   
    # Usar lock para exclusão mútua
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
        proximo_jogador = vez_do_jogador
        
        # Verifica se alguém ganhou
        if tanques_restantes[3 - numero_jogador] == 0:
            print(f"\n*** JOGO TERMINADO - Jogador {numero_jogador} venceu! ***")
            # Atualiza visão antes de terminar (ainda dentro do lock)
            # Copia conexões para usar fora do lock
            conexoes_fim = dict(conexoes)
    
    # Sai do lock antes de enviar mensagens
    
    # Se alguém ganhou, envia FIM_DE_JOGO para AMBOS
    if tanques_restantes[3 - numero_jogador] == 0:
        atualizar_visao_jogadores()
        
        mensagem_fim = {
            "tipo": "FIM_DE_JOGO", 
            "resultado": resultado, 
            "vencedor": f"Jogador {numero_jogador}"
        }
        
        # Envia para AMBOS jogadores
        for num in [1, 2]:
            if conexoes_fim.get(num):
                print(f"Enviando FIM_DE_JOGO para Jogador {num}")
                enviar_mensagem(conexoes_fim[num], mensagem_fim)
        
        return mensagem_fim
    
    # Atualiza a visão de ambos os jogadores (fora do lock)
    atualizar_visao_jogadores()
    
    # Notifica o próximo jogador que é sua vez (fora do lock)
    with lock_jogo:
        conexao_proxima = conexoes.get(proximo_jogador)
    
    if conexao_proxima:
        enviar_mensagem(conexao_proxima, {"tipo": "SUA_VEZ", "mensagem": "É a sua vez de atacar!"})
    
    return {"tipo": "RESULTADO", "mensagem": resultado}


def gerenciar_cliente(conexao, numero_jogador):
    """Thread que gerencia a comunicação com um cliente"""
    global jogadores_prontos, jogo_iniciado
    
    # Define timeout de 60 segundos para detectar clientes travados
    conexao.settimeout(60.0)
    
    print(f"Jogador {numero_jogador} conectado!")
    
    # Registra a conexão sob lock
    with lock_jogo:
        conexoes[numero_jogador] = conexao
    
    # Envia mensagem de boas-vindas
    mensagem_boas_vindas = {
        "tipo": "BEM_VINDO",
        "mensagem": f"Bem-vindo! Você é o Jogador {numero_jogador}",
        "numero_jogador": numero_jogador
    }
    enviar_mensagem(conexao, mensagem_boas_vindas)
    
    # Aguarda o outro jogador se conectar
    while True:
        with lock_jogo:
            if all(conexoes.values()):
                break
        time.sleep(0.5)
    
    # Aguarda um tempo para garantir que ambos receberam a mensagem de boas-vindas
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
        
        if not resposta:
            print(f"Jogador {numero_jogador} desconectou durante posicionamento")
            limpar_conexao_jogador(numero_jogador)
            return
        
        if resposta.get("tipo") == "POSICAO_TANQUE":
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
    while True:
        with lock_jogo:
            if jogadores_prontos >= 2:
                break
        time.sleep(0.5)
   
    # Inicia o jogo - só uma vez para ambos
    with lock_jogo:
        if not jogo_iniciado:
            jogo_iniciado = True
            print("\n=== JOGO INICIADO ===\n")
            # Copia conexões para notificar fora do lock
            conexoes_copy = dict(conexoes)
        else:
            conexoes_copy = None
    
    # Notifica fora do lock para evitar deadlock
    if conexoes_copy:
        for num in [1, 2]:
            if conexoes_copy[num]:
                enviar_mensagem(conexoes_copy[num], {"tipo": "JOGO_INICIADO", "mensagem": "O jogo começou!"})
        # Atualiza a visão dos tabuleiros
        atualizar_visao_jogadores()
        # Notifica o Jogador 1 que é sua vez
        if conexoes_copy[1]:
            enviar_mensagem(conexoes_copy[1], {"tipo": "SUA_VEZ", "mensagem": "É a sua vez de atacar!"})
    else:
        # Se o jogo já foi iniciado, apenas aguarda
        time.sleep(0.5)
   
    # Loop principal do jogo
    jogo_em_andamento = True
    while jogo_em_andamento:
        # Recebe ações do cliente
        mensagem = receber_mensagem(conexao)
       
        if not mensagem:
            print(f"Jogador {numero_jogador} desconectou durante o jogo")
            limpar_conexao_jogador(numero_jogador)
            break
       
        if mensagem.get("tipo") == "ATAQUE":
            posicao = mensagem.get("posicao", "")
            resultado = processar_ataque(numero_jogador, posicao)
            
            # Tenta enviar resultado
            if not enviar_mensagem(conexao, resultado):
                print(f"Jogador {numero_jogador} desconectou ao enviar resultado")
                limpar_conexao_jogador(numero_jogador)
                break
            
            # Se foi ERRO (posição inválida, já atacada, etc), mantém a vez do jogador
            if resultado.get("tipo") == "ERRO":
                enviar_mensagem(conexao, {"tipo": "SUA_VEZ", "mensagem": "É a sua vez de atacar!"})
                continue
           
            # Se o jogo terminou, sai do loop (FIM_DE_JOGO já foi enviado por processar_ataque)
            if resultado.get("tipo") == "FIM_DE_JOGO":
                print(f"Thread do Jogador {numero_jogador} encerrando - jogo finalizado")
                break
   
    print(f"Jogador {numero_jogador} desconectado")
    
    # Limpa a conexão e buffer ao final
    conn_id = id(conexao)
    buffers_conexao.pop(conn_id, None)
    
    with lock_jogo:
        if conexoes[numero_jogador]:
            try:
                conexao.close()
            except:
                pass
            conexoes[numero_jogador] = None


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
        
        # Cria uma thread para gerenciar este cliente (a conexão será registrada na thread)
        thread_cliente = threading.Thread(target=gerenciar_cliente, args=(conexao, numero_jogador))
        thread_cliente.start()
    
    print("Dois jogadores conectados! Partida em andamento...\n")


if __name__ == "__main__":
    iniciar_servidor()