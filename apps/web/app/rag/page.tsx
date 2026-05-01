import Link from "next/link";

import { Card } from "@/components/ui";

export default function RagPlaceholderPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-text m-0 mb-2">RAG / AI</h1>
        <p className="text-text-secondary m-0 max-w-2xl">
          Tenant-scoped retrieval over findings and evidence will surface here when the API exposes search
          and chat flows.
        </p>
      </div>
      <Card title="Roadmap">
        <ul className="m-0 pl-5 text-text-secondary space-y-2">
          <li>Semantic search over stored RAG chunks</li>
          <li>Scan-aware Q&amp;A grounded in findings</li>
          <li>Tooling for FinOps and posture follow-ups</li>
        </ul>
        <p className="text-sm text-text-muted mt-4 mb-0">
          For now, explore data via{" "}
          <Link href="/findings" className="text-primary">
            Findings
          </Link>{" "}
          and the{" "}
          <a href="/docs" className="text-primary">
            API
          </a>
          .
        </p>
      </Card>
    </div>
  );
}
