/**
 * Tool handlers for OneStream Metadata MCP server.
 *
 * Returns structured placeholder data since no live OneStream environment
 * connection is available. When connected, these handlers will use the
 * OneStreamClient to fetch real dimension/member data via the REST API.
 */

// -- Placeholder data representing typical OneStream dimension structures --

interface DimensionInfo {
  name: string;
  type: 'standard' | 'cube';
  memberCount: number;
  description: string;
}

interface MemberNode {
  name: string;
  description: string;
  level: number;
  isBase: boolean;
  children?: MemberNode[];
}

interface MemberProperties {
  name: string;
  dimensionName: string;
  description: string;
  alias: string;
  level: number;
  isBase: boolean;
  isCalculated: boolean;
  aggregationWeight: number;
  formula: string;
  dataStorage: string;
  parentName: string;
  customAttributes: Record<string, string>;
}

const PLACEHOLDER_DIMENSIONS: DimensionInfo[] = [
  { name: 'Account', type: 'standard', memberCount: 245, description: 'Chart of accounts hierarchy' },
  { name: 'Entity', type: 'standard', memberCount: 128, description: 'Legal entities and organizational units' },
  { name: 'Time', type: 'standard', memberCount: 60, description: 'Time periods (months, quarters, years)' },
  { name: 'Scenario', type: 'standard', memberCount: 12, description: 'Planning and reporting scenarios' },
  { name: 'Consolidation', type: 'standard', memberCount: 8, description: 'Consolidation members' },
  { name: 'Flow', type: 'standard', memberCount: 15, description: 'Flow dimension for movement analysis' },
  { name: 'Origin', type: 'standard', memberCount: 10, description: 'Data origin tracking' },
  { name: 'Intercompany', type: 'standard', memberCount: 130, description: 'Intercompany trading partner members' },
  { name: 'UD1', type: 'cube', memberCount: 35, description: 'User-defined dimension 1 - Product lines' },
  { name: 'UD2', type: 'cube', memberCount: 22, description: 'User-defined dimension 2 - Regions' },
  { name: 'UD3', type: 'cube', memberCount: 18, description: 'User-defined dimension 3 - Departments' },
  { name: 'UD4', type: 'cube', memberCount: 8, description: 'User-defined dimension 4 - Currency' },
  { name: 'UD5', type: 'cube', memberCount: 5, description: 'User-defined dimension 5 - Custom' },
  { name: 'UD6', type: 'cube', memberCount: 3, description: 'User-defined dimension 6 - Custom' },
  { name: 'UD7', type: 'cube', memberCount: 4, description: 'User-defined dimension 7 - Custom' },
  { name: 'UD8', type: 'cube', memberCount: 6, description: 'User-defined dimension 8 - Custom' },
];

const PLACEHOLDER_ACCOUNT_MEMBERS: MemberNode[] = [
  {
    name: 'TotalAccounts',
    description: 'Total Accounts',
    level: 0,
    isBase: false,
    children: [
      {
        name: 'IncomeStatement',
        description: 'Income Statement',
        level: 1,
        isBase: false,
        children: [
          {
            name: 'Revenue',
            description: 'Total Revenue',
            level: 2,
            isBase: false,
            children: [
              { name: 'ProductRevenue', description: 'Product Revenue', level: 3, isBase: true },
              { name: 'ServiceRevenue', description: 'Service Revenue', level: 3, isBase: true },
              { name: 'OtherRevenue', description: 'Other Revenue', level: 3, isBase: true },
            ],
          },
          {
            name: 'COGS',
            description: 'Cost of Goods Sold',
            level: 2,
            isBase: false,
            children: [
              { name: 'DirectMaterials', description: 'Direct Materials', level: 3, isBase: true },
              { name: 'DirectLabor', description: 'Direct Labor', level: 3, isBase: true },
              { name: 'ManufacturingOverhead', description: 'Manufacturing Overhead', level: 3, isBase: true },
            ],
          },
          {
            name: 'OpEx',
            description: 'Operating Expenses',
            level: 2,
            isBase: false,
            children: [
              { name: 'SGA', description: 'Selling, General & Administrative', level: 3, isBase: true },
              { name: 'RandD', description: 'Research & Development', level: 3, isBase: true },
              { name: 'Depreciation', description: 'Depreciation & Amortization', level: 3, isBase: true },
            ],
          },
        ],
      },
      {
        name: 'BalanceSheet',
        description: 'Balance Sheet',
        level: 1,
        isBase: false,
        children: [
          {
            name: 'Assets',
            description: 'Total Assets',
            level: 2,
            isBase: false,
            children: [
              { name: 'CurrentAssets', description: 'Current Assets', level: 3, isBase: true },
              { name: 'FixedAssets', description: 'Fixed Assets', level: 3, isBase: true },
              { name: 'IntangibleAssets', description: 'Intangible Assets', level: 3, isBase: true },
            ],
          },
          {
            name: 'Liabilities',
            description: 'Total Liabilities',
            level: 2,
            isBase: false,
            children: [
              { name: 'CurrentLiabilities', description: 'Current Liabilities', level: 3, isBase: true },
              { name: 'LongTermDebt', description: 'Long-Term Debt', level: 3, isBase: true },
            ],
          },
          {
            name: 'Equity',
            description: 'Shareholders Equity',
            level: 2,
            isBase: false,
            children: [
              { name: 'CommonStock', description: 'Common Stock', level: 3, isBase: true },
              { name: 'RetainedEarnings', description: 'Retained Earnings', level: 3, isBase: true },
            ],
          },
        ],
      },
      {
        name: 'Statistics',
        description: 'Statistical Accounts',
        level: 1,
        isBase: false,
        children: [
          { name: 'Headcount', description: 'Headcount', level: 2, isBase: true },
          { name: 'FTE', description: 'Full-Time Equivalents', level: 2, isBase: true },
        ],
      },
    ],
  },
];

