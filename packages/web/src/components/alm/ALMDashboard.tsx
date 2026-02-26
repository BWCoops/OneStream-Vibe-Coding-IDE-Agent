import { useState, useEffect } from 'react';
import { api } from '@/services/api';

interface ChangeRequest {
  id: string;
  cr_number: string;
  title: string;
  type: string;
  status: string;
  requested_by: string;
  created_at: string;
}

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-gray-600',
  pending: 'bg-yellow-600',
  approved: 'bg-green-600',
  rejected: 'bg-red-600',
  deployed: 'bg-blue-600',
};

export function ALMDashboard() {
  const [changeRequests, setChangeRequests] = useState<ChangeRequest[]>([]);

  useEffect(() => {
    api
      .get<{ change_requests: ChangeRequest[] }>('/audit?entityType=change_request')
      .then((data) => setChangeRequests(data.change_requests ?? []))
      .catch(() => {});
  }, []);

  return (
    <div className="flex h-full flex-col bg-[var(--bg-primary)] p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-medium text-[var(--text-primary)]">ALM Dashboard</h2>
        <button
          className="rounded bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--bg-primary)]"
        >
          New Change Request
        </button>
      </div>

      {/* Status overview */}
      <div className="mb-4 grid grid-cols-4 gap-3">
        {['Draft', 'Pending', 'Approved', 'Deployed'].map((status) => (
          <div key={status} className="rounded bg-[var(--bg-surface)] p-3 text-center">
            <div className="text-2xl font-bold text-[var(--text-primary)]">
              {changeRequests.filter((cr) => cr.status === status.toLowerCase()).length}
            </div>
            <div className="text-xs text-[var(--text-secondary)]">{status}</div>
          </div>
        ))}
      </div>

      {/* Change request list */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--text-secondary)]">
              <th className="pb-2">CR#</th>
              <th className="pb-2">Title</th>
              <th className="pb-2">Type</th>
              <th className="pb-2">Status</th>
              <th className="pb-2">Requested By</th>
              <th className="pb-2">Created</th>
            </tr>
          </thead>
          <tbody>
            {changeRequests.map((cr) => (
              <tr key={cr.id} className="border-b border-[var(--border)] hover:bg-[var(--bg-surface)]">
                <td className="py-2 font-mono text-[var(--accent)]">{cr.cr_number}</td>
                <td className="py-2 text-[var(--text-primary)]">{cr.title}</td>
                <td className="py-2 capitalize">{cr.type}</td>
                <td className="py-2">
                  <span
                    className={`rounded px-2 py-0.5 text-xs text-white ${STATUS_STYLES[cr.status] ?? 'bg-gray-600'}`}
                  >
                    {cr.status}
                  </span>
                </td>
                <td className="py-2">{cr.requested_by}</td>
                <td className="py-2 text-[var(--text-secondary)]">
                  {new Date(cr.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
            {changeRequests.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-[var(--text-secondary)]">
                  No change requests found. Create one to start the approval workflow.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
