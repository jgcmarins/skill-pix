"""Testes do gerador de Pix. Rode com: python3 -m unittest discover -s tests -v"""
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "skills", "pix", "scripts")
sys.path.insert(0, SCRIPTS)

import pix  # noqa: E402

try:
    import qrcode  # noqa: F401
except ImportError:
    qrcode = None

try:
    import cv2
    import numpy as np
except ImportError:  # leitura do QR é opcional fora do CI
    cv2 = None

# Exemplo oficial do Manual do BR Code do Banco Central
OFICIAL = ("00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-426655440000"
           "5204000053039865802BR5913Fulano de Tal6008BRASILIA62070503***63041D3D")


def ler_qr(imagem):
    texto, _, _ = cv2.QRCodeDetector().detectAndDecode(imagem)
    return texto


def texto_para_imagem(linhas, tema):
    """Converte o QR desenhado com meios-blocos de volta em imagem."""
    pixels = []
    for linha in linhas:
        pixels.append([c in "█▀" for c in linha])
        pixels.append([c in "█▄" for c in linha])
    claro = np.array(pixels, dtype=bool)
    if tema == "claro":
        claro = ~claro
    img = np.pad(np.where(claro, 255, 0).astype(np.uint8), 4, constant_values=255)
    return cv2.resize(img, None, fx=10, fy=10, interpolation=cv2.INTER_NEAREST)


class TestPayload(unittest.TestCase):
    def test_exemplo_oficial_do_banco_central(self):
        self.assertEqual(
            pix.gerar_payload("123e4567-e12b-12d1-a456-426655440000", "Fulano de Tal", "BRASILIA"),
            OFICIAL,
        )

    def test_crc16(self):
        self.assertEqual(pix.crc16(OFICIAL[:-4]), "1D3D")

    def test_so_a_chave_usa_nome_e_cidade_padrao(self):
        p = pix.gerar_payload("pix@exemplo.com")
        self.assertIn("5903PIX6006BRASIL", p)
        self.assertNotIn("54", p[p.index("5303986"):p.index("5802BR")])  # sem valor

    def test_nome_e_cidade_informados(self):
        p = pix.gerar_payload("pix@exemplo.com", "João Conceição", "Florianópolis")
        self.assertIn("5914Joao Conceicao6013Florianopolis", p)

    def test_limites_de_nome_e_cidade(self):
        p = pix.gerar_payload("pix@exemplo.com", "Maria da Silva Santos Oliveira", "Sao Jose dos Campos")
        self.assertIn("5925Maria da Silva Santos Oli", p)
        self.assertIn("6015Sao Jose dos Ca", p)

    def test_valor_txid_e_descricao(self):
        p = pix.gerar_payload("+5548999999999", valor="25,90", txid="PEDIDO-123", descricao="Almoço")
        self.assertIn("0206Almoco", p)
        self.assertIn("540525.90", p)
        self.assertIn("62130509PEDIDO123", p)


class TestValor(unittest.TestCase):
    def test_formatos_aceitos(self):
        casos = {
            "150": "150.00", "150.00": "150.00", "150,5": "150.50", "1.234,56": "1234.56",
            "1,234.56": "1234.56", "R$ 10": "10.00", "R$10,00": "10.00", "1.234.567": "1234567.00",
        }
        for entrada, esperado in casos.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(pix.normalizar_valor(entrada), esperado)

    def test_valores_invalidos(self):
        for entrada in ["0", "0.001", "-5", "nan", "inf", "abc", "99999999999999"]:
            with self.subTest(entrada=entrada):
                with self.assertRaises(ValueError):
                    pix.normalizar_valor(entrada)

    def test_valor_br(self):
        self.assertEqual(pix.valor_br("1.00"), "1,00")
        self.assertEqual(pix.valor_br("1234567.89"), "1.234.567,89")


class TestChave(unittest.TestCase):
    def test_chaves_validas(self):
        casos = {
            "Pix@Exemplo.com": "pix@exemplo.com",
            "529.982.247-25": "52998224725",
            "11.222.333/0001-81": "11222333000181",
            "+55 (48) 99999-9999": "+5548999999999",
            "5548999999999": "+5548999999999",
            "123E4567-E12B-12D1-A456-426655440000": "123e4567-e12b-12d1-a456-426655440000",
        }
        for entrada, esperado in casos.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(pix.normalizar_chave(entrada), esperado)

    def test_chaves_invalidas(self):
        for entrada in ["48999999999", "11.222.333/0001-80", "+1 555 1234", "çã@exemplo.com", "abc"]:
            with self.subTest(entrada=entrada):
                with self.assertRaises(ValueError):
                    pix.normalizar_chave(entrada)

    def test_chave_legivel(self):
        self.assertEqual(pix.chave_legivel("52998224725"), "529.982.247-25")
        self.assertEqual(pix.chave_legivel("11222333000181"), "11.222.333/0001-81")
        self.assertEqual(pix.chave_legivel("+5548999999999"), "+55 (48) 99999-9999")
        self.assertEqual(pix.chave_legivel("pix@exemplo.com"), "pix@exemplo.com")


