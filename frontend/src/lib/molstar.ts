export interface ViewerResidue {
  chain: string;
  seqId: number;
  compId: string;
  insertionCode: string;
}

export interface StructureElementSchemaItem {
  auth_asym_id?: string;
  auth_seq_id?: number;
  pdbx_PDB_ins_code?: string;
}

export interface MolstarLoci {
  readonly kind: 'element-loci';
}

export interface MolstarLocation {
  unit: unknown;
  element: number;
}

export interface MolstarViewer {
  plugin: {
    behaviors: {
      interaction: {
        click: unknown;
      };
    };
    managers: {
      camera: {
        reset(): void;
      };
      structure: {
        hierarchy: {
          current: {
            structures: ReadonlyArray<{ components: ReadonlyArray<unknown> }>;
          };
        };
        component: {
          updateRepresentationsTheme(
            components: ReadonlyArray<unknown>,
            params: { color?: string },
          ): Promise<unknown> | undefined;
        };
      };
    };
  };
  loadStructureFromUrl(
    url: string,
    format: 'cif' | 'pdb' | string,
    isBinary: boolean,
    options?: { label?: string },
  ): Promise<void>;
  structureInteractivity(options: {
    elements?: { items: StructureElementSchemaItem[] };
    action: 'highlight' | 'select' | 'focus' | ('highlight' | 'select' | 'focus')[];
    focusOptions?: { minRadius?: number; extraRadius?: number };
  }): void;
  subscribe<T>(observable: unknown, action: (value: T) => void): { unsubscribe: () => void };
  handleResize(): void;
  dispose(): void;
}

interface ClickEvent {
  current?: {
    loci?: unknown;
  };
}

export interface MolstarGlobal {
  Viewer: {
    create(
      element: HTMLElement,
      options?: Record<string, unknown>,
    ): Promise<MolstarViewer>;
  };
  lib: {
    structure: {
      StructureElement: {
        Loci: {
          is(value: unknown): value is MolstarLoci;
          getFirstLocation(loci: MolstarLoci): MolstarLocation | undefined;
        };
      };
      StructureProperties: {
        residue: {
          auth_seq_id(unit: unknown, element: number): number;
          auth_asym_id(unit: unknown, element: number): string;
          label_comp_id(unit: unknown, element: number): string;
          pdbx_PDB_ins_code(unit: unknown, element: number): string;
        };
      };
    };
  };
}

declare global {
  interface Window {
    molstar?: MolstarGlobal;
  }
}

let loaderPromise: Promise<MolstarGlobal> | null = null;

export function hasWebGL(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2') ?? canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

export function loadMolstar(): Promise<MolstarGlobal> {
  if (window.molstar) return Promise.resolve(window.molstar);
  if (loaderPromise) return loaderPromise;

  loaderPromise = new Promise<MolstarGlobal>((resolve, reject) => {
    const cssId = 'molstar-viewer-css';
    if (!document.getElementById(cssId)) {
      const link = document.createElement('link');
      link.id = cssId;
      link.rel = 'stylesheet';
      link.href = '/molstar/molstar.css';
      document.head.appendChild(link);
    }

    const script = document.createElement('script');
    script.src = '/molstar/molstar.js';
    script.async = true;
    script.onload = () => {
      if (window.molstar) {
        resolve(window.molstar);
      } else {
        loaderPromise = null;
        reject(new Error('Mol* loaded but did not expose a global viewer API.'));
      }
    };
    script.onerror = () => {
      loaderPromise = null;
      reject(new Error('The Mol* viewer bundle could not be loaded. Run "npm run prepare:molstar".'));
    };
    document.head.appendChild(script);
  });

  return loaderPromise;
}

export function residueFromClick(
  molstar: MolstarGlobal,
  event: ClickEvent,
): ViewerResidue | null {
  const loci = event.current?.loci;
  const { StructureElement, StructureProperties } = molstar.lib.structure;
  if (!StructureElement.Loci.is(loci)) return null;
  const location = StructureElement.Loci.getFirstLocation(loci);
  if (!location) return null;

  const { unit, element } = location;
  const seqId = StructureProperties.residue.auth_seq_id(unit, element);
  if (!Number.isFinite(seqId) || seqId <= 0) return null;

  return {
    chain: StructureProperties.residue.auth_asym_id(unit, element),
    seqId,
    compId: StructureProperties.residue.label_comp_id(unit, element),
    insertionCode: StructureProperties.residue.pdbx_PDB_ins_code(unit, element) ?? '',
  };
}
