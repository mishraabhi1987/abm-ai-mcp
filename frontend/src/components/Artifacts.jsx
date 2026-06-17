import { useState } from "react";
import { theme } from "../theme";
import CodeArtifact from "./CodeArtifact";
import CopyBlock from "./CopyBlock";
import { sendMessage, generateLyrics } from "../api/chat";

const CODE_INSTRUCTION =
  "You are a code generator. Output ONE complete, self-contained HTML document " +
  "with inline <style> and <script> (HTML + CSS + JS in a single file). " +
  "Return ONLY the raw code — no explanation, no markdown fences. Request: ";

function extractCode(text) {
  if (!text) return "";
  const fence = text.match(/```(?:html|js|javascript)?\s*([\s\S]*?)```/i);
  if (fence) return fence[1].trim();
  const tagIdx = text.search(/<!doctype|<html|<body|<div|<section/i);
  if (tagIdx >= 0) return text.slice(tagIdx).trim();
  return text.trim();
}

export default function Artifacts() {
  const [mode, setMode] = useState("code"); // "code" | "lyrics"
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState(null); // { type, code|text }
  const [error, setError] = useState("");

  const C = {
    red: "#E2492E",
    muted: "#8a8a90",
    border: "rgba(255,255,255,0.08)",
    panel: "#141417",
    bg: "#0d0d10",
  };

  const handleGenerate = async () => {
    const p = prompt.trim();
    if (!p || loading) return;
    setLoading(true);
    setError("");
    setOutput(null);
    try {
      if (mode === "code") {
        const { answer } = await sendMessage(CODE_INSTRUCTION + p);
        setOutput({ type: "code", code: extractCode(answer) });
      } else {
        const { lyrics } = await generateLyrics(p);
        setOutput({ type: "lyrics", text: lyrics });
      }
    } catch (e) {
      setError(e.message || "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const tab = (active) => ({
    padding: "6px 14px",
    fontSize: 13,
    borderRadius: 8,
    cursor: "pointer",
    border: "none",
    fontWeight: active ? 600 : 400,
    background: active ? C.red : "transparent",
    color: active ? "#fff" : C.muted,
  });

  return (
    // Fills the area below the top zone, as its own flex column
    <div
      style={{
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        position: "relative",
        zIndex: 1,
        fontFamily: theme.inter,
        color: theme.text,
      }}
    >
      {/* MIDDLE — fills remaining height (top zone & input are fixed) */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          padding: 20,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            maxWidth: 760,
            width: "100%",
            margin: "0 auto",
            flex: 1,
            minHeight: 0,
            display: "flex",
            flexDirection: "column",
          }}
        >
          {error && (
            <p style={{ color: C.red, fontSize: 14, marginBottom: 14 }}>
              {error}
            </p>
          )}
          {output?.type === "code" && (
            <CodeArtifact initialCode={output.code} />
          )}
          {output?.type === "lyrics" && (
            <div style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
              <CopyBlock content={output.text} label="Lyrics" />
            </div>
          )}
        </div>
      </div>

      {/* BOTTOM — fixed input: toggle (left) + generate (right) */}
      <div
        style={{
          flexShrink: 0,
          padding: "12px 20px 16px",
          borderTop: `1px solid ${C.border}`,
          background: theme.bg,
        }}
      >
        <div
          style={{
            maxWidth: 760,
            margin: "0 auto",
            background: C.panel,
            border: `1px solid ${C.border}`,
            borderRadius: 16,
            padding: 14,
          }}
        >
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={
              mode === "code"
                ? "Describe the UI — e.g. a glowing pricing card with a hover effect"
                : "Genre / mood — e.g. hindi romantic, anchor: a fading evening"
            }
            style={{
              width: "100%",
              minHeight: 70,
              boxSizing: "border-box",
              resize: "vertical",
              border: "none",
              outline: "none",
              background: "transparent",
              color: theme.text,
              fontFamily: theme.inter,
              fontSize: 15,
              lineHeight: 1.6,
            }}
          />

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginTop: 8,
            }}
          >
            <div
              style={{
                display: "flex",
                gap: 6,
                background: C.bg,
                border: `1px solid ${C.border}`,
                borderRadius: 10,
                padding: 4,
              }}
            >
              <button
                style={tab(mode === "code")}
                onClick={() => {
                  setMode("code");
                  setOutput(null);
                  setError("");
                }}
              >
                Code
              </button>
              <button
                style={tab(mode === "lyrics")}
                onClick={() => {
                  setMode("lyrics");
                  setOutput(null);
                  setError("");
                }}
              >
                Lyrics
              </button>
            </div>

            <button
              onClick={handleGenerate}
              disabled={loading}
              style={{
                padding: "10px 20px",
                borderRadius: 10,
                border: "none",
                cursor: loading ? "default" : "pointer",
                fontWeight: 600,
                fontSize: 15,
                background: C.red,
                color: "#fff",
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading
                ? "Generating…"
                : mode === "code"
                  ? "Generate code →"
                  : "Write lyrics →"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
