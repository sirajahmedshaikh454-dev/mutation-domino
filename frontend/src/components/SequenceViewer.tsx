import { useMemo } from 'react';

interface SequenceViewerProps {
  sequence: string;
  selectedPosition: number | null;
  onSelect: (position: number, letter: string) => void;
  chunkSize?: number;
}

export function SequenceViewer({
  sequence,
  selectedPosition,
  onSelect,
  chunkSize = 20,
}: SequenceViewerProps) {
  const rows = useMemo(() => {
    const result: { start: number; residues: { position: number; letter: string }[] }[] = [];
    for (let index = 0; index < sequence.length; index += chunkSize) {
      const residues = sequence
        .slice(index, index + chunkSize)
        .split('')
        .map((letter, offset) => ({ position: index + offset + 1, letter }));
      result.push({ start: index + 1, residues });
    }
    return result;
  }, [sequence, chunkSize]);

  return (
    <div>
      <div className="sequence-strip max-h-72 overflow-auto rounded-xl border border-slate-200 bg-slate-50/80 p-3">
        <div className="inline-block min-w-full">
          {rows.map((row) => (
            <div key={row.start} className="flex items-center gap-3 whitespace-nowrap">
              <span className="w-10 shrink-0 text-right font-mono text-[0.68rem] text-slate-400">
                {row.start}
              </span>
              <div className="flex gap-0.5">
                {row.residues.map(({ position, letter }) => {
                  const selected = selectedPosition === position;
                  return (
                    <button
                      key={position}
                      type="button"
                      onClick={() => onSelect(position, letter)}
                      aria-label={`Position ${position}, ${letter}`}
                      aria-pressed={selected}
                      title={`${letter}${position}`}
                      className={`sequence-residue ${selected ? 'sequence-residue-selected' : ''}`}
                    >
                      {letter}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Click any residue to set the canonical variant position. The wild-type letter is filled from
        the UniProt sequence.
      </p>
    </div>
  );
}
