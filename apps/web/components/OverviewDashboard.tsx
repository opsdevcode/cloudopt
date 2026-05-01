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

const CHART_COLORS = ["#635bff", "#0073e6", "#0cad55", "#d97706", "#cd3d64", "#8898aa", "#b07d3a"];

function dictToChartData(d: Record<string, number> | undefined, labelKey: string) {
  if (!d) return [];
  return Object.entries(d).map(([name, value]) => ({ [labelKey]: name, value }));
}

export function OverviewDashboard() {
  const client = useMemo(() => createCloudoptClient(), []);

  const metrics = useQuery({
    queryKey: ["metrics", "overview"],
    queryFn: async () => {
      const { data, error } = await client.GET("/api/v1/metrics/overview", {});
      if (error) throw new Error(typeof error === "object" ? JSON.stringify(error) : String(error));
      if (!data) throw new Error("No overview data");
      return data;
    },
  });

  const health = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/health");
      if (!res.ok) throw new Error(`Health ${res.status}`);
      return res.json() as Promise<{ status?: string }>;
    },
  });

  const sevData = useMemo(
    () => dictToChartData(metrics.data?.findings_by_severity, "severity"),
    [metrics.data?.findings_by_severity],
  );
  const kindData = useMemo(
    () => dictToChartData(metrics.data?.findings_by_finding_kind, "kind"),
    [metrics.data?.findings_by_finding_kind],
  );

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-text m-0 mb-2">
          Overview
        </h1>
        <p className="text-text-secondary m-0 max-w-2xl">
          Cross-scan FinOps and posture signals. Per-scan detail lives under{" "}
          <Link href="/scans" className="text-primary font-medium">
            Scans
          </Link>
          .
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card title="API">
          {health.isLoading ? (
            <p className="text-text-muted m-0">Checking…</p>
          ) : health.isError ? (
            <p className="text-error m-0">Unreachable</p>
          ) : (
            <p className="text-success font-semibold m-0">Live — {health.data?.status ?? "ok"}</p>
          )}
          <p className="text-sm text-text-muted mt-2 mb-0">
            <a href="/docs" className="text-primary">
              OpenAPI docs
            </a>
          </p>
        </Card>
        <Card title="Findings">
          {metrics.isLoading ? (
            <p className="text-text-muted m-0">Loading…</p>
          ) : (
            <p className="text-3xl font-bold text-text m-0 tabular-nums">
              {metrics.data?.findings_total ?? "—"}
            </p>
          )}
        </Card>
        <Card title="Est. monthly savings">
          {metrics.isLoading ? (
            <p className="text-text-muted m-0">Loading…</p>
          ) : (
            <p className="text-3xl font-bold text-text m-0 tabular-nums">
              {metrics.data != null
                ? new Intl.NumberFormat(undefined, {
                    style: "currency",
                    currency: "USD",
                    maximumFractionDigits: 0,
                  }).format(metrics.data.estimated_savings_monthly_total)
                : "—"}
            </p>
          )}
        </Card>
        <Card title="Scans">
          {metrics.isLoading ? (
            <p className="text-text-muted m-0">Loading…</p>
          ) : (
            <p className="text-3xl font-bold text-text m-0 tabular-nums">{metrics.data?.scans_total ?? "—"}</p>
          )}
        </Card>
      </div>

      {metrics.isError ? (
        <Card title="Metrics error">
          <p className="text-error m-0">
            Could not load overview. Is the API running? Try{" "}
            <code className="text-text">docker-compose up api</code> or{" "}
            <code className="text-text">uvicorn apps.api.main:app --reload</code>.
          </p>
        </Card>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Findings by severity">
          <div className="h-64 min-h-[240px] min-w-0 w-full">
            {sevData.length === 0 && !metrics.isLoading ? (
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
                    innerRadius={48}
                    outerRadius={80}
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
        <Card title="Findings by kind">
          <div className="h-64 min-h-[240px] min-w-0 w-full">
            {kindData.length === 0 && !metrics.isLoading ? (
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

      <Card title="Scan activity">
        <p className="text-sm text-text-secondary m-0 mb-4">
          Status mix across all runs.{" "}
          <Link href="/scans" className="text-primary font-medium">
            Manage scans
          </Link>
        </p>
        <div className="flex flex-wrap gap-2">
          {metrics.data?.scans_by_status
            ? Object.entries(metrics.data.scans_by_status).map(([k, v]) => (
                <span
                  key={k}
                  className="inline-flex items-center gap-2 rounded-ops-md border border-border px-3 py-1.5 text-sm bg-bg-muted"
                >
                  <StatusBadge status={k} />
                  <span className="tabular-nums font-semibold text-text">{v}</span>
                </span>
              ))
            : null}
        </div>
      </Card>

      <Card title="Recent scans">
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left text-text-muted border-b border-border">
                <th className="py-2 pr-4 font-medium">Kind</th>
                <th className="py-2 pr-4 font-medium">Status</th>
                <th className="py-2 pr-4 font-medium">Cluster</th>
                <th className="py-2 pr-4 font-medium">Created</th>
                <th className="py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {(metrics.data?.recent_scans ?? []).map((s) => (
                <tr key={s.id} className="border-b border-border/80">
                  <td className="py-2 pr-4 font-mono text-xs">{s.scan_kind}</td>
                  <td className="py-2 pr-4">
                    <StatusBadge status={s.status} />
                  </td>
                  <td className="py-2 pr-4 text-text-secondary">{s.cluster_name ?? "—"}</td>
                  <td className="py-2 pr-4 text-text-muted whitespace-nowrap">
                    {new Date(s.created_at).toLocaleString()}
                  </td>
                  <td className="py-2">
                    <Link href={`/scans/${s.id}`} className="text-primary font-medium">
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!metrics.isLoading && (metrics.data?.recent_scans?.length ?? 0) === 0 ? (
            <p className="text-text-muted mt-4 mb-0">No scans yet. Create one from the Scans page.</p>
          ) : null}
        </div>
      </Card>
    </div>
  );
}
