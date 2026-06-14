import { useState } from "react";
import Navbar from "./components/Navbar";
import Bubble from "./components/Bubble";
import ChatBox from "./components/ChatBox";
import ChartWidget from "./components/ChartWidget";
import { sendMessage, newChat } from "./api/chat";
import { theme } from "./theme";
import NeuralBg from "./components/NeuralBg";
import NexusCenter from "./components/NexusCenter";
import Header from "./components/Header";

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

  return (
    <div style={styles.app}>
      <NeuralBg />
      <Header />
      <NexusCenter /> {/* Navbar ki jagah */}
      <div style={styles.chatArea}>
        <ChatBox
          onSend={handleSend}
          onNewChat={handleNewChat}
          loading={loading}
        />
        <div style={{ marginTop: "30px" }}>
          {[...messages]
            .map((msg, i) => ({ msg, i })) // index yaad rakho
            .reverse() // ulta karo (naya upar)
            .map(({ msg, i }) => (
              <div key={i}>
                <Bubble role={msg.role} content={msg.content} />
                {msg.chartData && <ChartWidget chartData={msg.chartData} />}
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
