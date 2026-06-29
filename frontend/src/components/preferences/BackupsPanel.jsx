import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../api/client'
import { Database, Download, RefreshCw, Trash2, HardDrive } from 'lucide-react'
import { formatDate, formatBytes } from '../../utils/formatters'
import { ConfirmDialog } from '../common/ConfirmDialog'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { useToast } from '../../hooks/useToast'

export const BackupsPanel = () => {
  const queryClient = useQueryClient()
  const { addToast } = useToast()
  
  const [restoreSnap, setRestoreSnap] = useState(null)
  const [deleteSnap, setDeleteSnap] = useState(null)

  const { data: backups, isLoading, refetch } = useQuery({
    queryKey: ['backups'],
    queryFn: () => apiClient.get('/api/admin/backups'),
  })

  const createBackup = useMutation({
    mutationFn: () => apiClient.post('/api/admin/backups'),
    onSuccess: () => {
      addToast({ title: 'Backup Started', message: 'Snapshot creation is in progress.', level: 'success' })
      refetch()
    },
    onError: (err) => {
      addToast({ title: 'Backup Failed', message: err.message, level: 'critical' })
    }
  })

  const restoreBackup = useMutation({
    mutationFn: (name) => apiClient.post(`/api/admin/backups/${name}/restore`, { target_indices: null }),
    onSuccess: () => {
      addToast({ title: 'Restore Complete', message: 'Indices restored successfully.', level: 'success' })
      setRestoreSnap(null)
      refetch()
    },
    onError: (err) => {
      addToast({ title: 'Restore Failed', message: err.message, level: 'critical' })
      setRestoreSnap(null)
    }
  })

  const deleteBackup = useMutation({
    mutationFn: (name) => apiClient.delete(`/api/admin/backups/${name}`),
    onSuccess: () => {
      addToast({ title: 'Backup Deleted', message: 'Snapshot removed successfully.', level: 'success' })
      setDeleteSnap(null)
      refetch()
    },
    onError: (err) => {
      addToast({ title: 'Delete Failed', message: err.message, level: 'critical' })
      setDeleteSnap(null)
    }
  })

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-[var(--bg-secondary)] p-6 rounded-xl border border-[var(--border)]">
        <div>
          <h3 className="text-lg font-semibold text-[var(--text-primary)]">Elasticsearch Snapshots</h3>
          <p className="text-[var(--text-secondary)] text-sm mt-1">
            Manage full cluster backups for disaster recovery. Automated backups run daily at 02:30 IST.
          </p>
        </div>
        <button
          onClick={() => createBackup.mutate()}
          disabled={createBackup.isPending}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          {createBackup.isPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <HardDrive className="h-4 w-4" />}
          Create Backup Now
        </button>
      </div>

      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-12 flex justify-center"><LoadingSpinner size="lg" /></div>
        ) : !backups || backups.length === 0 ? (
          <div className="p-12 text-center text-[var(--text-secondary)]">
            <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No backups found. Create one to get started.</p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--bg-tertiary)]">
                <th className="px-6 py-4 text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Snapshot Name</th>
                <th className="px-6 py-4 text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Created</th>
                <th className="px-6 py-4 text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Duration</th>
                <th className="px-6 py-4 text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {backups.map((snap) => (
                <tr key={snap.snapshot_name} className="hover:bg-[var(--bg-tertiary)]/50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-medium text-[var(--text-primary)]">{snap.snapshot_name}</div>
                    <div className="text-xs text-[var(--text-secondary)] mt-1">{snap.indices.length} indices</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${
                      snap.state === 'SUCCESS' ? 'bg-green-500/10 text-green-400' :
                      snap.state === 'IN_PROGRESS' ? 'bg-blue-500/10 text-blue-400' :
                      'bg-red-500/10 text-red-400'
                    }`}>
                      {snap.state}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-[var(--text-secondary)]">
                    {formatDate(new Date(snap.start_time))}
                  </td>
                  <td className="px-6 py-4 text-sm text-[var(--text-secondary)]">
                    {(snap.duration_ms / 1000).toFixed(1)}s
                  </td>
                  <td className="px-6 py-4 text-right space-x-2">
                    <button
                      onClick={() => setRestoreSnap(snap.snapshot_name)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-[var(--bg-tertiary)] hover:bg-orange-500/20 text-orange-400 rounded transition-colors"
                    >
                      <Download className="h-3.5 w-3.5" /> Restore
                    </button>
                    <button
                      onClick={() => setDeleteSnap(snap.snapshot_name)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-[var(--bg-tertiary)] hover:bg-red-500/20 text-red-400 rounded transition-colors"
                    >
                      <Trash2 className="h-3.5 w-3.5" /> Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <ConfirmDialog
        isOpen={!!restoreSnap}
        title="Restore Snapshot"
        message={`WARNING: This will close all active SOC indices and completely overwrite them with the state from "${restoreSnap}". All data ingested since this backup will be permanently lost. Are you absolutely sure?`}
        confirmText={restoreBackup.isPending ? "Restoring..." : "Yes, Restore Data"}
        confirmStyle="danger"
        onConfirm={() => restoreBackup.mutate(restoreSnap)}
        onCancel={() => setRestoreSnap(null)}
      />

      <ConfirmDialog
        isOpen={!!deleteSnap}
        title="Delete Snapshot"
        message={`Are you sure you want to permanently delete snapshot "${deleteSnap}"? This cannot be undone.`}
        confirmText={deleteBackup.isPending ? "Deleting..." : "Delete Snapshot"}
        confirmStyle="danger"
        onConfirm={() => deleteBackup.mutate(deleteSnap)}
        onCancel={() => setDeleteSnap(null)}
      />
    </div>
  )
}
