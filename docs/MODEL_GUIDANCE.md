# Model guidance (suggestions, not mandates)

> **CloudOpt does not require any specific LLM.** It ships with an offline **sandbox** provider and runs, tests, and demos with **no keys, no GPU, and no network**. Everything below is a *swappable suggestion*. Providers and models are pure configuration (see [routing](#routing-schema)).
>
> **Evidence rule:** every recommendation here carries a dated citation (benchmark/source, link, license). Benchmarks and leaderboards change — treat all claims as **as-of the date noted** and re-verify before relying on them. If you cannot cite hard evidence, do not add a recommendation.

_Last reviewed: 2026-07. OSS / open-weight options are listed first in every tier._

## Tiers (roles)

CloudOpt routes each task to one of four tiers. You bind each tier to a provider + model.

| Tier | Used for | What matters |
|------|----------|--------------|
| `embed` | RAG ingest + query embeddings | embedding quality (retrieval), dimension must match the DB vector column |
| `cheap` | bulk summarize/classify (future) | throughput + $/token |
| `standard` | FinOps agent tool loop | tool/function-calling reliability, latency |
| `heavy` | final JSON synthesis, low-confidence retry | reasoning + strict JSON adherence |

## Suggestions by tier

Each entry: **why it maps to the tier**, plus a dated citation and license. These are examples that were reasonable at the review date — not an exhaustive or ranked list.

### `embed`

**OSS / open-weight (preferred):**
- **BAAI `bge-m3`** — multilingual, strong retrieval; the CloudOpt default embed model name. License: MIT. Evidence: model card + MTEB results, BAAI/bge-m3 on Hugging Face (as of 2026-07): <https://huggingface.co/BAAI/bge-m3>. Output dim 1024 (set `CLOUDOPT_EMBEDDING_DIMENSIONS=1024`).
- **`nomic-embed-text`** — small, fast, easy to run under Ollama for laptop use. License: Apache-2.0. Evidence: Nomic model card / release notes: <https://huggingface.co/nomic-ai/nomic-embed-text-v1.5>. Output dim 768.
- General ranking reference: **MTEB leaderboard** (compare candidates yourself, dated): <https://huggingface.co/spaces/mteb/leaderboard>.

**Hosted (if you accept a provider):**
- **OpenAI `text-embedding-3-large/-small`** — strong retrieval, no infra. License: proprietary (API). Evidence: OpenAI embeddings docs: <https://platform.openai.com/docs/guides/embeddings>. Dims configurable (e.g. 3072/1536).

> Whatever you pick, `CLOUDOPT_EMBEDDING_DIMENSIONS` **must** equal the model's output dimension and the `rag_chunks.embedding` vector column (see `alembic/versions/002_*`).

### `cheap`

**OSS / open-weight (preferred):**
- **Qwen2.5-7B-Instruct** or **Llama 3.1 8B Instruct** — good quality-per-dollar for bulk summarize/classify; run locally via Ollama/vLLM. Licenses: Qwen (Apache-2.0 for many sizes — verify the specific checkpoint) <https://huggingface.co/Qwen/Qwen2.5-7B-Instruct>; Llama 3.1 (Meta Llama 3.1 Community License) <https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct>.

**Hosted:**
- Any provider's small/"mini" tier. Verify current pricing on the provider's pricing page (dated) before relying on cost claims.

### `standard` (tool/function calling)

**OSS / open-weight (preferred):**
- **Qwen2.5-7B/14B-Instruct** — documented tool/function-calling support; the CloudOpt default chat model name. License: see checkpoint (Apache-2.0 for several sizes). Evidence: Qwen function-calling docs <https://qwen.readthedocs.io/en/latest/framework/function_call.html>.
- **Llama 3.1 Instruct** — native tool-calling. License: Meta Llama 3.1 Community License. Evidence: Llama 3.1 model card (tool use) <https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct>.

> If your backend model does not support tools, set `CLOUDOPT_AGENT_TOOLS_ENABLED=false` to use the single-shot path.

### `heavy` (reasoning + strict JSON)

**OSS / open-weight (preferred):**
- Larger open-weight instruct models (e.g. **Qwen2.5-32B/72B-Instruct**, **Llama 3.1 70B Instruct**) when you have the hardware or a hosted OSS endpoint. Licenses as above. Evidence: respective model cards on Hugging Face (dated).

**Hosted (strong JSON adherence):**
- Providers exposing a **JSON / structured-output mode** reachable via the OpenAI-compatible `response_format={"type":"json_object"}` that CloudOpt already sends. Verify structured-output support in the provider's current docs (dated).

## Routing schema

Bind tiers to providers via `CLOUDOPT_LLM_ROUTING_JSON` (inline) or `CLOUDOPT_LLM_ROUTING_FILE` (path). Example (local Ollama for everything):

```json
{
  "providers": {
    "local": { "name": "local", "kind": "openai_compatible", "base_url": "http://localhost:11434/v1", "api_key": "EMPTY" }
  },
  "tiers": {
    "embed":    { "provider": "local", "model": "nomic-embed-text" },
    "cheap":    { "provider": "local", "model": "llama3.1" },
    "standard": { "provider": "local", "model": "llama3.1" },
    "heavy":    { "provider": "local", "model": "llama3.1:70b" }
  }
}
```

Simpler single-provider setups can skip the JSON and just set `CLOUDOPT_LLM_BASE_URL` / `CLOUDOPT_LLM_CHAT_MODEL` / `CLOUDOPT_LLM_EMBED_MODEL` (routes all tiers to that one endpoint).

### Precedence

`per-scan override (scan.metadata.llm)` → `env/file routing` → `CLOUDOPT_LLM_* shorthand` → `offline sandbox`.
(A per-tenant DB-backed layer is deferred until authentication + SSRF controls exist.)

## Verifying a claim before you add it here

1. Name the exact model checkpoint and its license.
2. Link a primary source (model card, official docs, or a dated leaderboard snapshot) — not a blog aggregator.
3. Note the date you checked. Benchmarks move; stale numbers are worse than none.
4. Keep the framing: "suggestion / example," never "must use."
