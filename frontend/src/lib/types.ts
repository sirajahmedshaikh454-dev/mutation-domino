export interface Provenance {
  source: string;
  source_url: string;
  retrieved_at: string;
  source_version: string;
  mode: string;
}

export interface StructureSummary {
  available?: boolean;
  source: string;
  is_predicted: boolean;
  confidence_source: 'plddt' | 'b_factor' | 'none';
  model_version: string;
  chain: string;
  url: string;
  checksum_sha256: string;
  retrieved_at: string;
  file_format: string;
  file_size_bytes: number;
  tool_used: string;
  model_created_date: string;
  mode: string;
  coverage: Record<string, number>;
  download_path: string;
}

export interface ProteinResponse {
  accession: string;
  name: string;
  organism: string;
  gene: string | null;
  length: number;
  sequence: string;
  provenance: Provenance;
  structure: StructureSummary;
  warnings: string[];
}

export interface ResidueProperties {
  one_letter: string;
  three_letter: string;
  category: string;
  charge_class: string;
  aromatic: boolean;
  polar_side_chain: boolean;
  hydropathy: number;
  residue_mass_da: number;
  sidechain_heavy_atoms: number;
}

export interface PropertyChange {
  from: string | boolean;
  to: string | boolean;
  changed: boolean;
}

export interface PropertyDeltas {
  hydropathy: number;
  residue_mass_da: number;
  sidechain_heavy_atoms: number;
  category_changed: boolean;
  charge_class_changed: boolean;
  aromatic_changed: boolean;
}

export interface PropertyReport {
  wild_type: ResidueProperties;
  mutant: ResidueProperties;
  deltas: PropertyDeltas;
  changes: {
    category: PropertyChange;
    charge_class: PropertyChange;
    aromatic: PropertyChange;
    polar_side_chain: PropertyChange;
  };
  table: { version: string; source: string };
}

export interface ContactRow {
  structure_index: number;
  chain_id: string;
  sequence_id: number;
  insertion_code: string;
  residue_id: string;
  resname: string;
  one_letter: string;
  canonical_position: number | null;
  distance_angstrom: number;
  category: 'ca_neighbor' | 'heavy_atom_contact';
  target_atom?: string;
  partner_atom?: string;
  properties: {
    category: string;
    charge_class: string;
    aromatic: boolean;
    hydropathy: number;
  };
}

export interface NeighborhoodReport {
  ca_neighbors: {
    radius_angstrom: number;
    count: number;
    truncated: boolean;
    rows: ContactRow[];
  };
  heavy_atom_contacts: {
    radius_angstrom: number;
    count: number;
    truncated: boolean;
    rows: ContactRow[];
  };
}

export interface ConfidenceBand {
  key: 'very_low' | 'low' | 'confident' | 'very_confident';
  label: string;
  threshold: number;
}

export interface ConfidenceReport {
  source: string;
  availability: 'available' | 'b_factor_only' | 'not_available';
  per_residue_value: number | null;
  band: ConfidenceBand | null;
  semantics: string;
  note: string;
}

export interface MappingReport {
  canonical_position: number;
  canonical_residue: string;
  structure_chain: string;
  structure_residue_id: string;
  structure_sequence_id: number;
  insertion_code: string;
  residue_name: string;
  residue_three_letter: string;
  mapping_status: string;
  alignment: Record<string, unknown>;
  warnings: string[];
}

export interface AnalysisResult {
  schema_version: string;
  algorithm_version: string;
  generated_at: string;
  input: {
    accession: string;
    variant: string;
    variant_input: string;
    parameters: AnalysisParameters;
  };
  protein: {
    accession: string;
    name: string;
    organism: string;
    gene: string | null;
    length: number;
  };
  structure: StructureSummary & {
    coverage: {
      structure_residues: number;
      canonical_length: number;
      observed_sequence_length: number;
    };
  };
  mapping: MappingReport;
  variant: {
    normalized: string;
    wild_type: string;
    position: number;
    mutant: string;
    wild_type_three_letter: string;
    mutant_three_letter: string;
  };
  residue: {
    structure_residue_id: string;
    resname: string;
    one_letter: string;
    ca_present: boolean;
    heavy_atom_count: number;
  };
  confidence: ConfidenceReport;
  properties: PropertyReport;
  neighborhood: NeighborhoodReport;
  interpretation: {
    observations: string[];
    descriptors: string[];
    cautions: string[];
  };
  warnings: string[];
  provenance: {
    mode: string;
    protein_source: {
      name: string;
      url: string;
      retrieved_at: string;
      source_version: string;
    };
    structure_source: {
      name: string;
      url: string;
      retrieved_at: string;
      model_version: string;
      checksum_sha256: string;
      tool_used: string;
    };
    mapping_method: string;
    parameters: AnalysisParameters;
    algorithm_version: string;
    schema_version: string;
  };
}

export interface AnalysisParameters {
  ca_radius_angstrom: number;
  heavy_atom_radius_angstrom: number;
}

export interface AnalysisResponse {
  id: string;
  status: string;
  created_at: string;
  result: AnalysisResult;
}

export interface AnalysisSummary {
  id: string;
  accession: string;
  variant: string;
  protein_name: string;
  organism: string;
  status: string;
  created_at: string;
  structure_source: string;
  model_version: string;
}

export interface AnalysisListResponse {
  items: AnalysisSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateAnalysisInput {
  accession: string;
  variant: string;
  parameters: AnalysisParameters;
}

export interface ApiErrorPayload {
  code: string;
  message: string;
  details: Record<string, unknown>;
}
