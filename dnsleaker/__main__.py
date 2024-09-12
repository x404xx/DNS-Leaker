import asyncio

from .api import DNSLeakTester

if __name__ == "__main__":
    asyncio.run(DNSLeakTester().run())
