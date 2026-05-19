import Link from "next/link";

/**
 * Landing page — minimal hero pointing to the playground. Phase 1d is a
 * developer-facing demo, so we don't invest in marketing surface yet.
 */
export default function HomePage() {
  return (
    <main
      style={{
        maxWidth: 760,
        margin: "0 auto",
        padding: "6rem 1.5rem",
      }}
    >
      <h1 style={{ fontSize: "2.5rem", margin: 0 }}>Speccify</h1>
      <p style={{ fontSize: "1.125rem", color: "#a8b0b8", marginTop: "1rem" }}>
        Spec-first components. Describe behaviour in YAML, let the agent
        compile to your target framework.
      </p>
      <p style={{ marginTop: "2rem" }}>
        <Link
          href="/playground"
          style={{
            display: "inline-block",
            padding: "0.75rem 1.25rem",
            background: "#3b82f6",
            color: "white",
            borderRadius: 6,
            textDecoration: "none",
            fontWeight: 600,
          }}
        >
          Open Playground →
        </Link>
      </p>
      <p
        style={{
          marginTop: "3rem",
          fontSize: "0.875rem",
          color: "#6b7280",
        }}
      >
        Phase 1d preview · offline replay cache · no live LLM
      </p>
    </main>
  );
}
