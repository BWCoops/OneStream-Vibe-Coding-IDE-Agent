import { useState, useEffect } from 'react';
import { api } from '@/services/api';

interface RTMEntry {
  requirement_id: string;
  title: string;
  category: string;
  status: string;
  has_implementation: boolean;
  has_tests: boolean;
  has_deployment: boolean;
}

const COVERAGE_COLORS = {
  full: 'bg-[var(--success)]',
  partial: 'bg-[var(--warning)]',
  none: 'bg-[var(--error)]',
};

export function TraceabilityMatrix() {
  const [entries, setEntries] = useState<RTMEntry[]>([]);
  const [filter, setFilter] = useState('all');

  const coverage = (entry: RTMEntry): 'full' | 'partial' | 'none' => {
    const links = [entry.has_implementation, entry.has_tests, entry.has_deployment];
    const count = links.filter(Boolean).length;
    if (count === 3) return 'full';
    if (count > 0) return 'partial';
    return 'none';
  };

  const stats = {
    total: entries.length,
    full: entries.filter((e) => coverage(e) === 'full').length,
    partial: entries.filter((e) => coverage(e) === 'partial').length,
    gaps: entries.filter((e) => coverage(e) === 'none').length,
  };

  return (
    <div className="flex h-full flex-col bg-[var(--bg-primary)] p-4">
      <div className="mb-4">
        <h2 className="text-lg font-medium text-[var(--text-primary)]">Requirements Traceability Matrix</h2>
        <p className="text-xs text-[var(--text-secondary)]">
          Track requirements from capture through implementation, testing, and deployment
        </p>
      </div>

      {/* Coverage summary */}
      <div className="mb-4 grid grid-cols-4 gap-3">
        <div className="rounded bg-[var(--bg-surface)] p-3 text-center">
          <div className="text-2xl font-bold text-[var(--text-primary)]">{stats.total}</div>
          <div className="text-xs text-[var(--text-secondary)]">Requirements</div>
        </div>
        <div className="rounded bg-[var(--bg-surface)] p-3 text-center">
          <div className="text-2xl font-bold text-[var(--success)]">{stats.full}</div>
          <div className="text-xs text-[var(--text-secondary)]">Fully Covered</div>
        </div>
        <div className="rounded bg-[var(--bg-surface)] p-3 text-center">
          <div className="text-2xl font-bold text-[var(--warning)]">{stats.partial}</div>
          <div className="text-xs text-[var(--text-secondary)]">Partial</div>
        </div>
        <div className="rounded bg-[var(--bg-surface)] p-3 text-center">
          <div className="text-2xl font-bold text-[var(--error)]">{stats.gaps}</div>
          <div className="text-xs text-[var(--text-secondary)]">Gaps</div>
        </div>
      </div>

      {/* Matrix table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--text-secondary)]">
              <th className="pb-2">Req ID</th>
              <th className="pb-2">Title</th>
              <th className="pb-2">Category</th>
              <th className="pb-2 text-center">Code</th>
              <th className="pb-2 text-center">Tests</th>
              <th className="pb-2 text-center">Deployed</th>
              <th className="pb-2 text-center">Coverage</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.requirement_id} className="border-b border-[var(--border)]">
                <td className="py-2 font-mono text-[var(--accent)]">{entry.requirement_id}</td>
                <td className="py-2 text-[var(--text-primary)]">{entry.title}</td>
                <td className="py-2">{entry.category}</td>
                <td className="py-2 text-center">{entry.has_implementation ? 'Y' : '-'}</td>
                <td className="py-2 text-center">{entry.has_tests ? 'Y' : '-'}</td>
                <td className="py-2 text-center">{entry.has_deployment ? 'Y' : '-'}</td>
                <td className="py-2 text-center">
                  <span
                    className={`inline-block h-3 w-3 rounded-full ${COVERAGE_COLORS[coverage(entry)]}`}
                  />
                </td>
              </tr>
            ))}
            {entries.length === 0 && (
              <tr>
                <td colSpan={7} className="py-8 text-center text-[var(--text-secondary)]">
                  No requirements tracked yet. Requirements are auto-registered when code is generated from specifications.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
