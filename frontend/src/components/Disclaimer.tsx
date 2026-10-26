import { Info } from 'lucide-react';

export function Disclaimer({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <p className="flex items-start gap-2 text-xs leading-relaxed text-slate-500">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        Research and education only. Describes wild-type structural context, not a mutant effect or
        clinical risk.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-amber-200 bg-amber-50/80 p-5 sm:flex-row sm:items-start">
      <Info className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" aria-hidden="true" />
      <div>
        <p className="text-sm font-semibold text-amber-950">
          Wild-type context only — not a prediction of the mutant
        </p>
        <p className="mt-1 text-sm leading-relaxed text-amber-900">
          Mutation Domino reports geometry and coarse residue properties from a supplied wild-type
          structure. It does not model mutant coordinates, estimate stability, classify
          pathogenicity, or support clinical decisions. pLDDT, when shown, is confidence in the
          wild-type predicted local structure.
        </p>
      </div>
    </div>
  );
}
