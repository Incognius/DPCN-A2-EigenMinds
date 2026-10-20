import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { Scope } from "./types";

export type Page =
  | "overview" | "institutes" | "faculty" | "journals" | "areas"
  | "citation" | "collaboration" | "connectivity" | "methods";

interface Store {
  page: Page; setPage: (p: Page) => void;
  scope: Scope; setScope: (s: Scope) => void;
  facultyKey: string | null; openFaculty: (k: string | null) => void;
}

const Ctx = createContext<Store | null>(null);
const PAGES: Page[] = ["overview", "institutes", "faculty", "journals", "areas", "citation", "collaboration", "connectivity", "methods"];

function readHash(): { page: Page; scope: Scope } {
  const [p, s] = window.location.hash.replace(/^#\/?/, "").split("/");
  return {
    page: (PAGES.includes(p as Page) ? p : "overview") as Page,
    scope: (["ALL", "IISERB", "IISERM", "IISERTVM"].includes(s) ? s : "ALL") as Scope,
  };
}

/** Page + institute scope live in the URL hash, so every view is linkable. */
export function StoreProvider({ children }: { children: ReactNode }) {
  const init = readHash();
  const [page, setPageState] = useState<Page>(init.page);
  const [scope, setScopeState] = useState<Scope>(init.scope);
  const [facultyKey, openFaculty] = useState<string | null>(null);

  useEffect(() => {
    const on = () => { const h = readHash(); setPageState(h.page); setScopeState(h.scope); };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  const write = (p: Page, s: Scope) => { window.location.hash = `/${p}/${s}`; };
  const setPage = useCallback((p: Page) => { setPageState(p); write(p, scope); window.scrollTo({ top: 0 }); }, [scope]);
  const setScope = useCallback((s: Scope) => { setScopeState(s); write(page, s); }, [page]);

  return <Ctx.Provider value={{ page, setPage, scope, setScope, facultyKey, openFaculty }}>{children}</Ctx.Provider>;
}

export function useStore() {
  const s = useContext(Ctx);
  if (!s) throw new Error("useStore outside provider");
  return s;
}
