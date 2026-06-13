from __future__ import annotations

import sys

from kanton_skewers_app.application import Application


def main() -> int:
    return Application().run(sys.argv[1:])
