import { useState, useRef, useEffect } from "react";
import Navbar from "./components/Navbar";
import Bubble from "./components/Bubble";
import ChatBox from "./components/ChatBox";
import ChartWidget from "./components/ChartWidget";
import { sendMessage, newChat } from "./api/chat";
import { theme } from "./theme";
import NeuralBg from "./components/NeuralBg";
import NexusCenter from "./components/NexusCenter";
import Header from "./components/Header";
import TabBar from "./components/TabBar";
import Artifacts from "./components/Artifacts";

// NOTE: must match the exact string TabBar passes for the Artifacts tab.
// If your TabBar sends something else (e.g. "Artifacts / Code"), change ONLY this line.
const ARTIFACTS_TAB = "Artifacts";

const styles = {
  app: {
    minHeight: "100vh",
    background: `
      radial-gradient(900px 480px at 50% -8%, rgba(199,5,5,0.10), transparent 62%),
      radial-gradient(700px 420px at 50% 108%, rgba(255,200,61,0.06), transparent 60%),
      ${theme.bg}
    `,
    color: theme.text,
    fontFamily: theme.inter,
    paddingBottom: "80px",
    position: "relative",
    zIndex: 1,
  },
  chatArea: {
    maxWidth: "700px",
    margin: "0 auto",
    padding: "0 20px",
  },
};

export default function App() {
  // saari chat history — array of messages
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("Chat");

  const endRef = useRef(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  // user message bheja
  const handleSend = async (text) => {
    // 1. user ka message turant dikhao
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      // 2. backend se jawab lao
      const { answer, chartData } = await sendMessage(text);

      // 3. assistant ka jawab add karo
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: answer, chartData: chartData },
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

  // New Chat button
  const handleNewChat = async () => {
    await newChat();
    setMessages([]);
  };

  const isArtifacts = activeTab === ARTIFACTS_TAB;

  return (
    <div style={styles.app}>
      <NeuralBg />
      <Header />
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
      <NexusCenter /> {/* Navbar ki jagah */}
      {/* Sirf neeche ka region badalta hai — top (Header/TabBar/NexusCenter) waisa hi */}
      {isArtifacts ? (
        <Artifacts />
      ) : (
        <>
          <div style={styles.chatArea}>
            <div style={{ paddingBottom: 170 }}>
              {messages.map((msg, i) => (
                <div key={i}>
                  <Bubble role={msg.role} content={msg.content} />
                  {msg.chartData && <ChartWidget chartData={msg.chartData} />}
                </div>
              ))}
              <div ref={endRef} />
            </div>
          </div>

          <div
            style={{
              position: "fixed",
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 10,
              padding: "12px 20px",
              background: theme.bg,
              borderTop: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <div style={{ maxWidth: 700, margin: "0 auto" }}>
              <ChatBox
                onSend={handleSend}
                onNewChat={handleNewChat}
                loading={loading}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
