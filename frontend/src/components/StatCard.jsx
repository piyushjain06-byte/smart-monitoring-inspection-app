export default function StatCard({ label, value, accent = "var(--ink)" }) {
  return (
    <div className="bg-white border border-[var(--line)] px-4 py-3" style={{ borderLeft: `3px solid ${accent}` }}>
      <div className="text-2xl font-semibold text-[var(--ink)]">{value}</div>
      <div className="text-xs text-[var(--ink-soft)] mt-0.5">{label}</div>
    </div>
  );
}
