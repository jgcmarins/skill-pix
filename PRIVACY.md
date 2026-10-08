# Política de privacidade — skill pix

Última atualização: 7 de outubro de 2026

A skill pix gera QR codes Pix estáticos localmente. Ela não opera nenhum servidor.

## O que a skill coleta

Nada. O autor da skill não recebe, armazena nem tem acesso a nenhum dado seu.

## Como os dados são usados

A chave Pix, o nome, a cidade, o valor, o identificador e a descrição que você informa são usados apenas para montar o código Pix (BR Code) e a imagem do QR code. O processamento acontece no ambiente de execução de código do Claude ou na sua máquina.

## Conexões de rede

O script não faz nenhuma requisição de rede. A única conexão possível é a instalação da biblioteca `qrcode` (versão 8.2) pelo PyPI, feita pelo `pip` quando ela ainda não está instalada, num ambiente isolado em `~/.cache/skill-pix/venv`. Nenhum dado seu é enviado nessa instalação.

## Dados na conversa

O que você digita na conversa é tratado pela Anthropic conforme a política de privacidade do Claude: https://www.anthropic.com/legal/privacy

## Contato

Dúvidas: https://github.com/jgcmarins/skill-pix/issues
