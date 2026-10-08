# pix — skill do Claude para QR code Pix

[![CI](https://github.com/jgcmarins/skill-pix/actions/workflows/ci.yml/badge.svg)](https://github.com/jgcmarins/skill-pix/actions/workflows/ci.yml)

Gera QR code Pix **estático** (imagem PNG + código copia e cola) só com a chave Pix, no padrão BR Code do Banco Central. Funciona com chave de qualquer banco e é lido por qualquer app de banco. Não usa API nem precisa de conta em serviço nenhum.

```
/pix:pix pix@exemplo.com 100,00
```

Chave e valor em qualquer ordem. O valor é opcional: sem ele, quem paga digita na hora. No Claude web e no app desktop, basta pedir "gera um QR code pix para pix@exemplo.com".

## Dados

| Dado | Obrigatório | Observação |
|------|-------------|------------|
| Chave Pix | Sim | CPF, CNPJ, e-mail, telefone (`+5511999999999`) ou chave aleatória |
| Valor | Não | Aceita `100`, `100,00`, `1.234,56`, `R$ 10`. Sem valor, quem paga digita |
| Nome do recebedor | Não | Padrão `PIX`. O app do banco mostra o nome do cadastro da chave, não o do QR |
| Cidade | Não | Padrão `BRASIL` |
| Identificador (txid) | Não | Até 25 letras e números |
| Descrição | Não | Muitos bancos não mostram |

Nome e cidade são campos obrigatórios do BR Code, mas o nome que o pagador vê vem do cadastro da chave no Banco Central. Por isso a skill preenche valores padrão e não pergunta. Isso foi testado com leitura do QR e com copia e cola em vários bancos.

## Instalação

### Claude web e app desktop (claude.ai)

1. Ative a execução de código em **Settings > Capabilities** ("Code execution and file creation").
2. Em **Customize > Plugins**, clique em **Add > Add marketplace** e cole `jgcmarins/skill-pix`.
3. Instale o plugin **pix** e peça: "gera um QR code pix".

Alternativa: baixe o `pix.zip` da [página de releases](https://github.com/jgcmarins/skill-pix/releases) e suba em **Customize > Skills** > "+" > "Upload a skill".

### Claude Code

Dentro de uma sessão:

```
/plugin marketplace add jgcmarins/skill-pix
/plugin install pix@skill-pix
```

Ou pelo terminal:

```bash
claude plugin marketplace add jgcmarins/skill-pix
claude plugin install pix@skill-pix
```

Depois, numa sessão, digite `/pix:pix pix@exemplo.com 100,00` ou peça "gera um QR code pix". No Claude Code, skills de plugin aparecem com o nome do plugin na frente, por isso o comando é `/pix:pix`.

## Onde o QR aparece

- **Claude web e app desktop**: o Claude devolve a imagem PNG do QR code. Embaixo do QR vem escrito "Pix para {chave} no valor de R$ {valor}" e o rodapé "Pix gerado utilizando a skill pix (github.com/jgcmarins/skill-pix)".
- **Claude Code (terminal)**: o QR aparece desenhado no próprio terminal, com caracteres de bloco (como o `expo start` faz), e a imagem PNG fica salva no diretório atual.

## Uso direto do script

O script também funciona sozinho. O `run.sh` instala a biblioteca `qrcode` na primeira vez, num ambiente isolado em `~/.cache/skill-pix/venv`:

```bash
bash skills/pix/scripts/run.sh pix@exemplo.com 25,00 --terminal escuro --saida pix.png
```

O código copia e cola sai no terminal, seguido do QR em texto (`--terminal escuro` ou `--terminal claro`, conforme o fundo do seu terminal). A imagem é salva em `pix.png`. Opcionais: `--nome`, `--cidade`, `--txid`, `--descricao`.

## Testes

```bash
python3 -m pip install "qrcode[pil]==8.2" opencv-python-headless
python3 -m unittest discover -s tests -v
```

Os testes conferem o payload contra o exemplo oficial do Banco Central, a leitura de chave e valor em qualquer ordem, e leem de volta, com um leitor de QR, tanto a imagem quanto o QR desenhado no terminal. O CI roda os testes e o `claude plugin validate` a cada push.

## Dados e privacidade

- Tudo roda localmente, no ambiente de execução de código do Claude ou na sua máquina. O script **não envia nenhum dado** para servidor algum: não chama API, não tem telemetria e não guarda nada além da imagem que você pedir.
- A única conexão de rede é a instalação da biblioteca [`qrcode`](https://pypi.org/project/qrcode/) (versão fixa `8.2`) pelo PyPI, e só quando ela ainda não está instalada. Ela é instalada num ambiente isolado (`~/.cache/skill-pix/venv`), sem alterar o Python do sistema.
- Os dados que você informa (chave, nome, cidade, valor) ficam na conversa com o Claude, como qualquer mensagem.

Detalhes em [PRIVACY.md](PRIVACY.md).

## Avisos

- A skill **só gera o código**. Ela não confere se a chave existe nem de quem ela é. Confira a chave antes de divulgar o QR: chave errada manda o dinheiro para outra pessoa.
- QR estático **não confirma o pagamento** automaticamente. Confira no extrato.
- O mesmo QR pode ser pago **mais de uma vez**.
- O nome que o pagador vê no app vem do cadastro da chave no Banco Central, não do QR.

## Como funciona

O script monta o payload no formato EMV definido pelo Manual do BR Code do Banco Central e calcula o CRC16-CCITT no final. A saída foi validada contra o exemplo oficial do manual.

## Licença

MIT
