"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, StatusBadge } from "@/components/ui";
import { createCloudoptClient } from "@/lib/api";

const CHART_COLORS = ["#635bff", "#0073e6", "#0cad55", "#d97706", "#cd3d64", "#8898aa"];

function dictToPairs(d: Record<string, number> | undefined, key: string) {
  if (!d) return [];
  return Object.entries(d).map(([name, value]) => ({ [key]: name, value }));
}

function pollMs(status: string | undefined) {
  if (!status) return false;
  const terminal = new Set(["completed", "failed"]);
  return terminal.has(status) ? false : 2500;
}

export function ScanDetailView({ scanId }: { scanId: string }) {
  const client = useMemo(() => createCloudoptClient(), []);

  const scan = useQuery({
    queryKey: ["scan", scanId],
    queryFn: async () => {
      const { data, error } = await client.GET("/api/v1/scans/{scan_id}", {
        params: { path: { scan_id: scanId } },
      });
      if (error) throw error;
      if (!data) throw new Error("Not found");
      return data;
    },
    refetchInterval: (q) => pollMs(q.state.data?.status),
  });

  const summary = useQuery({
    queryKey: ["scan", scanId, "summary"],
    queryFn: async () => {
      const { data, error } = await client.GET("/api/v1/scans/{scan_id}/summary", {
        params: { path: { scan_id: scanId } },
      });
      if (error) throw error;
      if (!data) throw new Error("No summary");
      return data;
    },
    enabled: !!scanId,
    refetchInterval: () => pollMs(scan.data?.status),
  });

  const sevData = useMemo(
    () => dictToPairs(summary.data?.by_severity, "severity"),
    [summary.data?.by_severity],
  );
  const kindData = useMemo(
    () => dictToPairs(summary.data?.by_finding_kind, "kind"),
    [summary.data?.by_finding_kind],
  );

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-2">
        <Link href="/scans" className="text-sm text-primary font-medium w-fit">
          ← Back to scans
        </Link>
        {scan.isLoading ? (
          <p className="text-text-muted m-0">Loading scan…</p>
        ) : scan.isError ? (
          <p className="text-error m-0">Scan not found or API error.</p>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-text m-0">
                Scan <span className="font-mono text-xl">{scan.data?.id}</span>
              </h1>
              <StatusBadge status={scan.data?.status ?? ""} />
            </div>
            <p className="text-text-secondary m-0">
              Kind <span className="font-semibold text-text">{scan.data?.scan_kind}</span>
              {scan.data?.cluster_name ? (
                <>
                  {" "}
                  · Cluster <span className="font-semibold text-text">{scan.data.cluster_name}</span>
                </>
              ) : null}
            </p>
          </>
        )}
      </div>

      {scan.data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card title="Created">
            <p className="m-0 text-sm text-text">{new Date(scan.data.created_at).toLocaleString()}</p>
          </Card>
          <Card title="Started">
            <p className="m-0 text-sm text-text">
              {scan.data.started_at ? new Date(scan.data.started_at).toLocaleString() : "—"}
            </p>
          </Card>
          <Card title="Completed">
            <p className="m-0 text-sm text-text">
              {scan.data.completed_at ? new Date(scan.data.completed_at).toLocaleString() : "—"}
            </p>
          </Card>
          <Card title="Updated">
            <p className="m-0 text-sm text-text">
              {scan.data.updated_at ? new Date(scan.data.updated_at).toLocaleString() : "—"}
            </p>
          </Card>
        </div>
      ) : null}

      {scan.data?.metadata ? (
        <Card title="Metadata">
          <pre className="text-xs font-mono bg-bg-muted rounded-ops-md p-4 overflow-x-auto m-0 border border-border">
            {JSON.stringify(scan.data.metadata, null, 2)}
          </pre>
        </Card>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card title="Findings (this scan)">
          {summary.isLoading ? (
            <p className="text-text-muted m-0">Loading…</p>
          ) : (
            <p className="text-3xl font-bold m-0 tabular-nums">{summary.data?.findings_total ?? "—"}</p>
          )}
        </Card>
        <Card title="Shortcuts">
          <Link
            href={`/findings?scan_id=${encodeURIComponent(scanId)}`}
            className="text-primary font-medium text-sm"
          >
            View findings for this scan →
          </Link>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="By severity">
          <div className="h-56 min-h-[220px] min-w-0 w-full">
            {sevData.length === 0 && !summary.isLoading ? (
              <p className="text-text-muted m-0">No findings yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sevData}
                    dataKey="value"
                    nameKey="severity"
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={72}
                    paddingAngle={2}
                  >
                    {sevData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
        <Card title="By finding kind">
          <div className="h-56 min-h-[220px] min-w-0 w-full">
            {kindData.length === 0 && !summary.isLoading ? (
              <p className="text-text-muted m-0">No findings yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={kindData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="kind" tick={{ fill: "var(--color-text-muted)", fontSize: 11 }} />
                  <YAxis tick={{ fill: "var(--color-text-muted)", fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#635bff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
