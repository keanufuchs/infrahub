from asyncio import run as aiorun

from infrahub_sdk import InfrahubClient


async def main():
    client = await InfrahubClient.init(address="http://localhost:8000")
    await client.branch.rebase(branch_name="new-branch")


if __name__ == "__main__":
    aiorun(main())
