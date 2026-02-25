import type { Tool } from '@modelcontextprotocol/sdk/types.js';

export const toolDefinitions: Tool[] = [
  {
    name: 'list_environments',
    description:
      'List all registered OneStream environments with their current status, platform version, and API version',
    inputSchema: {
      type: 'object',
      properties: {
        projectId: {
          type: 'string',
          description: 'Project ID to filter environments (optional)',
        },
        status: {
          type: 'string',
          enum: ['active', 'inactive', 'maintenance'],
          description: 'Filter by environment status (optional)',
        },
      },
      required: [],
    },
  },
  {
    name: 'promote_artifact',
    description:
      'Promote a business rule or artifact from a source environment to a target environment. Requires SOX-compliant approval if configured.',
    inputSchema: {
      type: 'object',
      properties: {
        sourceEnvironmentId: {
          type: 'string',
          description: 'Source environment ID to promote from',
        },
        targetEnvironmentId: {
          type: 'string',
          description: 'Target environment ID to promote to',
        },
        artifactType: {
          type: 'string',
          enum: [
            'business_rule',
            'dashboard',
            'cube_view',
            'data_adapter',
            'workflow',
            'member_list',
          ],
          description: 'Type of artifact to promote',
        },
        artifactId: {
          type: 'string',
          description: 'ID of the artifact to promote',
        },
        changeRequestId: {
          type: 'string',
          description: 'Associated change request ID for audit trail (optional)',
        },
        comment: {
          type: 'string',
          description: 'Promotion comment for audit log',
        },
      },
      required: [
        'sourceEnvironmentId',
        'targetEnvironmentId',
        'artifactType',
        'artifactId',
      ],
    },
  },
  {
    name: 'get_promotion_status',
    description:
      'Check the status of a promotion job, including validation results and deployment progress',
    inputSchema: {
      type: 'object',
      properties: {
        promotionId: {
          type: 'string',
          description: 'Promotion job ID returned by promote_artifact',
        },
      },
      required: ['promotionId'],
    },
  },
  {
    name: 'compare_environments',
    description:
      'Compare artifacts between two environments to identify differences, drift, and version mismatches',
    inputSchema: {
      type: 'object',
      properties: {
        sourceEnvironmentId: {
          type: 'string',
          description: 'Source environment ID (baseline)',
        },
        targetEnvironmentId: {
          type: 'string',
          description: 'Target environment ID to compare against',
        },
        artifactType: {
          type: 'string',
          enum: [
            'business_rule',
            'dashboard',
            'cube_view',
            'data_adapter',
            'workflow',
            'member_list',
            'all',
          ],
          description: 'Type of artifacts to compare (default: all)',
        },
        includeSourceDiff: {
          type: 'boolean',
          description:
            'Include source code diff for changed artifacts (default: false)',
        },
      },
      required: ['sourceEnvironmentId', 'targetEnvironmentId'],
    },
  },
  {
    name: 'rollback_promotion',
    description:
      'Rollback a previously promoted artifact to its prior version in the target environment. Creates an audit entry for the rollback action.',
    inputSchema: {
      type: 'object',
      properties: {
        promotionId: {
          type: 'string',
          description: 'Promotion job ID to rollback',
        },
        reason: {
          type: 'string',
          description: 'Reason for the rollback (required for audit trail)',
        },
      },
      required: ['promotionId', 'reason'],
    },
  },
];
