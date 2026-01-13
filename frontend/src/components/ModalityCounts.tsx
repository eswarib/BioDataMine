interface ModalityCountsProps {
  total_files: number;
  modality_counts: Record<string, number>;
  kind_counts: Record<string, number>;
  stage?: string;
}

const MODALITY_COLORS: Record<string, string> = {
  CT: 'from-cyan-500 to-blue-500',
  MR: 'from-violet-500 to-purple-500',
  MRI: 'from-violet-500 to-purple-500',
  XR: 'from-emerald-500 to-teal-500',
  'X-Ray': 'from-emerald-500 to-teal-500',
  US: 'from-amber-500 to-orange-500',
  Ultrasound: 'from-amber-500 to-orange-500',
  PET: 'from-rose-500 to-pink-500',
  NM: 'from-fuchsia-500 to-purple-500',
  MG: 'from-lime-500 to-green-500',
  Mammography: 'from-lime-500 to-green-500',
  Fundus: 'from-sky-500 to-indigo-500',
  OCT: 'from-indigo-500 to-blue-500',
  Dermoscopy: 'from-orange-500 to-red-500',
  Histopathology: 'from-pink-500 to-rose-500',
  unknown: 'from-slate-500 to-slate-600',
};

const KIND_ICONS: Record<string, React.ReactNode> = {
  dicom: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  nifti: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
    </svg>
  ),
  image: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  unknown: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
};

export function ModalityCounts({ total_files, modality_counts, kind_counts, stage }: ModalityCountsProps) {
  const sortedModalities = Object.entries(modality_counts).sort(([, a], [, b]) => b - a);
  const totalModality = Object.values(modality_counts).reduce((sum, v) => sum + v, 0);

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-slate-850 rounded-xl p-4 border border-slate-700/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Total Files</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          </div>
          <span className="text-2xl font-bold text-white">{total_files.toLocaleString()}</span>
        </div>
        
        <div className="bg-slate-850 rounded-xl p-4 border border-slate-700/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Modalities</span>
            <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
              </svg>
            </div>
          </div>
          <span className="text-2xl font-bold text-white">{Object.keys(modality_counts).length}</span>
        </div>
        
        <div className="bg-slate-850 rounded-xl p-4 border border-slate-700/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">File Types</span>
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
          </div>
          <span className="text-2xl font-bold text-white">{Object.keys(kind_counts).length}</span>
        </div>

        <div className="bg-slate-850 rounded-xl p-4 border border-slate-700/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Stage</span>
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
          </div>
          <span className="text-lg font-semibold text-white capitalize">{stage || 'Unknown'}</span>
        </div>
      </div>

      {/* Modality Breakdown */}
      <div className="bg-slate-850 rounded-xl p-5 border border-slate-700/50">
        <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
          <svg className="w-4 h-4 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Modality Distribution
        </h3>
        
        {sortedModalities.length === 0 ? (
          <p className="text-slate-500 text-sm italic">No modality data available</p>
        ) : (
          <div className="space-y-3">
            {sortedModalities.map(([modality, count]) => {
              const percentage = totalModality > 0 ? (count / totalModality) * 100 : 0;
              const colorClass = MODALITY_COLORS[modality] || MODALITY_COLORS.unknown;
              
              return (
                <div key={modality}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-slate-300">{modality}</span>
                    <span className="text-xs text-slate-500">
                      {count.toLocaleString()} <span className="text-slate-600">({percentage.toFixed(1)}%)</span>
                    </span>
                  </div>
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full bg-gradient-to-r ${colorClass} rounded-full transition-all duration-500`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* File Types */}
      <div className="bg-slate-850 rounded-xl p-5 border border-slate-700/50">
        <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
          <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
          </svg>
          File Types
        </h3>
        
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(kind_counts).map(([kind, count]) => (
            <div
              key={kind}
              className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700/30"
            >
              <div className="w-9 h-9 rounded-lg bg-slate-700/50 flex items-center justify-center text-slate-400">
                {KIND_ICONS[kind] || KIND_ICONS.unknown}
              </div>
              <div>
                <span className="block text-sm font-medium text-slate-300 uppercase">{kind}</span>
                <span className="text-xs text-slate-500">{count.toLocaleString()} files</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

