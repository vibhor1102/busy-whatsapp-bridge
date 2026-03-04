import sys
import json
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import get_config_file

async def main():
    resp = await get_config_file()
    print(json.dumps(resp, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
