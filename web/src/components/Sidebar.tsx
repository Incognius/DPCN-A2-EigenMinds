import { BookOpenText, Building2, FlaskConical, GitFork, LayoutDashboard, Library, Network, Share2, Users, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useStore, type Page } from "../lib/store";

const NAV: { page: Page; label: string; icon: LucideIcon }[] = [
  { page: "overview", label: "Overview", icon: LayoutDashboard },
  { page: "institutes", label: "Institutes", icon: Building2 },
  { page: "faculty", label: "Faculty", icon: Users },
  { page: "journals", label: "Journals & Impact", icon: Library },
  { page: "areas", label: "Research Areas", icon: FlaskConical },
  { page: "citation", label: "Citation Network", icon: Share2 },
  { page: "collaboration", label: "Collaboration", icon: Network },
  { page: "connectivity", label: "Indian Connectivity", icon: GitFork },
];

export function Logo() {
  return (
    <div className="flex items-center gap-2.5 px-2">
      <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden>
        <path d="M7 6v20M25 6v20M7 16h18" stroke="#f4eef3" strokeWidth="4" strokeLinecap="round" />
      </svg>
      <span className="text-[19px] font-bold tracking-tight">IISER Atlas</span>
    </div>
  );
}

export default function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { page, setPage } = useStore();
  const item = (p: Page, label: string, Icon: (typeof NAV)[number]["icon"]) => {
    const active = page === p;
    return (
      <button key={p} onClick={() => { setPage(p); onClose(); }}
        className={`group flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left text-[15px] font-medium transition
          ${active ? "text-white" : "text-ink-2 hover:bg-white/[0.03] hover:text-white"}`}
        style={active ? {
          background: "linear-gradient(100deg, rgba(199,143,184,.55) 0%, rgba(125,69,112,.38) 55%, rgba(60,30,52,.2) 100%)",
          boxShadow: "inset 0 1px 0 rgba(255,255,255,.12), 0 10px 30px -14px rgba(199,143,184,.7)",
        } : undefined}>
        <span className={`grid h-7 w-7 place-items-center rounded-full ${active ? "bg-white/15" : ""}`}>
          <Icon size={18} strokeWidth={1.8} />
        </span>
        {label}
      </button>
    );
  };
  return (
    <>
      <div className={`fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition lg:hidden ${open ? "opacity-100" : "pointer-events-none opacity-0"}`} onClick={onClose} />
      <aside className={`fixed inset-y-3 left-3 z-50 flex w-[262px] flex-col rounded-[26px] border border-white/[0.06] p-4 transition-transform
          lg:sticky lg:top-5 lg:z-0 lg:h-[calc(100vh-40px)] lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-[120%]"}`}
        style={{ background: "linear-gradient(180deg,#0f0b0e 0%,#0b080a 100%)" }}>
        <div className="flex items-center justify-between pb-6 pt-2">
          <Logo />
          <button className="text-ink-muted lg:hidden" onClick={onClose} aria-label="Close menu"><X size={20} /></button>
        </div>
        <nav className="flex flex-col gap-1">{NAV.map((n) => item(n.page, n.label, n.icon))}</nav>
        <div className="mt-auto flex flex-col gap-1 pt-6">
          {item("methods", "Methods & Data", BookOpenText)}
          <div className="mx-2 mt-3 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-3 text-[12px] leading-relaxed text-ink-muted">
            <div className="font-semibold text-ink-2">Team EigenMinds · Group 20</div>
            Ponnambalam V, Manit Roy, Shashwat Mukadam
          </div>
        </div>
      </aside>
    </>
  );
}
