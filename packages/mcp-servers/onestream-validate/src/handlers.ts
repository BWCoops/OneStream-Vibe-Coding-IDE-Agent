import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { parse as parseYaml } from 'yaml';

// --- Deprecated API detection (shared with onestream-rules, factored for reuse) ---

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

// --- Rule structure validation ---

interface StructureCheck {
  name: string;
  passed: boolean;
  severity: 'error' | 'warning' | 'info';
  message: string;
}

function validateRuleStructureChecks(
  sourceCode: string,
  ruleType?: string,
  requirementId?: string,
): StructureCheck[] {
  const checks: StructureCheck[] = [];

  // Check for Try/Catch/Finally block
  const hasTryCatch =
    /\bTry\b/i.test(sourceCode) &&
    /\bCatch\b/i.test(sourceCode) &&
    /\bFinally\b/i.test(sourceCode);
  checks.push({
    name: 'try_catch_finally',
    passed: hasTryCatch,
    severity: 'error',
    message: hasTryCatch
      ? 'Structured Try/Catch/Finally block found'
      : 'Missing structured Try/Catch/Finally block. All business rules must include error handling.',
  });

  // Check for error logging via BRApi.ErrorLog.LogMessage
  const hasErrorLogging = /BRApi\.ErrorLog\.LogMessage/i.test(sourceCode);
  checks.push({
    name: 'error_logging',
    passed: hasErrorLogging,
    severity: 'error',
    message: hasErrorLogging
      ? 'BRApi.ErrorLog.LogMessage usage found'
      : 'Missing BRApi.ErrorLog.LogMessage. All errors must be logged via the OneStream error log API.',
  });

  // Check for step identification in error handling
  const hasStepIdentification =
    /\bstep\b/i.test(sourceCode) || /\bstepDescription\b/i.test(sourceCode) || /\bcurrentStep\b/i.test(sourceCode);
  checks.push({
    name: 'step_identification',
    passed: hasStepIdentification,
    severity: 'warning',
    message: hasStepIdentification
      ? 'Step identification found in error handling'
      : 'Consider adding step identification variables for better error diagnostics.',
  });

  // Check for parameterised configuration via substitution variables
  const hasSubstitutionVars =
    /api\.Parser\.SubstituteTokens/i.test(sourceCode) ||
    /BRApi\.Finance\.GetSubstitutionVariableValue/i.test(sourceCode) ||
    /GetSubstitutionVariableValue/i.test(sourceCode);
  checks.push({
    name: 'substitution_variables',
    passed: hasSubstitutionVars,
    severity: 'warning',
    message: hasSubstitutionVars
      ? 'Substitution variable usage found'
      : 'Consider using substitution variables for parameterised configuration instead of hardcoded values.',
  });

  // Check for inline documentation
  const hasDocumentation = /'''/.test(sourceCode) || /\/\/\//.test(sourceCode) || /'.*requirement/i.test(sourceCode);
  checks.push({
    name: 'inline_documentation',
    passed: hasDocumentation,
    severity: 'info',
    message: hasDocumentation
      ? 'Inline documentation found'
      : 'Add inline documentation with requirement ID cross-references.',
  });

  // Check for requirement ID cross-reference if requirementId was provided
  if (requirementId) {
    const hasRequirementRef = sourceCode.includes(requirementId);
    checks.push({
      name: 'requirement_cross_reference',
      passed: hasRequirementRef,
      severity: 'warning',
      message: hasRequirementRef
        ? `Requirement ID "${requirementId}" cross-reference found`
        : `Requirement ID "${requirementId}" not found in source code. Add cross-reference in inline documentation.`,
    });
  }

  return checks;
}

// --- Complexity analysis ---

interface ComplexityResult {
  totalLines: number;
  codeLines: number;
  commentLines: number;
  blankLines: number;
  methodCount: number;
  maxNestingDepth: number;
  estimatedCyclomaticComplexity: number;
  warnings: string[];
}

function analyzeCodeComplexity(
  sourceCode: string,
  language: string,
  thresholds?: { maxCyclomaticComplexity?: number; maxNestingDepth?: number; maxMethodLines?: number },
): ComplexityResult {
  const maxCC = thresholds?.maxCyclomaticComplexity ?? 10;
  const maxNesting = thresholds?.maxNestingDepth ?? 4;
  const maxMethodLns = thresholds?.maxMethodLines ?? 50;

  const lines = sourceCode.split('\n');
  const totalLines = lines.length;
  let codeLines = 0;
  let commentLines = 0;
  let blankLines = 0;

  const isVb = language === 'vb.net';
  const commentPrefix = isVb ? "'" : '//';

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === '') {
      blankLines++;
    } else if (trimmed.startsWith(commentPrefix) || trimmed.startsWith('REM ')) {
      commentLines++;
    } else {
      codeLines++;
    }
  }

  // Estimate method count
  let methodCount = 0;
  if (isVb) {
    const methodMatches = sourceCode.match(/\b(Sub|Function)\s+\w+/gi);
    methodCount = methodMatches ? methodMatches.length : 0;
  } else {
    const methodMatches = sourceCode.match(/\b(void|string|int|bool|Task|object|var)\s+\w+\s*\(/g);
    methodCount = methodMatches ? methodMatches.length : 0;
  }

  // Estimate max nesting depth
  let currentNesting = 0;
  let maxNestingDepth = 0;
  const nestOpen = isVb
    ? /\b(If|For|While|Do|Select|Try|Using|With)\b/gi
    : /\{/g;
  const nestClose = isVb
    ? /\b(End If|End Select|End Try|End Using|End With|Next|Loop|Wend)\b/gi
    : /\}/g;

  for (const line of lines) {
    const trimmed = line.trim();
    const opens = trimmed.match(nestOpen)?.length ?? 0;
    const closes = trimmed.match(nestClose)?.length ?? 0;
    currentNesting += opens - closes;
    if (currentNesting > maxNestingDepth) {
      maxNestingDepth = currentNesting;
    }
    // Reset regex lastIndex for global patterns
    nestOpen.lastIndex = 0;
    nestClose.lastIndex = 0;
  }

  // Estimate cyclomatic complexity (count decision points)
  const decisionPatterns = isVb
    ? /\b(If|ElseIf|Case|While|For|AndAlso|OrElse|Catch)\b/gi
    : /\b(if|else\s+if|case|while|for|&&|\|\||catch)\b/g;
  const decisions = sourceCode.match(decisionPatterns)?.length ?? 0;
  const estimatedCyclomaticComplexity = decisions + 1; // Base complexity of 1

  // Generate warnings
  const warnings: string[] = [];
  if (estimatedCyclomaticComplexity > maxCC) {
    warnings.push(
      `Cyclomatic complexity (${estimatedCyclomaticComplexity}) exceeds threshold (${maxCC}). Consider refactoring into smaller methods.`,
    );
  }
  if (maxNestingDepth > maxNesting) {
    warnings.push(
      `Maximum nesting depth (${maxNestingDepth}) exceeds threshold (${maxNesting}). Consider extracting nested logic into helper methods.`,
    );
  }
  if (methodCount === 0 && codeLines > maxMethodLns) {
    warnings.push(
      `Code has ${codeLines} lines with no clear method decomposition. Consider breaking into multiple methods.`,
    );
  }

  return {
    totalLines,
    codeLines,
    commentLines,
    blankLines,
    methodCount,
    maxNestingDepth,
    estimatedCyclomaticComplexity,
    warnings,
  };
}

// --- Main handler ---

export async function handleToolCall(
  name: string,
  args: Record<string, unknown>,
): Promise<{ content: Array<{ type: string; text: string }> }> {
  switch (name) {
    case 'validate_syntax': {
      const sourceCode = args.sourceCode as string;
      const language = (args.language as string) ?? 'vb.net';
      const platformVersion = args.platformVersion as string | undefined;

      // TODO: Send to Roslyn service for syntax-only validation
      // const roslynEndpoint = process.env.ROSLYN_SERVICE_URL ?? 'http://localhost:5100';
      // const response = await fetch(`${roslynEndpoint}/api/validate/syntax`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ SourceCode: sourceCode, Language: language, PlatformVersion: platformVersion }),
      // });

      // Perform basic local checks as a fallback until Roslyn service is connected
      const issues: Array<{ line: number; message: string; severity: string }> = [];
      const lines = sourceCode.split('\n');

      if (language === 'vb.net') {
        // Check for unmatched block structures
        let ifCount = 0;
        let endIfCount = 0;
        let forCount = 0;
        let nextCount = 0;
        let tryCount = 0;
        let endTryCount = 0;

        for (let i = 0; i < lines.length; i++) {
          const trimmed = lines[i].trim().toUpperCase();
          if (/^\s*IF\b.*\bTHEN\s*$/i.test(lines[i].trim())) ifCount++;
          if (/^\s*END\s+IF\b/i.test(trimmed)) endIfCount++;
          if (/^\s*FOR\b/i.test(trimmed)) forCount++;
          if (/^\s*NEXT\b/i.test(trimmed)) nextCount++;
          if (/^\s*TRY\b/i.test(trimmed)) tryCount++;
          if (/^\s*END\s+TRY\b/i.test(trimmed)) endTryCount++;
        }

        if (ifCount !== endIfCount) {
          issues.push({
            line: 0,
            message: `Mismatched If/End If blocks: ${ifCount} If vs ${endIfCount} End If`,
            severity: 'error',
          });
        }
        if (forCount !== nextCount) {
          issues.push({
            line: 0,
            message: `Mismatched For/Next blocks: ${forCount} For vs ${nextCount} Next`,
            severity: 'error',
          });
        }
        if (tryCount !== endTryCount) {
          issues.push({
            line: 0,
            message: `Mismatched Try/End Try blocks: ${tryCount} Try vs ${endTryCount} End Try`,
            severity: 'error',
          });
        }
      } else {
        // C# basic brace matching
        let braceCount = 0;
        for (let i = 0; i < lines.length; i++) {
          for (const ch of lines[i]) {
            if (ch === '{') braceCount++;
            if (ch === '}') braceCount--;
          }
          if (braceCount < 0) {
            issues.push({
              line: i + 1,
              message: 'Unexpected closing brace',
              severity: 'error',
            });
          }
        }
        if (braceCount > 0) {
          issues.push({
            line: lines.length,
            message: `${braceCount} unclosed brace(s) detected`,
            severity: 'error',
          });
        }
      }

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              valid: issues.filter((i) => i.severity === 'error').length === 0,
              language,
              platformVersion: platformVersion ?? null,
              issues,
              note: 'Basic syntax validation performed locally. Full Roslyn validation available when Roslyn service is connected.',
            }),
          },
        ],
      };
    }

    case 'compile_code': {
      const sourceCode = args.sourceCode as string;
      const language = (args.language as string) ?? 'vb.net';
      const platformVersion = args.platformVersion as string | undefined;
      const references = args.references as string[] | undefined;

      // TODO: Send to Roslyn service for full compilation
      // const roslynEndpoint = process.env.ROSLYN_SERVICE_URL ?? 'http://localhost:5100';
      // const response = await fetch(`${roslynEndpoint}/api/compile`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({
      //     SourceCode: sourceCode,
      //     Language: language,
      //     PlatformVersion: platformVersion,
      //     References: references,
      //   }),
      // });
      // const result = await response.json();

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'roslyn_service_not_connected',
              message: 'Roslyn compilation service is not yet connected. Configure ROSLYN_SERVICE_URL environment variable.',
              language,
              platformVersion: platformVersion ?? null,
              references: references ?? [],
              sourceCodeLength: sourceCode.length,
            }),
          },
        ],
      };
    }

    case 'check_deprecated_apis': {
      const sourceCode = args.sourceCode as string;
      const platformVersion = args.platformVersion as string | undefined;
      const found = checkDeprecatedApis(sourceCode, platformVersion);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              deprecated_apis_found: found.length,
              platform_version: platformVersion ?? 'latest',
              issues: found.map((d) => ({
                api: d.api,
                severity: d.severity,
                deprecated_in: d.deprecated_in,
                replacement: d.replacement,
                note: d.note,
              })),
            }),
          },
        ],
      };
    }

    case 'validate_rule_structure': {
      const sourceCode = args.sourceCode as string;
      const ruleType = args.ruleType as string | undefined;
      const requirementId = args.requirementId as string | undefined;

      const checks = validateRuleStructureChecks(sourceCode, ruleType, requirementId);
      const errorCount = checks.filter((c) => !c.passed && c.severity === 'error').length;
      const warningCount = checks.filter((c) => !c.passed && c.severity === 'warning').length;

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              valid: errorCount === 0,
              ruleType: ruleType ?? 'unknown',
              summary: {
                total_checks: checks.length,
                passed: checks.filter((c) => c.passed).length,
                errors: errorCount,
                warnings: warningCount,
              },
              checks,
            }),
          },
        ],
      };
    }

    case 'analyze_complexity': {
      const sourceCode = args.sourceCode as string;
      const language = (args.language as string) ?? 'vb.net';
      const thresholds = args.thresholds as
        | { maxCyclomaticComplexity?: number; maxNestingDepth?: number; maxMethodLines?: number }
        | undefined;

      const result = analyzeCodeComplexity(sourceCode, language, thresholds);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              language,
              metrics: {
                total_lines: result.totalLines,
                code_lines: result.codeLines,
                comment_lines: result.commentLines,
                blank_lines: result.blankLines,
                method_count: result.methodCount,
                max_nesting_depth: result.maxNestingDepth,
                estimated_cyclomatic_complexity: result.estimatedCyclomaticComplexity,
                comment_ratio: result.totalLines > 0
                  ? Math.round((result.commentLines / result.totalLines) * 100) / 100
                  : 0,
              },
              warnings: result.warnings,
              thresholds: {
                max_cyclomatic_complexity: thresholds?.maxCyclomaticComplexity ?? 10,
                max_nesting_depth: thresholds?.maxNestingDepth ?? 4,
                max_method_lines: thresholds?.maxMethodLines ?? 50,
              },
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
