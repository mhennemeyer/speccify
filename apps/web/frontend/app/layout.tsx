import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Speccify Playground",
  description:
    "Browser playground for the Speccify spec-first component pipeline.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
          margin: 0,
          padding: 0,
          background: "#0b0d10",
          color: "#e6e8eb",
          minHeight: "100vh",
        }}
      >
        {children}
      </body>
    </html>
  );
}
