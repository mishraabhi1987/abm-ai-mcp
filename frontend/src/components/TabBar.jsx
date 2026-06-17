import { theme } from "../theme";

const TABS = ["Chat Bot", "Artifacts", "Agents", "Career", "News / Social"];

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
  },
};

export default function TabBar({ activeTab, onTabChange }) {
  return (
    <div style={styles.tabBar}>
      {TABS.map((tab) => (
        <button
          key={tab}
          style={{
            ...styles.tab,
            ...(activeTab === tab ? styles.tabActive : {}),
          }}
          onClick={() => onTabChange(tab)}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
