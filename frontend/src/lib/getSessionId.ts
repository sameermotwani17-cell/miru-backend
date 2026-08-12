export function getSessionId(): string | null {
  if (typeof window === "undefined") return null;

  const params = new URLSearchParams(window.location.search);
  const urlId = params.get("session_id");

  if (urlId) return urlId;

  const stored = sessionStorage.getItem("saiko_session_id");
  if (stored) return stored;

  return null;
}
