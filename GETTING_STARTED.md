# Getting Started with Claude Code
## Prerequisites
1. **Node.js 18+** — Required for Claude Code
2. **Claude Code installed** — `npm install -g @anthropic-ai/claude-code`
3. **Anthropic API key** — Set as `ANTHROPIC_API_KEY` environment variable
4. **Docker Desktop** — For local PostgreSQL, Redis, Neo4j, RabbitMQ
## Setup
```bash
# 1. Clone / create the repo
mkdir onestream-ide-agent
cd onestream-ide-agent
# 2. Copy CLAUDE.md into the root (this is critical — it's the project constitution)
cp /path/to/CLAUDE.md .
# 3. Copy the knowledge base files (OneStream API docs, code patterns, etc.)
cp -r /path/to/knowledge-base ./knowledge-base/
# 4. Start Claude Code
claude
# 5. Your first prompt:
```
## First Session — Scaffolding
Open Claude Code in the repo root and say:
```
Read CLAUDE.md carefully. Then scaffold the full repo structure from the
Repository Structure section. Create all directories, package.json files
(with the exact dependencies from the tech stack), docker-compose.yml for
local dev (PostgreSQL 16 with pgvector, Redis 7, Neo4j 5, RabbitMQ 3.13,
EventStoreDB), and a basic .env.example. Don't write application code yet —
just the skeleton.
```
## Second Session — MCP Servers (the critical foundation)
```
Build the onestream-rules MCP server in packages/mcp-servers/onestream-rules/.
It should:
- Implement the MCP protocol over stdio and HTTP+SSE transports
- Expose tools: list_rules, get_rule, create_rule, update_rule, compile_rule, check_deprecated
- Use the OneStream REST API v7.2.0 with PAT authentication
- Detect platform version on first connection (.NET 8 vs legacy)
- Include the deprecated API registry from knowledge-base/deprecated-apis/
- Include proper TypeScript types and unit tests
Reference the MCP Server Design section in CLAUDE.md for the tool schemas.
```
## Third Session — Agent Orchestration
```
Build the LangGraph orchestrator in services/orchestrator/. Start with:
1. The planning agent (task decomposition)
2. The code generator agent (VB.NET generation for Finance Rules)
3. The code reviewer agent (verification/critic — this is the most important one,
   give it 2x context as described in CLAUDE.md)
4. Wire them into the generator-critic loop graph from CLAUDE.md
Use the code pattern templates in knowledge-base/code-patterns/ as few-shot
examples in the generator's prompt. The reviewer must check for deprecated
APIs using knowledge-base/deprecated-apis/.
```
## Fourth Session — Data Orchestration Engine
```
Build the data orchestration engine in services/data-orchestration/.
Implement:
1. The Pipeline and Stage data models from CLAUDE.md
2. DAG-based scheduler with dependency resolution
3. Database connector (SQL Server via Microsoft.Data.SqlClient pattern)
4. File connector (CSV with SFTP via SSH.NET pattern)
5. Column-level lineage tracking
6. Basic retry with exponential backoff
7. SLA monitoring (define target, track progress, alert on risk)
Generate the corresponding OneStream data adapter business rule code that
the pipeline definitions translate into.
```
## Key Tips for Working with Claude Code on This Project
### Feed it domain knowledge
Claude Code doesn't know OneStream's APIs. Before asking it to generate
OneStream-specific code, paste relevant sections from:
- `knowledge-base/api-reference/` — BRApi method signatures and usage
- `knowledge-base/code-patterns/` — Working VB.NET examples
- `knowledge-base/deprecated-apis/` — What NOT to generate
### Use the CLAUDE.md as the single source of truth
When Claude Code drifts from the architecture, say:
```
Check CLAUDE.md section [X]. You've deviated from the spec — [explain how].
```
### Build incrementally, test continuously
After each session, verify:
- `docker compose up` still works
- Unit tests pass
- MCP servers respond to tool discovery
- Generated VB.NET code compiles via the Roslyn service
### For the verification agent
This is the hardest part. The prompt engineering for the code reviewer
needs real OneStream examples of:
- Common consolidation mistakes (IC elimination not matching, wrong FX rates)
- Performance anti-patterns (row-by-row vs bulk operations)
- Security issues (hardcoded credentials, SQL injection in dynamic queries)
- .NET 8 vs legacy incompatibilities
Collect these from real OneStream projects and add them to the knowledge base.
## OneStream Knowledge You Need to Provide
Claude Code cannot learn OneStream's APIs from the internet — they're not
well-documented publicly. You need to supply:
1. **BRApi documentation** — Method signatures, parameters, return types,
   usage examples for all namespaces (Finance, Finance.Data, Finance.Members,
   Database, Dashboard, Dashboard.Extender, ErrorLog, Workflow)
2. **Working business rule examples** — At least 5-10 real production rules
   covering: Finance Rules, Calculation Rules, Connector BRs, Data Management,
   Dashboard Adapters, Dashboard Extender, Workflow handlers
3. **OneStream REST API spec** — Endpoint list, request/response schemas,
   authentication flow, PascalCase JSON examples
4. **Dimension model examples** — Real entity hierarchies, account structures,
   custom dimension (UD1-UD8) designs
5. **SAP BPC Script Logic examples** (if building migration module) —
   LOOKUP, WHEN/IS, XDIM_MEMBERSET patterns with their OneStream equivalents
6. **Deprecated API mapping** — Which APIs changed between .NET Framework 4.8
   and .NET 8, with before/after code samples
Store all of these in the `knowledge-base/` directory. The RAG pipeline and
agent prompts will reference them.
