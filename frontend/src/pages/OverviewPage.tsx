const sections = [
  {
    number: "01",
    title: "Immobilien",
    description: "Verwaltungsobjekte, Gebäude und Einheiten an einem Ort organisieren.",
    icon: "⌂",
  },
  {
    number: "02",
    title: "Rechnungen",
    description: "Belege erfassen, Vorschläge prüfen und Entscheidungen nachvollziehbar bestätigen.",
    icon: "▤",
  },
  {
    number: "03",
    title: "Abrechnung",
    description: "Kostenverteilungen transparent vorbereiten und bestätigte Ergebnisse festhalten.",
    icon: "◷",
  },
];

export function OverviewPage() {
  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-10 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Willkommen bei verwIQ</p>
          <h1 className="max-w-2xl text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">Verwaltung, die den Überblick leichter macht.</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500 sm:text-base">Ein ruhiger, klarer Arbeitsbereich für die täglichen Aufgaben Ihrer Hausverwaltung.</p>
        </div>
        <span className="w-fit rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700">Web-App · Vorschau</span>
      </div>

      <section aria-labelledby="start-title" className="relative overflow-hidden rounded-2xl bg-slate-950 p-6 text-white shadow-sm sm:p-9">
        <div aria-hidden="true" className="absolute -right-12 -top-24 size-72 rounded-full border border-white/10" />
        <div aria-hidden="true" className="absolute -right-2 -top-14 size-52 rounded-full border border-white/10" />
        <div className="relative max-w-2xl">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1.5 text-[11px] font-medium text-slate-300">
            <span className="size-1.5 rounded-full bg-emerald-400" />
            Neue Plattform bereit
          </div>
          <h2 id="start-title" className="text-2xl font-semibold tracking-tight sm:text-[28px]">Ein neuer Arbeitsbereich für Ihre Immobilien.</h2>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-300">Die technische Basis ist vorbereitet. Sobald die nächsten Fachmodule angeschlossen sind, erscheinen hier Ihre Objekte und Aufgaben.</p>
          <div className="mt-7 flex flex-wrap gap-2 text-xs text-slate-300">
            <span className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">Keine Echtdaten geladen</span>
            <span className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">Datenbank noch nicht verbunden</span>
          </div>
        </div>
      </section>

      <section aria-labelledby="modules-title" className="mt-10">
        <div className="mb-4 flex items-end justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400">PLATTFORM</p>
            <h2 id="modules-title" className="mt-1 text-lg font-semibold tracking-tight">Wichtige Bereiche</h2>
          </div>
          <span className="text-xs text-slate-400">Schritt für Schritt verfügbar</span>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {sections.map((section) => (
            <article key={section.number} className="rounded-xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.03)]">
              <div className="flex items-center justify-between">
                <span className="grid size-10 place-items-center rounded-xl bg-indigo-50 text-lg text-indigo-700">{section.icon}</span>
                <span className="font-mono text-xs text-slate-300">{section.number}</span>
              </div>
              <h3 className="mt-5 text-sm font-semibold text-slate-800">{section.title}</h3>
              <p className="mt-2 min-h-12 text-xs leading-5 text-slate-500">{section.description}</p>
              <div className="mt-5 border-t border-slate-100 pt-3 text-[11px] font-medium text-slate-400">Noch nicht angebunden</div>
            </article>
          ))}
        </div>
      </section>

      <footer className="mt-10 border-t border-slate-200 pt-5 text-xs text-slate-400">verwIQ · Version 0.1.0</footer>
    </div>
  );
}
