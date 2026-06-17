import { useEffect, useRef } from "react";
import { theme } from "../theme";

// Merged background layer: animated neural canvas + centered Oculus orb.
// Both are fixed, behind content (zIndex 0), and click-through (pointerEvents none).
export default function Backdrop() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    let W,
      H,
      nodes = [],
      pulses = [],
      pulseTimer = 0;
    let animationId;

    const COLORS = ["#e63c1e", "#cc4e2a", "#d4730a", "#e8a020", "#f0c040"];

    function hexToRgb(hex) {
      return {
        r: parseInt(hex.slice(1, 3), 16),
        g: parseInt(hex.slice(3, 5), 16),
        b: parseInt(hex.slice(5, 7), 16),
      };
    }

    function init() {
      nodes = [];
      pulses = [];
      const count = 48;
      for (let i = 0; i < count; i++) {
        const angle = Math.random() * Math.PI * 2;
        const spd = 0.12 + Math.random() * 0.18;
        nodes.push({
          x: Math.random() * W,
          y: Math.random() * H,
          vx: Math.cos(angle) * spd,
          vy: Math.sin(angle) * spd,
          r: 1.8 + Math.random() * 2,
          color: COLORS[Math.floor(Math.random() * COLORS.length)],
          phase: Math.random() * Math.PI * 2,
          phaseSpeed: 0.012 + Math.random() * 0.018,
        });
      }
    }

    function resize() {
      W = canvas.width = window.innerWidth;
      H = canvas.height = window.innerHeight;
      init();
    }

    function spawnPulse(i, j) {
      pulses.push({
        from: i,
        to: j,
        t: 0,
        speed: 0.008 + Math.random() * 0.012,
        color: nodes[i].color,
      });
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      const MAX_DIST = 130;

      // connections
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < MAX_DIST) {
            const alpha = (1 - dist / MAX_DIST) * 0.15;
            const { r, g, b } = hexToRgb(nodes[i].color);
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(${r},${g},${b},${alpha})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }
      }

      // pulses
      pulses = pulses.filter((p) => p.t <= 1);
      for (const p of pulses) {
        const A = nodes[p.from],
          B = nodes[p.to];
        if (!A || !B) continue;
        const x = A.x + (B.x - A.x) * p.t;
        const y = A.y + (B.y - A.y) * p.t;
        const { r, g, b } = hexToRgb(p.color);
        const grd = ctx.createRadialGradient(x, y, 0, x, y, 7);
        grd.addColorStop(0, `rgba(${r},${g},${b},0.7)`);
        grd.addColorStop(0.4, `rgba(${r},${g},${b},0.25)`);
        grd.addColorStop(1, `rgba(${r},${g},${b},0)`);
        ctx.beginPath();
        ctx.arc(x, y, 7, 0, Math.PI * 2);
        ctx.fillStyle = grd;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(x, y, 2.2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${r},${g},${b},0.95)`;
        ctx.fill();
        p.t += p.speed;
      }

      // nodes with breathing glow
      for (const n of nodes) {
        n.phase += n.phaseSpeed;
        const breathe = 0.35 + 0.25 * Math.sin(n.phase);
        const { r, g, b } = hexToRgb(n.color);
        const halo = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 5);
        halo.addColorStop(
          0,
          `rgba(${r},${g},${b},${(breathe * 0.4).toFixed(2)})`,
        );
        halo.addColorStop(1, `rgba(${r},${g},${b},0)`);
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r * 5, 0, Math.PI * 2);
        ctx.fillStyle = halo;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${r},${g},${b},${breathe.toFixed(2)})`;
        ctx.fill();
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 0 || n.x > W) n.vx *= -1;
        if (n.y < 0 || n.y > H) n.vy *= -1;
      }

      // spawn pulses
      pulseTimer++;
      if (pulseTimer % 18 === 0) {
        const i = Math.floor(Math.random() * nodes.length);
        const candidates = [];
        for (let j = 0; j < nodes.length; j++) {
          if (j === i) continue;
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          if (Math.sqrt(dx * dx + dy * dy) < 130) candidates.push(j);
        }
        if (candidates.length) {
          const j = candidates[Math.floor(Math.random() * candidates.length)];
          spawnPulse(i, j);
        }
      }

      animationId = requestAnimationFrame(draw);
    }

    window.addEventListener("resize", resize);
    resize();
    draw();

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(animationId);
    };
  }, []);

  // --- Oculus styles (from NexusCenter, now used as a centered background) ---
  const styles = {
    oculusLayer: {
      position: "fixed",
      inset: 0,
      zIndex: 0,
      display: "grid",
      placeItems: "center",
      pointerEvents: "none", // click/scroll guzar jaaye, block na ho
    },
    center: {
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
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
  };

  return (
    <>
      {/* animated neural canvas */}
      <canvas
        ref={canvasRef}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "100vw",
          height: "100vh",
          zIndex: 0,
          pointerEvents: "none",
          display: "block",
        }}
      />

      {/* centered Oculus orb — sits above canvas, behind app content */}
      <div style={styles.oculusLayer}>
        <div style={styles.center}>
          <div style={styles.eyebrow}>Intelligent Oculus</div>

          <div style={styles.orbWrap}>
            <div
              style={{
                ...styles.ring,
                inset: 0,
                borderColor: "rgba(255,200,61,.14)",
                animation: "spin 38s linear infinite",
              }}
            />
            <div
              style={{
                ...styles.ring,
                inset: "11%",
                borderColor: "rgba(230,60,30,.22)",
                borderStyle: "dashed",
                animation: "spin 26s linear infinite reverse",
              }}
            />
            <div
              style={{
                ...styles.ring,
                inset: "24%",
                borderColor: "rgba(255,200,61,.18)",
                animation: "spin 18s linear infinite",
              }}
            />

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
      </div>
    </>
  );
}
