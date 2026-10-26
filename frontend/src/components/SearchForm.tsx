import { useState, type FormEvent } from 'react';
import { ArrowRight, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface SearchFormProps {
  initialAccession?: string;
  autoFocus?: boolean;
  compact?: boolean;
}

const ACCESSION_PATTERN = /^[A-Z0-9]{6,10}$/;

export function SearchForm({ initialAccession = '', autoFocus = false, compact = false }: SearchFormProps) {
  const navigate = useNavigate();
  const [accession, setAccession] = useState(initialAccession);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = accession.trim().toUpperCase();
    if (!normalized) {
      setError('Enter a UniProt accession, for example P69905.');
      return;
    }
    if (!ACCESSION_PATTERN.test(normalized)) {
      setError('A UniProt accession is 6–10 letters or digits, for example P69905.');
      return;
    }
    setError(null);
    navigate(`/protein/${normalized}`);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full" noValidate>
      <label htmlFor="accession" className={compact ? 'sr-only' : 'label mb-2 block'}>
        UniProt accession
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="relative min-w-0 flex-1">
          <Search
            className="pointer-events-none absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-slate-400"
            aria-hidden="true"
          />
          <input
            id="accession"
            name="accession"
            value={accession}
            onChange={(event) => {
              setAccession(event.target.value);
              if (error) setError(null);
            }}
            autoFocus={autoFocus}
            autoComplete="off"
            spellCheck={false}
            placeholder="P69905"
            aria-invalid={Boolean(error)}
            aria-describedby={error ? 'accession-error' : 'accession-help'}
            className="input pl-10 font-mono tracking-wide uppercase"
          />
        </div>
        <button type="submit" className="btn-primary shrink-0">
          Load protein
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      {error ? (
        <p id="accession-error" className="mt-2 text-xs font-medium text-rose-700" role="alert">
          {error}
        </p>
      ) : (
        <div id="accession-help" className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
          <span>Canonical UniProt accession.</span>
          <button
            type="button"
            className="font-semibold text-brand-700 hover:underline"
            onClick={() => {
              setAccession('P69905');
              setError(null);
            }}
          >
            Use example P69905
          </button>
        </div>
      )}
    </form>
  );
}
