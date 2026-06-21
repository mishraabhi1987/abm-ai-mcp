import { useState } from "react";
import { marked } from "marked";
import { theme } from "../theme";
import { mdStyles } from "./Bubble";
import { runFinanceAgent } from "../api/agents";

const MODES = ["Finance"];

function exchangeLabel(symbol) {
  if (symbol.endsWith(".NS")) return "NSE";
  if (symbol.endsWith(".BO")) return "BSE";
  return "NYSE/NASDAQ";
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr.slice(0, 10);
  }
}

const styles = {
  shell: {
    flex: 1,
    minHeight: 0,
    display: "flex",
    flexDirection: "column",
    position: "relative",
    zIndex: 1,
    fontFamily: theme.inter,
    color: theme.text,
  },
  middle: {
    flex: 1,
    minHeight: 0,
    overflowY: "auto",
    padding: "20px 20px 0",
  },
  content: {
    maxWidth: 760,
    margin: "0 auto",
    paddingBottom: 24,
  },
  // Price hero
  priceHero: {
    background: theme.surface,
    border: `1px solid ${theme.line}`,
    borderRadius: 16,
    padding: "20px 24px",
    marginBottom: 20,
  },
  chipRow: {
    display: "flex",
    gap: 8,
    marginBottom: 14,
    alignItems: "center",
  },
  tickerChip: {
    fontFamily: theme.mono,
    fontSize: 13,
    fontWeight: 600,
    background: theme.bgSoft,
    border: `1px solid ${theme.line}`,
    borderRadius: 6,
    padding: "3px 10px",
    color: theme.textDim,
    letterSpacing: "0.04em",
  },
  exchangeChip: {
    fontSize: 11,
    fontWeight: 600,
    background: "rgba(255,200,61,0.08)",
    border: `1px solid rgba(255,200,61,0.2)`,
    borderRadius: 6,
    padding: "3px 9px",
    color: theme.accent,
    letterSpacing: "0.06em",
  },
  priceRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: 12,
    marginBottom: 16,
  },
  bigPrice: {
    fontFamily: theme.mono,
    fontSize: 40,
    fontWeight: 700,
    letterSpacing: "-0.02em",
    color: theme.text,
  },
  currency: {
    fontFamily: theme.mono,
    fontSize: 18,
    color: theme.textDim,
    marginLeft: 6,
  },
  metricsRow: {
    display: "flex",
    gap: 24,
    flexWrap: "wrap",
    borderTop: `1px solid ${theme.line}`,
    paddingTop: 14,
  },
  metric: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  metricLabel: {
    fontSize: 11,
    color: theme.textFaint,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  metricValue: {
    fontFamily: theme.mono,
    fontSize: 14,
    color: theme.textDim,
  },
  // Section eyebrow
  eyebrow: {
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: "0.1em",
    textTransform: "uppercase",
    color: theme.accent,
    marginBottom: 12,
  },
  section: {
    marginBottom: 24,
  },
  // News
  newsEmpty: {
    fontSize: 14,
    color: theme.textFaint,
    padding: "12px 0",
  },
  newsCard: {
    display: "block",
    textDecoration: "none",
    background: theme.surface,
    border: `1px solid ${theme.line}`,
    borderRadius: 12,
    padding: "14px 16px",
    marginBottom: 10,
    color: theme.text,
  },
  newsMeta: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 6,
  },
  sourceBadge: {
    fontSize: 11,
    fontWeight: 600,
    background: theme.bgSoft,
    border: `1px solid ${theme.line}`,
    borderRadius: 5,
    padding: "2px 8px",
    color: theme.textDim,
    fontFamily: theme.mono,
  },
  newsDate: {
    fontSize: 12,
    color: theme.textFaint,
  },
  newsHeadline: {
    fontFamily: theme.sora,
    fontSize: 14,
    fontWeight: 600,
    color: theme.text,
    lineHeight: 1.4,
    marginBottom: 4,
  },
  newsSummary: {
    fontSize: 13,
    color: theme.textDim,
    lineHeight: 1.5,
  },
  // Analysis
  analysisBox: {
    background: theme.surface,
    border: `1px solid ${theme.line}`,
    borderRadius: 14,
    padding: "16px 20px",
  },
  disclaimer: {
    fontSize: 12,
    color: theme.textFaint,
    borderTop: `1px solid ${theme.line}`,
    marginTop: 14,
    paddingTop: 12,
  },
  // Error
  errorText: {
    color: theme.primaryDeep,
    fontSize: 14,
    marginBottom: 14,
  },
  // Bottom input area
  bottom: {
    flexShrink: 0,
    padding: "12px 20px 16px",
    borderTop: `1px solid ${theme.line}`,
    background: theme.bg,
  },
  inputBox: {
    maxWidth: 760,
    margin: "0 auto",
    background: theme.surface,
    border: `1px solid ${theme.line}`,
    borderRadius: 16,
    padding: 14,
  },
  textarea: {
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
  },
  actions: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 8,
  },
  modeToggle: {
    display: "flex",
    gap: 6,
    background: theme.bgSoft,
    border: `1px solid ${theme.line}`,
    borderRadius: 10,
    padding: 4,
  },
};

function changePillStyle(change) {
  const positive = change >= 0;
  return {
    display: "inline-flex",
    alignItems: "center",
    padding: "6px 14px",
    borderRadius: 20,
    fontFamily: theme.mono,
    fontSize: 15,
    fontWeight: 700,
    background: positive ? "rgba(74,222,128,0.12)" : "rgba(199,5,5,0.12)",
    color: positive ? "#4ade80" : "#ff6b6b",
    border: positive ? "1px solid rgba(74,222,128,0.25)" : "1px solid rgba(199,5,5,0.25)",
  };
}

