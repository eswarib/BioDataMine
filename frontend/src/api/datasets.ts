// API base - nginx proxies /api/* to backend
const API_BASE = '/api';

export interface DatasetSummary {
  total_files: number;
  scheduled_files: number;
  modality_counts: Record<string, number>;
  modalities: Record<string, Record<string, unknown>>;
  mixed_modality: boolean | null;
  outliers: number;
  kind_counts: Record<string, number>;
  ext_counts: Record<string, number>;
  scheduled_ext_counts: Record<string, number>;
  duplicate_basename_count: number;
  duplicate_basename_ext_counts: Record<string, number>;
  image_2d_count: number;
  volume_3d_count: number;
}

export interface DatasetListItem {
  dataset_id: string;
  name: string;
  status: 'processing' | 'ready' | 'failed';
  created_at: string;
  summary: DatasetSummary;
}

export interface DatasetSummaryResponse extends DatasetSummary {
  stage: string;
  modality_percentages: Record<string, number>;
}

export interface FileListItem {
  dataset_id: string;
  relpath: string;
  kind: 'dicom' | 'nifti' | 'image' | 'unknown';
  modality: string;
  modality_model: Record<string, unknown>;
  ndim: number | null;
  dims: number[] | null;
  size_bytes: number;
  created_at: string;
  meta: Record<string, unknown>;
}

export interface DatasetDetail {
  _id: string;
  name: string;
  source_url: string;
  team_id: string | null;
  owner_user_id: string | null;
  status: 'processing' | 'ready' | 'failed';
  created_at: string;
  summary: DatasetSummary;
  meta: Record<string, unknown>;
}

export interface IngestRequest {
  url: string;
  name?: string;
  team_id?: string;
}

export interface IngestResponse {
  dataset_id: string;
  status: 'processing' | 'ready' | 'failed';
  all_dataset_ids: string[] | null;
  source_type: string;
  resolved_urls: string[] | null;
}

export async function fetchDatasets(): Promise<DatasetListItem[]> {
  const res = await fetch(`${API_BASE}/datasets`);
  if (!res.ok) throw new Error('Failed to fetch datasets');
  return res.json();
}

export async function fetchDataset(datasetId: string): Promise<DatasetDetail> {
  const res = await fetch(`${API_BASE}/datasets/${datasetId}`);
  if (!res.ok) throw new Error('Failed to fetch dataset');
  return res.json();
}

export async function fetchDatasetSummary(datasetId: string): Promise<DatasetSummaryResponse> {
  const res = await fetch(`${API_BASE}/datasets/${datasetId}/summary`);
  if (!res.ok) throw new Error('Failed to fetch dataset summary');
  return res.json();
}

export async function fetchDatasetFiles(
  datasetId: string,
  skip = 0,
  limit = 200
): Promise<FileListItem[]> {
  const res = await fetch(`${API_BASE}/datasets/${datasetId}/files?skip=${skip}&limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch dataset files');
  return res.json();
}

export async function ingestDataset(request: IngestRequest): Promise<IngestResponse> {
  const res = await fetch(`${API_BASE}/datasets/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error('Failed to ingest dataset');
  return res.json();
}
