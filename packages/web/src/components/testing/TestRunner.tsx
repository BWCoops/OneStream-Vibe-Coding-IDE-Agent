import { useState } from 'react';
import { api } from '@/services/api';

interface TestResult {
  test_id: string;
  name: string;
  status: 'pass' | 'fail' | 'error' | 'pending';
  error?: string;
}

interface TestRunSummary {
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  results: TestResult[];
}

const STATUS_COLORS: Record<string, string> = {
  pass: 'text-[var(--success)]',
  fail: 'text-[var(--error)]',
  error: 'text-[var(--error)]',
  pending: 'text-[var(--text-secondary)]',
};

const STATUS_ICONS: Record<string, string> = {
  pass: 'P',
  fail: 'F',
  error: 'E',
  pending: '-',
};

export function TestRunner() {
  const [running, setRunning] = useState(false);
  const [summary, setSummary] = useState<TestRunSummary | null>(null);

  const runTests = async () => {
    setRunning(true);
    try {
      const result = await api.post<TestRunSummary>('/rules/current/test', {
        test_type: 'unit',
      });
      setSummary(result);
    } catch {
      // Error handled by API layer
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex h-full flex-col bg-[var(--bg-primary)] p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-medium text-[var(--text-primary)]">Test Runner</h2>
        <button
          onClick={runTests}
          disabled={running}
          className="rounded bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--bg-primary)] hover:bg-[var(--accent-hover)] disabled:opacity-50"
        >
          {running ? 'Running...' : 'Run Tests'}
        </button>
      </div>

      {summary && (
        <>
          {/* Summary bar */}
          <div className="mb-4 flex gap-4 rounded bg-[var(--bg-surface)] p-3">
            <div className="text-sm">
              <span className="text-[var(--text-secondary)]">Total: </span>
              <span className="font-medium">{summary.total}</span>
            </div>
            <div className="text-sm">
              <span className="text-[var(--text-secondary)]">Passed: </span>
              <span className="font-medium text-[var(--success)]">{summary.passed}</span>
            </div>
            <div className="text-sm">
              <span className="text-[var(--text-secondary)]">Failed: </span>
              <span className="font-medium text-[var(--error)]">{summary.failed}</span>
            </div>
            <div className="text-sm">
              <span className="text-[var(--text-secondary)]">Rate: </span>
              <span className="font-medium">{summary.pass_rate.toFixed(0)}%</span>
            </div>
          </div>

          {/* Results list */}
          <div className="flex-1 overflow-auto">
            {summary.results.map((result) => (
              <div
                key={result.test_id}
                className="flex items-center gap-3 border-b border-[var(--border)] py-2"
              >
                <span
                  className={`flex h-6 w-6 items-center justify-center rounded text-xs font-bold ${STATUS_COLORS[result.status]}`}
                >
                  {STATUS_ICONS[result.status]}
                </span>
                <div className="flex-1">
                  <div className="text-sm text-[var(--text-primary)]">{result.name}</div>
                  {result.error && (
                    <div className="text-xs text-[var(--error)]">{result.error}</div>
                  )}
                </div>
                <span className={`text-xs ${STATUS_COLORS[result.status]}`}>{result.status}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {!summary && !running && (
        <div className="flex flex-1 items-center justify-center text-sm text-[var(--text-secondary)]">
          Click "Run Tests" to execute test cases against the current rule
        </div>
      )}
    </div>
  );
}
