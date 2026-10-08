#!/usr/bin/env python3
"""Gera BR Code Pix estático (copia e cola) e imagem PNG do QR code.

Uso:
  python pix.py CHAVE [VALOR]                  # chave e valor em qualquer ordem
  python pix.py --chave CHAVE [--valor 10.50] [--nome NOME] [--cidade CIDADE]
                [--txid ID] [--descricao TEXTO] [--terminal escuro|claro]
                [--saida pix.png]
"""
import argparse
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import sys
import unicodedata

# Nome e cidade são obrigatórios no BR Code, mas o app do banco mostra o nome
# do cadastro da chave no Banco Central (DICT). Testado em vários bancos.
NOME_PADRAO = "PIX"
CIDADE_PADRAO = "BRASIL"

SKILL_NOME = "pix"
SKILL_LINK = "github.com/jgcmarins/skill-pix"

EVP = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def limpar(texto: str, limite: int) -> str:
    """Remove acentos e caracteres fora do padrão, corta no limite."""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9 .,\-/@+]", "", t).strip()
    return t[:limite].strip()


def cpf_valido(d: str) -> bool:
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10) % 11 % 10 != int(d[n]):
            return False
    return True


def cnpj_valido(d: str) -> bool:
    if len(d) != 14 or d == d[0] * 14:
        return False
    for n in (12, 13):
        pesos = list(range(n - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(d[i]) * pesos[i] for i in range(n))
        dv = 11 - soma % 11
        if (0 if dv >= 10 else dv) != int(d[n]):
            return False
    return True


def normalizar_valor(valor) -> str:
    """Aceita 150, 150.00, 150,00, 1.234,56, 1,234.56 e R$ 10. Devolve '150.00'."""
    if "-" in str(valor):
        raise ValueError("Valor deve ser maior que zero.")
    v = re.sub(r"[^\d.,]", "", str(valor))
    if "," in v and "." in v:
        # o último separador é o decimal
        if v.rfind(",") > v.rfind("."):
            v = v.replace(".", "").replace(",", ".")
        else:
            v = v.replace(",", "")
    elif "," in v:
        v = v.replace(",", ".")
    elif v.count(".") > 1:
        v = v.replace(".", "")  # 1.234.567
    try:
        d = Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise ValueError(f"Valor inválido: {valor!r}. Use, por exemplo, 150.00 ou 150,00.")
    if d <= 0:
        raise ValueError("Valor deve ser maior que zero.")
    texto = f"{d:.2f}"
    if len(texto) > 13:
        raise ValueError("Valor grande demais.")
    return texto


def normalizar_chave(chave: str) -> str:
    c = chave.strip()
    if "@" in c:  # e-mail
        if not c.isascii() or " " in c:
            raise ValueError(f"E-mail inválido: {chave!r}.")
        return c.lower()
    if EVP.fullmatch(c):
        return c.lower()  # chave aleatória
    digitos = re.sub(r"\D", "", c)
    if c.startswith("+"):
        if not (digitos.startswith("55") and len(digitos) in (12, 13)):
            raise ValueError(
                f"Telefone inválido: {chave!r}. Use DDI 55 + DDD + número, ex.: +5548999999999."
            )
        return "+" + digitos  # telefone já com DDI
    if len(digitos) == 11:
        if not cpf_valido(digitos):
            raise ValueError(
                f"CPF inválido: {chave!r}. Se for telefone, use o formato +55{digitos}."
            )
        return digitos  # CPF (telefone precisa vir com +55)
    if len(digitos) == 14:
        if not cnpj_valido(digitos):
            raise ValueError(f"CNPJ inválido: {chave!r}. Confira os dígitos.")
        return digitos
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        return "+" + digitos  # telefone com 55 sem o +
    raise ValueError(
        f"Chave não reconhecida: {chave!r}. Use CPF/CNPJ, e-mail, chave aleatória "
        "ou telefone no formato +5548999999999."
    )


def parece_valor(token: str) -> bool:
    """Diz se um pedaço da entrada livre é o valor (e não a chave)."""
    t = token.strip()
    if t.upper().startswith("R$"):
        return True
    if not re.fullmatch(r"[\d.,]+", t):
        return False  # e-mail, telefone com +, chave aleatória, CPF/CNPJ com - ou /
    if t.isdigit() and len(t) in (11, 14):
        return False  # CPF ou CNPJ sem formatação
    if t.isdigit() and len(t) in (12, 13) and t.startswith("55"):
        return False  # telefone com 55 sem o +
    return True


def separar_entrada(tokens) -> tuple:
    """Separa chave e valor de uma entrada livre, em qualquer ordem.

    Ex.: ["pix@exemplo.com", "100,00"], ["R$", "100", "+55", "48", "99999-9999"].
    """
    texto = " ".join(tokens)
    texto = re.sub(r"(?i)\b(reais|real)\b", "", texto)
    texto = re.sub(r"(?i)R\$\s+", "R$", texto)
    # junta telefone digitado com espaços: +55 48 99999-9999
    texto = re.sub(r"\+[\d\s()\-]+\d", lambda m: re.sub(r"[\s()\-]", "", m.group()), texto)

    chave = valor = None
    for t in texto.split():
        if parece_valor(t):
            if valor is not None:
                raise ValueError(f"Mais de um valor na entrada: {valor!r} e {t!r}.")
            valor = t
        else:
            if chave is not None:
                raise ValueError(f"Mais de uma chave na entrada: {chave!r} e {t!r}.")
            chave = t
    if chave is None:
        raise ValueError("Falta a chave Pix.")
    return chave, valor


def valor_br(valor: str) -> str:
    """'1234.50' -> '1.234,50'."""
    inteiro, centavos = valor.split(".")
    return f"{int(inteiro):,}".replace(",", ".") + "," + centavos


def chave_legivel(chave: str) -> str:
    """Formata CPF, CNPJ e telefone para exibição. Outras chaves ficam iguais."""
    if chave.startswith("+55") and len(chave) in (13, 14):
        ddd, num = chave[3:5], chave[5:]
        return f"+55 ({ddd}) {num[:-4]}-{num[-4:]}"
    if chave.isdigit() and len(chave) == 11:
        return f"{chave[:3]}.{chave[3:6]}.{chave[6:9]}-{chave[9:]}"
    if chave.isdigit() and len(chave) == 14:
        return f"{chave[:2]}.{chave[2:5]}.{chave[5:8]}/{chave[8:12]}-{chave[12:]}"
    return chave


def legenda(chave: str, valor) -> str:
    texto = f"Pix para {chave_legivel(chave)}"
    if valor is not None:
        texto += f" no valor de R$ {valor_br(valor)}"
    return texto


def rodape() -> str:
    return f"Pix gerado utilizando a skill {SKILL_NOME} ({SKILL_LINK})"


def campo(id_: str, valor: str) -> str:
    if len(valor) > 99:
        raise ValueError(f"Campo {id_} passa de 99 caracteres.")
    return f"{id_}{len(valor):02d}{valor}"


def crc16(payload: str) -> str:
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def gerar_payload(chave, nome=None, cidade=None, valor=None, txid=None, descricao=None) -> str:
    chave = normalizar_chave(chave)
    nome = limpar(nome or "", 25) or NOME_PADRAO
    cidade = limpar(cidade or "", 15) or CIDADE_PADRAO

    conta = campo("00", "br.gov.bcb.pix") + campo("01", chave)
    if descricao:
        desc = limpar(descricao, 99)
        espaco = 99 - len(conta) - 4
        if espaco > 0 and desc:
            conta += campo("02", desc[:espaco])

    p = campo("00", "01")
    p += campo("26", conta)
    p += campo("52", "0000")
    p += campo("53", "986")
    if valor is not None:
        p += campo("54", normalizar_valor(valor))
    p += campo("58", "BR")
    p += campo("59", nome)
    p += campo("60", cidade)
    tx = re.sub(r"[^A-Za-z0-9]", "", txid or "")[:25] or "***"
    p += campo("62", campo("05", tx))
    p += "6304"
    return p + crc16(p)


def qr_texto(qr, tema: str = "escuro", borda: int = 2) -> str:
    """Desenha o QR com meios-blocos Unicode, dois módulos por linha (como o Expo).

    No tema escuro o fundo do terminal é escuro, então os módulos claros do QR
    (incluindo a margem) são desenhados como blocos cheios.
    """
    m = qr.get_matrix()  # já inclui a borda do QRCode (border=0 aqui)
    n = len(m)
    tamanho = n + 2 * borda

    def claro(y, x):
        y, x = y - borda, x - borda
        escuro = 0 <= y < n and 0 <= x < n and m[y][x]
        return not escuro

    preenchido = claro if tema == "escuro" else (lambda y, x: not claro(y, x))
    linhas = []
    for y in range(0, tamanho, 2):
        linha = ""
        for x in range(tamanho):
            cima = preenchido(y, x)
            baixo = preenchido(y + 1, x) if y + 1 < tamanho else tema == "escuro"
            linha += "█" if cima and baixo else "▀" if cima else "▄" if baixo else " "
        linhas.append(linha)
    return "\n".join(linhas)


def _fonte(tamanho: int):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=tamanho)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def _encaixar(draw, opcoes, largura, tamanhos):
    """Escolhe o maior tamanho de fonte em que alguma opção de quebra de linha cabe."""
    for tamanho in tamanhos:
        fonte = _fonte(tamanho)
        for linhas in opcoes:
            if all(draw.textlength(l, font=fonte) <= largura for l in linhas):
                return linhas, fonte
    return opcoes[-1], _fonte(tamanhos[-1])


