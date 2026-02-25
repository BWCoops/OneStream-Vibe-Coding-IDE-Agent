import type { Tool } from '@modelcontextprotocol/sdk/types.js';

export const toolDefinitions: Tool[] = [
  {
    name: 'list_rules',
    description: 'List business rules by type from a OneStream environment',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
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
          description: 'Filter by rule type (optional)',
        },
      },
      required: ['environmentId'],
    },
  },
  {
    name: 'get_rule',
    description: 'Get the full source code of a business rule',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        ruleId: { type: 'string', description: 'Business rule ID' },
      },
      required: ['environmentId', 'ruleId'],
    },
  },
  {
    name: 'create_rule',
    description: 'Create a new business rule in a OneStream environment',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        name: { type: 'string', description: 'Rule name' },
        ruleType: { type: 'string', description: 'Type of business rule' },
        sourceCode: { type: 'string', description: 'VB.NET or C# source code' },
      },
      required: ['environmentId', 'name', 'ruleType', 'sourceCode'],
    },
  },
  {
    name: 'update_rule',
    description: 'Update the source code of an existing business rule',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        ruleId: { type: 'string', description: 'Business rule ID' },
        sourceCode: { type: 'string', description: 'Updated VB.NET or C# source code' },
      },
      required: ['environmentId', 'ruleId', 'sourceCode'],
    },
  },
  {
    name: 'compile_rule',
    description: 'Compile and validate a business rule via the Roslyn service',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        ruleId: { type: 'string', description: 'Business rule ID' },
      },
      required: ['environmentId', 'ruleId'],
    },
  },
  {
    name: 'check_deprecated',
    description: 'Check source code for deprecated OneStream API usage based on platform version',
    inputSchema: {
      type: 'object',
      properties: {
        sourceCode: { type: 'string', description: 'Source code to analyze' },
        platformVersion: {
          type: 'string',
          description: 'Target platform version (e.g., "9.1.0" for .NET 8)',
        },
      },
      required: ['sourceCode'],
    },
  },
];
