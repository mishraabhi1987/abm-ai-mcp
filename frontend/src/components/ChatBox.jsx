import { useState } from "react";
import { theme } from "../theme";

const styles = {
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    maxWidth: "700px",
    margin: "0 auto",
    marginTop: "30px",
    width: "100%",
    padding: "20px", // ← glass panel ko andar space
    background: "rgba(20, 20, 24, 0.45)",
    backdropFilter: "blur(16px)",
    WebkitBackdropFilter: "blur(16px)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: "20px",
    boxSizing: "border-box", // ← padding add kiya toh zaroori

    position: "fixed", // ← व्यूपोर्ट पर हमेशा फिक्स रखने के लिए
    bottom: "20px", // ← नीचे से 20px की दूरी (ताकि किनारे से न चिपके)
    left: "50%", // ← सेंटर करने का पहला स्टेप
    transform: "translateX(-50%)", // ← सेंटर करने का सटीक तरीका
    zIndex: 1000,
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
  chatBox: {
    background: "rgba(20, 20, 24, 0.45)", // solid se transparent
    backdropFilter: "blur(16px)",
    WebkitBackdropFilter: "blur(16px)", // Safari ke liye (tum Mac pe ho)
    border: "1px solid rgba(255, 255, 255, 0.08)",
    borderRadius: "20px",
    // ...baaki same
  },
};

export default function ChatBox({ onSend, onNewChat, loading }) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    const text = input.trim();
    if (!text || loading) return;
    onSend(text); // parent ko message bhejo
    setInput(""); // input clear karo
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
      {/* New Chat — top right */}
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
        {/* New Chat — left */}
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

        {/* Ask — right */}
        <button
          style={{
            ...styles.askBtn,
            alignSelf: "auto", // override
            marginTop: 0, // override
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
