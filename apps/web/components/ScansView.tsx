"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Card, GhostButton, PrimaryButton, StatusBadge } from "@/components/ui";
import { createCloudoptClient } from "@/lib/api";

const SCAN_KINDS = ["finops", "aws_audit", "k8s_audit", "combined"] as const;

export function ScansView() {
  const client = useMemo(() => createCloudoptClient(), []);
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [scanKind, setScanKind] = useState<string>("finops");
  const [clusterName, setClusterName] = useState("");
  const [tenantId, setTenantId] = useState("default");

  const scans = useQuery({
    queryKey: ["scans"],
    queryFn: async () => {
      const { data, error } = await client.GET("/api/v1/scans", {});
      if (error) throw error;
      return data ?? [];
    },
  });

  const createScan = useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/api/v1/scans", {
        body: {
          scan_kind: scanKind,
          tenant_id: tenantId,
          cluster_name: clusterName.trim() || null,
          metadata: null,
        },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scans"] });
      qc.invalidateQueries({ queryKey: ["metrics", "overview"] });
      setOpen(false);
      setClusterName("");
    },
  });

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-text m-0 mb-2">Scans</h1>
          <p className="text-text-secondary m-0">
            Create runs and open a scan for live status, timelines, and finding breakdowns.
          </p>
        </div>
        <PrimaryButton type="button" onClick={() => setOpen(true)}>
          New scan
        </PrimaryButton>
      </div>

      {open ? (
        <Card title="Create scan">
          <form
            className="space-y-4 max-w-lg"
            onSubmit={(e) => {
              e.preventDefault();
              createScan.mutate();
            }}
          >
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">Scan kind</label>
              <select
                value={scanKind}
                onChange={(e) => setScanKind(e.target.value)}
                className="w-full rounded-ops-md border border-border bg-bg px-3 py-2 text-sm text-text"
              >
                {SCAN_KINDS.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">Tenant ID</label>
              <input
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                className="w-full rounded-ops-md border border-border bg-bg px-3 py-2 text-sm font-mono text-text"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                Cluster name <span className="text-text-muted font-normal">(optional)</span>
              </label>
              <input
                value={clusterName}
                onChange={(e) => setClusterName(e.target.value)}
                placeholder="production"
                className="w-full rounded-ops-md border border-border bg-bg px-3 py-2 text-sm text-text"
              />
            </div>
            {createScan.isError ? (
              <p className="text-error text-sm m-0">Could not create scan. Check API logs.</p>
            ) : null}
            <div className="flex gap-2">
              <PrimaryButton type="submit" disabled={createScan.isPending}>
                {createScan.isPending ? "Creating…" : "Enqueue scan"}
              </PrimaryButton>
              <GhostButton type="button" onClick={() => setOpen(false)}>
                Cancel
              </GhostButton>
            </div>
          </form>
        </Card>
      ) : null}

      <Card title="Recent scans">
        {scans.isLoading ? (
          <p className="text-text-muted m-0">Loading…</p>
        ) : scans.isError ? (
          <p className="text-error m-0">Failed to load scans.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="text-left text-text-muted border-b border-border">
                  <th className="py-2 pr-4 font-medium">ID</th>
                  <th className="py-2 pr-4 font-medium">Kind</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 pr-4 font-medium">Cluster</th>
                  <th className="py-2 pr-4 font-medium">Started</th>
                  <th className="py-2 pr-4 font-medium">Completed</th>
                  <th className="py-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {(scans.data ?? []).map((s) => (
                  <tr key={s.id} className="border-b border-border/80">
                    <td className="py-2 pr-4 font-mono text-xs max-w-[140px] truncate" title={s.id}>
                      {s.id.slice(0, 8)}…
                    </td>
                    <td className="py-2 pr-4">{s.scan_kind}</td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={s.status} />
                    </td>
                    <td className="py-2 pr-4 text-text-secondary">{s.cluster_name ?? "—"}</td>
                    <td className="py-2 pr-4 text-text-muted whitespace-nowrap text-xs">
                      {s.started_at ? new Date(s.started_at).toLocaleString() : "—"}
                    </td>
                    <td className="py-2 pr-4 text-text-muted whitespace-nowrap text-xs">
                      {s.completed_at ? new Date(s.completed_at).toLocaleString() : "—"}
                    </td>
                    <td className="py-2">
                      <Link href={`/scans/${s.id}`} className="text-primary font-medium">
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
