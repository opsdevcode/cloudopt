"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Card, GhostButton, SeverityBadge } from "@/components/ui";
import { createCloudoptClient } from "@/lib/api";

import type { components } from "@/lib/cloudopt-api";

type FindingRow = components["schemas"]["FindingResponse"];

export function FindingsView() {
  const client = useMemo(() => createCloudoptClient(), []);
  const searchParams = useSearchParams();
  const scanIdFromUrl = searchParams.get("scan_id") ?? "";

  const [scanId, setScanId] = useState(scanIdFromUrl);
  const [scanKind, setScanKind] = useState("");
  const [findingKind, setFindingKind] = useState("");
  const [frameworkPrefix, setFrameworkPrefix] = useState("");
  const [limit, setLimit] = useState(100);
  const [selected, setSelected] = useState<FindingRow | null>(null);

  useEffect(() => {
    setScanId(scanIdFromUrl);
  }, [scanIdFromUrl]);

  const findings = useQuery({
    queryKey: ["findings", scanId, scanKind, findingKind, frameworkPrefix, limit],
    queryFn: async () => {
      const { data, error } = await client.GET("/api/v1/findings", {
        params: {
          query: {
            scan_id: scanId.trim() || undefined,
            scan_kind: scanKind.trim() || undefined,
            finding_kind: findingKind.trim() || undefined,
            framework: frameworkPrefix.trim() || undefined,
            limit,
          },
        },
      });
      if (error) throw error;
      return data ?? [];
    },
  });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-text m-0 mb-2">Findings</h1>
        <p className="text-text-secondary m-0 max-w-3xl">
          Filter across FinOps and audit findings. Open a row for JSON details and recommendations.
        </p>
      </div>

      <Card title="Filters">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wide text-text-muted mb-1">
              Scan ID
            </label>
            <input
              value={scanId}
              onChange={(e) => setScanId(e.target.value)}
              placeholder="uuid"
              className="w-full rounded-ops-md border border-border bg-bg px-3 py-2 text-sm font-mono text-text"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wide text-text-muted mb-1">
              Scan kind
            </label>
            <input
              value={scanKind}
              onChange={(e) => setScanKind(e.target.value)}
              placeholder="finops | aws_audit | …"
              className="w-full rounded-ops-md border border-border bg-bg px-3 py-2 text-sm text-text"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wide text-text-muted mb-1">
              Finding kind
            </label>
            <input
              value={findingKind}
              onChange={(e) => setFindingKind(e.target.value)}
              placeholder="cost | …"
              className="w-full rounded-ops-md border border-border bg-bg px-3 py-2 text-sm text-text"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wide text-text-muted mb-1">
              Framework prefix
            </label>
            <input
              value={frameworkPrefix}
              onChange={(e) => setFrameworkPrefix(e.target.value)}
              placeholder="CIS | AWS…"
              className="w-full rounded-ops-md border border-border bg-bg px-3 py-2 text-sm text-text"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wide text-text-muted mb-1">
              Limit
            </label>
            <input
              type="number"
              min={1}
              max={500}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value) || 100)}
              className="w-full rounded-ops-md border border-border bg-bg px-3 py-2 text-sm text-text"
            />
          </div>
          <div className="flex items-end">
            <GhostButton
              type="button"
              className="w-full sm:w-auto"
              onClick={() => {
                setScanId("");
                setScanKind("");
                setFindingKind("");
                setFrameworkPrefix("");
                setLimit(100);
              }}
            >
              Clear filters
            </GhostButton>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1fr_minmax(280px,360px)]">
        <Card title={`Results (${findings.data?.length ?? 0})`}>
          {findings.isLoading ? (
            <p className="text-text-muted m-0">Loading…</p>
          ) : findings.isError ? (
            <p className="text-error m-0">Failed to load findings.</p>
          ) : (
            <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
              <table className="w-full text-sm border-collapse min-w-[720px]">
                <thead className="sticky top-0 bg-bg z-10 shadow-sm">
                  <tr className="text-left text-text-muted border-b border-border">
                    <th className="py-2 pr-3 font-medium">Severity</th>
                    <th className="py-2 pr-3 font-medium">Title</th>
                    <th className="py-2 pr-3 font-medium">Kind</th>
                    <th className="py-2 pr-3 font-medium">Category</th>
                    <th className="py-2 pr-3 font-medium text-right">Savings/mo</th>
                    <th className="py-2 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {(findings.data ?? []).map((f) => (
                    <tr
                      key={f.id}
                      className={`border-b border-border/80 cursor-pointer hover:bg-bg-muted/80 ${
                        selected?.id === f.id ? "bg-primary-muted/40" : ""
                      }`}
                      onClick={() => setSelected(f)}
                    >
                      <td className="py-2 pr-3 align-top">
                        <SeverityBadge severity={f.severity} />
                      </td>
                      <td className="py-2 pr-3 align-top text-text max-w-xs">
                        <span className="line-clamp-2">{f.title}</span>
                      </td>
                      <td className="py-2 pr-3 align-top font-mono text-xs">{f.finding_kind}</td>
                      <td className="py-2 pr-3 align-top text-text-secondary">{f.category}</td>
                      <td className="py-2 pr-3 align-top text-right tabular-nums">
                        {new Intl.NumberFormat(undefined, {
                          style: "currency",
                          currency: "USD",
                          maximumFractionDigits: 0,
                        }).format(f.estimated_savings_monthly)}
                      </td>
                      <td className="py-2 align-top">
                        <Link
                          href={`/scans/${f.scan_id}`}
                          className="text-primary font-medium whitespace-nowrap"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Scan
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title={selected ? "Finding detail" : "Detail"}>
          {!selected ? (
            <p className="text-text-muted m-0 text-sm">Select a finding to inspect metadata and guidance.</p>
          ) : (
            <div className="space-y-4 text-sm">
              <div>
                <p className="text-xs uppercase tracking-wide text-text-muted m-0 mb-1">Title</p>
                <p className="text-text font-semibold m-0">{selected.title}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <SeverityBadge severity={selected.severity} />
                <span className="inline-flex rounded-full px-2 py-0.5 text-xs font-medium bg-bg-muted text-text-secondary">
                  {selected.finding_kind}
                </span>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-text-muted m-0 mb-1">IDs</p>
                <p className="font-mono text-xs break-all m-0 text-text-secondary">finding: {selected.id}</p>
                <p className="font-mono text-xs break-all m-0 text-text-secondary">scan: {selected.scan_id}</p>
              </div>
              {selected.framework ? (
                <p className="m-0">
                  <span className="text-text-muted">Framework:</span>{" "}
                  <span className="text-text">{selected.framework}</span>
                </p>
              ) : null}
              {selected.resource_type ? (
                <p className="m-0">
                  <span className="text-text-muted">Resource:</span>{" "}
                  <span className="font-mono text-xs">{selected.resource_type}</span>{" "}
                  {selected.resource_id ? (
                    <span className="font-mono text-xs text-text-secondary">{selected.resource_id}</span>
                  ) : null}
                </p>
              ) : null}
              {selected.description ? (
                <div>
                  <p className="text-xs uppercase tracking-wide text-text-muted m-0 mb-1">Description</p>
                  <p className="text-text-secondary m-0 whitespace-pre-wrap">{selected.description}</p>
                </div>
              ) : null}
              {selected.recommendation ? (
                <div>
                  <p className="text-xs uppercase tracking-wide text-text-muted m-0 mb-1">Recommendation</p>
                  <p className="text-text-secondary m-0 whitespace-pre-wrap">{selected.recommendation}</p>
                </div>
              ) : null}
              <div>
                <p className="text-xs uppercase tracking-wide text-text-muted m-0 mb-1">Details JSON</p>
                <pre className="text-xs font-mono bg-bg-muted rounded-ops-md p-3 overflow-x-auto m-0 border border-border max-h-48 overflow-y-auto">
                  {JSON.stringify(selected.details ?? {}, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
