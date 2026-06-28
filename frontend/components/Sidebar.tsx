"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/lib/nav";
import { Icon } from "./Icon";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-white/5 bg-navy-900/80 backdrop-blur lg:flex">
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-navy-900">
          <span className="text-lg font-bold">E</span>
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">Digital Twin</p>
          <p className="truncate text-xs text-slate-400">Electrolux UAE Ops</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-2">
        {NAV_ITEMS.map((item) => {
          const active =
            pathname === item.href ||
            (pathname === "/" && item.href === "/overview");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-link ${active ? "nav-link-active" : ""}`}
            >
              <Icon path={item.icon} className="h-5 w-5 shrink-0" />
              <span className="flex flex-col">
                <span>{item.label}</span>
                <span className="text-[11px] font-normal text-slate-500">
                  {item.description}
                </span>
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="px-5 py-4 text-[11px] leading-relaxed text-slate-500">
        <p className="font-semibold text-slate-400">2026 Hormuz Resilience</p>
        <p>Sensitive-material supply twin</p>
      </div>
    </aside>
  );
}
