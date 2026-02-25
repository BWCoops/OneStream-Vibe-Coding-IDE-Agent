export type BusinessRuleType =
  | 'finance_rule'
  | 'calculation_rule'
  | 'connector_br'
  | 'data_management'
  | 'dashboard_adapter'
  | 'dashboard_extender'
  | 'workflow_handler';

export type DotnetRuntime = 'net8.0' | 'net48';

export interface BusinessRule {
  id: string;
  projectId: string;
  type: BusinessRuleType;
  name: string;
  sourceCode: string;
  targetRuntime: DotnetRuntime;
  version: number;
  status: 'draft' | 'review' | 'approved' | 'deployed';
  gitSha: string | null;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface CompilationResult {
  success: boolean;
  errors: CompilationDiagnostic[];
  warnings: CompilationDiagnostic[];
  deprecatedApis: DeprecatedApiUsage[];
}

export interface CompilationDiagnostic {
  severity: 'error' | 'warning' | 'info';
  message: string;
  line: number;
  column: number;
  code: string;
}

export interface DeprecatedApiUsage {
  api: string;
  deprecatedIn: string;
  replacement: string;
  severity: 'error' | 'warning';
  line: number;
  note: string;
}

export interface PipelineDefinition {
  id: string;
  name: string;
  description: string;
  stages: PipelineStage[];
  schedule: PipelineSchedule | null;
  slaTargetMinutes: number | null;
}

export interface PipelineStage {
  id: string;
  type: 'EXTRACT' | 'TRANSFORM' | 'VALIDATE' | 'LOAD';
  connectorType: string;
  dependencies: string[];
  transformation: string;
  validationRules: string[];
}

export interface PipelineSchedule {
  type: 'cron' | 'event' | 'conditional';
  expression: string;
}
