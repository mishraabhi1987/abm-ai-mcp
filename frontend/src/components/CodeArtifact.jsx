import { useState } from "react";

const SAMPLE = `<!doctype html>
<html>
<head>
<style>
  body{margin:0;min-height:100vh;display:grid;place-items:center;
       font-family:system-ui,sans-serif;background:#0a0a0c;color:#e7e7ea}
  .card{padding:28px 34px;border-radius:16px;background:#161618;
        border:1px solid rgba(255,255,255,.08);text-align:center}
  h1{margin:0 0 4px;font-size:20px;letter-spacing:.5px}
  h1 b{color:#E2492E}
  p{margin:0 0 18px;color:#8a8a90;font-size:14px}
  button{border:0;border-radius:10px;padding:10px 18px;cursor:pointer;
         background:#E2492E;color:#fff;font-size:15px;font-weight:600}
  #n{color:#E9A23B}
</style>
</head>
<body>
  <div class="card">
    <h1>AB<b>M</b> Playground</h1>
    <p>HTML + CSS + JS — live preview</p>
    <button onclick="document.getElementById('n').textContent=++count">
      Tapped <span id="n">0</span> times
    </button>
    <script>let count = 0;</script>
  </div>
</body>
</html>`;

// tiny dependency-free icons
const IconCode = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M8 6l-6 6 6 6M16 6l6 6-6 6" />
  </svg>
);
const IconEye = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);
const IconPlay = () => (
  <svg
    width="13"
    height="13"
    viewBox="0 0 24 24"
    fill="currentColor"
    stroke="none"
  >
    <path d="M6 4l14 8-14 8z" />
  </svg>
);

export default function CodeArtifact({ initialCode = SAMPLE }) {
  const [code, setCode] = useState(initialCode || SAMPLE);
  const [view, setView] = useState("code");
  const [runKey, setRunKey] = useState(0);

  const C = {
    bg: "#0a0a0c",
    panel: "#141417",
    border: "rgba(255,255,255,0.08)",
    muted: "#8a8a90",
    red: "#E2492E",
  };

  const tab = (active) => ({
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "6px 13px",
    fontSize: 13,
    borderRadius: 8,
    cursor: "pointer",
    border: "none",
    fontWeight: active ? 600 : 400,
    background: active ? C.red : "transparent",
    color: active ? "#fff" : C.muted,
  });

  return (
    <div
      style={{
        background: C.bg,
        borderRadius: 14,
        border: `1px solid ${C.border}`,
        overflow: "hidden",
        fontFamily: "system-ui, sans-serif",
        maxWidth: 760,
        margin: "0 auto",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 12px",
          borderBottom: `1px solid ${C.border}`,
          background: C.panel,
        }}
      >
        <span
          style={{
            fontSize: 13,
            color: C.muted,
            fontFamily: "ui-monospace, monospace",
          }}
        >
          index.html
        </span>
        <div
          style={{
            display: "flex",
            gap: 4,
            background: "#0d0d10",
            padding: 4,
            borderRadius: 10,
          }}
        >
          <button style={tab(view === "code")} onClick={() => setView("code")}>
            <IconCode /> Code
          </button>
          <button
            style={tab(view === "preview")}
            onClick={() => {
              setView("preview");
              setRunKey((k) => k + 1);
            }}
          >
            <IconEye /> Preview
          </button>
        </div>
      </div>

      {view === "code" ? (
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          spellCheck={false}
          style={{
            width: "100%",
            height: 360,
            boxSizing: "border-box",
            resize: "vertical",
            border: "none",
            outline: "none",
            padding: 16,
            background: C.bg,
            color: "#d6d6da",
            fontFamily: "ui-monospace, monospace",
            fontSize: 13,
            lineHeight: 1.6,
          }}
        />
      ) : (
        <div style={{ position: "relative" }}>
          <button
            onClick={() => setRunKey((k) => k + 1)}
            style={{
              position: "absolute",
              top: 10,
              right: 10,
              zIndex: 2,
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "6px 12px",
              fontSize: 13,
              fontWeight: 600,
              border: "none",
              borderRadius: 8,
              cursor: "pointer",
              background: C.red,
              color: "#fff",
            }}
          >
            <IconPlay /> Run
          </button>
          <iframe
            key={runKey}
            srcDoc={code}
            title="preview"
            sandbox="allow-scripts allow-modals"
            style={{
              width: "100%",
              height: 360,
              border: "none",
              background: "#fff",
              display: "block",
            }}
          />
        </div>
      )}
    </div>
  );
}
