import { useState, useRef } from "react";
import { theme } from "../theme";
import { inputAreaContainer, inputAreaTextarea } from "../styles/inputArea";

const MODELS = [
  { id: "claude-haiku", label: "Claude Haiku" },
  { id: "qwen-3.5",     label: "Qwen 3.5 (offline)" },
];

const styles = {
  container: { ...inputAreaContainer },
  textarea: { ...inputAreaTextarea },
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
  // shared style for New Chat and Attach buttons
  secondaryBtn: {
    fontFamily: theme.sora,
    fontWeight: 600,
    fontSize: "14px",
    padding: "10px 18px",
    border: `1.5px solid ${theme.line}`,
    borderRadius: "12px",
    background: theme.bgSoft,
    color: theme.textDim,
    cursor: "pointer",
  },
  secondaryBtnDisabled: {
    opacity: 0.35,
    cursor: "not-allowed",
  },
  chip: {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    padding: "4px 10px",
    borderRadius: "8px",
    background: theme.bgSoft,
    border: `1px solid ${theme.line}`,
    color: theme.textDim,
    fontFamily: theme.inter,
    fontSize: "12px",
  },
  chipRemove: {
    background: "none",
    border: "none",
    color: theme.textFaint,
    cursor: "pointer",
    padding: "0 2px",
    fontSize: "14px",
    lineHeight: 1,
  },
  modelSelect: {
    padding: "6px 12px",
    borderRadius: "8px",
    border: `1.5px solid ${theme.line}`,
    background: theme.bgSoft,
    color: theme.text,
    fontFamily: theme.sora,
    fontSize: "13px",
    fontWeight: 600,
    cursor: "pointer",
    outline: "none",
  },
};

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      // strip the data-URL prefix (e.g. "data:application/pdf;base64,")
      const base64 = reader.result.split(",")[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default function ChatBox({ onSend, onNewChat, loading }) {
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [selectedModel, setSelectedModel] = useState("claude-haiku");
  const fileInputRef = useRef(null);

  const handleSend = () => {
    const text = input.trim();
    if ((!text && attachments.length === 0) || loading) return;
    onSend(text, attachments, selectedModel);
    setInput("");
    setAttachments([]);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    const read = await Promise.all(
      files.map(async (file) => ({
        filename: file.name,
        media_type: file.type || "application/octet-stream",
        data_base64: await readFileAsBase64(file),
      }))
    );
    setAttachments((prev) => [...prev, ...read]);
    // reset so the same file can be re-attached if removed
    e.target.value = "";
  };

  const removeAttachment = (index) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div style={styles.container}>
      {/* File chips — shown above textarea when files are attached */}
      {attachments.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
          {attachments.map((a, i) => (
            <span key={i} style={styles.chip}>
              {a.filename}
              <button
                style={styles.chipRemove}
                onClick={() => removeAttachment(i)}
                aria-label={`Remove ${a.filename}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <textarea
        className="nexus-textarea"
        style={styles.textarea}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask anything — stock price, weather, news, code..."
      />

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt,.md,image/*"
        multiple
        style={{ display: "none" }}
        onChange={handleFileChange}
      />

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: "8px",
        }}
      >
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <button
            style={styles.secondaryBtn}
            onClick={onNewChat}
            className="new-chat-btn"
          >
            + New Chat
          </button>
          <button
            style={{
              ...styles.secondaryBtn,
              ...(selectedModel === "qwen-3.5" ? styles.secondaryBtnDisabled : {}),
            }}
            onClick={() => fileInputRef.current?.click()}
            disabled={selectedModel === "qwen-3.5"}
            title={selectedModel === "qwen-3.5" ? "Attachments not supported for offline models" : "Attach PDF, image, or text file"}
          >
            ⊕ Attach
          </button>
        </div>

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <select
            aria-label="Model"
            style={styles.modelSelect}
            value={selectedModel}
            onChange={(e) => {
              setSelectedModel(e.target.value);
              if (e.target.value === "qwen-3.5") setAttachments([]);
            }}
          >
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
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
    </div>
  );
}
