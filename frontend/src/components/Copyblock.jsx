import { useState } from "react";
import { theme } from "../theme";

// One-click copyable text block. Readable (NOT code/monospace) — meant for lyrics,
// notes, news, etc. Pass the text as `content`; optional `label` for the header.
export default function CopyBlock({ content = "", label = "Lyrics" }) {
  const [copied, setCopied] = useState(false);

  const C = {
    red: "#E2492E",
    muted: "#8a8a90",
    border: "rgba(255,255,255,0.08)",
    panel: "#141417",
    head: "#1b1b1f",
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      // clipboard API blocked (e.g. non-HTTPS) -> fallback
      const ta = document.createElement("textarea");
      ta.value = content;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  return (
    <div
      style={{
        background: C.panel,
        border: `1px solid ${C.border}`,
        borderRadius: 16,
        overflow: "hidden",
        fontFamily: theme.inter,
      }}
    >
      {/* header with Copy button */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px",
          background: C.head,
          borderBottom: `1px solid ${C.border}`,
        }}
      >
        <span style={{ fontSize: 13, color: C.muted }}>{label}</span>
        <button
          onClick={handleCopy}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "5px 12px",
            fontSize: 13,
            fontWeight: 600,
            border: "none",
            borderRadius: 8,
            cursor: "pointer",
            background: copied ? "#2e7d4f" : C.red,
            color: "#fff",
          }}
        >
          {/* tiny clipboard icon (dependency-free) */}
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="9" y="9" width="13" height="13" rx="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      {/* readable lyrics body — NOT monospace */}
      <div
        style={{
          whiteSpace: "pre-wrap",
          fontSize: 15,
          lineHeight: 1.9,
          padding: "22px 24px",
          color: theme.text,
        }}
      >
        {content}
      </div>
    </div>
  );
}
