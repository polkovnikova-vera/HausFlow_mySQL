import { useEffect, useState } from "react";
import { loadHealth } from "../services/health";

type ConnectionState = "checking" | "connected" | "offline";

export function ConnectionStatus() {
  const [state, setState] = useState<ConnectionState>("checking");

  useEffect(() => {
    let active = true;

    loadHealth()
      .then(() => active && setState("connected"))
      .catch(() => active && setState("offline"));

    return () => {
      active = false;
    };
  }, []);

  const label = {
    checking: "Backend wird geprüft",
    connected: "Backend verbunden",
    offline: "Backend nicht erreichbar",
  }[state];

  const dotClass = {
    checking: "bg-amber-400",
    connected: "bg-emerald-500",
    offline: "bg-slate-300",
  }[state];

  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600">
      <span aria-hidden="true" className={`size-2 rounded-full ${dotClass}`} />
      <span>{label}</span>
    </div>
  );
}
