"""Tests for the Mirascope + Langfuse integration."""
import os
from typing import AsyncContextManager, ContextManager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cohere import StreamedChatResponse_TextGeneration
from cohere.types import NonStreamedChatResponse, StreamedChatResponse
from google.ai.generativelanguage import GenerateContentResponse
from groq.lib.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat import ChatCompletion
from pydantic import BaseModel

from mirascope.anthropic.calls import AnthropicCall
from mirascope.anthropic.types import AnthropicCallResponseChunk
from mirascope.chroma.types import ChromaQueryResult, ChromaSettings
from mirascope.chroma.vectorstores import ChromaVectorStore
from mirascope.cohere.calls import CohereCall
from mirascope.cohere.embedders import CohereEmbedder
from mirascope.cohere.types import CohereCallParams
from mirascope.gemini.calls import GeminiCall
from mirascope.groq.calls import GroqCall
from mirascope.langfuse.langfuse import mirascope_langfuse_generation, with_langfuse
from mirascope.openai import OpenAICall
from mirascope.openai.embedders import OpenAIEmbedder
from mirascope.openai.extractors import OpenAIExtractor
from mirascope.openai.tools import OpenAITool
from mirascope.openai.types import OpenAICallResponse
from mirascope.rag.embedders import BaseEmbedder
from mirascope.rag.types import Document

os.environ["OPENAI_API_KEY"] = "test"


class MyCall(OpenAICall):
    prompt_template = "test"


@patch(
    "openai.resources.chat.completions.Completions.create",
    new_callable=MagicMock,
)
@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
def test_call_with_langfuse(
    mock_langfuse: MagicMock,
    mock_create: MagicMock,
    fixture_chat_completion: ChatCompletion,
) -> None:
    """Tests that `OpenAICall.call` returns the expected response with langfuse."""
    mock_langfuse.trace = MagicMock()
    mock_create.return_value = fixture_chat_completion

    @with_langfuse
    class MyNestedCall(MyCall):
        ...

    my_call = MyNestedCall()
    my_call.call()
    assert my_call.call_params.langfuse is not None
    mock_langfuse.return_value.trace.assert_called_once()


@patch("google.generativeai.GenerativeModel.generate_content", new_callable=MagicMock)
@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
def test_gemini_call_call_with_langfuse(
    mock_langfuse: MagicMock,
    mock_generate_content: MagicMock,
    fixture_generate_content_response: GenerateContentResponse,
) -> None:
    """Tests that `GeminiClass.call` returns the expected response with Langfuse."""
    mock_generate_content.return_value = fixture_generate_content_response
    mock_generate_content.__name__ = "call"

    @with_langfuse
    class MyGeminiCall(GeminiCall):
        ...

    my_call = MyGeminiCall()
    my_call.call()
    assert my_call.call_params.langfuse is not None


@patch("cohere.Client.chat", new_callable=MagicMock)
@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
def test_cohere_call_call_with_langfuse(
    mock_langfuse: MagicMock,
    mock_chat: MagicMock,
    fixture_non_streamed_response: NonStreamedChatResponse,
) -> None:
    """Tests that `CohereCall.call` returns the expected response with langfuse."""
    mock_chat.return_value = fixture_non_streamed_response

    @with_langfuse
    class CohereTempCall(CohereCall):
        prompt_template = ""
        api_key = "test"
        call_params = CohereCallParams(preamble="test")

    my_call = CohereTempCall()
    my_call.call()
    assert my_call.call_params.langfuse is not None


@patch("cohere.Client.chat_stream", new_callable=MagicMock)
@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
def test_cohere_call_stream_with_langfuse(
    mock_langfuse: MagicMock,
    mock_chat_stream: MagicMock,
    fixture_cohere_response_chunks: list[StreamedChatResponse],
) -> None:
    """Tests that `CohereCall.stream` returns the expected response with langfuse."""
    mock_chat_stream.return_value = fixture_cohere_response_chunks
    mock_chat_stream.__name__ = "stream"

    @with_langfuse
    class CohereTempCall(CohereCall):
        prompt_template = ""
        api_key = "test"
        call_params = CohereCallParams(preamble="test")

    my_call = CohereTempCall()
    chunks = [chunk for chunk in my_call.stream()]
    for chunk in chunks:
        assert isinstance(chunk.chunk, StreamedChatResponse_TextGeneration)
    assert my_call.call_params.langfuse is not None