def gerar_imagem(payload: str, chave: str, valor, saida: str) -> None:
    """Salva o QR com a legenda embaixo: para quem é o Pix, o valor e o rodapé da skill."""
    import qrcode
    from PIL import Image, ImageDraw

    qr = qrcode.make(payload, error_correction=qrcode.constants.ERROR_CORRECT_M,
                     box_size=10, border=4).get_image().convert("RGB")
    largura = max(qr.width, 640)
    margem = 32
    util = largura - 2 * margem
    rascunho = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    principal = legenda(chave, valor)
    opcoes = [[principal]]
    if valor is not None:
        opcoes.append([f"Pix para {chave_legivel(chave)}", f"no valor de R$ {valor_br(valor)}"])
    linhas_p, fonte_p = _encaixar(rascunho, opcoes, util, range(30, 13, -2))
    linhas_r, fonte_r = _encaixar(
        rascunho,
        [[rodape()], [f"Pix gerado utilizando a skill {SKILL_NOME}", SKILL_LINK]],
        util, range(18, 11, -1),
    )

    def altura(fonte):
        caixa = fonte.getbbox("Ag")
        return caixa[3] - caixa[1]

    esp = 10
    alt_p = len(linhas_p) * (altura(fonte_p) + esp)
    alt_r = len(linhas_r) * (altura(fonte_r) + esp)
    altura_total = qr.height + alt_p + 16 + alt_r + margem
    img = Image.new("RGB", (largura, altura_total), "white")
    img.paste(qr, ((largura - qr.width) // 2, 0))
    d = ImageDraw.Draw(img)

    y = qr.height
    for linha, fonte, cor in [(l, fonte_p, (17, 17, 17)) for l in linhas_p] + \
                             [(None, None, None)] + \
                             [(l, fonte_r, (110, 110, 110)) for l in linhas_r]:
        if linha is None:
            y += 16
            continue
        w = d.textlength(linha, font=fonte)
        d.text(((largura - w) / 2, y), linha, font=fonte, fill=cor)
        y += altura(fonte) + esp
    img.save(saida)


def main():
    ap = argparse.ArgumentParser(description="Gera QR code Pix estático.")
    ap.add_argument("entrada", nargs="*",
                    help="chave e valor em qualquer ordem, ex.: pix@exemplo.com 100,00")
    ap.add_argument("--chave")
    ap.add_argument("--valor")
    ap.add_argument("--nome", help=f"opcional; padrão {NOME_PADRAO}")
    ap.add_argument("--cidade", help=f"opcional; padrão {CIDADE_PADRAO}")
    ap.add_argument("--txid")
    ap.add_argument("--descricao")
    ap.add_argument("--saida", default="pix.png")
    ap.add_argument("--terminal", choices=["escuro", "claro"],
                    help="também desenha o QR em texto, para terminal com fundo escuro ou claro")
    a = ap.parse_args()

    try:
        chave, valor = a.chave, a.valor
        if a.entrada:
            chave_e, valor_e = separar_entrada(a.entrada) if a.chave is None else (None, None)
            if a.chave is not None:
                # chave já veio por flag: a entrada livre só pode ser o valor
                valor_e = " ".join(a.entrada)
            chave = chave or chave_e
            if valor is None:
                valor = valor_e
        if not chave:
            raise ValueError("Falta a chave Pix.")
        payload = gerar_payload(chave, a.nome, a.cidade, valor, a.txid, a.descricao)
        chave_n = normalizar_chave(chave)
        valor_n = normalizar_valor(valor) if valor is not None else None
    except ValueError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)

    print(payload)
    try:
        import qrcode  # pip install "qrcode[pil]==8.2"
    except ImportError:
        print('ERRO: falta a biblioteca qrcode. Rode: python3 -m pip install "qrcode[pil]==8.2"', file=sys.stderr)
        sys.exit(2)

    if a.terminal:
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
        qr.add_data(payload)
        qr.make(fit=True)
        print()
        print(qr_texto(qr, a.terminal))

    gerar_imagem(payload, chave_n, valor_n, a.saida)
    print(f"Legenda: {legenda(chave_n, valor_n)}", file=sys.stderr)
    print(f"Rodapé: {rodape()}", file=sys.stderr)
    print(f"QR salvo em: {a.saida}", file=sys.stderr)


if __name__ == "__main__":
    main()
