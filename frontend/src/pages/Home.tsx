import { SearchForm } from '../components/SearchForm';
import { Disclaimer } from '../components/Disclaimer';

export function Home() {
  return (
    <div className="space-y-8">
      <section className="card card-pad">
        <p className="label">Structural context explorer</p>
        <h1 className="mt-2 text-3xl font-bold sm:text-4xl">
          Mutation Domino
        </h1>
        <p className="mt-3 max-w-3xl text-slate-600">
          Explore the wild-type structural neighborhood of a missense variant. Enter a UniProt
          accession to load metadata and an AlphaFold prediction, then specify a substitution to
          inspect contacts, confidence, and physicochemical property changes.
        </p>
        <div className="mt-6 max-w-xl">
          <SearchForm autoFocus />
        </div>
      </section>
      <section className="grid gap-4 sm:grid-cols-3">
        <div className="card card-pad">
          <h2 className="text-lg font-semibold">Wild-type reference</h2>
          <p className="mt-2 text-sm text-slate-600">
            The 3D viewer shows the supplied wild-type model. No mutant coordinates are generated.
          </p>
        </div>
        <div className="card card-pad">
          <h2 className="text-lg font-semibold">Transparent metrics</h2>
          <p className="mt-2 text-sm text-slate-600">
            CA neighbors, heavy-atom contacts, pLDDT confidence bands, and residue property deltas.
          </p>
        </div>
        <div className="card card-pad">
          <h2 className="text-lg font-semibold">Provenance</h2>
          <p className="mt-2 text-sm text-slate-600">
            Every analysis stores source URLs, checksums, timestamps, mapping method, and parameters.
          </p>
        </div>
      </section>
      <Disclaimer />
    </div>
  );
}