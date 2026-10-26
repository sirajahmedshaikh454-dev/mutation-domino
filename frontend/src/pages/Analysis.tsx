import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { getAnalysis, exportJsonUrl, exportPdfUrl } from '../lib/api';
import { ErrorNotice } from '../components/ErrorNotice';
import { MolstarViewer } from '../components/MolstarViewer';
interface ResidueRef {
  chain: string;
  seqId: number;
  insertionCode?: string;
}
import type { ContactRow } from '../lib/types';
import { Disclaimer } from '../components/Disclaimer';

function toRef(row: { chain_id: string; sequence_id: number; insertion_code: string }): ResidueRef {
  return { chain: row.chain_id, seqId: row.sequence_id, insertionCode: row.insertion_code };
}

export function Analysis() {
  const { id = '' } = useParams();
  const query = useQuery({
    queryKey: ['analysis', id],
    queryFn: ({ signal }) => getAnalysis(id, signal),
    enabled: Boolean(id),
  });

  const [focusTarget, setFocusTarget] = useState<ResidueRef | null>(null);
  const [resetToken, setResetToken] = useState(0);

  const result = query.data?.result;
  const target = useMemo<ResidueRef | null>(() => {
    if (!result) return null;
    return {
      chain: result.mapping.structure_chain,
      seqId: result.mapping.structure_sequence_id,
      insertionCode: result.mapping.insertion_code,
    };
  }, [result]);

  const allNeighbors = useMemo<ResidueRef[]>(() => {
    if (!result) return [];
    const rows: ContactRow[] = [
      ...result.neighborhood.ca_neighbors.rows,
      ...result.neighborhood.heavy_atom_contacts.rows,
    ];
    const seen = new Set<string>();
    const refs: ResidueRef[] = [];
    for (const row of rows) {
      const key = `${row.chain_id}:${row.sequence_id}:${row.insertion_code}`;
      if (seen.has(key)) continue;
      seen.add(key);
      refs.push(toRef(row));
    }
    return refs;
  }, [result]);

  if (query.isLoading) return <p className="text-slate-600">Loading analysis…</p>;
  if (query.isError) {
    return <ErrorNotice error={query.error} title="Analysis could not be loaded" onRetry={() => query.refetch()} />;
  }
  if (!result) return null;

  const colorByConfidence = result.confidence.availability === 'available';

  return (
    <div className="space-y-6">
      <section className="card card-pad">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="label">Analysis</p>
            <h1 className="mt-2 text-2xl font-bold">
              {result.variant.normalized} · {result.protein.name}
            </h1>
            <p className="text-sm text-slate-600">{result.protein.organism}</p>
          </div>
          <div className="flex gap-2">
            <a className="btn-secondary" href={exportJsonUrl(query.data!.id)} download>
              Export JSON
            </a>
            <a className="btn-secondary" href={exportPdfUrl(query.data!.id)} download>
              Export PDF
            </a>
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          ID {query.data!.id} · created {query.data!.created_at} · mode {result.provenance.mode}
        </p>
      </section>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div>
              <p className="label">3D viewer</p>
              <h2 className="text-base font-semibold">Wild-type reference structure</h2>
            </div>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setResetToken((v) => v + 1)}
            >
              Reset view
            </button>
          </div>
          <MolstarViewer
            accession={result.protein.accession}
            fileFormat={result.structure.file_format}
            colorByConfidence={colorByConfidence}
            target={target}
            neighbors={allNeighbors}
            focusTarget={focusTarget}
            resetToken={resetToken}
            onResidueSelect={(r) => {
              if (!r) return;
              setFocusTarget({ chain: r.chain, seqId: r.seqId, insertionCode: r.insertionCode });
            }}
          />
        </div>

        <div className="space-y-6">
          <section className="card card-pad">
            <h2 className="text-lg font-semibold">Mapping</h2>
            <div className="mt-2 space-y-1 text-sm">
              <p>
                Canonical position {result.mapping.canonical_position} ({result.mapping.canonical_residue})
              </p>
              <p>
                Structure chain {result.mapping.structure_chain}, residue{' '}
                {result.mapping.structure_residue_id}
              </p>
              <p className="text-xs text-slate-500">{result.mapping.mapping_status}</p>
            </div>
            {result.mapping.warnings.length > 0 && (
              <ul className="mt-2 list-disc pl-5 text-xs text-amber-700">
                {result.mapping.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            )}
          </section>

          <section className="card card-pad">
            <h2 className="text-lg font-semibold">Confidence</h2>
            <p className="mt-2 text-sm">
              {result.confidence.source} · {result.confidence.availability}
            </p>
            <p className="text-sm">
              Value: {result.confidence.per_residue_value ?? 'N/A'}
              {result.confidence.band ? ` (${result.confidence.band.label})` : ''}
            </p>
            <p className="mt-2 text-xs text-slate-500">{result.confidence.semantics}</p>
            <p className="text-xs text-slate-500">{result.confidence.note}</p>
          </section>

          <section className="card card-pad">
            <h2 className="text-lg font-semibold">Residue properties</h2>
            <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="data-key">WT</p>
                <p className="font-semibold">{result.properties.wild_type.one_letter}</p>
                <p className="text-xs text-slate-500">{result.properties.wild_type.category}</p>
              </div>
              <div>
                <p className="data-key">Mutant</p>
                <p className="font-semibold">{result.properties.mutant.one_letter}</p>
                <p className="text-xs text-slate-500">{result.properties.mutant.category}</p>
              </div>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Δhydropathy {result.properties.deltas.hydropathy.toFixed(2)} · Δmass{' '}
              {result.properties.deltas.residue_mass_da.toFixed(1)} Da
            </p>
          </section>
        </div>
      </section>

      <section className="card card-pad">
        <h2 className="text-lg font-semibold">Neighborhood</h2>
        <p className="mt-1 text-xs text-slate-500">
          CA neighbors (≤{result.neighborhood.ca_neighbors.radius_angstrom} Å):{' '}
          {result.neighborhood.ca_neighbors.count} · Heavy-atom contacts (≤
          {result.neighborhood.heavy_atom_contacts.radius_angstrom} Å):{' '}
          {result.neighborhood.heavy_atom_contacts.count}
        </p>
        <div className="mt-3 overflow-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="py-2">Residue</th>
                <th className="py-2">Chain</th>
                <th className="py-2">Canonical pos</th>
                <th className="py-2">Distance (Å)</th>
                <th className="py-2">Category</th>
              </tr>
            </thead>
            <tbody>
              {result.neighborhood.ca_neighbors.rows.map((row, index) => (
                <tr
                  key={`ca-${index}`}
                  className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
                  onClick={() => setFocusTarget(toRef(row))}
                >
                  <td className="py-2 font-mono">
                    {row.one_letter}
                    {row.sequence_id}
                  </td>
                  <td className="py-2">{row.chain_id}</td>
                  <td className="py-2">{row.canonical_position ?? '—'}</td>
                  <td className="py-2">{row.distance_angstrom.toFixed(2)}</td>
                  <td className="py-2 text-xs">CA neighbor</td>
                </tr>
              ))}
              {result.neighborhood.heavy_atom_contacts.rows.map((row, index) => (
                <tr
                  key={`ha-${index}`}
                  className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
                  onClick={() => setFocusTarget(toRef(row))}
                >
                  <td className="py-2 font-mono">
                    {row.one_letter}
                    {row.sequence_id}
                  </td>
                  <td className="py-2">{row.chain_id}</td>
                  <td className="py-2">{row.canonical_position ?? '—'}</td>
                  <td className="py-2">{row.distance_angstrom.toFixed(2)}</td>
                  <td className="py-2 text-xs">Heavy-atom contact</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card card-pad">
        <h2 className="text-lg font-semibold">Interpretation</h2>
        <div className="mt-2 space-y-2">
          {result.interpretation.observations.map((o) => (
            <p key={o} className="text-sm">
              <span className="font-semibold">Observation:</span> {o}
            </p>
          ))}
          {result.interpretation.descriptors.map((d) => (
            <p key={d} className="text-sm">
              <span className="font-semibold">Descriptor:</span> {d}
            </p>
          ))}
          {result.interpretation.cautions.map((c) => (
            <p key={c} className="text-sm text-amber-800">
              <span className="font-semibold">Caution:</span> {c}
            </p>
          ))}
        </div>
      </section>

      {result.warnings.length > 0 && (
        <section className="card card-pad">
          <h2 className="text-lg font-semibold">Warnings</h2>
          <ul className="mt-2 list-disc pl-5 text-sm text-amber-700">
            {result.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </section>
      )}

      <Disclaimer />
    </div>
  );
}