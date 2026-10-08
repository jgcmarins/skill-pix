#!/usr/bin/env bash
# Roda pix.py garantindo a biblioteca qrcode, sem mexer no Python do sistema.
# Ordem: Python do sistema (se já tiver qrcode) > venv próprio da skill > pip do sistema.
set -e
export PIP_DISABLE_PIP_VERSION_CHECK=1
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$(command -v python3 || command -v python)" || { echo "ERRO: Python 3 não encontrado." >&2; exit 2; }
PACOTE="qrcode[pil]==8.2"
VENV="${PIX_VENV:-$HOME/.cache/skill-pix/venv}"

if "$PY" -c "import qrcode" 2>/dev/null; then
  exec "$PY" "$DIR/pix.py" "$@"
fi

if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c "import qrcode" 2>/dev/null; then
  exec "$VENV/bin/python" "$DIR/pix.py" "$@"
fi

echo "Instalando $PACOTE (só na primeira vez)..." >&2
if "$PY" -m venv "$VENV" >/dev/null 2>&1 && "$VENV/bin/python" -m pip install -q "$PACOTE" >&2; then
  exec "$VENV/bin/python" "$DIR/pix.py" "$@"
fi

# Sem venv disponível (ex.: Linux sem python3-venv): tenta o pip do sistema.
rm -rf "$VENV"
"$PY" -m pip install -q "$PACOTE" >&2 2>/dev/null \
  || "$PY" -m pip install -q --user "$PACOTE" >&2 2>/dev/null \
  || "$PY" -m pip install -q --break-system-packages "$PACOTE" >&2
exec "$PY" "$DIR/pix.py" "$@"
