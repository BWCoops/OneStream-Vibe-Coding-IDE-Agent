import { useState } from 'react';
import { useProjectStore } from '@/stores/projectStore';

interface PipelineStage {
  id: string;
  type: 'EXTRACT' | 'TRANSFORM' | 'VALIDATE' | 'LOAD';
  name: string;
  connectorType: string;
  dependencies: string[];
}

interface PipelineDefinition {
  name: string;
  description: string;
  stages: PipelineStage[];
}

const STAGE_COLORS: Record<string, string> = {
  EXTRACT: 'bg-blue-600',
  TRANSFORM: 'bg-purple-600',
  VALIDATE: 'bg-yellow-600',
  LOAD: 'bg-green-600',
};

export function PipelineDesigner() {
  const [pipeline, setPipeline] = useState<PipelineDefinition>({
    name: '',
    description: '',
    stages: [],
  });

  const addStage = (type: PipelineStage['type']) => {
    const newStage: PipelineStage = {
      id: `stage_${Date.now()}`,
      type,
      name: `${type} Stage ${pipeline.stages.length + 1}`,
      connectorType: type === 'EXTRACT' ? 'sql_server' : type === 'LOAD' ? 'sql_server' : '',
      dependencies: pipeline.stages.length > 0 ? [pipeline.stages[pipeline.stages.length - 1].id] : [],
    };
    setPipeline((p) => ({ ...p, stages: [...p.stages, newStage] }));
  };

  const removeStage = (id: string) => {
    setPipeline((p) => ({
      ...p,
      stages: p.stages
        .filter((s) => s.id !== id)
        .map((s) => ({ ...s, dependencies: s.dependencies.filter((d) => d !== id) })),
    }));
  };

  return (
    <div className="flex h-full flex-col bg-[var(--bg-primary)] p-4">
      <div className="mb-4">
        <h2 className="text-lg font-medium text-[var(--text-primary)]">Pipeline Designer</h2>
        <div className="mt-2 flex gap-2">
          <input
            type="text"
            placeholder="Pipeline name"
            value={pipeline.name}
            onChange={(e) => setPipeline((p) => ({ ...p, name: e.target.value }))}
            className="flex-1 rounded bg-[var(--bg-surface)] px-3 py-1.5 text-sm text-[var(--text-primary)] outline-none"
          />
        </div>
      </div>

      {/* Stage palette */}
      <div className="mb-4 flex gap-2">
        {(['EXTRACT', 'TRANSFORM', 'VALIDATE', 'LOAD'] as const).map((type) => (
          <button
            key={type}
            onClick={() => addStage(type)}
            className={`rounded px-3 py-1.5 text-xs font-medium text-white ${STAGE_COLORS[type]} hover:opacity-80`}
          >
            + {type}
          </button>
        ))}
      </div>

      {/* DAG visualization */}
      <div className="flex-1 overflow-auto rounded border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
        {pipeline.stages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-[var(--text-secondary)]">
            Add stages to build your data pipeline DAG
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {pipeline.stages.map((stage, idx) => (
              <div key={stage.id} className="flex items-center gap-3">
                {idx > 0 && (
                  <div className="flex w-8 justify-center text-[var(--text-secondary)]">|</div>
                )}
                <div
                  className={`flex items-center gap-2 rounded-lg px-4 py-3 text-white ${STAGE_COLORS[stage.type]}`}
                >
                  <span className="text-xs font-bold opacity-70">{stage.type}</span>
                  <input
                    type="text"
                    value={stage.name}
                    onChange={(e) =>
                      setPipeline((p) => ({
                        ...p,
                        stages: p.stages.map((s) =>
                          s.id === stage.id ? { ...s, name: e.target.value } : s,
                        ),
                      }))
                    }
                    className="bg-transparent text-sm outline-none placeholder-white/50"
                  />
                  <button
                    onClick={() => removeStage(stage.id)}
                    className="ml-2 text-xs opacity-50 hover:opacity-100"
                  >
                    x
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="mt-4 flex gap-2">
        <button className="rounded bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--bg-primary)] hover:bg-[var(--accent-hover)]">
          Save Pipeline
        </button>
        <button className="rounded bg-[var(--bg-surface)] px-4 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--border)]">
          Validate DAG
        </button>
      </div>
    </div>
  );
}
