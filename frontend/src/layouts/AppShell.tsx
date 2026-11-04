import type { ReactNode } from "react";
import { ConnectionStatus } from "../components/ConnectionStatus";

const navigation = [
  { label: "Übersicht", icon: "⌂", active: true },
  { label: "Verwaltungsobjekte", icon: "▦", active: false },
  { label: "Rechnungen", icon: "▤", active: false },
  { label: "Kontobewegungen", icon: "↔", active: false },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#f5f7fb] text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-10 hidden w-64 flex-col border-r border-slate-200 bg-white lg:flex">
        <div className="flex h-[76px] items-center gap-3 border-b border-slate-100 px-6">
          <div className="grid size-9 place-items-center rounded-xl bg-indigo-600 text-sm font-bold text-white">v</div>
          <div>
            <div className="text-[17px] font-semibold tracking-tight">verwIQ</div>
            <div className="text-[11px] text-slate-400">Immobilienverwaltung</div>
          </div>
        </div>

        <nav aria-label="Hauptnavigation" className="flex-1 space-y-1 px-3 py-6">
          <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">Arbeitsbereich</p>
          {navigation.map((item) => (
            <div
              key={item.label}
              aria-current={item.active ? "page" : undefined}
              aria-disabled={!item.active}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm ${
                item.active
                  ? "bg-indigo-50 font-semibold text-indigo-700"
                  : "cursor-default text-slate-400"
              }`}
              title={item.active ? undefined : "Wird in einem späteren Schritt angebunden"}
            >
              <span aria-hidden="true" className="grid size-5 place-items-center text-base">{item.icon}</span>
              <span>{item.label}</span>
              {!item.active && <span className="ml-auto text-[10px]">Demnächst</span>}
            </div>
          ))}
        </nav>

        <div className="border-t border-slate-100 p-4">
          <div className="rounded-xl bg-slate-50 p-3">
            <div className="text-xs font-semibold text-slate-700">Einfach in der Bedienung.</div>
            <div className="mt-1 text-[11px] text-slate-500">Intelligent im Hintergrund.</div>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-[76px] items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur sm:px-8">
          <div className="flex items-center gap-3 lg:hidden">
            <div className="grid size-9 place-items-center rounded-xl bg-indigo-600 text-sm font-bold text-white">v</div>
            <span className="font-semibold">verwIQ</span>
          </div>
          <div className="hidden text-sm text-slate-500 lg:block">Arbeitsbereich <span className="px-2 text-slate-300">/</span><span className="font-medium text-slate-800">Übersicht</span></div>
          <div className="ml-auto flex items-center gap-3">
            <ConnectionStatus />
            <div aria-label="Benutzerkonto noch nicht verbunden" className="grid size-9 place-items-center rounded-full bg-slate-100 text-xs font-semibold text-slate-500">—</div>
          </div>
        </header>
        <main className="mx-auto max-w-[1440px] px-5 py-8 sm:px-8 sm:py-10">{children}</main>
      </div>
    </div>
  );
}
