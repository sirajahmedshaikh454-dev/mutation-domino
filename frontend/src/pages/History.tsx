import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { listAnalyses, exportJsonUrl, exportPdfUrl } from '../lib/api';
import { ErrorNotice } from '../components/ErrorNotice';

export function History() {
  const query = useQuery({
    queryKey: ['analyses', 0],
    queryFn: ({ signal }) => listAnalyses({ limit: 50, offset: 0 }, signal),
  });

  if (query.isLoading) return <p className="text-slate-600">Loading history…</p>;
  if (query.isError) {
    return <ErrorNotice error={query.error} title="History could not be loaded" onRetry={() => query.refetch()} />;
  }

  const items = query.data?.items ?? [];
  if (items.length === 0) {
    return (
      <section className="card card-pad">
        <h1 className="text-2xl font-bold">Analysis history</h1>
        <p className="mt-2 text-slate-600">No saved analyses yet.</p>
      </section>
    );
  }

  return (
    <section className="card card-pad">
      <h1 className="text-2xl font-bold">Analysis history</h1>
      <div className="mt-4 overflow-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase text-slate-500">
            <tr>
              <th className="py-2">Accession</th>
              <th className="py-2">Variant</th>
              <th className="py-2">Protein</th>
              <th className="py-2">Created</th>
              <th className="py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-t border-slate-100">
                <td className="py-2 font-mono">{item.accession}</td>
                <td className="py-2 font-mono">{item.variant}</td>
                <td className="py-2">{item.protein_name}</td>
                <td className="py-2 text-xs text-slate-500">{item.created_at}</td>
                <td className="py-2">
                  <div className="flex gap-2">
                    <Link className="btn-ghost" to={`/analyses/${item.id}`}>
                      Open
                    </Link>
                    <a className="btn-ghost" href={exportJsonUrl(item.id)} download>
                      JSON
                    </a>
                    <a className="btn-ghost" href={exportPdfUrl(item.id)} download>
                      PDF
                    </a>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}