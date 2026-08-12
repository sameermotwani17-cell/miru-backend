import { NextRequest, NextResponse } from "next/server";

const BACKEND_BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  "https://miru-backend-production.up.railway.app";

export async function GET(request: NextRequest) {
  const sessionId = request.nextUrl.searchParams.get("session_id")?.trim();

  if (!sessionId) {
    return NextResponse.json(
      { detail: "Missing required query param: session_id" },
      { status: 400 }
    );
  }

  const query = request.nextUrl.searchParams.toString();
  const upstreamUrl = `${BACKEND_BASE}/api/interview/results${
    query ? `?${query}` : ""
  }`;

  try {
    const response = await fetch(upstreamUrl, {
      method: "GET",
      cache: "no-store",
    });

    const body = await response.json().catch(() => null);
    return NextResponse.json(
      body ?? { detail: `Upstream error: ${response.status}` },
      { status: response.status }
    );
  } catch {
    return NextResponse.json({ detail: "Upstream request failed." }, { status: 502 });
  }
}
