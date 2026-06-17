// Ek single chat message — user ya assistant
import { marked } from "marked";
import { theme } from "../theme";

const styles = {
  row: {
    display: "flex",
    marginBottom: "16px",
  },
  userRow: {
    justifyContent: "flex-end",
  },
  botRow: {
    justifyContent: "flex-start",
  },
  bubble: {
    maxWidth: "100%",
    padding: "14px 18px",
    borderRadius: "16px",
    fontSize: "15px",
    lineHeight: "1.6",
    wordWrap: "break-word",
    boxSizing: "border-box",
  },
  userBubble: {
    maxWidth: "78%", // user message compact rahe, daayein
    background: "#3a2416",
    color: "#f0b541",
    border: "1px solid #5a3a1f",
    borderBottomRightRadius: "4px",
    whiteSpace: "pre-wrap", // user text mein line breaks preserve
  },
  botBubble: {
    width: "100%", // assistant reply hamesha poori width (consistent)
    background: "#1e1e1e",
    color: "#e8e8e8",
    border: "1px solid #2e2e2e",
    borderBottomLeftRadius: "4px",
  },
};

// Markdown content ke liye compact styles (alag variable)
const mdStyles = `
  .md-content > *:first-child { margin-top: 0; }
  .md-content > *:last-child { margin-bottom: 0; }
  .md-content h1, .md-content h2, .md-content h3 {
    font-family: ${theme.sora};
    margin: 14px 0 6px;
    line-height: 1.25;
  }
  .md-content h1 { font-size: 19px; }
  .md-content h2 { font-size: 17px; color: ${theme.accent}; }
  .md-content h3 { font-size: 15px; color: ${theme.accent}; }
  .md-content p { margin: 6px 0; }
  .md-content ul, .md-content ol { margin: 6px 0; padding-left: 20px; }
  .md-content li { margin: 3px 0; }
  .md-content li::marker { color: ${theme.primary}; }
  .md-content strong { color: #fff; font-weight: 600; }
  .md-content a { color: ${theme.accent}; }
  .md-content code {
    font-family: ${theme.mono};
    font-size: 13px;
    background: ${theme.bg};
    padding: 2px 6px;
    border-radius: 5px;
    color: ${theme.accent};
  }
  .md-content table { border-collapse: collapse; margin: 10px 0; width: 100%; }
  .md-content th, .md-content td {
    border: 1px solid ${theme.line};
    padding: 7px 11px; text-align: left; font-size: 14px;
  }
  .md-content th {
    background: ${theme.bgSoft};
    font-family: ${theme.mono};
    color: ${theme.accent};
  }
   .md-content hr {
    border: none;
    border-top: 1px solid #3a3a42;
    margin: 14px 0;
  }
  .md-content pre {
    background: ${theme.bg};
    border: 1px solid ${theme.lineSoft};
    border-radius: 10px;
    padding: 14px;
    overflow-x: auto;
    margin: 10px 0;
  }
.md-content pre code {
    background: none;
    padding: 0;
    color: #c8c8d0;
    font-size: 13px;
    line-height: 1.5;
  }
`;

export default function Bubble({ role, content }) {
  const isUser = role === "user";

  return (
    <div
      style={{ ...styles.row, ...(isUser ? styles.userRow : styles.botRow) }}
    >
      <div
        style={{
          ...styles.bubble,
          ...(isUser ? styles.userBubble : styles.botBubble),
        }}
      >
        {isUser ? (
          content
        ) : (
          <>
            <style>{mdStyles}</style>
            <div
              className="md-content"
              dangerouslySetInnerHTML={{ __html: marked.parse(content || "") }}
            />
          </>
        )}
      </div>
    </div>
  );
}
