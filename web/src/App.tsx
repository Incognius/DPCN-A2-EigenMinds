import { lazy, Suspense, useEffect, useState } from "react";
import ErrorBoundary from "./components/ErrorBoundary";
import FacultyDrawer from "./components/FacultyDrawer";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import { Loading } from "./components/ui";
import { useStore } from "./lib/store";
import Overview from "./pages/Overview";

const pages = {
  institutes: lazy(() => import("./pages/Institutes")),
  faculty: lazy(() => import("./pages/FacultyPage")),
  journals: lazy(() => import("./pages/Journals")),
  areas: lazy(() => import("./pages/Areas")),
  citation: lazy(() => import("./pages/CitationNet")),
  collaboration: lazy(() => import("./pages/Collaboration")),
  connectivity: lazy(() => import("./pages/Connectivity")),
  methods: lazy(() => import("./pages/Methods")),
};

export default function App() {
  const { page } = useStore();
  const [menu, setMenu] = useState(false);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [page]);
  const Page = page === "overview" ? Overview : pages[page];
  return (
    <div className="mx-auto max-w-[1680px] p-3 sm:p-5">
      <div className="frame flex gap-5 p-3 sm:p-5">
        <Sidebar open={menu} onClose={() => setMenu(false)} />
        <main className="min-w-0 flex-1 pb-6 lg:pt-3">
          <Header onMenu={() => setMenu(true)} />
          <div className="mt-6">
            <ErrorBoundary resetKey={page}>
              <Suspense fallback={<Loading h={480} />}>
                <Page />
              </Suspense>
            </ErrorBoundary>
          </div>
          <footer className="mt-10 flex flex-wrap items-center justify-between gap-2 text-[12px] text-ink-faint">
            <span>DPCN Research Mapping Project · Group 20 · IISER Bhopal, Mohali, Thiruvananthapuram</span>
            <span>Data: OpenAlex, SCImago (sjrdata mirror), CORE 2023 · faculty rosters from institute websites</span>
          </footer>
        </main>
      </div>
      <FacultyDrawer />
    </div>
  );
}
