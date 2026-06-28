import Link from "next/link";

export default function NotFound() {
  return (
    <main className="grid min-h-screen place-items-center bg-paper px-4">
      <section className="w-full max-w-md rounded-lg border border-line bg-surface p-6 text-center shadow-soft">
        <p className="text-sm font-semibold text-marine">404</p>
        <h1 className="mt-2 text-2xl font-semibold text-ink">Page not found</h1>
        <p className="mt-2 text-sm text-ink/64">The dashboard view you requested does not exist.</p>
        <Link
          href="/"
          className="mt-5 inline-flex h-10 items-center justify-center rounded-md bg-marine px-4 text-sm font-semibold text-white transition hover:bg-marine/90"
        >
          Back to dashboard
        </Link>
      </section>
    </main>
  );
}
