// @ts-check
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import tailwindcss from "@tailwindcss/vite";

// Plausible analytics is only injected in production builds and only when a
// domain is configured via the PUBLIC_PLAUSIBLE_DOMAIN environment variable.
const plausibleDomain = process.env.PUBLIC_PLAUSIBLE_DOMAIN;
const isProd = process.env.NODE_ENV === "production";
const plausibleEnabled = isProd && Boolean(plausibleDomain);

const plausibleHead = plausibleEnabled
  ? [
      {
        tag: "script",
        attrs: {
          defer: true,
          "data-domain": plausibleDomain,
          src: "https://plausible.io/js/script.js",
        },
      },
    ]
  : [];

// https://astro.build/config
export default defineConfig({
  site: "https://speccify.io",
  vite: {
    plugins: [tailwindcss()],
  },
  integrations: [
    starlight({
      title: "Speccify",
      description:
        "Playbooks for complex, recurring workflows — written for coding agents, shared over Git.",
      // Without this, Starlight asks for /favicon.svg on every docs page and
      // the site ships a 404 the marketing pages do not have.
      favicon: "/logo.svg",
      head: plausibleHead,
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/mhennemeyer/speccify",
        },
      ],
      sidebar: [
        {
          label: "Getting Started",
          items: [{ autogenerate: { directory: "getting-started" } }],
        },
        {
          label: "Concepts",
          items: [{ autogenerate: { directory: "concepts" } }],
        },
        {
          label: "Viewer",
          items: [{ autogenerate: { directory: "viewer" } }],
        },
        {
          label: "Git sources & discovery",
          items: [{ autogenerate: { directory: "git-sources" } }],
        },
        {
          label: "CLI Reference",
          items: [{ autogenerate: { directory: "cli" } }],
        },
        {
          label: "MCP Reference",
          items: [{ autogenerate: { directory: "mcp" } }],
        },
      ],
    }),
  ],
});
