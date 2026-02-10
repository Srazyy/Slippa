"""
Entry point for running Slippa as a module: python -m slippa
"""

import sys
from slippa.cli import main


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
        sys.exit(0)
