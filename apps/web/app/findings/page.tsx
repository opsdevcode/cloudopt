import { Suspense } from "react";

import { FindingsView } from "@/components/FindingsView";

export default function FindingsPage() {
  return (
    <Suspense fallback={<p className="text-text-muted">Loading findings…</p>}>
      <FindingsView />
    </Suspense>
  );
}
