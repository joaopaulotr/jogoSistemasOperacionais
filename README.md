# Battle Memory — Batalha de Tanques (jogo em Python)

Uma implementação simples de um jogo de batalha naval/"tanques" em rede usando sockets TCP e threads em Python. O projeto contém um servidor que gerencia o estado do jogo em memória e um cliente de console que o jogador usa para posicionar tanques e atacar o adversário.

## Visão rápida

- Servidor: `servidor.py` — aceita 2 jogadores, gerencia posicionamento e turnos.
- Cliente: `cliente.py` — cliente de console que envia posições e ataques ao servidor.
- Protocolo: JSON sobre TCP (porta padrão 5555).

## Requisitos

- Python 3.7+ (recomendado 3.8+)
- Sistema operacional: Windows, Linux ou macOS

## Estrutura do repositório

- `servidor.py` — lógica do servidor, aceita conexões e gerencia o jogo.
- `cliente.py` — cliente de terminal para jogar.
- `LICENSE` — licença do projeto.
- `README.md` — este arquivo.

## Como executar (Windows PowerShell)

1. Abra dois terminais PowerShell (um para o servidor e outro para o cliente). Primeiro, inicie o servidor:

```powershell
# No terminal 1
python .\servidor.py
```

2. Em outro terminal, inicie o cliente (repita em outro terminal para conectar o segundo jogador):

```powershell
# No terminal 2 (Jogador 1)
python .\cliente.py

# No terminal 3 (Jogador 2)
python .\cliente.py
```

Por padrão o servidor escuta em `localhost` na porta `5555`. Se quiser alterar, edite as constantes `HOST` e `PORTA` em ambos arquivos.

## Como jogar

1. Cada jogador posiciona 3 tanques em posições válidas do tabuleiro 5x5 (linhas A–E, colunas 1–5). Exemplo de posições válidas: `A1`, `B3`, `E5`.
2. Depois que ambos posicionarem, o jogo inicia e os jogadores se alternam atacando uma posição por vez (ex.: `B4`).
3. O servidor informa resultados: acerto (`X`) ou erro (`O`) no tabuleiro inimigo e marca os tanques atingidos no seu próprio tabuleiro.
4. O jogo termina quando todos os tanques de um jogador forem destruídos.

Legenda exibida no cliente:
- T = Seu tanque
- X = Acerto (tanque destruído)
- O = Erro (água)
- ~ = Desconhecido/sem informação

## Protocolo JSON (mensagens relevantes)

O cliente e servidor trocam mensagens JSON simples. Tipos principais observados no código:

- `BEM_VINDO` — servidor -> cliente: mensagem de boas-vindas e número do jogador.
- `POSICIONAR` — servidor -> cliente: solicita posicionar tanques.
- `POSICAO_TANQUE` — cliente -> servidor: posição escolhida para um tanque (ex.: `{ "tipo": "POSICAO_TANQUE", "posicao": "A1" }`).
- `OK` — servidor -> cliente: confirmação de posicionamento.
- `ERRO` — servidor -> cliente: mensagem de erro (posição inválida, já atacada, etc.).
- `JOGO_INICIADO` — servidor -> cliente: indica que o jogo começou.
- `ATUALIZAR` — servidor -> cliente: envia os dois tabuleiros (`meu_tabuleiro` e `tabuleiro_inimigo`) e contagem de tanques.
- `SUA_VEZ` — servidor -> cliente: indica que é a vez do jogador atacar.
- `ATAQUE` — cliente -> servidor: envia um ataque (ex.: `{ "tipo": "ATAQUE", "posicao": "B4" }`).
- `RESULTADO` — servidor -> cliente: resultado do último ataque (`ACERTOU` ou `ERROU`).
- `FIM_DE_JOGO` — servidor -> cliente: informa vencedor e termina o jogo.

Observação: as mensagens são simples JSON serializados em UTF-8 pelo socket TCP.

## Notas técnicas e limitações

- O servidor mantém o estado do jogo em memória e usa `threading.Lock` para sincronização.
- A implementação aceita exatamente 2 jogadores por partida. Conexões extras não são tratadas.
- Não há persistência nem autenticação — é um protótipo educacional.
- O cliente e servidor trocam mensagens via `sock.send`/`sock.recv` sem adicionar um protocolo de framing além do limite do buffer; isso funciona para mensagens curtas mas pode exigir refinamento (por exemplo: prefixar o tamanho da mensagem) para uso em produção.
