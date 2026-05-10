import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Preflight Sandbox",
  description: "Demo dashboard for the agent-facing preflight evaluation API",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gradient-to-b from-zinc-50 to-white">{children}</body>
    </html>
  );
}
