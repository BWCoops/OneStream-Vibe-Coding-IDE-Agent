import type { Tool } from '@modelcontextprotocol/sdk/types.js';

export const toolDefinitions: Tool[] = [
  {
    name: 'list_data_adapters',
    description: 'List configured data adapters in a OneStream environment',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        adapterType: {
          type: 'string',
          enum: [
            'sql_server',
            'oracle',
            'postgresql',
            'mysql',
            'csv',
            'excel',
            'xml',
            'json',
            'sap',
            'oracle_ebs',
            'workday',
            'dynamics',
            'rest_api',
            'soap',
            'odata',
            'azure_blob',
            's3',
            'sftp',
          ],
          description: 'Filter by adapter type (optional)',
        },
        status: {
          type: 'string',
          enum: ['active', 'inactive', 'error'],
          description: 'Filter by adapter status (optional)',
        },
      },
      required: ['environmentId'],
    },
  },
  {
    name: 'get_adapter_config',
    description: 'Get the full configuration of a specific data adapter including connection details, mappings, and schedule',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        adapterId: { type: 'string', description: 'Data adapter ID' },
        includeCredentials: {
          type: 'boolean',
          description: 'Whether to include masked credential references (default: false)',
        },
      },
      required: ['environmentId', 'adapterId'],
    },
  },
  {
    name: 'test_adapter_connection',
    description: 'Test the connectivity of a data adapter to verify the source or target system is reachable',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        adapterId: { type: 'string', description: 'Data adapter ID' },
        timeout: {
          type: 'number',
          description: 'Connection timeout in seconds (default: 30)',
        },
      },
      required: ['environmentId', 'adapterId'],
    },
  },
  {
    name: 'execute_data_load',
    description: 'Trigger a data load operation using a configured data adapter. Returns a load execution ID for tracking.',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        adapterId: { type: 'string', description: 'Data adapter ID to execute' },
        parameters: {
          type: 'object',
          description: 'Runtime parameters for the load operation (e.g., date range, filters)',
          properties: {
            startDate: { type: 'string', description: 'Start date for data extraction (ISO 8601)' },
            endDate: { type: 'string', description: 'End date for data extraction (ISO 8601)' },
            scenario: { type: 'string', description: 'OneStream scenario (e.g., "Actual", "Budget")' },
            year: { type: 'string', description: 'Target year' },
            period: { type: 'string', description: 'Target period' },
          },
        },
        dryRun: {
          type: 'boolean',
          description: 'If true, validate the load configuration without executing (default: false)',
        },
      },
      required: ['environmentId', 'adapterId'],
    },
  },
  {
    name: 'get_load_status',
    description: 'Check the status of a data load operation including progress, row counts, and any errors',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        executionId: { type: 'string', description: 'Load execution ID returned from execute_data_load' },
        includeDetails: {
          type: 'boolean',
          description: 'Whether to include detailed row-level error information (default: false)',
        },
      },
      required: ['environmentId', 'executionId'],
    },
  },
];