function subTabStyle(active) {
  return {
    padding: "6px 14px",
    fontSize: 13,
    borderRadius: 8,
    cursor: "pointer",
    border: "none",
    fontWeight: active ? 600 : 400,
    background: active ? theme.primaryDeep : "transparent",
    color: active ? "#fff" : theme.textDim,
    fontFamily: theme.inter,
  };
}

function runBtnStyle(loading) {
  return {
    padding: "10px 20px",
    borderRadius: 10,
    border: "none",
    cursor: loading ? "default" : "pointer",
    fontWeight: 600,
    fontSize: 15,
    background: theme.primaryDeep,
    color: "#fff",
    opacity: loading ? 0.6 : 1,
    fontFamily: theme.inter,
  };
}

export default function Agents() {
  const [mode, setMode] = useState("Finance");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const switchMode = (next) => {
    setMode(next);
    setResult(null);
    setError("");
  };

  const handleRun = async () => {
    const q = prompt.trim();
    if (!q || loading) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await runFinanceAgent(q);
      if (data.price?.error) {
        setError(data.price.error);
      } else {
        setResult(data);
      }
    } catch (e) {
      setError(e.message || "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.shell}>
      {/* Hover lift for news cards */}
      <style>{`
        .agent-news-card {
          transition: transform 0.2s ease, box-shadow 0.2s ease,
                      background 0.2s ease, border-color 0.2s ease,
                      backdrop-filter 0.2s ease;
        }
        .agent-news-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 24px rgba(0,0,0,0.4);
          background: rgba(255,255,255,0.06) !important;
          border-color: rgba(255,255,255,0.12) !important;
          backdrop-filter: blur(14px);
          -webkit-backdrop-filter: blur(14px);
        }
      `}</style>

      {/* MIDDLE — scrollable results */}
      <div style={styles.middle}>
        <div style={styles.content}>
          {error && <p style={styles.errorText}>{error}</p>}

          {result && (
            <>
              {/* ── PRICE HERO ── */}
              <div style={styles.priceHero}>
                <div style={styles.chipRow}>
                  <span style={styles.tickerChip}>{result.price.symbol}</span>
                  <span style={styles.exchangeChip}>{exchangeLabel(result.price.symbol)}</span>
                </div>
                <div style={styles.priceRow}>
                  <div>
                    <span style={styles.bigPrice}>
                      {result.price.current.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                    <span style={styles.currency}>{result.price.currency}</span>
                  </div>
                  <span style={changePillStyle(result.price.change ?? 0)}>
                    {(result.price.change ?? 0) >= 0 ? "+" : ""}{result.price.change?.toFixed(2) ?? "—"}
                    {" "}({(result.price.change_pct ?? 0) >= 0 ? "+" : ""}{result.price.change_pct?.toFixed(2) ?? "—"}%)
                  </span>
                </div>
                <div style={styles.metricsRow}>
                  <div style={styles.metric}>
                    <span style={styles.metricLabel}>Prev Close</span>
                    <span style={styles.metricValue}>{result.price.prev_close?.toFixed(2) ?? "—"}</span>
                  </div>
                  <div style={styles.metric}>
                    <span style={styles.metricLabel}>Day Change</span>
                    <span style={styles.metricValue}>
                      {(result.price.change ?? 0) >= 0 ? "+" : ""}{result.price.change?.toFixed(2) ?? "—"}
                    </span>
                  </div>
                  <div style={styles.metric}>
                    <span style={styles.metricLabel}>Change %</span>
                    <span style={styles.metricValue}>
                      {(result.price.change_pct ?? 0) >= 0 ? "+" : ""}{result.price.change_pct?.toFixed(2) ?? "—"}%
                    </span>
                  </div>
                </div>
              </div>

              {/* ── NEWS ── */}
              <div style={styles.section}>
                <div style={styles.eyebrow}>News</div>
                {result.news.length === 0 ? (
                  <p style={styles.newsEmpty}>No recent news found.</p>
                ) : (
                  result.news.map((item, i) => (
                    <a
                      key={item.url || i}
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={styles.newsCard}
                      className="agent-news-card"
                    >
                      <div style={styles.newsMeta}>
                        {item.source && <span style={styles.sourceBadge}>{item.source}</span>}
                        {item.date && <span style={styles.newsDate}>{formatDate(item.date)}</span>}
                      </div>
                      <div style={styles.newsHeadline}>{item.title}</div>
                      {item.summary && <div style={styles.newsSummary}>{item.summary}</div>}
                    </a>
                  ))
                )}
              </div>

              {/* ── ANALYSIS ── */}
              {result.analysis && (
                <div style={styles.section}>
                  <div style={styles.eyebrow}>Analysis</div>
                  <div style={styles.analysisBox}>
                    <style>{mdStyles}</style>
                    <div
                      className="md-content"
                      dangerouslySetInnerHTML={{ __html: marked.parse(result.analysis) }}
                    />
                    <p style={styles.disclaimer}>
                      Not financial advice. Interpretation only — verify all data before acting.
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* BOTTOM — pinned input */}
      <div style={styles.bottom}>
        <div style={styles.inputBox}>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Reliance Industries · RELIANCE · RELIANCE.NS · TCS"
            style={styles.textarea}
          />
          <div style={styles.actions}>
            <div style={styles.modeToggle}>
              {MODES.map((m) => (
                <button key={m} style={subTabStyle(mode === m)} onClick={() => switchMode(m)}>
                  {m}
                </button>
              ))}
            </div>
            <button onClick={handleRun} disabled={loading} style={runBtnStyle(loading)}>
              {loading ? "Analyzing…" : "Run agent →"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