class TestEntradaLivre(unittest.TestCase):
    def test_qualquer_ordem(self):
        casos = [
            (["pix@exemplo.com", "100,00"], ("pix@exemplo.com", "100,00")),
            (["100,00", "pix@exemplo.com"], ("pix@exemplo.com", "100,00")),
            (["pix@exemplo.com"], ("pix@exemplo.com", None)),
            (["R$", "1.234,56", "+55", "48", "99999-9999"], ("+5548999999999", "R$1.234,56")),
            (["529.982.247-25", "R$10"], ("529.982.247-25", "R$10")),
            (["52998224725", "10", "reais"], ("52998224725", "10")),
            (["10", "11222333000181"], ("11222333000181", "10")),
            (["5548999999999", "5"], ("5548999999999", "5")),
            (["123e4567-e12b-12d1-a456-426655440000 50"], ("123e4567-e12b-12d1-a456-426655440000", "50")),
        ]
        for tokens, esperado in casos:
            with self.subTest(tokens=tokens):
                self.assertEqual(pix.separar_entrada(tokens), esperado)

    def test_entradas_ambiguas(self):
        for tokens in [["10", "20"], ["a@b.com", "c@d.com"], ["100,00"], []]:
            with self.subTest(tokens=tokens):
                with self.assertRaises(ValueError):
                    pix.separar_entrada(tokens)


class TestLegenda(unittest.TestCase):
    def test_com_valor(self):
        self.assertEqual(pix.legenda("pix@exemplo.com", "100.00"),
                         "Pix para pix@exemplo.com no valor de R$ 100,00")

    def test_sem_valor(self):
        self.assertEqual(pix.legenda("52998224725", None), "Pix para 529.982.247-25")

    def test_rodape(self):
        self.assertEqual(pix.rodape(),
                         "Pix gerado utilizando a skill pix (github.com/jgcmarins/skill-pix)")


@unittest.skipIf(qrcode is None, "biblioteca qrcode não instalada")
class TestCli(unittest.TestCase):
    def rodar(self, *args):
        with tempfile.TemporaryDirectory() as tmp:
            saida = os.path.join(tmp, "pix.png")
            r = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "pix.py"), *args, "--saida", saida],
                capture_output=True, text=True,
            )
            imagem = cv2.imread(saida) if cv2 is not None and os.path.exists(saida) else None
            return r, imagem

    def test_erro_sai_com_codigo_1(self):
        r, _ = self.rodar("pix@exemplo.com", "-5")
        self.assertEqual(r.returncode, 1)
        self.assertIn("ERRO:", r.stderr)

    def test_chave_e_valor_em_qualquer_ordem(self):
        r1, _ = self.rodar("pix@exemplo.com", "100,00")
        r2, _ = self.rodar("100,00", "pix@exemplo.com")
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertEqual(r1.stdout, r2.stdout)
        self.assertIn("5406100.00", r1.stdout.splitlines()[0])
        self.assertIn("Legenda: Pix para pix@exemplo.com no valor de R$ 100,00", r1.stderr)

    def test_flags_continuam_funcionando(self):
        r, _ = self.rodar("--chave", "pix@exemplo.com", "--valor", "5", "--nome", "Ana", "--cidade", "Recife")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("54045.005802BR5903Ana6006Recife", r.stdout)

    @unittest.skipIf(cv2 is None, "opencv não instalado")
    def test_png_com_legenda_continua_legivel(self):
        r, imagem = self.rodar("pix@exemplo.com", "R$ 1.234,56")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((imagem[-100:] < 128).any(), "sem legenda embaixo do QR")
        self.assertEqual(ler_qr(imagem), r.stdout.splitlines()[0])

    @unittest.skipIf(cv2 is None, "opencv não instalado")
    def test_qr_no_terminal_e_legivel(self):
        for tema in ("escuro", "claro"):
            with self.subTest(tema=tema):
                r, _ = self.rodar("pix@exemplo.com", "10", "--terminal", tema)
                self.assertEqual(r.returncode, 0, r.stderr)
                payload, vazio, *linhas = r.stdout.splitlines()
                self.assertEqual(vazio, "")
                self.assertTrue(all(set(l) <= set("█▀▄ ") for l in linhas))
                self.assertEqual(ler_qr(texto_para_imagem(linhas, tema)), payload)


class TestSkillMd(unittest.TestCase):
    def test_um_unico_marcador_de_argumentos(self):
        # O Claude Code substitui todas as ocorrências; uma segunda vira texto sem sentido.
        with open(os.path.join(SCRIPTS, "..", "SKILL.md"), encoding="utf-8") as f:
            self.assertEqual(f.read().count("$ARGUMENTS"), 1)


if __name__ == "__main__":
    unittest.main()
