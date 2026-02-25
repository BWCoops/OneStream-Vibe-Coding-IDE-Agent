import type { Tool } from '@modelcontextprotocol/sdk/types.js';

export const toolDefinitions: Tool[] = [
  {
    name: 'validate_syntax',
    description: 'Validate VB.NET or C# syntax without full compilation. Performs lexical and syntactic analysis to detect syntax errors quickly.',
    inputSchema: {
      type: 'object',
      properties: {
        sourceCode: { type: 'string', description: 'VB.NET or C# source code to validate' },
        language: {
          type: 'string',
          enum: ['vb.net', 'csharp'],
          description: 'Programming language of the source code (default: vb.net)',
        },
        platformVersion: {
          type: 'string',
          description: 'Target platform version (e.g., "9.1.0" for .NET 8, "7.5.0" for .NET Framework 4.8)',
        },
      },
      required: ['sourceCode'],
    },
  },
  {
    name: 'compile_code',
    description: 'Full Roslyn compilation of VB.NET or C# code. Returns compilation diagnostics including errors, warnings, and info messages with line/column positions.',
    inputSchema: {
      type: 'object',
      properties: {
        sourceCode: { type: 'string', description: 'VB.NET or C# source code to compile' },
        language: {
          type: 'string',
          enum: ['vb.net', 'csharp'],
          description: 'Programming language of the source code (default: vb.net)',
        },
        platformVersion: {
          type: 'string',
          description: 'Target platform version to determine .NET runtime and available APIs',
        },
        references: {
          type: 'array',
          items: { type: 'string' },
          description: 'Additional assembly references required for compilation',
        },
      },
      required: ['sourceCode'],
    },
  },
  {
    name: 'check_deprecated_apis',
    description: 'Check source code for deprecated OneStream API usage based on the target platform version. Returns all deprecated API calls found with their replacements.',
    inputSchema: {
      type: 'object',
      properties: {
        sourceCode: { type: 'string', description: 'Source code to analyze for deprecated API usage' },
        platformVersion: {
          type: 'string',
          description: 'Target platform version (e.g., "9.1.0" for .NET 8). Defaults to latest.',
        },
      },
      required: ['sourceCode'],
    },
  },
  {
    name: 'validate_rule_structure',
    description: 'Validate that a business rule follows OneStream best practices: structured Try/Catch/Finally, BRApi.ErrorLog.LogMessage for error reporting, parameterised configuration via substitution variables, and inline documentation.',
    inputSchema: {
      type: 'object',
      properties: {
        sourceCode: { type: 'string', description: 'Business rule source code to validate' },
        ruleType: {
          type: 'string',
          enum: [
            'finance_rule',
            'calculation_rule',
            'connector_br',
            'data_management',
            'dashboard_adapter',
            'dashboard_extender',
            'workflow_handler',
          ],
          description: 'Type of business rule (affects which structural checks are applied)',
        },
        requirementId: {
          type: 'string',
          description: 'Requirement ID for cross-reference validation in inline documentation',
        },
      },
      required: ['sourceCode'],
    },
  },
  {
    name: 'analyze_complexity',
    description: 'Analyze code complexity metrics including cyclomatic complexity, nesting depth, lines of code, and method count. Returns a complexity report with recommendations.',
    inputSchema: {
      type: 'object',
      properties: {
        sourceCode: { type: 'string', description: 'Source code to analyze' },
        language: {
          type: 'string',
          enum: ['vb.net', 'csharp'],
          description: 'Programming language of the source code (default: vb.net)',
        },
        thresholds: {
          type: 'object',
          description: 'Custom thresholds for complexity warnings',
          properties: {
            maxCyclomaticComplexity: {
              type: 'number',
              description: 'Maximum cyclomatic complexity per method before warning (default: 10)',
            },
            maxNestingDepth: {
              type: 'number',
              description: 'Maximum nesting depth before warning (default: 4)',
            },
            maxMethodLines: {
              type: 'number',
              description: 'Maximum lines per method before warning (default: 50)',
            },
          },
        },
      },
      required: ['sourceCode'],
    },
  },
];
