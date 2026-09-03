import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/institutes", label: "Institutes & Projects" },
  { to: "/attendance", label: "Attendance" },
  { to: "/templates", label: "Inspection Templates" },
  { to: "/manage", label: "Manage" },
];

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 bg-[var(--ink)] text-white flex flex-col">
        <div className="px-5 py-5 border-b border-white/10">
          <div className="mono text-[11px] tracking-wide text-white/60">PS 26095</div>
          <div className="text-sm font-semibold leading-snug mt-1">
            Smart Monitoring<br />Platform
          </div>
        </div>

        <nav className="flex-1 px-2 py-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block px-3 py-2 text-sm rounded-sm transition-colors ${
                  isActive ? "bg-white/10 text-white" : "text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-4 border-t border-white/10 text-xs text-white/60">
          <div className="text-white/90 font-medium">
            {user?.first_name || user?.username}
          </div>
          <div>{user?.role_display}</div>
          <button
            onClick={logout}
            className="mt-3 text-white/70 hover:text-white underline underline-offset-2"
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
