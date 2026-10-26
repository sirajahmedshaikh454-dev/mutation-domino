import { NavLink, Route, Routes } from 'react-router-dom';
import { Home } from '../pages/Home';
import { Protein } from '../pages/Protein';
import { Analysis } from '../pages/Analysis';
import { History } from '../pages/History';
import { useTheme } from '../components/ThemeProvider';
import { Monitor, Moon, Sun } from 'lucide-react';

export default function App() {
  const { mode, setMode } = useTheme();
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/85 backdrop-blur dark:border-slate-800/80 dark:bg-slate-950/85">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          <NavLink to="/" className="flex items-center gap-2 font-semibold text-ink-900 no-underline dark:text-slate-100">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-brand-700 text-xs font-bold text-white">
              MD
            </span>
            Mutation Domino
          </NavLink>
          <div className="flex items-center gap-2">
            <nav className="flex items-center gap-1">
              <NavLink to="/" className="tab dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white" end>
                Home
              </NavLink>
              <NavLink to="/history" className="tab dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white">
                History
              </NavLink>
            </nav>
            <div className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white p-1 dark:border-slate-700 dark:bg-slate-900" role="group" aria-label="Theme">
              <button
                type="button"
                aria-label="Light theme"
                aria-pressed={mode === 'light'}
                className={`rounded-lg p-1.5 transition ${mode === 'light' ? 'bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-white' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'}`}
                onClick={() => setMode('light')}
              >
                <Sun className="h-4 w-4" aria-hidden="true" />
              </button>
              <button
                type="button"
                aria-label="Dark theme"
                aria-pressed={mode === 'dark'}
                className={`rounded-lg p-1.5 transition ${mode === 'dark' ? 'bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-white' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'}`}
                onClick={() => setMode('dark')}
              >
                <Moon className="h-4 w-4" aria-hidden="true" />
              </button>
              <button
                type="button"
                aria-label="System theme"
                aria-pressed={mode === 'system'}
                className={`rounded-lg p-1.5 transition ${mode === 'system' ? 'bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-white' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'}`}
                onClick={() => setMode('system')}
              >
                <Monitor className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/protein/:accession" element={<Protein />} />
          <Route path="/analyses/:id" element={<Analysis />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </main>
      <footer className="mx-auto max-w-7xl px-4 py-6 text-xs text-slate-500 dark:text-slate-400 sm:px-6">
        Research and education only. Not for clinical decision-making. No mutant 3D structure is
        generated.
      </footer>
    </div>
  );
}