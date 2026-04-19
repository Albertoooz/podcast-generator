import asyncio

from app.graph.workflow import create_podcast


async def main() -> None:
    result = await create_podcast(
        content="Brief notes about your topic…",
        episode_profile="diverse_panel",
        episode_name="demo",
        output_dir="output/demo",
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