@patch("cohere.AsyncClient.chat", new_callable=AsyncMock)
@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
@pytest.mark.asyncio
async def test_cohere_call_call_async_with_langfuse(
    mock_langfuse: MagicMock,
    mock_chat: AsyncMock,
    fixture_non_streamed_response: NonStreamedChatResponse,
) -> None:
    """Tests that `CohereCall.call_async` returns the expected response with langfuse."""
    mock_chat.return_value = fixture_non_streamed_response

    @with_langfuse
    class CohereTempCall(CohereCall):
        prompt_template = ""
        api_key = "test"
        call_params = CohereCallParams(preamble="test")

    my_call = CohereTempCall()
    await my_call.call_async()
    assert my_call.call_params.langfuse is not None


@patch("cohere.AsyncClient.chat_stream", new_callable=MagicMock)
@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
@pytest.mark.asyncio
async def test_cohere_call_stream_async_with_langfuse(
    mock_langfuse: MagicMock,
    mock_chat_stream: MagicMock,
    fixture_cohere_async_response_chunks,
):
    """Tests `CohereCall.stream_async` returns expected response with logfire."""

    @with_langfuse
    class TempCall(CohereCall):
        prompt_template = ""
        api_key = "test"

    mock_chat_stream.return_value = fixture_cohere_async_response_chunks
    mock_chat_stream.__name__ = "stream"
    my_call = TempCall()
    stream = my_call.stream_async()

    async for chunk in stream:
        assert isinstance(chunk.chunk, StreamedChatResponse_TextGeneration)
    assert my_call.call_params.langfuse is not None


@patch("mirascope.openai.calls.OpenAICall.call", new_callable=MagicMock)
@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
def test_extractor_with_langfuse(
    mock_langfuse: MagicMock,
    mock_call: MagicMock,
    fixture_chat_completion_with_tools: ChatCompletion,
    fixture_my_openai_tool: type[OpenAITool],
    fixture_my_openai_tool_schema: type[BaseModel],
) -> None:
    mock_call.return_value = OpenAICallResponse(
        response=fixture_chat_completion_with_tools,
        tool_types=[fixture_my_openai_tool],
        start_time=0,
        end_time=0,
    )

    @with_langfuse
    class TempExtractor(OpenAIExtractor[BaseModel]):
        prompt_template = "test"
        api_key = "test"

        extract_schema: type[BaseModel] = fixture_my_openai_tool_schema

    my_extractor = TempExtractor()
    my_extractor.extract()
    assert my_extractor.call_params.langfuse is not None


@patch(
    "anthropic.resources.messages.Messages.stream",
    new_callable=MagicMock,
)
@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
def test_anthropic_call_stream_with_langfuse(
    mock_langfuse: MagicMock,
    mock_stream: MagicMock,
    fixture_anthropic_message_chunks: ContextManager[list],
):
    """Tests that `AnthropicCall.stream` returns the expected response with langfuse."""

    mock_stream.return_value = fixture_anthropic_message_chunks
    mock_stream.__name__ = "stream"

    @with_langfuse
    class AnthropicLangfuseCall(AnthropicCall):
        prompt_template = ""
        api_key = "test"

    my_call = AnthropicLangfuseCall()
    stream = my_call.stream()
    for chunk in stream:
        assert isinstance(chunk, AnthropicCallResponseChunk)
    assert my_call.call_params.langfuse is not None


@patch(
    "anthropic.resources.messages.AsyncMessages.stream",
    new_callable=MagicMock,
)
@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
@pytest.mark.asyncio
async def test_anthropic_call_stream_async(
    mock_langfuse: MagicMock,
    mock_stream: MagicMock,
    fixture_anthropic_async_message_chunks: AsyncContextManager[list],
):
    """Tests `AnthropicPrompt.stream_async` returns the expected response when called."""
    mock_stream.return_value = fixture_anthropic_async_message_chunks
    mock_stream.__name__ = "stream"

    @with_langfuse
    class AnthropicLangfuseCall(AnthropicCall):
        prompt_template = ""
        api_key = "test"

    my_call = AnthropicLangfuseCall()
    stream = my_call.stream_async()
    async for chunk in stream:
        assert isinstance(chunk, AnthropicCallResponseChunk)
    assert my_call.call_params.langfuse is not None