const PLACEHOLDER_ENTITY_MEMBERS: MemberNode[] = [
  {
    name: 'TotalEntity',
    description: 'Total Entity',
    level: 0,
    isBase: false,
    children: [
      {
        name: 'Corporate',
        description: 'Corporate Headquarters',
        level: 1,
        isBase: false,
        children: [
          { name: 'Corp_Finance', description: 'Corporate Finance', level: 2, isBase: true },
          { name: 'Corp_IT', description: 'Corporate IT', level: 2, isBase: true },
          { name: 'Corp_HR', description: 'Corporate HR', level: 2, isBase: true },
        ],
      },
      {
        name: 'NorthAmerica',
        description: 'North America Region',
        level: 1,
        isBase: false,
        children: [
          { name: 'US_East', description: 'United States - East', level: 2, isBase: true },
          { name: 'US_West', description: 'United States - West', level: 2, isBase: true },
          { name: 'Canada', description: 'Canada', level: 2, isBase: true },
        ],
      },
      {
        name: 'Europe',
        description: 'Europe Region',
        level: 1,
        isBase: false,
        children: [
          { name: 'UK', description: 'United Kingdom', level: 2, isBase: true },
          { name: 'Germany', description: 'Germany', level: 2, isBase: true },
          { name: 'France', description: 'France', level: 2, isBase: true },
        ],
      },
      {
        name: 'AsiaPacific',
        description: 'Asia Pacific Region',
        level: 1,
        isBase: false,
        children: [
          { name: 'Japan', description: 'Japan', level: 2, isBase: true },
          { name: 'Australia', description: 'Australia', level: 2, isBase: true },
        ],
      },
    ],
  },
];

const PLACEHOLDER_SCENARIO_MEMBERS: MemberNode[] = [
  {
    name: 'TotalScenario',
    description: 'Total Scenario',
    level: 0,
    isBase: false,
    children: [
      { name: 'Actual', description: 'Actual results', level: 1, isBase: true },
      { name: 'Budget', description: 'Annual budget', level: 1, isBase: true },
      { name: 'Forecast', description: 'Rolling forecast', level: 1, isBase: true },
      { name: 'Forecast_Q1', description: 'Q1 Forecast', level: 1, isBase: true },
      { name: 'Forecast_Q2', description: 'Q2 Forecast', level: 1, isBase: true },
      { name: 'Forecast_Q3', description: 'Q3 Forecast', level: 1, isBase: true },
      { name: 'Forecast_Q4', description: 'Q4 Forecast', level: 1, isBase: true },
      { name: 'PriorYear', description: 'Prior year actual', level: 1, isBase: true },
    ],
  },
];

