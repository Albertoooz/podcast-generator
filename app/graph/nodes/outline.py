from typing import Any, cast

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger

from app.graph.state import PodcastState
from app.llm.factory import get_chat_model
from app.models.schema import Outline
from app.prompting import render_outline_prompt
from app.retry import create_retry_decorator, get_retry_config


async def generate_outline_node(state: PodcastState, config: RunnableConfig) -> dict[str, Any]:
    logger.info("Starting outline generation")
    configurable = config.get("configurable") or {}
    provider = configurable.get("outline_provider", "openai")
    model_name = configurable.get("outline_model", "gpt-4o-mini")
    outline_cfg = dict(configurable.get("outline_config") or {})

    llm = get_chat_model(provider, model_name, **outline_cfg).with_structured_output(Outline)
    retry_cfg = get_retry_config(configurable)
    llm_retry = create_retry_decorator(**retry_cfg)

    @llm_retry
    async def _invoke(prompt: str) -> Outline:
        msg = HumanMessage(content=prompt)
        result = await llm.ainvoke([msg], config=config)
        return cast(Outline, result)

    sp = state["speaker_profile"]
    assert sp is not None
    prompt = render_outline_prompt(
        {
            "briefing": state["briefing"],
            "num_segments": state["num_segments"],
            "context": state["content"],
            "speakers": sp.speakers,
            "language": state.get("language"),
            "format_instructions": "",
        }
    )

    outline = await _invoke(prompt)
    logger.info("Outline has {} segments", len(outline.segments))
    return {"outline": outline}
