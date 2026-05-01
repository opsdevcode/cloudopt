import Link from "next/link";

const nav = [
  { href: "/", label: "Overview" },
  { href: "/scans", label: "Scans" },
  { href: "/findings", label: "Findings" },
  { href: "/rag", label: "RAG / AI" },
];

export function AppChrome({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-50 border-b border-border bg-white/85 backdrop-blur-md">
        <div className="max-w-content mx-auto px-6 md:px-10 py-4 flex items-center justify-between gap-6">
          <Link href="/" className="flex items-center gap-3 no-underline hover:opacity-90 transition-opacity">
            <span className="font-semibold text-lg tracking-tight text-text">CloudOpt</span>
            <span className="text-xs font-medium uppercase tracking-wider text-text-muted hidden sm:inline">
              Console
            </span>
          </Link>
          <nav className="flex flex-wrap gap-1 md:gap-6 items-center">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-sm font-medium text-text-secondary hover:text-text px-2 py-1 rounded-ops transition-colors hover:bg-bg-muted"
              >
                {item.label}
              </Link>
            ))}
            <a
              href="/docs"
              className="text-sm font-medium text-primary hover:text-primary-hover px-2 py-1"
            >
              API docs
            </a>
          </nav>
        </div>
      </header>
      <main className="flex-1 w-full max-w-content mx-auto px-6 md:px-10 py-10">{children}</main>
      <footer className="border-t border-border py-8 text-sm text-text-muted">
        <div className="max-w-content mx-auto px-6 md:px-10 flex flex-wrap gap-4 justify-between">
          <span>CloudOpt — FinOps & posture findings</span>
          <span>
            Brand palette & typography aligned with{" "}
            <a href="https://opsdevco.de/" className="text-primary hover:text-primary-hover">
              OpsDevCode
            </a>
          </span>
        </div>
      </footer>
    </div>
  );
}
