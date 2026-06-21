"""
Entry point for ``python -m agilang``.

This simply forwards to ``agilang.cli.main``.
"""

from .cli import main


if __name__ == "__main__":
    main()