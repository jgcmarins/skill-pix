---
name: pix
description: Gera QR code Pix estático (imagem PNG + código copia e cola) a partir só da chave Pix, com valor opcional. Use quando o usuário digitar /pix (ex.: "/pix pix@exemplo.com 100,00") ou pedir para gerar um QR code ou código Pix.
---

# Gerador de QR code Pix estático

Gera um BR Code Pix estático no padrão do Banco Central. Funciona com chave cadastrada em qualquer banco e é lido por qualquer app de banco. Não usa API: só monta o código e gera a imagem.

## Passo 1: entender o pedido

Argumentos do comando: `$ARGUMENTS`

Se a linha acima estiver vazia ou mostrar o texto `$ARGUMENTS` sem substituição (Claude web ou app desktop), use a mensagem do usuário.

Só a **chave Pix** é obrigatória. O **valor** é opcional: sem valor, quem paga digita na hora. Chave e valor podem vir em qualquer ordem (`/pix pix@exemplo.com 100,00` ou `/pix 100,00 pix@exemplo.com`).

- Se veio a chave, gere direto. Não peça nome, cidade nem mais nada.
- Se não veio a chave, peça só a chave e diga que o valor é opcional.
- Não invente nenhum dado.
- Só passe nome, cidade, identificador (`--txid`) ou descrição se o usuário informar por conta própria.

Telefone precisa de DDI e DDD. Um número de 11 dígitos, como `48999999999`, é lido como CPF. Se o script recusar dizendo que o CPF é inválido, pergunte se é telefone e, se for, use `+5548999999999`.

## Passo 2: gerar

Os scripts ficam em `scripts/`, dentro da pasta desta skill. No Claude Code o caminho é `${CLAUDE_SKILL_DIR}/scripts/run.sh`. Se esse texto aparecer sem ser substituído (Claude web ou app desktop), use o caminho absoluto da pasta onde está este SKILL.md.

Rode sempre pelo `run.sh`. Ele instala a biblioteca `qrcode` na primeira vez, num ambiente isolado, sem mexer no Python do sistema. Passe a chave e o valor como argumentos separados, cada um entre aspas simples. O script descobre qual é qual:

```bash
bash "${CLAUDE_SKILL_DIR}/scripts/run.sh" 'CHAVE' ['VALOR'] [--terminal escuro] --saida pix.png
```

Opcionais, só se o usuário informar: `--nome 'NOME'`, `--cidade 'CIDADE'`, `--txid PEDIDO123`, `--descricao 'texto'`.

Escolha a saída conforme onde você está rodando:

- **Claude web ou app desktop (chat)**, onde existe `/mnt/user-data/outputs`: use `--saida /mnt/user-data/outputs/pix.png` e não use `--terminal`.
- **Claude Code (terminal)**: use `--terminal escuro` e `--saida pix.png` (diretório atual). Se o usuário disser que o terminal tem fundo claro, use `--terminal claro`.

Saída do script:

- Primeira linha do stdout: o código copia e cola. Ele sai mesmo se a geração da imagem falhar.
- Com `--terminal`, depois de uma linha em branco vem o QR desenhado com os caracteres `█ ▀ ▄` e espaço.
- No stderr: `Legenda: ...` e `Rodapé: ...`, os mesmos textos escritos embaixo do QR na imagem.
- Se der erro, o script imprime `ERRO: ...` e sai com código diferente de 0. Explique o erro ao usuário e peça o dado corrigido.

O script já trata sozinho: nome `PIX` e cidade `BRASIL` quando não informados (o app do banco mostra o nome do cadastro da chave, não o do QR), remoção de acentos, formato do valor (aceita `150`, `150,00`, `1.234,56`, `R$ 10`), limpeza e validação de CPF/CNPJ e cálculo do CRC16.

## Passo 3: entregar

Entregue ao usuário, nesta ordem:

1. O QR code:
   - **Claude web ou app desktop**: a imagem `pix.png`. A legenda e o rodapé já estão escritos nela.
   - **Claude Code**: o QR em texto, num bloco ` ```text `, copiado **exatamente** como o script imprimiu, linha por linha, sem tirar nem acrescentar nenhum caractere ou espaço. Qualquer diferença pode deixar o QR ilegível. Depois do bloco, informe o caminho do `pix.png` e diga que, se o celular não ler o QR do terminal, dá para abrir a imagem (no macOS: `open pix.png`).
2. O código copia e cola, num bloco de código para facilitar copiar.
3. A legenda, em negrito, exatamente como o script imprimiu. Ex.: **Pix para pix@exemplo.com no valor de R$ 100,00**.
4. O rodapé, exatamente como o script imprimiu: Pix gerado utilizando a skill pix ([github.com/jgcmarins/skill-pix](https://github.com/jgcmarins/skill-pix))

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
| 59 | Nome, até 25 caracteres (padrão `PIX`) |
| 60 | Cidade, até 15 caracteres (padrão `BRASIL`) |
| 62 | `05` = txid, até 25 alfanuméricos, ou `***` |
| 63 | CRC16-CCITT (polinômio 0x1021, inicial 0xFFFF), 4 caracteres hexadecimais maiúsculos |

O script foi validado contra o exemplo oficial do Manual do BR Code do Banco Central.
