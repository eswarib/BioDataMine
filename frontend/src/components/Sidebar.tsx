import type { DatasetListItem } from '../api/datasets';

interface SidebarProps {
  datasets: DatasetListItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAddNew: () => void;
  loading: boolean;
}

const StatusBadge = ({ status }: { status: string }) => {
  const styles = {
    ready: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    processing: 'bg-amber-500/20 text-amber-400 border-amber-500/30 animate-pulse',
    failed: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
  };
  
  return (
    <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border ${styles[status as keyof typeof styles] || styles.processing}`}>
      {status}
    </span>
  );
};

export function Sidebar({ datasets, selectedId, onSelect, onAddNew, loading }: SidebarProps) {
  return (
    <aside className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col h-screen">
      {/* Header */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-emerald-400 to-cyan-400 flex items-center justify-center">
            <svg className="w-5 h-5 text-slate-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white tracking-tight">BioDataMine</h1>
            <p className="text-xs text-slate-500">Medical Image Analysis</p>
          </div>
        </div>
      </div>

      {/* Add Dataset Button */}
      <div className="p-3 border-b border-slate-800">
        <button
          onClick={onAddNew}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-900 font-medium text-sm hover:from-emerald-400 hover:to-cyan-400 transition-all shadow-lg shadow-emerald-500/20"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Dataset
        </button>
      </div>

      {/* Search */}
      <div className="p-3 border-b border-slate-800">
        <div className="relative">
          <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search datasets..."
            className="w-full bg-slate-850 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition-all"
          />
        </div>
      </div>

      {/* Datasets List */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-2">
          <div className="flex items-center justify-between px-2 py-2 mb-1">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Datasets</span>
            <span className="text-xs text-slate-600">{datasets.length}</span>
          </div>
          
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-500">
              <div className="w-6 h-6 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-3" />
              <span className="text-sm">Loading...</span>
            </div>
          ) : datasets.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-500">
              <svg className="w-12 h-12 mb-3 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
              <p className="text-sm">No datasets yet</p>
              <p className="text-xs text-slate-600 mt-1">Click "Add Dataset" to get started</p>
            </div>
          ) : (
            <div className="space-y-1">
              {datasets.map((dataset) => (
                <button
                  key={dataset.dataset_id}
                  onClick={() => onSelect(dataset.dataset_id)}
                  className={`w-full text-left px-3 py-3 rounded-lg transition-all group ${
                    selectedId === dataset.dataset_id
                      ? 'bg-slate-800 border border-emerald-500/30'
                      : 'hover:bg-slate-850 border border-transparent'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <span className={`text-sm font-medium truncate ${
                      selectedId === dataset.dataset_id ? 'text-emerald-400' : 'text-slate-300 group-hover:text-white'
                    }`}>
                      {dataset.name}
                    </span>
                    <StatusBadge status={dataset.status} />
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      {dataset.summary.total_files} files
                    </span>
                    <span className="flex items-center gap-1">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                      </svg>
                      {Object.keys(dataset.summary.modality_counts).length} modalities
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-slate-800">
        <div className="flex items-center gap-2 text-xs text-slate-600">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Connected to API</span>
        </div>
      </div>
    </aside>
  );
}

