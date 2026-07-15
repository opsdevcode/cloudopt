# LLM usage and per-account “memory” in CloudOpt

CloudOpt uses **retrieval and structured data** to reflect how each account uses the cloud. The base model does **not** continuously learn new facts by updating its weights from tenant data in normal operation.

## Why not “the model learns each account” in the weight sense

- **Cross-tenant risk**: shared weights can blur boundaries between customers unless you run separate fine-tunes per tenant (expensive and hard to govern).
- **Drift and audit**: FinOps decisions should be **traceable** to stored evidence (findings, billing snippets, policies), not opaque internal states.
- **Facts change**: Costs and topology change daily; **retrieval** from your DB reflects current state better than stale memorization in weights.

## What we implement instead

| Mechanism | Purpose |
|-----------|---------|
| **Structured tenant fields** | Per-scan `tenant_id`, preferences and suppressions in Postgres (future fields as needed). |
| **RAG (`rag_chunks`)** | Embeddings over findings text (including FinOps-oriented findings when embedded), scan summaries, and later CUR-derived snippets—scoped by **`tenant_id`**. Audit-heavy scans may skip bulk embedding to control cost; retrieval remains grounded in stored rows either way. |
| **Prompt-time context** | Before generation, retrieve top-k chunks for **that tenant only** and attach them to the prompt. |
| **Fine-tuning / LoRA** | Optional later for formatting or narrow tasks—not a substitute for RAG for factual account behavior. |

## Provider-agnostic routing (four tiers)

CloudOpt never hardcodes a model. Each task routes to a tier — `embed`, `cheap`, `standard`, `heavy` — that is bound to a provider via configuration. Resolution precedence (highest first):

1. **Per-scan override** — `scan.metadata.llm` pins a tier/model (or `{"mode":"sandbox"}`) for one run.
2. **Env/file routing** — `CLOUDOPT_LLM_ROUTING_JSON` / `CLOUDOPT_LLM_ROUTING_FILE` bind tiers to providers.
3. **Single-provider shorthand** — `CLOUDOPT_LLM_BASE_URL` + `CLOUDOPT_LLM_CHAT_MODEL` / `CLOUDOPT_LLM_EMBED_MODEL` route all tiers to one endpoint.
4. **Offline sandbox** — the zero-config default: deterministic, network-free responses so the product runs and tests with no keys/GPU.

Role → tier: RAG embeddings use `embed`; the FinOps agent tool loop uses `standard`; final JSON synthesis / low-confidence retry uses `heavy`; bulk summarize/classify (future) uses `cheap`.

A per-tenant, DB-backed routing layer (encrypted keys, config API/UI) is **deferred** until authentication and SSRF controls exist; the resolver already has a seam for it.

See [MODEL_GUIDANCE.md](MODEL_GUIDANCE.md) for evidence-backed suggestions and the routing JSON schema.

## Self-hosted / local inference

When `CLOUDOPT_LLM_BASE_URL` points at a local OpenAI-compatible server (Ollama, vLLM, llama.cpp) or self-hosted gateway, prompts and embeddings stay in your network. Customer billing text should still be **minimized and redacted** in stored chunks per your security policy.
