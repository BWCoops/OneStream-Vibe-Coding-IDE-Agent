/**
 * OneStream REST API client with PAT authentication and platform version detection.
 */

export interface OneStreamConfig {
  baseUrl: string;
  apiVersion: string;
  pat: string;
}

export interface PlatformInfo {
  version: string;
  dotnetRuntime: 'net8.0' | 'net48';
  isLegacy: boolean;
}

export class OneStreamClient {
  private baseUrl: string;
  private apiVersion: string;
  private pat: string;
  private platformInfo: PlatformInfo | null = null;

  constructor(config: OneStreamConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.apiVersion = config.apiVersion;
    this.pat = config.pat;
  }

  private get apiBase(): string {
    return `${this.baseUrl}/OneStreamWeb/api/v${this.apiVersion}`;
  }

  private get headers(): Record<string, string> {
    return {
      Authorization: `Bearer ${this.pat}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  async detectPlatformVersion(): Promise<PlatformInfo> {
    if (this.platformInfo) return this.platformInfo;

    const response = await fetch(`${this.apiBase}/server/info`, {
      headers: this.headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to detect platform version: ${response.status}`);
    }

    const data = await response.json();
    const version = data.PlatformVersion ?? data.platformVersion ?? 'unknown';
    const major = parseInt(version.split('.')[0], 10);
    const isLegacy = major < 8;

    this.platformInfo = {
      version,
      dotnetRuntime: isLegacy ? 'net48' : 'net8.0',
      isLegacy,
    };

    return this.platformInfo;
  }

  async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.apiBase}${path}`, {
      method,
      headers: this.headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OneStream API error ${response.status}: ${errorText}`);
    }

    return response.json();
  }

  // Business Rules API
  async listRules(ruleType?: string): Promise<unknown[]> {
    const params = ruleType ? `?RuleType=${ruleType}` : '';
    return this.request('GET', `/businessrules${params}`);
  }

  async getRule(ruleId: string): Promise<unknown> {
    return this.request('GET', `/businessrules/${ruleId}`);
  }

  async createRule(rule: { Name: string; RuleType: string; SourceCode: string }): Promise<unknown> {
    return this.request('POST', '/businessrules', rule);
  }

  async updateRule(ruleId: string, sourceCode: string): Promise<unknown> {
    return this.request('PUT', `/businessrules/${ruleId}`, { SourceCode: sourceCode });
  }

  async compileRule(ruleId: string): Promise<unknown> {
    return this.request('POST', `/businessrules/${ruleId}/compile`);
  }
}
