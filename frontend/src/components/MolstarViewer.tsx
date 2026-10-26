import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Loader2, RotateCcw } from 'lucide-react';
import { useTheme } from './ThemeProvider';
import {
  hasWebGL,
  loadMolstar,
  residueFromClick,
  type MolstarGlobal,
  type MolstarViewer as ViewerInstance,
  type StructureElementSchemaItem,
  type ViewerResidue,
} from '../lib/molstar';
import { structureUrl } from '../lib/api';

interface ResidueRef {
  chain: string;
  seqId: number;
  insertionCode?: string;
}

interface MolstarViewerProps {
  accession: string;
  fileFormat: string;
  colorByConfidence: boolean;
  target: ResidueRef | null;
  neighbors: ResidueRef[];
  focusTarget: ResidueRef | null;
  resetToken: number;
  onResidueSelect: (residue: ViewerResidue | null) => void;
}

type ViewerStatus = 'loading' | 'ready' | 'error' | 'unsupported';

function schemaItem(residue: ResidueRef): StructureElementSchemaItem {
  return {
    auth_asym_id: residue.chain,
    auth_seq_id: residue.seqId,
    ...(residue.insertionCode ? { pdbx_PDB_ins_code: residue.insertionCode } : {}),
  };
}

function residueKey(residue: ResidueRef | null | undefined): string {
  if (!residue) return '';
  return `${residue.chain}:${residue.seqId}:${residue.insertionCode ?? ''}`;
}

function applyReferenceHighlight(
  viewer: ViewerInstance,
  target: ResidueRef | null,
  neighbors: ResidueRef[],
): void {
  if (!target) return;
  viewer.structureInteractivity({
    elements: { items: [schemaItem(target)] },
    action: ['select', 'focus'],
    focusOptions: { extraRadius: 6 },
  });
  if (neighbors.length > 0) {
    viewer.structureInteractivity({
      elements: { items: neighbors.map(schemaItem) },
      action: 'highlight',
    });
  }
}

