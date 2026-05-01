"use client";

import { useParams } from "next/navigation";

import { ScanDetailView } from "@/components/ScanDetailView";

export default function ScanDetailPage() {
  const params = useParams();
  const scanId = typeof params.scanId === "string" ? params.scanId : "";
  if (!scanId) {
    return <p className="text-text-muted">Invalid scan.</p>;
  }
  return <ScanDetailView scanId={scanId} />;
}
