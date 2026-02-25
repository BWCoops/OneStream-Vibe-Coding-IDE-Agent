import type { Tool } from '@modelcontextprotocol/sdk/types.js';

export const toolDefinitions: Tool[] = [
  {
    name: 'list_dimensions',
    description: 'List available dimensions in a OneStream application (e.g., Account, Entity, Time, Scenario, UD1-UD8)',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        applicationType: {
          type: 'string',
          enum: ['standard', 'cube', 'all'],
          description: 'Filter by dimension application type (optional, defaults to all)',
        },
      },
      required: ['environmentId'],
    },
  },
  {
    name: 'get_dimension_members',
    description: 'Get members of a dimension with their hierarchy relationships, including parent-child structure',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        dimensionName: {
          type: 'string',
          description: 'Name of the dimension (e.g., Account, Entity, Scenario)',
        },
        parentMember: {
          type: 'string',
          description: 'Parent member name to get children of (optional, defaults to root)',
        },
        depth: {
          type: 'number',
          description: 'Depth of hierarchy to retrieve (optional, defaults to 1 for immediate children)',
        },
        includeDescriptions: {
          type: 'boolean',
          description: 'Include member descriptions in the response (optional, defaults to false)',
        },
      },
      required: ['environmentId', 'dimensionName'],
    },
  },
  {
    name: 'get_member_properties',
    description: 'Get all properties of a specific dimension member including aliases, formulas, and custom attributes',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        dimensionName: {
          type: 'string',
          description: 'Name of the dimension the member belongs to',
        },
        memberName: {
          type: 'string',
          description: 'Name of the member to retrieve properties for',
        },
      },
      required: ['environmentId', 'dimensionName', 'memberName'],
    },
  },
  {
    name: 'search_members',
    description: 'Search for dimension members by name or pattern across one or all dimensions',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        searchPattern: {
          type: 'string',
          description: 'Search pattern (supports * and ? wildcards)',
        },
        dimensionName: {
          type: 'string',
          description: 'Restrict search to a specific dimension (optional, searches all dimensions if omitted)',
        },
        maxResults: {
          type: 'number',
          description: 'Maximum number of results to return (optional, defaults to 50)',
        },
      },
      required: ['environmentId', 'searchPattern'],
    },
  },
  {
    name: 'get_hierarchy',
    description: 'Get the full hierarchy tree for a dimension, returned as a nested structure suitable for tree visualization',
    inputSchema: {
      type: 'object',
      properties: {
        environmentId: { type: 'string', description: 'Target environment ID' },
        dimensionName: {
          type: 'string',
          description: 'Name of the dimension to retrieve the hierarchy for',
        },
        rootMember: {
          type: 'string',
          description: 'Root member to start the hierarchy from (optional, defaults to dimension root)',
        },
        maxDepth: {
          type: 'number',
          description: 'Maximum depth of hierarchy to retrieve (optional, defaults to full depth)',
        },
        includeProperties: {
          type: 'boolean',
          description: 'Include member properties in each node (optional, defaults to false)',
        },
      },
      required: ['environmentId', 'dimensionName'],
    },
  },
];
