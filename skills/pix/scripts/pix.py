#!/usr/bin/env python3
"""Gera BR Code Pix estático (copia e cola) e imagem PNG do QR code.

Uso:
  python pix.py --chave CHAVE --nome NOME --cidade CIDADE [--valor 10.50]
                [--txid ID] [--descricao TEXTO] [--saida pix.png]
"""
import argparse
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import sys
import unicodedata


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
    if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", c):
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


def gerar_payload(chave, nome, cidade, valor=None, txid=None, descricao=None) -> str:
    chave = normalizar_chave(chave)
    nome = limpar(nome, 25)
    cidade = limpar(cidade, 15)
    if not nome or not cidade:
        raise ValueError("Nome e cidade são obrigatórios.")

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chave", required=True)
    ap.add_argument("--nome", required=True)
    ap.add_argument("--cidade", required=True)
    ap.add_argument("--valor")
    ap.add_argument("--txid")
    ap.add_argument("--descricao")
    ap.add_argument("--saida", default="pix.png")
    ap.add_argument("--terminal", choices=["escuro", "claro"],
                    help="também desenha o QR em texto, para terminal com fundo escuro ou claro")
    a = ap.parse_args()

    try:
        payload = gerar_payload(a.chave, a.nome, a.cidade, a.valor, a.txid, a.descricao)
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

    img = qrcode.make(payload, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    img.save(a.saida)
    print(f"QR salvo em: {a.saida}", file=sys.stderr)

if __name__ == "__main__":
    main()
