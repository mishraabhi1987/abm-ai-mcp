// Single source of truth for the shared input-area glass container and textarea.
// Used by ChatBox, Artifacts, and Agents — do not duplicate these values.

export const inputAreaContainer = {
  maxWidth: 700,
  margin: "0 auto",
  width: "100%",
  padding: 20,
  background: "rgba(20, 20, 24, 0.45)",
  backdropFilter: "blur(16px)",
  WebkitBackdropFilter: "blur(16px)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 20,
  boxSizing: "border-box",
  display: "flex",
  flexDirection: "column",
  gap: 12,
};

export const inputAreaTextarea = {
  background: "rgba(255, 255, 255, 0.04)",
  width: "100%",
  minHeight: 90,
  padding: "16px",
  color: "#e8e8e8",
  border: "1px solid #2e2e2e",
  borderRadius: 14,
  fontSize: 15,
  resize: "vertical",
  fontFamily: "inherit",
  boxSizing: "border-box",
  outline: "none",
  boxShadow: "0 0 30px rgba(199,5,5,0.25)",
  lineHeight: 1.6,
};
