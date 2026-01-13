interface EmptyStateProps {
  onAddDataset: () => void;
}

export function EmptyState({ onAddDataset }: EmptyStateProps) {
  return (
    <div className="flex-1 flex items-center justify-center bg-slate-950">
      <div className="text-center max-w-md">
        {/* Illustration */}
        <div className="relative mb-8">
          <div className="w-32 h-32 mx-auto rounded-3xl bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 flex items-center justify-center">
            <svg className="w-16 h-16 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          </div>
          {/* Decorative elements */}
          <div className="absolute -top-2 -right-2 w-6 h-6 rounded-lg bg-emerald-500/20 border border-emerald-500/30" />
          <div className="absolute -bottom-3 -left-3 w-8 h-8 rounded-full bg-cyan-500/10 border border-cyan-500/20" />
        </div>

        <h2 className="text-2xl font-semibold text-white mb-3">
          Select a Dataset
        </h2>
        <p className="text-slate-400 mb-8 leading-relaxed">
          Choose a dataset from the sidebar to view its details, or add a new one to get started with medical image analysis.
        </p>

        <button
          onClick={onAddDataset}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-900 font-medium hover:from-emerald-400 hover:to-cyan-400 transition-all shadow-lg shadow-emerald-500/20"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Your First Dataset
        </button>

        {/* Features */}
        <div className="mt-12 grid grid-cols-3 gap-6 text-left">
          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center mb-3">
              <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-sm font-medium text-white mb-1">Auto Detection</h3>
            <p className="text-xs text-slate-500">Automatically identifies modalities</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
            <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center mb-3">
              <svg className="w-4 h-4 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-sm font-medium text-white mb-1">Data Profiling</h3>
            <p className="text-xs text-slate-500">Comprehensive file analysis</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center mb-3">
              <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
              </svg>
            </div>
            <h3 className="text-sm font-medium text-white mb-1">Multi-format</h3>
            <p className="text-xs text-slate-500">DICOM, NIfTI, images & more</p>
          </div>
        </div>
      </div>
    </div>
  );
}













