#!/usr/bin/env python3

from __future__ import annotations

import sys

from kanton_skewers_app.application import Application


if __name__ == "__main__":
    raise SystemExit(Application().run(sys.argv[1:]))
