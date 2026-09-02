"use client";

/** The last resort: a failure in the root layout itself.
 *
 *  error.tsx cannot catch this one, because the layout that would render it is
 *  the thing that broke — so this component replaces the whole document and
 *  must carry its own <html> and <body>. It also cannot rely on the app's
 *  stylesheet having loaded, which is why the styling here is inline and
 *  deliberately plain rather than tokenised.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en-IN">
      <body
        style={{
          margin: 0,
          minHeight: "100dvh",
          display: "grid",
          placeItems: "center",
          background: "#F7F8FA",
          color: "#1A1D23",
          fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
          padding: "2rem",
        }}
      >
        <main style={{ maxWidth: "34rem" }}>
          <p
            style={{
              margin: 0,
              fontSize: "0.6875rem",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "#5A6577",
            }}
          >
            Siliguri Traffic Command
          </p>
          <h1 style={{ margin: "0.5rem 0 0", fontSize: "1.5rem", lineHeight: 1.3 }}>
            The command board is down. Traffic is unaffected.
          </h1>
          <p style={{ margin: "0.75rem 0 0", lineHeight: 1.6, color: "#3A424E" }}>
            Nothing recorded has been lost — incidents, assignments and notes are held by
            the command centre, not by this page.
          </p>
          <p style={{ margin: "0.5rem 0 0", lineHeight: 1.6, color: "#3A424E" }}>
            Work the wireless until it returns. Do not read a blank screen as a quiet city.
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              marginTop: "1.25rem",
              border: 0,
              borderRadius: 4,
              background: "#1A2B4A",
              color: "#fff",
              padding: "0.5rem 0.875rem",
              font: "inherit",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Try again
          </button>
          {error.digest && (
            <p style={{ marginTop: "1.25rem", fontSize: "0.75rem", color: "#7A8598" }}>
              Reference for the log: {error.digest}
            </p>
          )}
        </main>
      </body>
    </html>
  );
}