export function MolstarViewer({
  accession,
  fileFormat,
  colorByConfidence,
  target,
  neighbors,
  focusTarget,
  resetToken,
  onResidueSelect,
}: MolstarViewerProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<ViewerInstance | null>(null);
  const molstarRef = useRef<MolstarGlobal | null>(null);
  const onResidueSelectRef = useRef(onResidueSelect);
  const targetRef = useRef(target);
  const neighborsRef = useRef(neighbors);
  const { resolvedTheme } = useTheme();
  const [status, setStatus] = useState<ViewerStatus>(() =>
    hasWebGL() ? 'loading' : 'unsupported',
  );
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const viewerBackground = resolvedTheme === 'dark' ? 0x0b2429 : 0xf8fafc;
  const viewerBackgroundHex = resolvedTheme === 'dark' ? '#0b2429' : '#f8fafc';

  const targetKey = residueKey(target);
  const neighborKey = neighbors.map(residueKey).join('|');
  const focusKey = residueKey(focusTarget);

  useEffect(() => {
    onResidueSelectRef.current = onResidueSelect;
  });
  useEffect(() => {
    targetRef.current = target;
    neighborsRef.current = neighbors;
  }, [target, neighbors]);

  useEffect(() => {
    if (!hasWebGL()) {
      return;
    }

    const host = hostRef.current;
    if (!host) return;

    let cancelled = false;
    let viewer: ViewerInstance | null = null;
    let clickSubscription: { unsubscribe: () => void } | null = null;
    const observer = new ResizeObserver(() => viewerRef.current?.handleResize());

    host.replaceChildren();
    queueMicrotask(() => setStatus('loading'));
    setError(null);

    const start = async () => {
      try {
        const molstar = await loadMolstar();
        if (cancelled) return;
        molstarRef.current = molstar;
        viewer = await molstar.Viewer.create(host, {
          layoutIsExpanded: false,
          layoutShowControls: false,
          layoutShowSequence: false,
          layoutShowLog: false,
          layoutShowLeftPanel: false,
          collapseLeftPanel: true,
          collapseRightPanel: true,
          viewportShowControls: true,
          viewportShowExpand: false,
          viewportShowSettings: false,
          viewportShowSelectionMode: false,
          viewportShowAnimation: false,
          viewportShowScreenshotControls: false,
          viewportShowReset: false,
          viewportShowToggleFullscreen: true,
          viewportBackgroundColor: viewerBackgroundHex,
        });
        if (cancelled) {
          viewer.dispose();
          return;
        }
        viewerRef.current = viewer;
        observer.observe(host);

        await viewer.loadStructureFromUrl(
          structureUrl(accession),
          fileFormat === 'pdb' ? 'pdb' : 'mmcif',
          false,
          { label: `${accession} wild-type reference` },
        );
        viewer.plugin.managers.camera.reset();
        if (cancelled) return;

        if (colorByConfidence) {
          try {
            const structures = viewer.plugin.managers.structure.hierarchy.current.structures;
            for (const structure of structures) {
              await viewer.plugin.managers.structure.component.updateRepresentationsTheme(
                structure.components,
                { color: 'uncertainty' },
              );
            }
          } catch (themeError) {
            console.warn('Could not apply the Mol* uncertainty colour theme.', themeError);
          }
        }

        clickSubscription = viewer.subscribe(
          viewer.plugin.behaviors.interaction.click,
          (event: { current?: { loci?: unknown } }) => {
            const molstarInstance = molstarRef.current;
            if (!molstarInstance) return;
            onResidueSelectRef.current(residueFromClick(molstarInstance, event));
          },
        );

        applyReferenceHighlight(viewer, targetRef.current, neighborsRef.current);
        setStatus('ready');
      } catch (loadError) {
        if (cancelled) return;
        setError(
          loadError instanceof Error ? loadError.message : 'The 3D viewer could not be initialised.',
        );
        setStatus('error');
      }
    };

    void start();

    return () => {
      cancelled = true;
      observer.disconnect();
      clickSubscription?.unsubscribe();
      viewerRef.current?.dispose();
      viewerRef.current = null;
      host.replaceChildren();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [accession, fileFormat, colorByConfidence, attempt]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || status !== 'ready') return;
    try {
      (
        viewer.plugin as {
          canvas3d?: { setProps?: (props: { renderer: { backgroundColor: number } }) => void };
        }
      ).canvas3d?.setProps?.({ renderer: { backgroundColor: viewerBackground } });
    } catch (themeError) {
      console.warn('Could not update the Mol* background for the current theme.', themeError);
    }
  }, [status, viewerBackground]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || status !== 'ready') return;
    applyReferenceHighlight(viewer, targetRef.current, neighborsRef.current);
  }, [status, targetKey, neighborKey]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || status !== 'ready' || !focusTarget) return;
    viewer.structureInteractivity({
      elements: { items: [schemaItem(focusTarget)] },
      action: ['select', 'focus'],
      focusOptions: { extraRadius: 5 },
    });
  }, [status, focusKey, focusTarget]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || status !== 'ready') return;
    viewer.structureInteractivity({ action: ['select', 'highlight'] });
    viewer.plugin.managers.camera.reset();
    applyReferenceHighlight(viewer, targetRef.current, neighborsRef.current);
  }, [status, resetToken]);

  return (
    <div className="relative">
      <div
        ref={hostRef}
        className="molstar-host"
        role="img"
        aria-label={`Interactive 3D viewer showing the wild-type reference structure for ${accession}. Drag to rotate, scroll to zoom.`}
      />
      {status === 'loading' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-b-2xl bg-ink-950/70 text-white backdrop-blur-sm">
          <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
          <p className="text-sm font-medium">Loading the wild-type structure…</p>
          <p className="max-w-sm px-6 text-center text-xs text-white/70">
            Mol* is rendering the reference model. No mutant coordinates are generated.
          </p>
        </div>
      )}
      {status === 'unsupported' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-b-2xl bg-ink-950 px-6 text-center text-white">
          <AlertTriangle className="h-7 w-7 text-amber-300" aria-hidden="true" />
          <p className="text-base font-semibold">3D viewer unavailable</p>
          <p className="max-w-md text-sm text-white/75">
            This browser or device does not expose WebGL. The structural context and contact tables
            are still available, and you can download the wild-type structure.
          </p>
          <a
            className="btn-secondary mt-1 bg-white/10 text-white hover:bg-white/20 hover:text-white"
            href={structureUrl(accession)}
          >
            Download wild-type structure
          </a>
        </div>
      )}
      {status === 'error' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-b-2xl bg-ink-950 px-6 text-center text-white">
          <AlertTriangle className="h-7 w-7 text-amber-300" aria-hidden="true" />
          <p className="text-base font-semibold">The 3D viewer could not load</p>
          <p className="max-w-md text-sm text-white/75">{error}</p>
          <button
            type="button"
            className="btn-secondary bg-white/10 text-white hover:bg-white/20 hover:text-white"
            onClick={() => setAttempt((value) => value + 1)}
          >
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            Retry viewer
          </button>
        </div>
      )}
    </div>
  );
}
