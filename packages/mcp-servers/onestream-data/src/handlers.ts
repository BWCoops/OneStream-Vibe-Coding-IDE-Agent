// import { OneStreamClient } from '@onestream-ide/mcp-shared';

interface DataAdapter {
  id: string;
  name: string;
  adapterType: string;
  status: string;
  lastExecuted: string | null;
}

interface LoadExecution {
  executionId: string;
  adapterId: string;
  status: string;
  startedAt: string;
  completedAt: string | null;
  rowsProcessed: number;
  rowsFailed: number;
  errors: string[];
}

export async function handleToolCall(
  name: string,
  args: Record<string, unknown>,
): Promise<{ content: Array<{ type: string; text: string }> }> {
  switch (name) {
    case 'list_data_adapters': {
      const environmentId = args.environmentId as string;
      const adapterType = args.adapterType as string | undefined;
      const status = args.status as string | undefined;

      // TODO: Resolve environment, create OneStreamClient, call data adapter listing API
      // const client = await resolveClient(environmentId);
      // const adapters = await client.request<DataAdapter[]>('GET', '/dataadapters' + buildQuery({ adapterType, status }));

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'not_connected',
              message: 'OneStream environment connection not yet configured. Set up environment in the project settings.',
              environmentId,
              filters: {
                adapterType: adapterType ?? null,
                status: status ?? null,
              },
            }),
          },
        ],
      };
    }

    case 'get_adapter_config': {
      const environmentId = args.environmentId as string;
      const adapterId = args.adapterId as string;
      const includeCredentials = (args.includeCredentials as boolean) ?? false;

      // TODO: Resolve environment, fetch adapter configuration
      // const client = await resolveClient(environmentId);
      // const config = await client.request('GET', `/dataadapters/${adapterId}/config`);
      // If includeCredentials is false, strip credential fields from response

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'not_connected',
              message: 'OneStream environment connection not yet configured. Set up environment in the project settings.',
              environmentId,
              adapterId,
              includeCredentials,
            }),
          },
        ],
      };
    }

    case 'test_adapter_connection': {
      const environmentId = args.environmentId as string;
      const adapterId = args.adapterId as string;
      const timeout = (args.timeout as number) ?? 30;

      // TODO: Resolve environment, trigger connection test
      // const client = await resolveClient(environmentId);
      // const result = await client.request('POST', `/dataadapters/${adapterId}/test`, { Timeout: timeout });

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'not_connected',
              message: 'OneStream environment connection not yet configured. Set up environment in the project settings.',
              environmentId,
              adapterId,
              timeout,
            }),
          },
        ],
      };
    }

    case 'execute_data_load': {
      const environmentId = args.environmentId as string;
      const adapterId = args.adapterId as string;
      const parameters = args.parameters as Record<string, unknown> | undefined;
      const dryRun = (args.dryRun as boolean) ?? false;

      // TODO: Resolve environment, trigger data load execution
      // const client = await resolveClient(environmentId);
      // const payload = {
      //   AdapterId: adapterId,
      //   Parameters: parameters ? toPascalCase(parameters) : {},
      //   DryRun: dryRun,
      // };
      // const result = await client.request<LoadExecution>('POST', '/dataadapters/execute', payload);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'not_connected',
              message: 'OneStream environment connection not yet configured. Set up environment in the project settings.',
              environmentId,
              adapterId,
              parameters: parameters ?? null,
              dryRun,
            }),
          },
        ],
      };
    }

    case 'get_load_status': {
      const environmentId = args.environmentId as string;
      const executionId = args.executionId as string;
      const includeDetails = (args.includeDetails as boolean) ?? false;

      // TODO: Resolve environment, check load execution status
      // const client = await resolveClient(environmentId);
      // const status = await client.request<LoadExecution>('GET', `/dataadapters/executions/${executionId}`);
      // If includeDetails, also fetch row-level error details

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'not_connected',
              message: 'OneStream environment connection not yet configured. Set up environment in the project settings.',
              environmentId,
              executionId,
              includeDetails,
            }),
          },
        ],
      };
    }

    default:
      return {
        content: [{ type: 'text', text: `Unknown tool: ${name}` }],
      };
  }
}
