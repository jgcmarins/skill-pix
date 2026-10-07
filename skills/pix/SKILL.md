---
name: pix
description: Gera QR code Pix estático (imagem PNG + código copia e cola) para qualquer pessoa ou empresa, a partir de chave, nome, cidade e valor. Use quando o usuário digitar /pix ou pedir para gerar um QR code ou código Pix.
---

# Gerador de QR code Pix estático

Gera um BR Code Pix estático no padrão do Banco Central. Funciona com chave cadastrada em qualquer banco e é lido por qualquer app de banco. Não usa API: só monta o código e gera a imagem.

## Passo 1: pedir os dados

Se o usuário não passou todos os dados na mensagem, peça numa única mensagem, nesta ordem:

1. **Chave Pix** (obrigatório): CPF, CNPJ, e-mail, telefone ou chave aleatória
2. **Nome do recebedor** (obrigatório)
3. **Cidade do recebedor** (obrigatório)
4. **Valor** (opcional): se não informar, quem paga digita o valor
5. **Identificador** (opcional): código para achar o pagamento no extrato, ex.: `PEDIDO123`
6. **Descrição** (opcional): muitos bancos não mostram

Não invente nenhum dado. Se faltar chave, nome ou cidade, pergunte de novo.

Telefone precisa ter DDI e DDD. Se o usuário passar só `48999999999`, isso tem 11 dígitos e seria lido como CPF. Nesse caso, pergunte se é telefone e, se for, use `+5548999999999`.

## Passo 2: gerar

O script fica em `scripts/pix.py`, dentro da pasta desta skill. No Claude Code o caminho é `${CLAUDE_SKILL_DIR}/scripts/pix.py`. Se esse texto aparecer sem ser substituído (Claude web), use o caminho absoluto da pasta onde está este SKILL.md.

Confira a dependência e instale só se faltar:

```bash
python3 -c "import qrcode" 2>/dev/null || pip install "qrcode[pil]==8.2" || pip install "qrcode[pil]==8.2" --break-system-packages
```

Rode:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/pix.py" --chave "CHAVE" --nome "NOME" --cidade "CIDADE" \
  [--valor 150.00] [--txid PEDIDO123] [--descricao "texto"] --saida pix.png
```

- Salve a imagem onde o usuário consiga abrir: no Claude web, em `/mnt/user-data/outputs/pix.png`; no Claude Code, no diretório atual.
- A saída padrão (stdout) é o código copia e cola. Ele sai mesmo se a geração da imagem falhar.
- Se der erro, o script imprime `ERRO: ...` e sai com código diferente de 0. Explique o erro ao usuário e peça o dado corrigido.

O script já trata sozinho: remoção de acentos, limite de 25 caracteres no nome e 15 na cidade, formato do valor (aceita `150`, `150,00`, `1.234,56`, `R$ 10`), limpeza do CPF/CNPJ formatado, validação dos dígitos de CPF/CNPJ e cálculo do CRC16.

## Passo 3: entregar

Entregue ao usuário:

1. A imagem `pix.png`
2. O código copia e cola, num bloco de código para facilitar copiar
3. Um resumo curto: recebedor, chave e valor (ou "valor livre")

Avise, em uma linha, que o QR estático:
- não confirma o pagamento automaticamente (confira no extrato)
- pode ser pago mais de uma vez

## Referência técnica

Campos do payload (formato EMV: ID de 2 dígitos + tamanho de 2 dígitos + valor):

| ID | Conteúdo |
|----|----------|
| 00 | `01` (versão) |
| 26 | Conta: `00` = `br.gov.bcb.pix`, `01` = chave, `02` = descrição (campo 26 inteiro até 99 caracteres) |
| 52 | `0000` |
| 53 | `986` (real) |
| 54 | Valor, ex.: `150.00` (opcional) |
| 58 | `BR` |
| 59 | Nome, até 25 caracteres |
| 60 | Cidade, até 15 caracteres |
| 62 | `05` = txid, até 25 alfanuméricos, ou `***` |
| 63 | CRC16-CCITT (polinômio 0x1021, inicial 0xFFFF), 4 caracteres hexadecimais maiúsculos |

O script foi validado contra o exemplo oficial do Manual do BR Code do Banco Central.
