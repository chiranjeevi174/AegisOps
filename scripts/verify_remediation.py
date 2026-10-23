import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.verify_rca import main

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/verify_remediation.py <incident-uuid>")
    asyncio.run(main())