@patch(
    "groq.resources.chat.completions.AsyncCompletions.create", new_callable=AsyncMock
)
@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
@pytest.mark.asyncio
async def test_groq_call_stream_async(
    mock_langfuse: MagicMock,
    mock_create: AsyncMock,
    fixture_chat_completion_stream_response: list[ChatCompletionChunk],
):
    """Tests `GroqCall.stream_async` returns expected response with langfuse."""

    @with_langfuse
    class TempCall(GroqCall):
        prompt_template = ""
        api_key = "test"

    mock_create.return_value.__aiter__.return_value = (
        fixture_chat_completion_stream_response
    )
    mock_create.__name__ = "stream"
    my_call = TempCall()
    stream = my_call.stream_async()

    i = 0
    async for chunk in stream:
        assert chunk.chunk == fixture_chat_completion_stream_response[i]
        i += 1

    assert my_call.call_params.langfuse is not None


def test_value_error_on_mirascope_langfuse_generation():
    """Tests that `mirascope_langfuse_generation` raises a `ValueError`.
    One of response_type or response_chunk_type is required.
    """
    with pytest.raises(ValueError):

        def foo():
            ...  # pragma: no cover

        mirascope_langfuse_generation(None)(foo, "test")


class MyEmbedder(BaseEmbedder):
    def embed(self, input: list[str]) -> list[str]:
        return input  # pragma: no cover

    async def embed_async(self, input: list[str]) -> list[str]:
        return input  # pragma: no cover

    def __call__(self, input: str) -> list[float]:
        return [1, 2, 3]  # pragma: no cover


@patch("chromadb.api.models.Collection.Collection.upsert")
@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
def test_chroma_vectorstore_add_document_with_langfuse(
    mock_langfuse: MagicMock,
    mock_upsert: MagicMock,
):
    """Test the add method of the ChromaVectorStore class with documents as argument"""
    mock_upsert.return_value = None

    @with_langfuse
    class VectorStore(ChromaVectorStore):
        index_name = "test"
        client_settings = ChromaSettings(mode="ephemeral")
        embedder = MyEmbedder()

    my_vectorstore = VectorStore()
    my_vectorstore.add([Document(text="foo", id="1")])
    mock_upsert.assert_called_once_with(ids=["1"], documents=["foo"])
    assert my_vectorstore.vectorstore_params.langfuse is not None


@patch("chromadb.api.models.Collection.Collection.query")
@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
def test_chroma_vectorstore_retrieve_with_langfuse(
    mock_langfuse: MagicMock,
    mock_query: MagicMock,
):
    """Test the retrieve method of the ChromaVectorStore class."""
    mock_query.return_value = ChromaQueryResult(ids=[["1"]])

    @with_langfuse
    class VectorStore(ChromaVectorStore):
        index_name = "test"
        client_settings = ChromaSettings(mode="ephemeral")
        embedder = MyEmbedder()

    my_vectorstore = VectorStore()
    my_vectorstore.retrieve("test")
    mock_query.assert_called_once_with(query_texts=["test"])
    assert my_vectorstore.vectorstore_params.langfuse is not None


@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
def test_openai_embedder_with_langfuse(mock_langfuse: MagicMock) -> None:
    @with_langfuse
    class MyEmbedder(OpenAIEmbedder):
        ...

    my_embedder = MyEmbedder()
    assert my_embedder.embedding_params.langfuse is not None


@patch("mirascope.langfuse.langfuse.Langfuse", new_callable=MagicMock)
def test_cohere_embedder_with_langfuse(mock_langfuse: MagicMock) -> None:
    @with_langfuse
    class MyOtherEmbedder(CohereEmbedder):
        ...

    my_embedder = MyOtherEmbedder()
    assert my_embedder.embedding_params.langfuse is not None
