import { theme } from "../theme";

const TABS = [
  { id: "chat",     label: "Chat Bot"      },
  { id: "artifacts",label: "Artifacts"     },
  { id: "agents",   label: "Agents"        },
  { id: "career",   label: "Career"        },
  { id: "news",     label: "News / Social" },
];

const styles = {
  tabBar: {
    display: "flex",
    gap: "4px",
    padding: "5px",
    margin: "0 auto 28px",
    width: "fit-content",
    borderRadius: "14px",
    background: "rgba(255, 255, 255, 0.04)",
    backdropFilter: "blur(12px)",
    WebkitBackdropFilter: "blur(12px)",
    border: `1px solid ${theme.line}`,
    marginTop: "30px",
  },
  tab: {
    fontFamily: theme.sora,
    fontWeight: 600,
    fontSize: "13px",
    padding: "9px 22px",
    borderRadius: "10px",
    border: "none",
    background: "transparent",
    color: theme.textDim,
    cursor: "pointer",
    transition: "background 0.2s, color 0.2s",
  },
  tabActive: {
    background: theme.accentDeep,
    color: theme.lineSoft,
    boxShadow: "0 0 0 1.5px rgba(255,200,61,0.55), 0 2px 10px rgba(255,200,61,0.18)",
  },
};

export default function TabBar({ activeTab, onTabChange }) {
  return (
    <div style={styles.tabBar}>
      {TABS.map((tab) => (
        <button
          key={tab.id}
          style={{
            ...styles.tab,
            ...(activeTab === tab.id ? styles.tabActive : {}),
          }}
          onClick={() => onTabChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
