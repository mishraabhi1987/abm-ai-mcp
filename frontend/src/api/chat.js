// FastAPI backend communication layer.
// sessionId is module-level for the main chat tab.
// Artifacts manages its own sessionId and passes it explicitly via the options arg.

let sessionId = null;

export async function sendMessage(
  message,
  mode = "auto",
  { sessionId: sessionIdIn = null, attachments = null, model = "claude-haiku" } = {}
) {
  const sid = sessionIdIn ?? sessionId;

  const body = { message, mode, session_id: sid, model };
  if (attachments?.length) body.attachments = attachments;

  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(`Server error: ${res.status}`);
  }

  const data = await res.json();

  // Only update the module-level sessionId for the main chat tab
  if (!sessionIdIn) sessionId = data.session_id;

  return {
    answer: data.answer,
    chartData: data.chart_data,
    sessionId: data.session_id,
  };
}

export async function newChat() {
  if (sessionId) {
    await fetch("/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
  }
  sessionId = null;
}

const LYRICS_API_BASE = "http://localhost:8000";

export async function generateLyrics(prompt) {
  const res = await fetch(`${LYRICS_API_BASE}/api/lyrics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mood: prompt }),
  });
  if (!res.ok) throw new Error(`Lyrics request failed (${res.status})`);
  return res.json();
}
