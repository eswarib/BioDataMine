import { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { DatasetView } from './components/DatasetView';
import { AddDatasetModal } from './components/AddDatasetModal';
import { EmptyState } from './components/EmptyState';
import { fetchDatasets } from './api/datasets';
import type { DatasetListItem } from './api/datasets';

function App() {
  const [datasets, setDatasets] = useState<DatasetListItem[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadDatasets = useCallback(async () => {
    try {
      const data = await fetchDatasets();
      setDatasets(data);
    } catch (err) {
      console.error('Failed to load datasets:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDatasets();
    // Poll for updates every 10 seconds (for processing datasets)
    const interval = setInterval(loadDatasets, 10000);
    return () => clearInterval(interval);
  }, [loadDatasets]);

  const handleAddSuccess = () => {
    loadDatasets();
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        datasets={datasets}
        selectedId={selectedDatasetId}
        onSelect={setSelectedDatasetId}
        onAddNew={() => setShowAddModal(true)}
        loading={loading}
      />
      
      {selectedDatasetId ? (
        <DatasetView datasetId={selectedDatasetId} />
      ) : (
        <EmptyState onAddDataset={() => setShowAddModal(true)} />
      )}

      <AddDatasetModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handleAddSuccess}
      />
    </div>
  );
}

export default App;
