#!/usr/bin/env python3
"""Gera BR Code Pix estático (copia e cola) e imagem PNG do QR code.

Uso:
  python pix.py --chave CHAVE --nome NOME --cidade CIDADE [--valor 10.50]
                [--txid ID] [--descricao TEXTO] [--saida pix.png]
"""
import argparse
import re
import sys
import unicodedata


def limpar(texto: str, limite: int) -> str:
    """Remove acentos e caracteres fora do padrão, corta no limite."""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9 .,\-/@+]", "", t).strip()
    return t[:limite]


def normalizar_chave(chave: str) -> str:
    c = chave.strip()
    if "@" in c:  # e-mail
        return c.lower()
    if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", c):
        return c.lower()  # chave aleatória
    digitos = re.sub(r"\D", "", c)
    if c.startswith("+"):
        return "+" + digitos  # telefone já com DDI
    if len(digitos) in (11, 14):
        return digitos  # CPF ou CNPJ (telefone precisa vir com +55)
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
        v = float(str(valor).replace(",", "."))
        if v <= 0:
            raise ValueError("Valor deve ser maior que zero.")
        p += campo("54", f"{v:.2f}")
    p += campo("58", "BR")
    p += campo("59", nome)
    p += campo("60", cidade)
    tx = re.sub(r"[^A-Za-z0-9]", "", txid or "")[:25] or "***"
    p += campo("62", campo("05", tx))
    p += "6304"
    return p + crc16(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chave", required=True)
    ap.add_argument("--nome", required=True)
    ap.add_argument("--cidade", required=True)
    ap.add_argument("--valor")
    ap.add_argument("--txid")
    ap.add_argument("--descricao")
    ap.add_argument("--saida", default="pix.png")
    a = ap.parse_args()

    try:
        payload = gerar_payload(a.chave, a.nome, a.cidade, a.valor, a.txid, a.descricao)
    except ValueError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)

    import qrcode  # pip install "qrcode[pil]"
    img = qrcode.make(payload, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    img.save(a.saida)
    print(payload)
    print(f"QR salvo em: {a.saida}", file=sys.stderr)


if __name__ == "__main__":
    main()
