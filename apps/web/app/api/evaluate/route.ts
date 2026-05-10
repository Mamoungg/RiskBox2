import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const baseUrl = process.env.SANDBOX_API_URL ?? "http://localhost:8000";
  const apiKey = process.env.SANDBOX_SERVER_API_KEY;

  if (!apiKey) {
    return NextResponse.json({ error: "SANDBOX_SERVER_API_KEY is not configured" }, { status: 500 });
  }

  const body = await request.json();

  const upstream = await fetch(`${baseUrl.replace(/\/$/, "")}/api/v1/sandbox/evaluate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify(body),
  });

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/json" },
  });
}
