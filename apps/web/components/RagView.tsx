"use client";

import { useMemo, useState } from "react";

import { Card, PrimaryButton } from "@/components/ui";

type RagSearchHit = {
  content: string;
  source_type: string;
  source_id: string | null;
  score: number;
};

type RagAskResponse = {
  answer: string;
  chunks_used: RagSearchHit[];
  sandbox: boolean;
};

function getApiBase(): string {
  if (typeof window === "undefined") return "";
  return process.env.NEXT_PUBLIC_CLOUDOPT_API_URL?.trim() || "";
}

export function RagView() {
  const apiBase = useMemo(() => getApiBase(), []);
  const [tenantId, setTenantId] = useState("default");
  const [query, setQuery] = useState("");
  const [question, setQuestion] = useState("");
  const [hits, setHits] = useState<RagSearchHit[]>([]);
  const [askResult, setAskResult] = useState<RagAskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function runSearch() {
    setError(null);
    setLoading(true);
    setAskResult(null);
    try {
      const params = new URLSearchParams({
        tenant_id: tenantId,
        q: query,
        limit: "8",
      });
      const res = await fetch(`${apiBase}/api/v1/rag/search?${params}`);
      if (!res.ok) throw new Error(`Search failed (${res.status})`);
      setHits((await res.json()) as RagSearchHit[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
      setHits([]);
    } finally {
      setLoading(false);
    }
  }

  async function runAsk() {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/v1/rag/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_id: tenantId,
          question,
          limit: 8,
        }),
      });
      if (!res.ok) throw new Error(`Ask failed (${res.status})`);
      const data = (await res.json()) as RagAskResponse;
      setAskResult(data);
      setHits(data.chunks_used);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ask failed");
      setAskResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-text m-0 mb-2">RAG / AI</h1>
        <p className="text-text-secondary m-0 max-w-2xl">
          Semantic search and grounded Q&amp;A over tenant-scoped findings and scan summaries.
        </p>
      </div>

      <Card title="Tenant">
        <label className="block text-sm text-text-secondary mb-1" htmlFor="rag-tenant">
          Tenant ID
        </label>
        <input
          id="rag-tenant"
          className="w-full max-w-md rounded-lg border border-border bg-surface px-3 py-2 text-text"
          value={tenantId}
          onChange={(e) => setTenantId(e.target.value)}
        />
      </Card>

      <Card title="Search">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="block text-sm text-text-secondary mb-1" htmlFor="rag-query">
              Query
            </label>
            <input
              id="rag-query"
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. EKS rightsizing"
            />
          </div>
          <PrimaryButton type="button" onClick={runSearch} disabled={loading || !query.trim()}>
            Search
          </PrimaryButton>
        </div>
      </Card>

      <Card title="Ask">
        <div className="flex flex-col gap-3">
          <label className="block text-sm text-text-secondary mb-1" htmlFor="rag-question">
            Question
          </label>
          <textarea
            id="rag-question"
            className="w-full min-h-[80px] rounded-lg border border-border bg-surface px-3 py-2 text-text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What cost optimization opportunities apply to this tenant?"
          />
          <PrimaryButton type="button" onClick={runAsk} disabled={loading || !question.trim()}>
            Ask
          </PrimaryButton>
          {askResult && (
            <div className="rounded-lg border border-border bg-surface/50 p-4 text-sm text-text-secondary whitespace-pre-wrap">
              {askResult.sandbox && (
                <p className="text-text-muted text-xs m-0 mb-2">Sandbox mode (chunks + note)</p>
              )}
              {askResult.answer}
            </div>
          )}
        </div>
      </Card>

      {error && <p className="text-red-400 text-sm m-0">{error}</p>}

      <Card title="Results">
        {hits.length === 0 ? (
          <p className="text-text-muted m-0 text-sm">No chunks yet. Run a finops scan to populate RAG.</p>
        ) : (
          <ul className="m-0 p-0 list-none space-y-3">
            {hits.map((hit, i) => (
              <li
                key={`${hit.source_type}-${hit.source_id ?? i}`}
                className="rounded-lg border border-border p-3 bg-surface/30"
              >
                <div className="flex flex-wrap gap-2 text-xs text-text-muted mb-2">
                  <span>{hit.source_type}</span>
                  {hit.source_id && <span>id: {hit.source_id}</span>}
                  <span>score: {hit.score.toFixed(3)}</span>
                </div>
                <p className="m-0 text-sm text-text-secondary whitespace-pre-wrap">{hit.content}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
