import { useState } from "react";
import { theme } from "../theme";

const styles = {
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    maxWidth: "700px",
    margin: "0 auto",
    width: "100%",
    padding: "20px",
    background: "rgba(20, 20, 24, 0.45)",
    backdropFilter: "blur(16px)",
    WebkitBackdropFilter: "blur(16px)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: "20px",
    boxSizing: "border-box",
    // NOTE: position:fixed/bottom/left/transform/zIndex hata diye —
    // ab ye App ke bottom zone (flexShrink:0) ke andar normal block hai.
  },
  textarea: {
    background: "rgba(255, 255, 255, 0.04)",
    width: "100%",
    minHeight: "90px",
    padding: "16px",
    color: "#e8e8e8",
    border: "1px solid #2e2e2e",
    borderRadius: "14px",
    fontSize: "15px",
    resize: "vertical",
    fontFamily: "inherit",
    boxSizing: "border-box",
    outline: "none",
    boxShadow: "0 0 30px rgba(199,5,5,0.25)",
  },
  askBtn: {
    alignSelf: "flex-end",
    padding: "13px 30px",
    background: "#c70505",
    color: "#fff",
    border: "none",
    borderRadius: "10px",
    cursor: "pointer",
    fontSize: "15px",
    fontWeight: "700",
    marginTop: "10px",
    transition: "background 0.2s, box-shadow 0.2s",
  },
  askBtnDisabled: {
    background: "#5a3a2a",
    cursor: "not-allowed",
  },
};

export default function ChatBox({ onSend, onNewChat, loading }) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    const text = input.trim();
    if (!text || loading) return;
    onSend(text);
    setInput("");
  };

  // Enter = send, Shift+Enter = new line
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={styles.container}>
      <textarea
        className="nexus-textarea"
        style={styles.textarea}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask anything — stock price, weather, news, code..."
      />
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: "8px",
        }}
      >
        <button
          style={{
            fontFamily: theme.sora,
            fontWeight: 600,
            fontSize: "14px",
            padding: "10px 18px",
            border: `1.5px solid ${theme.line}`,
            borderRadius: "12px",
            background: theme.bgSoft,
            color: theme.textDim,
            cursor: "pointer",
          }}
          onClick={onNewChat}
          className="new-chat-btn"
        >
          + New Chat
        </button>

        <button
          style={{
            ...styles.askBtn,
            alignSelf: "auto",
            marginTop: 0,
            ...(loading ? styles.askBtnDisabled : {}),
          }}
          onClick={handleSend}
          disabled={loading}
        >
          {loading ? "Thinking..." : "Ask →"}
        </button>
      </div>
    </div>
  );
}
