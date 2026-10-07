# pix — skill do Claude para QR code Pix

Use com `/pix`.

Gera QR code Pix **estático** (imagem PNG + código copia e cola) para qualquer chave Pix, no padrão BR Code do Banco Central. Funciona com chave de qualquer banco e é lido por qualquer app de banco. Não usa API nem precisa de conta em serviço nenhum.

Você pede um QR code Pix, o Claude pergunta os dados e devolve a imagem e o código.

## Dados pedidos

| Dado | Obrigatório | Observação |
|------|-------------|------------|
| Chave Pix | Sim | CPF, CNPJ, e-mail, telefone (`+5511999999999`) ou chave aleatória |
| Nome do recebedor | Sim | Até 25 caracteres. Acentos são removidos |
| Cidade | Sim | Até 15 caracteres |
| Valor | Não | Sem valor, quem paga digita |
| Identificador (txid) | Não | Até 25 letras e números |
| Descrição | Não | Muitos bancos não mostram |

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

Depois, numa sessão, digite `/pix` ou peça "gera um QR code pix".

## Uso direto do script

O script também funciona sozinho:

```bash
pip install "qrcode[pil]==8.2"
python3 skills/pix/scripts/pix.py --chave "email@exemplo.com" --nome "Maria Silva" \
  --cidade "Sao Paulo" --valor 25.00 --saida pix.png
```

O código copia e cola sai no terminal e a imagem é salva em `pix.png`.

## Dados e privacidade

- Tudo roda localmente, no ambiente de execução de código do Claude ou na sua máquina. O script **não envia nenhum dado** para servidor algum: não chama API, não tem telemetria e não guarda nada além da imagem que você pedir.
- A única conexão de rede é a instalação da biblioteca [`qrcode`](https://pypi.org/project/qrcode/) (versão fixa `8.2`) pelo PyPI, e só quando ela ainda não está instalada.
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
