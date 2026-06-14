import { theme } from "../theme";

const styles = {
  center: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    paddingTop: "6vh",
  },
  eyebrow: {
    fontFamily: theme.mono,
    fontSize: "10px",
    letterSpacing: "4px",
    color: theme.textDim,
    textTransform: "uppercase",
    marginBottom: "10px",
  },
  orbWrap: {
    position: "relative",
    width: "min(340px, 60vw)",
    height: "min(340px, 60vw)",
    display: "grid",
    placeItems: "center",
    margin: "2px 0 4px",
  },
  ring: {
    position: "absolute",
    borderRadius: "50%",
    border: "1px solid rgba(230,60,30,.18)",
  },
  core: {
    position: "relative",
    width: "40%",
    height: "40%",
    borderRadius: "50%",
    display: "grid",
    placeItems: "center",
    background:
      "radial-gradient(circle at 50% 38%, rgba(255,200,61,.30), rgba(230,60,30,.16) 45%, rgba(10,6,7,.85) 75%)",
    boxShadow:
      "0 0 60px rgba(230,60,30,.4), inset 0 0 40px rgba(255,200,61,.18)",
    animation: "breathe 5s ease-in-out infinite",
  },
  // Title — ABM purane colors mein
  title: {
    fontFamily: theme.sora,
    fontWeight: 800,
    fontSize: "clamp(30px,4.6vw,52px)",
    letterSpacing: "2px",
    textAlign: "center",
    lineHeight: 1,
    marginTop: "-2px",
    display: "flex",
    gap: "0.18em",
    userSelect: "none",
  },
  tA: { color: theme.primary }, // A — red
  tB: { color: theme.accent }, // B — gold
  tM: { color: theme.text }, // M — white
  tAiNexus: { color: theme.accent }, // AI NEXUS — gold
  // Slogan — purana
  tagline: {
    fontFamily: theme.mono,
    fontSize: "12px",
    letterSpacing: "0.18em",
    textTransform: "uppercase",
    color: theme.textFaint,
    marginTop: "12px",
    marginBottom: "20px",
    textAlign: "center",
  },
  taglineBold: {
    color: theme.primary,
    fontWeight: 500,
  },
};

export default function NexusCenter() {
  return (
    <div style={styles.center}>
      <div style={styles.eyebrow}>Intelligent Oculus</div>

      {/* Orb */}
      <div style={styles.orbWrap}>
        {/* Ring 1 — outermost, gold */}
        <div
          style={{
            ...styles.ring,
            inset: 0,
            borderColor: "rgba(255,200,61,.14)",
            animation: "spin 38s linear infinite",
          }}
        />
        {/* Ring 2 — dashed red, reverse */}
        <div
          style={{
            ...styles.ring,
            inset: "11%",
            borderColor: "rgba(230,60,30,.22)",
            borderStyle: "dashed",
            animation: "spin 26s linear infinite reverse",
          }}
        />
        {/* Ring 3 — inner gold */}
        <div
          style={{
            ...styles.ring,
            inset: "24%",
            borderColor: "rgba(255,200,61,.18)",
            animation: "spin 18s linear infinite",
          }}
        />

        {/* Core with hexagon */}
        <div style={styles.core}>
          <svg
            width="86"
            height="86"
            viewBox="0 0 58 58"
            xmlns="http://www.w3.org/2000/svg"
            style={{ filter: "drop-shadow(0 0 14px rgba(255,200,61,.5))" }}
          >
            <polygon
              points="29,7 50,18.5 50,39.5 29,51 8,39.5 8,18.5"
              fill="none"
              stroke={theme.accent}
              strokeWidth="2.2"
            />
            <text
              x="29"
              y="37"
              fontFamily="Sora"
              fontWeight="800"
              fontSize="20"
              fill={theme.accent}
              textAnchor="middle"
            >
              AI
            </text>
          </svg>
        </div>
      </div>
    </div>
  );
}
