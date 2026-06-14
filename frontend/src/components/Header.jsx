import { theme } from "../theme";

const styles = {
  header: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center", // center align
    padding: "24px 0 0 0", // left padding hatao
    width: "100%",
  },
  logo: {
    fontFamily: theme.sora,
    fontWeight: 800,
    fontSize: "36px",
    letterSpacing: "1px",
    lineHeight: 1,
    display: "flex",
    gap: "0.15em",
    userSelect: "none",
  },
  a: { color: theme.primary },
  b: { color: theme.accent },
  m: { color: theme.text },
  aiNexus: { color: theme.textDim },
  tagline: {
    fontFamily: theme.mono,
    fontSize: "13px",
    letterSpacing: "0.18em",
    textTransform: "uppercase",
    color: theme.textFaint,
    marginTop: "6px",
  },
  taglineBold: {
    color: theme.primary,
    fontWeight: 500,
  },
};

export default function Header() {
  return (
    <div style={styles.header}>
      <div style={styles.logo}>
        <span style={styles.a}>A</span>
        <span style={styles.b}>B</span>
        <span style={styles.m}>M</span>
        <span style={styles.aiNexus}>&nbsp;AI</span>
      </div>
      <div style={styles.tagline}>
        Accelerating with{" "}
        <b style={styles.taglineBold}>Artificial Intelligence</b>
      </div>
    </div>
  );
}
