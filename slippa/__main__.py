"""
Entry point for running Slippa as a module: python -m slippa

Usage:
    python -m slippa          → Launches the web UI (default)
    python -m slippa --cli    → Runs the CLI version
    python -m slippa --web    → Launches the web UI
"""

import sys


if __name__ == "__main__":
    try:
        if "--cli" in sys.argv:
            from slippa.cli import main
            main()
        else:
            from slippa.web import run_web
            run_web()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
        sys.exit(0)
