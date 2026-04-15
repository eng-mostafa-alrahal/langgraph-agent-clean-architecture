"""PGVector store factory — builds a LangChain retriever backed by pgvector."""

from __future__ import annotations

import logging

from langchain_core.retrievers import BaseRetriever
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from app.core.config.settings import get_settings

logger = logging.getLogger(__name__)


def build_pgvector_store() -> PGVector:
    """Create a PGVector vector store using the project's PostgreSQL database.

    The PGVector class automatically creates the ``vector`` extension and its
    backing tables (``langchain_pg_collection``, ``langchain_pg_embedding``)
    on first use, so no separate Alembic migration is required.
    """
    settings = get_settings()

    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        dimensions=settings.EMBEDDING_DIMENSIONS,
        api_key=settings.OPENAI_API_KEY,
    )

    connection_string = settings.get_database_sync_url()

    store = PGVector(
        embeddings=embeddings,
        collection_name=settings.PGVECTOR_COLLECTION,
        connection=connection_string,
        use_jsonb=True,
    )
    logger.info(
        "PGVector store initialised (collection=%s)", settings.PGVECTOR_COLLECTION
    )
    return store


def build_pgvector_retriever(*, top_k: int = 5) -> BaseRetriever:
    """Convenience wrapper that returns a retriever ready for the RAG tool."""
    store = build_pgvector_store()
    return store.as_retriever(search_kwargs={"k": top_k})
