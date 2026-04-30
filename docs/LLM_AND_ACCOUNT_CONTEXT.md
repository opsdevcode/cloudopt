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
| **RAG (`rag_chunks`)** | Embeddings over findings text, scan summaries, and later CUR-derived snippets—scoped by **`tenant_id`**. |
| **Prompt-time context** | Before generation, retrieve top-k chunks for **that tenant only** and attach them to the prompt. |
| **Fine-tuning / LoRA** | Optional later for formatting or narrow tasks—not a substitute for RAG for factual account behavior. |

## Self-hosted inference

When `CLOUDOPT_LLM_BASE_URL` points at vLLM (or another OpenAI-compatible server), prompts and optional embeddings can stay in your network. Customer billing text should still be **minimized and redacted** in stored chunks per your security policy.
