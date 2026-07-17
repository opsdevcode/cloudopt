"""RAG search and grounded Q&A API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from packages.ai.llm_client import AsyncLLMRouter
from packages.ai.rag import format_rag_block, retrieve_hits_async
from packages.core.config import get_settings
from packages.core.database import get_db

router = APIRouter()

_SANDBOX_ASK_NOTE = (
    "Sandbox LLM mode: configure CLOUDOPT_LLM_* or routing for grounded answers. "
    "Retrieved chunks are included below."
)


class RagSearchHit(BaseModel):
    content: str
    source_type: str
    source_id: str | None
    score: float


class RagAskRequest(BaseModel):
    tenant_id: str = Field(default="default", min_length=1, max_length=255)
    question: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=8, ge=1, le=32)
    source_type: str | None = Field(default=None, max_length=64)
    scan_id: str | None = Field(default=None, max_length=36)


class RagAskResponse(BaseModel):
    answer: str
    chunks_used: list[RagSearchHit]
    sandbox: bool = False


@router.get("/search", response_model=list[RagSearchHit])
async def rag_search(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Query("default", min_length=1, max_length=255),
    q: str = Query(..., min_length=1, max_length=4000),
    limit: int = Query(8, ge=1, le=32),
    source_type: str | None = Query(None, max_length=64),
    scan_id: str | None = Query(None, max_length=36),
) -> list[RagSearchHit]:
    """Semantic search over tenant-scoped RAG chunks."""
    settings = get_settings()
    router_client = AsyncLLMRouter.from_settings(settings)
    embed_client = router_client.client_for("embed")
    hits = await retrieve_hits_async(
        db,
        tenant_id,
        q,
        limit=limit,
        source_type=source_type,
        scan_id=scan_id,
        client=embed_client,
    )
    return [
        RagSearchHit(
            content=h.content,
            source_type=h.source_type,
            source_id=h.source_id,
            score=h.score,
        )
        for h in hits
    ]


@router.post("/ask", response_model=RagAskResponse)
async def rag_ask(
    body: RagAskRequest,
    db: AsyncSession = Depends(get_db),
) -> RagAskResponse:
    """Retrieve relevant chunks and produce a short grounded answer."""
    settings = get_settings()
    llm_router = AsyncLLMRouter.from_settings(settings)
    embed_client = llm_router.client_for("embed")
    hits = await retrieve_hits_async(
        db,
        body.tenant_id,
        body.question,
        limit=body.limit,
        source_type=body.source_type,
        scan_id=body.scan_id,
        client=embed_client,
    )
    chunk_models = [
        RagSearchHit(
            content=h.content,
            source_type=h.source_type,
            source_id=h.source_id,
            score=h.score,
        )
        for h in hits
    ]

    if settings.llm_mode == "sandbox":
        rag_block = format_rag_block(hits)
        parts = [_SANDBOX_ASK_NOTE]
        if rag_block:
            parts.append(rag_block)
        parts.append(f"Question: {body.question}")
        return RagAskResponse(
            answer="\n\n".join(parts),
            chunks_used=chunk_models,
            sandbox=True,
        )

    chat_client = llm_router.client_for("cheap")
    rag_block = format_rag_block(hits)
    user_parts = []
    if rag_block:
        user_parts.append(rag_block)
    user_parts.append(f"Question: {body.question}")
    user_parts.append(
        "Answer concisely using only the retrieved context. If context is insufficient, say so."
    )
    try:
        raw = await chat_client.chat_json(
            [
                {
                    "role": "system",
                    "content": "You are a CloudOpt assistant for FinOps and cloud posture.",
                },
                {"role": "user", "content": "\n\n".join(user_parts)},
            ]
        )
    except Exception as exc:  # noqa: BLE001 — surface LLM failures to client
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc

    if isinstance(raw, dict) and "summary" in raw:
        answer = str(raw.get("summary", ""))
    elif isinstance(raw, dict) and "answer" in raw:
        answer = str(raw.get("answer", ""))
    else:
        answer = str(raw)

    return RagAskResponse(answer=answer, chunks_used=chunk_models, sandbox=False)
