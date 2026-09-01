import { useMemo } from "react";

/**
 * Part 33 — "historical trends". A dependency-free line chart (plain SVG,
 * no recharts/chart.js — those aren't in frontend/package.json and this
 * doesn't need them) plotting an institute's RiskSnapshot.score over time.
 * Dots are colour-coded by severity so a HIGH spike is visible at a glance.
 *
 * Expects `data` = chronological (oldest -> newest) array of objects with
 * at least { computed_at, score, severity } — i.e. exactly what
 * GET /api/analytics/risk/institute/<id>/history/ returns.
 */

const SEVERITY_COLOR = {
  LOW: "#157a4a",
  MEDIUM: "#b5790a",
  HIGH: "#b23b3b",
};

const WIDTH = 640;
const HEIGHT = 160;
const PAD_X = 36;
const PAD_Y = 20;

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export default function RiskTrendChart({ data }) {
  const points = useMemo(() => {
    if (!data || data.length === 0) return [];
    const n = data.length;
    const usableWidth = WIDTH - PAD_X * 2;
    const usableHeight = HEIGHT - PAD_Y * 2;
    return data.map((snap, i) => {
      const x = n === 1 ? PAD_X + usableWidth / 2 : PAD_X + (usableWidth * i) / (n - 1);
      const y = PAD_Y + usableHeight * (1 - snap.score / 100);
      return { x, y, ...snap };
    });
  }, [data]);

  if (points.length === 0) return null;

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");

  return (
    <div>
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" style={{ minWidth: 480 }}>
          {/* Reference gridlines at 0 / 50 / 100, matching the LOW/MEDIUM/HIGH bands */}
          {[0, 30, 60, 100].map((mark) => {
            const y = PAD_Y + (HEIGHT - PAD_Y * 2) * (1 - mark / 100);
            return (
              <g key={mark}>
                <line
                  x1={PAD_X}
                  y1={y}
                  x2={WIDTH - PAD_X}
                  y2={y}
                  stroke="#dde2e8"
                  strokeWidth="1"
                  strokeDasharray={mark === 0 || mark === 100 ? "0" : "3,3"}
                />
                <text x={2} y={y + 3} fontSize="9" fill="#33506b">
                  {mark}
                </text>
              </g>
            );
          })}

          <path d={linePath} fill="none" stroke="#1d6fa5" strokeWidth="2" />

          {points.map((p, i) => (
            <g key={i}>
              <circle
                cx={p.x}
                cy={p.y}
                r="4.5"
                fill={SEVERITY_COLOR[p.severity] || "#1d6fa5"}
                stroke="#fff"
                strokeWidth="1.5"
              />
              <title>{`${formatDate(p.computed_at)} — ${p.score}/100 (${p.severity})`}</title>
            </g>
          ))}
        </svg>
      </div>

      <div className="flex items-center justify-between text-[10px] text-[var(--ink-soft)] px-1 mt-1">
        <span>{formatDate(points[0].computed_at)}</span>
        <div className="flex items-center gap-3">
          {Object.entries(SEVERITY_COLOR).map(([label, color]) => (
            <span key={label} className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: color }} />
              {label}
            </span>
          ))}
        </div>
        <span>{formatDate(points[points.length - 1].computed_at)}</span>
      </div>
    </div>
  );
}
