import { useState, useEffect } from 'react';
import { fetchDataset, fetchDatasetSummary, fetchDatasetFiles } from '../api/datasets';
import type { DatasetDetail, DatasetSummaryResponse, FileListItem } from '../api/datasets';
import { ModalityCounts } from './ModalityCounts';
import { FileTable } from './FileTable';

interface DatasetViewProps {
  datasetId: string;
}

type Tab = 'overview' | 'files';

export function DatasetView({ datasetId }: DatasetViewProps) {
  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [summary, setSummary] = useState<DatasetSummaryResponse | null>(null);
  const [files, setFiles] = useState<FileListItem[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(true);
  const [filesLoading, setFilesLoading] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [datasetData, summaryData] = await Promise.all([
          fetchDataset(datasetId),
          fetchDatasetSummary(datasetId),
        ]);
        setDataset(datasetData);
        setSummary(summaryData);
      } catch (err) {
        console.error('Failed to load dataset:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [datasetId]);

  useEffect(() => {
    async function loadFiles() {
      if (activeTab !== 'files') return;
      setFilesLoading(true);
      try {
        const filesData = await fetchDatasetFiles(datasetId);
        setFiles(filesData);
      } catch (err) {
        console.error('Failed to load files:', err);
      } finally {
        setFilesLoading(false);
      }
    }
    loadFiles();
  }, [datasetId, activeTab]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center">
          <div className="w-10 h-10 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-4" />
          <span className="text-slate-500">Loading dataset...</span>
        </div>
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <svg className="w-16 h-16 mx-auto mb-4 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="text-slate-400">Dataset not found</p>
        </div>
      </div>
    );
  }

  const StatusBadge = () => {
    const styles = {
      ready: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      processing: 'bg-amber-500/20 text-amber-400 border-amber-500/30 animate-pulse',
      failed: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
    };
    
    return (
      <span className={`text-xs uppercase tracking-wider px-2 py-1 rounded border ${styles[dataset.status]}`}>
        {dataset.status}
      </span>
    );
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-800 p-4">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-xl font-semibold text-white truncate">{dataset.name}</h1>
              <StatusBadge />
            </div>
            {/* Dataset URL */}
            <div className="flex items-center gap-2 p-3 bg-slate-850 rounded-lg border border-slate-700/50 max-w-3xl">
              <svg className="w-4 h-4 text-slate-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              <code className="text-sm text-emerald-400 font-mono truncate flex-1">{dataset.source_url}</code>
              <button
                onClick={() => navigator.clipboard.writeText(dataset.source_url)}
                className="p-1.5 hover:bg-slate-700 rounded transition-colors"
                title="Copy URL"
              >
                <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
              <a
                href={dataset.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 hover:bg-slate-700 rounded transition-colors"
                title="Open in new tab"
              >
                <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-2">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === 'overview'
                ? 'bg-slate-800 text-emerald-400 border-b-2 border-emerald-400'
                : 'text-slate-400 hover:text-slate-300 hover:bg-slate-800/50'
            }`}
          >
            <span className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              Overview
            </span>
          </button>
          <button
            onClick={() => setActiveTab('files')}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === 'files'
                ? 'bg-slate-800 text-emerald-400 border-b-2 border-emerald-400'
                : 'text-slate-400 hover:text-slate-300 hover:bg-slate-800/50'
            }`}
          >
            <span className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Files
              <span className="bg-slate-700 text-slate-400 text-xs px-1.5 py-0.5 rounded">
                {summary?.total_files || 0}
              </span>
            </span>
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-6 bg-slate-950">
        {activeTab === 'overview' && summary && (
          <ModalityCounts
            total_files={summary.total_files}
            modality_counts={summary.modality_counts}
            kind_counts={summary.kind_counts}
            stage={summary.stage}
          />
        )}
        {activeTab === 'files' && (
          <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
            <FileTable files={files} loading={filesLoading} />
          </div>
        )}
      </main>
    </div>
  );
}

