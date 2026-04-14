"""Ermöglicht Aufruf via: python -m collmex."""

import sys

# Windows-Konsole: stdout/stderr auf UTF-8 umstellen,
# damit Umlaute aus Collmex (ö, ä, ü) korrekt dargestellt werden.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from collmex.cli import main

main()