function getDimensionMembers(dimensionName: string): MemberNode[] {
  switch (dimensionName.toLowerCase()) {
    case 'account':
      return PLACEHOLDER_ACCOUNT_MEMBERS;
    case 'entity':
      return PLACEHOLDER_ENTITY_MEMBERS;
    case 'scenario':
      return PLACEHOLDER_SCENARIO_MEMBERS;
    default:
      return [
        {
          name: `Total${dimensionName}`,
          description: `Total ${dimensionName}`,
          level: 0,
          isBase: false,
          children: [
            { name: `${dimensionName}_Member1`, description: `${dimensionName} Member 1`, level: 1, isBase: true },
            { name: `${dimensionName}_Member2`, description: `${dimensionName} Member 2`, level: 1, isBase: true },
            { name: `${dimensionName}_Member3`, description: `${dimensionName} Member 3`, level: 1, isBase: true },
          ],
        },
      ];
  }
}

function flattenMembers(nodes: MemberNode[], dimensionName: string): Array<{ name: string; description: string; dimensionName: string; level: number; isBase: boolean }> {
  const results: Array<{ name: string; description: string; dimensionName: string; level: number; isBase: boolean }> = [];
  function walk(members: MemberNode[]) {
    for (const m of members) {
      results.push({
        name: m.name,
        description: m.description,
        dimensionName,
        level: m.level,
        isBase: m.isBase,
      });
      if (m.children) walk(m.children);
    }
  }
  walk(nodes);
  return results;
}

function filterChildren(nodes: MemberNode[], parentName: string | undefined, depth: number): MemberNode[] {
  if (!parentName) {
    return truncateDepth(nodes, depth);
  }

  const found = findMember(nodes, parentName);
  if (!found || !found.children) {
    return [];
  }
  return truncateDepth(found.children, depth);
}

function findMember(nodes: MemberNode[], name: string): MemberNode | null {
  for (const node of nodes) {
    if (node.name.toLowerCase() === name.toLowerCase()) return node;
    if (node.children) {
      const found = findMember(node.children, name);
      if (found) return found;
    }
  }
  return null;
}

function truncateDepth(nodes: MemberNode[], maxDepth: number, currentDepth: number = 0): MemberNode[] {
  if (currentDepth >= maxDepth) {
    return nodes.map((n) => ({ ...n, children: undefined }));
  }
  return nodes.map((n) => ({
    ...n,
    children: n.children ? truncateDepth(n.children, maxDepth, currentDepth + 1) : undefined,
  }));
}

function matchesPattern(name: string, pattern: string): boolean {
  const regex = new RegExp(
    '^' + pattern.replace(/\*/g, '.*').replace(/\?/g, '.') + '$',
    'i',
  );
  return regex.test(name);
}

