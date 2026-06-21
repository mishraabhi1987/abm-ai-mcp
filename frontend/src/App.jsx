import { useState, useRef, useEffect } from "react";
import Bubble from "./components/Bubble";
import ChatBox from "./components/ChatBox";
import ChartWidget from "./components/ChartWidget";
import { sendMessage, newChat } from "./api/chat";
import { theme } from "./theme";
import Backdrop from "./components/Backdrop";
import Header from "./components/Header";
import TabBar from "./components/TabBar";
import Artifacts from "./components/Artifacts";
import Agents from "./components/Agents";

// Must match the exact strings TabBar passes for these tabs.
const ARTIFACTS_TAB = "Artifacts";
const AGENTS_TAB = "Agents";

const styles = {
  // Full-height flex column. The PAGE never scrolls — only the middle does.
  shell: {
    height: "100vh",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    background: `
      radial-gradient(900px 480px at 50% -8%, rgba(199,5,5,0.10), transparent 62%),
      radial-gradient(700px 420px at 50% 108%, rgba(255,200,61,0.06), transparent 60%),
      ${theme.bg}
    `,
    color: theme.text,
    fontFamily: theme.inter,
  },
  top: {
    flexShrink: 0, // Header + TabBar — fixed, never scrolls
    position: "relative",
    zIndex: 1, // sit above the Backdrop (zIndex 0)
  },
  pane: {
    flex: 1,
    minHeight: 0, // CRITICAL: lets the scroll child shrink instead of overflowing
    display: "flex",
    flexDirection: "column",
    position: "relative",
    zIndex: 1,
  },
  scrollArea: {
    flex: 1,
    minHeight: 0,
    overflowY: "auto", // <-- the ONLY scrolling region
    padding: "0 20px",
  },
  feed: {
    maxWidth: 700,
    margin: "0 auto",
    paddingTop: 20,
    paddingBottom: 20,
  },
  bottom: {
    flexShrink: 0, // Chatbox — fixed at the bottom
    padding: "12px 20px 16px",
    borderTop: "1px solid rgba(255,255,255,0.08)",
    background: theme.bg,
  },
};

export default function App() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("Chat");

  const endRef = useRef(null);
  useEffect(() => {
    // scrolls ONLY the middle area (its nearest scrollable ancestor), not the page
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const handleSend = async (text, attachments = []) => {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    try {
      const { answer, chartData } = await sendMessage(text, "auto", {
        attachments: attachments.length ? attachments : null,
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: answer, chartData },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = async () => {
    await newChat();
    setMessages([]);
  };

  const isArtifacts = activeTab === ARTIFACTS_TAB;
  const isAgents = activeTab === AGENTS_TAB;

  return (
    <div style={styles.shell}>
      <Backdrop />

      {/* TOP — fixed (never scrolls) */}
      <div style={styles.top}>
        <Header />
        <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
      </div>

      {/* BELOW TOP — fills the remaining height */}
      {isArtifacts ? (
        <Artifacts />
      ) : isAgents ? (
        <Agents />
      ) : (
        <div style={styles.pane}>
          {/* MIDDLE — only this scrolls */}
          <div style={styles.scrollArea}>
            <div style={styles.feed}>
              {messages.map((msg, i) => (
                <div key={i}>
                  <Bubble role={msg.role} content={msg.content} />
                  {msg.chartData && <ChartWidget chartData={msg.chartData} />}
                </div>
              ))}
              <div ref={endRef} />
            </div>
          </div>

          {/* BOTTOM — fixed chatbox */}
          <div style={styles.bottom}>
            <ChatBox
              onSend={handleSend}
              onNewChat={handleNewChat}
              loading={loading}
            />
          </div>
        </div>
      )}
    </div>
  );
}
