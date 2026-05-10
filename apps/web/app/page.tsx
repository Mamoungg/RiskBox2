"use client";

import { useMemo, useState } from "react";

import type { EvaluateRequest, EvaluateResponse } from "@agent-preflight/shared-types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const defaultPayload: EvaluateRequest = {
  task_type: "code_and_payment",
  action_summary: "Merge contractor PR touching authentication helpers and pay invoice INV-123",
  repository_url: "https://github.com/vercel/ai",
  repository_ref: "main",
  diff_text:
    "--- a/packages/auth/src/index.ts\n+++ b/packages/auth/src/index.ts\n@@\n- return verify(token)\n+ return true\n",
  policy_urls: ["https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions"],
  documentation_urls: [],
  payment_request: {
    amount: 2500,
    currency: "USD",
    recipient: "contractor@example.com",
    invoice_reference: "INV-123",
  },
  constraints: {
    max_risk_score: 45,
    require_citations: true,
  },
};

export default function HomePage() {
  const [jsonInput, setJsonInput] = useState(() => JSON.stringify(defaultPayload, null, 2));
  const [response, setResponse] = useState<EvaluateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const parsedPreview = useMemo(() => {
    try {
      return JSON.parse(jsonInput) as EvaluateRequest;
    } catch {
      return null;
    }
  }, [jsonInput]);

  async function runEvaluate() {
    setError(null);
    setResponse(null);
    setLoading(true);
    try {
      const payload = JSON.parse(jsonInput) as EvaluateRequest;
      const res = await fetch("/api/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const text = await res.text();
      if (!res.ok) {
        setError(text);
        return;
      }
      setResponse(JSON.parse(text) as EvaluateResponse);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "unknown_error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-12">
      <header className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">Hackathon MVP</p>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">Agent Preflight Sandbox</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-zinc-600">
          This UI is a thin inspection layer. Agents should call the FastAPI service directly with an{" "}
          <span className="font-mono text-xs">X-API-Key</span> header. The demo posts JSON through a Next.js route
          handler that injects a server-side key.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Evaluate payload</CardTitle>
            <CardDescription>Edit the JSON request sent to POST /api/v1/sandbox/evaluate</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="payload">JSON body</Label>
              <Textarea id="payload" value={jsonInput} onChange={(e) => setJsonInput(e.target.value)} />
            </div>
            {!parsedPreview && <p className="text-sm text-red-600">Invalid JSON — fix syntax before running.</p>}
            <Button onClick={runEvaluate} disabled={loading || !parsedPreview}>
              {loading ? "Running preflight…" : "Run preflight"}
            </Button>
            {error && (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-800">{error}</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Latest verdict</CardTitle>
            <CardDescription>Structured response from the API</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {response ? (
              <div className="space-y-3 text-sm">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="rounded-full bg-zinc-900 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white">
                    {response.status}
                  </span>
                  <span className="text-xs text-zinc-500">run_id: {response.run_id}</span>
                </div>
                <div>
                  <p className="text-xs uppercase text-zinc-500">Risk score</p>
                  <Input readOnly value={String(response.risk_score)} />
                </div>
                <div>
                  <p className="text-xs uppercase text-zinc-500">Summary</p>
                  <p className="rounded-md border bg-white p-3 text-sm leading-relaxed text-zinc-800">
                    {response.summary}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase text-zinc-500">Reasons</p>
                  <ul className="list-disc space-y-1 pl-5 text-sm text-zinc-700">
                    {response.reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs uppercase text-zinc-500">Safer alternative</p>
                  <p className="rounded-md border bg-white p-3 text-sm leading-relaxed text-zinc-800">
                    {response.safer_alternative}
                  </p>
                </div>
                <details className="rounded-md border bg-zinc-50 p-3 text-xs text-zinc-700">
                  <summary className="cursor-pointer font-semibold text-zinc-900">Sponsor payloads</summary>
                  <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words">
                    {JSON.stringify(
                      {
                        context_assessment: response.context_assessment,
                        code_assessment: response.code_assessment,
                        payment_assessment: response.payment_assessment,
                        llm_synthesis: response.llm_synthesis,
                        timings: response.timings,
                      },
                      null,
                      2,
                    )}
                  </pre>
                </details>
              </div>
            ) : (
              <p className="text-sm text-zinc-600">Run an evaluation to see the response.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
