import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { parse as parseYaml } from 'yaml';

interface DeprecatedApi {
  api: string;
  deprecated_in: string;
  replacement: string;
  severity: 'error' | 'warning';
  note: string;
}

let deprecatedApis: DeprecatedApi[] | null = null;

function loadDeprecatedApis(): DeprecatedApi[] {
  if (deprecatedApis) return deprecatedApis;
  try {
    const __dirname = dirname(fileURLToPath(import.meta.url));
    const filePath = resolve(__dirname, '../../../../knowledge-base/deprecated-apis/dotnet8-deprecated.yml');
    const content = readFileSync(filePath, 'utf-8');
    deprecatedApis = parseYaml(content) as DeprecatedApi[];
    return deprecatedApis;
  } catch {
    return [];
  }
}

function checkDeprecatedApis(sourceCode: string, platformVersion?: string): DeprecatedApi[] {
  const apis = loadDeprecatedApis();
  const major = platformVersion ? parseInt(platformVersion.split('.')[0], 10) : 8;

  return apis.filter((dep) => {
    const depMajor = parseInt(dep.deprecated_in.split('.')[0], 10);
    if (major < depMajor) return false;
    return sourceCode.includes(dep.api);
  });
}

export async function handleToolCall(
  name: string,
  args: Record<string, unknown>,
): Promise<{ content: Array<{ type: string; text: string }> }> {
  switch (name) {
    case 'list_rules': {
      // TODO: Resolve environment, create OneStreamClient, call listRules
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'not_connected',
              message: 'OneStream environment connection not yet configured. Set up environment in the project settings.',
            }),
          },
        ],
      };
    }

    case 'get_rule': {
      // TODO: Resolve environment, fetch rule source
      return {
        content: [{ type: 'text', text: JSON.stringify({ status: 'not_connected' }) }],
      };
    }

    case 'create_rule': {
      // TODO: Create rule via OneStream REST API
      return {
        content: [{ type: 'text', text: JSON.stringify({ status: 'not_connected' }) }],
      };
    }

    case 'update_rule': {
      // TODO: Update rule via OneStream REST API
      return {
        content: [{ type: 'text', text: JSON.stringify({ status: 'not_connected' }) }],
      };
    }

    case 'compile_rule': {
      // TODO: Send to Roslyn service for compilation
      return {
        content: [{ type: 'text', text: JSON.stringify({ status: 'not_connected' }) }],
      };
    }

    case 'check_deprecated': {
      const sourceCode = args.sourceCode as string;
      const platformVersion = args.platformVersion as string | undefined;
      const found = checkDeprecatedApis(sourceCode, platformVersion);
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              deprecated_apis_found: found.length,
              issues: found.map((d) => ({
                api: d.api,
                severity: d.severity,
                replacement: d.replacement,
                note: d.note,
              })),
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
