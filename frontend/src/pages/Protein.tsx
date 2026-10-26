import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { getProtein, createAnalysis } from '../lib/api';
import type { AnalysisParameters } from '../lib/types';
import { ErrorNotice } from '../components/ErrorNotice';
import { SequenceViewer } from '../components/SequenceViewer';
import { Disclaimer } from '../components/Disclaimer';

const AA = 'ACDEFGHIKLMNPQRSTVWY'.split('');

export function Protein() {
  const { accession = '' } = useParams();
  const navigate = useNavigate();
  const query = useQuery({
    queryKey: ['protein', accession],
    queryFn: ({ signal }) => getProtein(accession, signal),
    enabled: Boolean(accession),
  });

  const protein = query.data;
  const [position, setPosition] = useState<number | null>(null);
  const [wt, setWt] = useState('');
  const [mutant, setMutant] = useState('V');
  const [caRadius, setCaRadius] = useState(8);
  const [heavyRadius, setHeavyRadius] = useState(5);
  const [clientError, setClientError] = useState<string | null>(null);

  const selectedWt = useMemo(() => {
    if (!protein || position === null) return '';
    return protein.sequence[position - 1] ?? '';
  }, [protein, position]);

  const mutation = useMutation({
    mutationFn: (input: { accession: string; variant: string; parameters: AnalysisParameters }) =>
      createAnalysis(input),
    onSuccess: (result) => navigate(`/analyses/${result.id}`),
  });

  const handleSelect = (pos: number, letter: string) => {
    setPosition(pos);
    setWt(letter);
    setClientError(null);
  };

  const handleAnalyze = () => {
    setClientError(null);
    if (!protein) return;
    if (position === null || !wt) {
      setClientError('Select a residue position from the sequence.');
      return;
    }
    if (!AA.includes(wt) || !AA.includes(mutant)) {
      setClientError('Residue letters must be standard amino acids.');
      return;
    }
    if (wt === mutant) {
      setClientError('Wild-type and mutant residues must differ.');
      return;
    }
    if (position < 1 || position > protein.length) {
      setClientError('Position is out of range.');
      return;
    }
    if (protein.sequence[position - 1] !== wt) {
      setClientError('Wild-type letter does not match the UniProt sequence.');
      return;
    }
    mutation.mutate({
      accession: protein.accession,
      variant: `${wt}${position}${mutant}`,
      parameters: { ca_radius_angstrom: caRadius, heavy_atom_radius_angstrom: heavyRadius },
    });
  };

  if (query.isLoading) {
    return <p className="text-slate-600">Loading protein…</p>;
  }
  if (query.isError) {
    return <ErrorNotice error={query.error} title="Protein could not be loaded" onRetry={() => query.refetch()} />;
  }
  if (!protein) return null;

  return (
    <div className="space-y-6">
      <section className="card card-pad">
        <p className="label">Protein overview</p>
        <h1 className="mt-2 text-2xl font-bold">{protein.name}</h1>
        <p className="text-sm text-slate-600">{protein.organism}</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          <div>
            <p className="data-key">Accession</p>
            <p className="data-value">{protein.accession}</p>
          </div>
          <div>
            <p className="data-key">Length</p>
            <p className="data-value">{protein.length} aa</p>
          </div>
          <div>
            <p className="data-key">Gene</p>
            <p className="data-value">{protein.gene ?? '—'}</p>
          </div>
          <div>
            <p className="data-key">Structure</p>
            <p className="data-value">{protein.structure.source}</p>
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Structure: {protein.structure.model_version} · {protein.structure.file_format} ·{' '}
          {protein.structure.file_size_bytes} bytes
        </p>
        {protein.warnings.length > 0 && (
          <ul className="mt-3 list-disc pl-5 text-xs text-amber-700">
            {protein.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="card card-pad">
          <h2 className="text-lg font-semibold">Canonical sequence</h2>
          <div className="mt-3">
            <SequenceViewer
              sequence={protein.sequence}
              selectedPosition={position}
              onSelect={handleSelect}
            />
          </div>
        </div>
        <div className="card card-pad">
          <h2 className="text-lg font-semibold">Variant input</h2>
          <div className="mt-3 space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="label mb-1 block">WT</label>
                <input className="input font-mono uppercase" value={wt} readOnly />
              </div>
              <div>
                <label className="label mb-1 block">Position</label>
                <input
                  className="input font-mono"
                  type="number"
                  min={1}
                  max={protein.length}
                  value={position ?? ''}
                  onChange={(e) => {
                    const v = e.target.value ? Number(e.target.value) : null;
                    setPosition(v);
                    setWt(v && protein.sequence[v - 1] ? protein.sequence[v - 1] : '');
                    setClientError(null);
                  }}
                />
              </div>
              <div>
                <label className="label mb-1 block">Mutant</label>
                <select
                  className="input font-mono uppercase"
                  value={mutant}
                  onChange={(e) => setMutant(e.target.value)}
                >
                  {AA.map((a) => (
                    <option key={a} value={a}>
                      {a}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label mb-1 block">CA radius (Å)</label>
                <input
                  className="input"
                  type="number"
                  step="0.5"
                  value={caRadius}
                  onChange={(e) => setCaRadius(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="label mb-1 block">Heavy-atom radius (Å)</label>
                <input
                  className="input"
                  type="number"
                  step="0.5"
                  value={heavyRadius}
                  onChange={(e) => setHeavyRadius(Number(e.target.value))}
                />
              </div>
            </div>
            {clientError && (
              <p className="text-sm font-medium text-rose-700" role="alert">
                {clientError}
              </p>
            )}
            {mutation.isError && <ErrorNotice error={mutation.error} title="Analysis failed" />}
            <button
              type="button"
              className="btn-primary w-full"
              onClick={handleAnalyze}
              disabled={mutation.isPending}
            >
              {mutation.isPending ? 'Analyzing…' : 'Analyze variant'}
            </button>
            {selectedWt && position && (
              <p className="text-xs text-slate-500">
                Selected: {selectedWt}
                {position}
                {mutant}
              </p>
            )}
          </div>
        </div>
      </section>
      <Disclaimer />
    </div>
  );
}