import type { FileListItem } from '../api/datasets';

interface FileTableProps {
  files: FileListItem[];
  loading: boolean;
}

const KIND_BADGES: Record<string, { bg: string; text: string }> = {
  dicom: { bg: 'bg-cyan-500/10 border-cyan-500/30', text: 'text-cyan-400' },
  nifti: { bg: 'bg-violet-500/10 border-violet-500/30', text: 'text-violet-400' },
  image: { bg: 'bg-emerald-500/10 border-emerald-500/30', text: 'text-emerald-400' },
  unknown: { bg: 'bg-slate-500/10 border-slate-500/30', text: 'text-slate-400' },
};

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatDims(dims: number[] | null): string {
  if (!dims || dims.length === 0) return '—';
  return dims.join(' × ');
}

export function FileTable({ files, loading }: FileTableProps) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-4" />
        <span className="text-slate-500 text-sm">Loading files...</span>
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-500">
        <svg className="w-16 h-16 mb-4 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p className="text-base">No files found</p>
        <p className="text-sm text-slate-600 mt-1">Files will appear here once processing completes</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-700/50">
            <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">File Path</th>
            <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Kind</th>
            <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Modality</th>
            <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Dimensions</th>
            <th className="text-right py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Size</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/50">
          {files.map((file, index) => {
            const kindStyle = KIND_BADGES[file.kind] || KIND_BADGES.unknown;
            return (
              <tr
                key={`${file.relpath}-${index}`}
                className="hover:bg-slate-800/30 transition-colors group"
              >
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-slate-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="text-sm text-slate-300 font-mono truncate max-w-md group-hover:text-white transition-colors" title={file.relpath}>
                      {file.relpath}
                    </span>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <span className={`inline-block px-2 py-0.5 rounded border text-xs font-medium uppercase ${kindStyle.bg} ${kindStyle.text}`}>
                    {file.kind}
                  </span>
                </td>
                <td className="py-3 px-4">
                  <span className="text-sm text-slate-300">{file.modality || '—'}</span>
                </td>
                <td className="py-3 px-4">
                  <span className="text-sm text-slate-400 font-mono">
                    {file.ndim ? `${file.ndim}D` : ''} {formatDims(file.dims)}
                  </span>
                </td>
                <td className="py-3 px-4 text-right">
                  <span className="text-sm text-slate-400">{formatBytes(file.size_bytes)}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

