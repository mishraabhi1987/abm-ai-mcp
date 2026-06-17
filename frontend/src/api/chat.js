// FastAPI backend se baat karne wala layer
// session_id yahin manage hota hai (frontend memory)

let sessionId = null;

// Main chat function — message bhejta hai, jawab laata hai
export async function sendMessage(message, mode = "auto") {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: message,
      mode: mode,
      session_id: sessionId,
    }),
  });

  if (!res.ok) {
    throw new Error(`Server error: ${res.status}`);
  }

  const data = await res.json();

  // backend se mila session_id save karo (agle message ke liye)
  sessionId = data.session_id;

  return {
    answer: data.answer,
    chartData: data.chart_data,
  };
}

// New Chat button ke liye — history clear karo
export async function newChat() {
  if (sessionId) {
    await fetch("/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
  }
  sessionId = null; // reset
}

// If your existing file already defines a BASE/API_URL constant, reuse it
// and delete this line. Otherwise set it to your FastAPI origin.
const LYRICS_API_BASE = "http://localhost:8000"; // <-- match your /chat base

export async function generateLyrics(prompt) {
  const res = await fetch(`${LYRICS_API_BASE}/api/lyrics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mood: prompt }), // whole input passed as mood/genre
  });
  if (!res.ok) throw new Error(`Lyrics request failed (${res.status})`);
  return res.json(); // { lyrics: "..." }
}
