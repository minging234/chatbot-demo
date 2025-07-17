import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from app.agents import AIAgent

@pytest.mark.asyncio
async def test_reply_returns_parsed_result():
    # Arrange
    mock_llm = Mock()
    mock_llm.ainvoke = AsyncMock(return_value="raw_response")
    mock_builder = Mock()
    mock_builder.build = Mock(return_value="built_prompt")
    mock_parser = Mock()
    mock_parser.parse_result = Mock(return_value="parsed_result")
    agent = AIAgent(mock_llm, mock_builder, mock_parser)
    user_msg = "Hello"
    context = [Mock()]

    # Act
    result = await agent.reply(user_msg, context)

    # Assert
    mock_builder.build.assert_called_once_with(user_msg, context)
    mock_llm.ainvoke.assert_awaited_once_with("built_prompt")
    mock_parser.parse_result.assert_called_once_with("raw_response")
    assert result == "parsed_result"

@pytest.mark.asyncio
async def test_reply_with_empty_context():
    mock_llm = Mock()
    mock_llm.ainvoke = AsyncMock(return_value="raw_response")
    mock_builder = Mock()
    mock_builder.build = Mock(return_value="built_prompt")
    mock_parser = Mock()
    mock_parser.parse_result = Mock(return_value="parsed_result")
    agent = AIAgent(mock_llm, mock_builder, mock_parser)
    user_msg = "Test"
    context = []

    result = await agent.reply(user_msg, context)

    mock_builder.build.assert_called_once_with(user_msg, context)
    mock_llm.ainvoke.assert_awaited_once_with("built_prompt")
    mock_parser.parse_result.assert_called_once_with("raw_response")
    assert result == "parsed_result"

@pytest.mark.asyncio
async def test_reply_propagates_llm_exception():
    mock_llm = Mock()
    mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM error"))
    mock_builder = Mock()
    mock_builder.build = Mock(return_value="prompt")
    mock_parser = Mock()
    agent = AIAgent(mock_llm, mock_builder, mock_parser)

    with pytest.raises(RuntimeError, match="LLM error"):
        await agent.reply("msg", [])

@pytest.mark.asyncio
async def test_reply_propagates_parser_exception():
    mock_llm = Mock()
    mock_llm.ainvoke = AsyncMock(return_value="raw")
    mock_builder = Mock()
    mock_builder.build = Mock(return_value="prompt")
    mock_parser = Mock()
    mock_parser.parse_result = Mock(side_effect=ValueError("Parse error"))
    agent = AIAgent(mock_llm, mock_builder, mock_parser)

    with pytest.raises(ValueError, match="Parse error"):
        await agent.reply("msg", [])