export async function handleToolCall(
  name: string,
  args: Record<string, unknown>,
): Promise<{ content: Array<{ type: string; text: string }> }> {
  switch (name) {
    case 'list_dimensions': {
      const applicationType = args.applicationType as string | undefined;

      let dimensions = PLACEHOLDER_DIMENSIONS;
      if (applicationType && applicationType !== 'all') {
        dimensions = dimensions.filter((d) => d.type === applicationType);
      }

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'placeholder',
              environmentId: args.environmentId,
              message: 'Returning placeholder dimension list. Connect to a OneStream environment for live data.',
              dimensions,
              totalCount: dimensions.length,
            }, null, 2),
          },
        ],
      };
    }

    case 'get_dimension_members': {
      const dimensionName = args.dimensionName as string;
      const parentMember = args.parentMember as string | undefined;
      const depth = (args.depth as number) ?? 1;
      const includeDescriptions = (args.includeDescriptions as boolean) ?? false;

      const allMembers = getDimensionMembers(dimensionName);
      const members = filterChildren(allMembers, parentMember, depth);

      const stripDescriptions = (nodes: MemberNode[]): unknown[] =>
        nodes.map((n) => {
          const result: Record<string, unknown> = {
            name: n.name,
            level: n.level,
            isBase: n.isBase,
          };
          if (includeDescriptions) {
            result.description = n.description;
          }
          if (n.children) {
            result.children = stripDescriptions(n.children);
          }
          return result;
        });

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'placeholder',
              environmentId: args.environmentId,
              dimensionName,
              parentMember: parentMember ?? '(root)',
              depth,
              message: 'Returning placeholder member data. Connect to a OneStream environment for live data.',
              members: includeDescriptions ? members : stripDescriptions(members),
            }, null, 2),
          },
        ],
      };
    }

    case 'get_member_properties': {
      const dimensionName = args.dimensionName as string;
      const memberName = args.memberName as string;

      const allMembers = getDimensionMembers(dimensionName);
      const member = findMember(allMembers, memberName);

      if (!member) {
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                status: 'placeholder',
                environmentId: args.environmentId,
                error: `Member '${memberName}' not found in dimension '${dimensionName}' (placeholder data)`,
              }, null, 2),
            },
          ],
        };
      }

      // Find parent by walking the tree
      let parentName = '(none)';
      function findParent(nodes: MemberNode[], targetName: string, currentParent: string | null): string | null {
        for (const node of nodes) {
          if (node.name.toLowerCase() === targetName.toLowerCase()) return currentParent;
          if (node.children) {
            const result = findParent(node.children, targetName, node.name);
            if (result !== null) return result;
          }
        }
        return null;
      }
      const foundParent = findParent(allMembers, memberName, null);
      if (foundParent) parentName = foundParent;

      const properties: MemberProperties = {
        name: member.name,
        dimensionName,
        description: member.description,
        alias: member.description,
        level: member.level,
        isBase: member.isBase,
        isCalculated: !member.isBase,
        aggregationWeight: 1.0,
        formula: member.isBase ? '' : `Children(${member.name})`,
        dataStorage: member.isBase ? 'StoreData' : 'DynamicCalc',
        parentName,
        customAttributes: {
          CurrencyType: 'Local',
          AccountType: dimensionName === 'Account' ? 'Expense' : 'None',
        },
      };

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'placeholder',
              environmentId: args.environmentId,
              message: 'Returning placeholder member properties. Connect to a OneStream environment for live data.',
              properties,
            }, null, 2),
          },
        ],
      };
    }

    case 'search_members': {
      const searchPattern = args.searchPattern as string;
      const dimensionName = args.dimensionName as string | undefined;
      const maxResults = (args.maxResults as number) ?? 50;

      const dimensionsToSearch = dimensionName
        ? PLACEHOLDER_DIMENSIONS.filter((d) => d.name.toLowerCase() === dimensionName.toLowerCase())
        : PLACEHOLDER_DIMENSIONS;

      const results: Array<{ name: string; description: string; dimensionName: string; level: number; isBase: boolean }> = [];

      for (const dim of dimensionsToSearch) {
        const members = getDimensionMembers(dim.name);
        const flat = flattenMembers(members, dim.name);
        for (const m of flat) {
          if (matchesPattern(m.name, searchPattern) || matchesPattern(m.description, searchPattern)) {
            results.push(m);
            if (results.length >= maxResults) break;
          }
        }
        if (results.length >= maxResults) break;
      }

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'placeholder',
              environmentId: args.environmentId,
              searchPattern,
              dimensionName: dimensionName ?? '(all)',
              message: 'Returning placeholder search results. Connect to a OneStream environment for live data.',
              results,
              totalFound: results.length,
              truncated: results.length >= maxResults,
            }, null, 2),
          },
        ],
      };
    }

    case 'get_hierarchy': {
      const dimensionName = args.dimensionName as string;
      const rootMember = args.rootMember as string | undefined;
      const maxDepth = args.maxDepth as number | undefined;
      const includeProperties = (args.includeProperties as boolean) ?? false;

      const allMembers = getDimensionMembers(dimensionName);

      let hierarchy: MemberNode[];
      if (rootMember) {
        const root = findMember(allMembers, rootMember);
        hierarchy = root ? [root] : [];
      } else {
        hierarchy = allMembers;
      }

      if (maxDepth !== undefined) {
        hierarchy = truncateDepth(hierarchy, maxDepth);
      }

      // Optionally enrich with properties
      function enrichWithProperties(nodes: MemberNode[]): unknown[] {
        return nodes.map((n) => ({
          name: n.name,
          description: n.description,
          level: n.level,
          isBase: n.isBase,
          ...(includeProperties
            ? {
                dataStorage: n.isBase ? 'StoreData' : 'DynamicCalc',
                aggregationWeight: 1.0,
                formula: n.isBase ? '' : `Children(${n.name})`,
              }
            : {}),
          children: n.children ? enrichWithProperties(n.children) : undefined,
        }));
      }

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'placeholder',
              environmentId: args.environmentId,
              dimensionName,
              rootMember: rootMember ?? '(dimension root)',
              message: 'Returning placeholder hierarchy. Connect to a OneStream environment for live data.',
              hierarchy: includeProperties ? enrichWithProperties(hierarchy) : hierarchy,
            }, null, 2),
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
