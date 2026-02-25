# OneStream Vibe Coding IDE Agent
## Project Overview
AI-powered web IDE for OneStream XF platform development. Combines domain-specific OneStream knowledge with code generation, data orchestration, testing, and SOX/DORA-compliant ALM.
## Architecture Principles
1. **MCP-native** — All OneStream operations exposed as MCP servers (JSON-RPC 2.0). The platform is both an MCP server (tools for external clients) and MCP client (consuming external tools).
2. **Multi-agent orchestration** — LangGraph-based agents: Planning, Execution (code gen), Verification (critic), Test Engineer, Data Orchestration, Requirements Analyst.
3. **Verification-first** — The verification/critic agent is the most sophisticated component. It receives 2x context budget vs the generator. AI code averages 75% more defects than human code — the reviewer matters more than the writer.
4. **Platform-version-aware** — All generated code targets either .NET 8 (Platform v9.x) or .NET Framework 4.8 (legacy). Deprecated APIs are detected and flagged automatically.
5. **Dual deployment** — Cloud (Claude API) and on-premises (vLLM with QLoRA fine-tuned model) topologies. Treat as configuration, not separate codebases.
6. **Compliance by design** — DORA, EU AI Act, ISO 27001:2022, SOX Section 404 embedded in data model and agent orchestration, not bolted on.
## Tech Stack (Do NOT deviate without discussion)
### Frontend
- React 18+ with TypeScript 5.4+
- Monaco Editor with custom OneStream language server
- Yjs (CRDT) + y-monaco for real-time collaboration
- Tailwind CSS + shadcn/ui
- TanStack Query (server state) + Zustand (client state)
- Socket.io for WebSocket (streaming, Yjs sync)
- Vite build, Vitest testing
### Backend
- Python 3.12+ with FastAPI — AI orchestration, agent services
- Node.js 20 LTS with Express — real-time services, Yjs sync provider, WebSocket
- PostgreSQL 16+ with pgvector (pgvectorscale extension) — primary DB + vector search
- Neo4j 5.x — GraphRAG knowledge graph
- Redis 7.x — caching, sessions, pub/sub
- RabbitMQ 3.13+ — async message queuing
- EventStoreDB — immutable audit trail (SOX/DORA)
- HashiCorp Vault — credential management, PAT storage
- OPA (Open Policy Agent) — policy-as-code compliance enforcement
### AI/ML
- Claude API (Anthropic) — primary LLM (cloud deployment)
- vLLM — on-premises inference (PagedAttention, continuous batching)
- QLoRA fine-tuned model — Qwen2.5-Coder-7B or DeepSeek-Coder-6.7B on OneStream patterns
- LangGraph — multi-agent orchestration
- MCP SDK — TypeScript + Python implementations
- Microsoft GraphRAG — entity knowledge graph indexing
- Sentence Transformers — embeddings for hybrid search
- Roslyn Compiler Services — VB.NET/C# parsing, validation, compilation
- DeepEval — LLM output evaluation in CI/CD
- Langfuse (self-hosted) — AI observability, tracing, prompt management
- Tonic.ai / MOSTLY AI — synthetic financial data generation
## Repository Structure
```
onestream-ide-agent/
├── CLAUDE.md                          # This file
├── docker-compose.yml                 # Local dev environment
├── docker-compose.prod.yml            # Production compose
├── .env.example                       # Environment template
│
├── packages/
│   ├── web/                           # React frontend
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── editor/            # Monaco editor + Yjs integration
│   │   │   │   ├── chat/              # AI assistant panel
│   │   │   │   ├── pipeline/          # Data orchestration DAG designer
│   │   │   │   ├── testing/           # Test runner panel
│   │   │   │   ├── alm/              # ALM dashboard, CR management
│   │   │   │   ├── rtm/              # Traceability matrix viewer
│   │   │   │   └── shared/            # Common components
│   │   │   ├── hooks/
│   │   │   ├── stores/                # Zustand stores
│   │   │   ├── services/              # API clients
│   │   │   └── types/
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   ├── api-gateway/                   # Node.js API gateway
│   │   ├── src/
│   │   │   ├── routes/
│   │   │   ├── middleware/            # Auth, rate limiting, RBAC
│   │   │   ├── websocket/            # Socket.io + Yjs provider
│   │   │   └── mcp/                  # MCP server HTTP/SSE transport
│   │   └── package.json
│   │
│   ├── mcp-servers/                   # MCP server implementations
│   │   ├── onestream-rules/           # Business rule CRUD via REST API
│   │   ├── onestream-metadata/        # Dimension/member operations
│   │   ├── onestream-deploy/          # Environment promotion
│   │   ├── onestream-data/            # Data adapter management
│   │   ├── onestream-validate/        # Compilation, validation
│   │   └── shared/                    # Common MCP utilities, PAT auth
│   │
│   └── roslyn-service/                # .NET service for VB.NET/C# compilation
│       ├── src/
│       └── Dockerfile
│
├── services/
│   ├── orchestrator/                  # Python — LangGraph agent orchestration
│   │   ├── agents/
│   │   │   ├── planning.py            # Task decomposition, dependency graphs
│   │   │   ├── code_generator.py      # VB.NET/C# generation (execution agent)
│   │   │   ├── code_reviewer.py       # Verification agent (critic) — 2x context
│   │   │   ├── test_engineer.py       # Test generation, synthetic data
│   │   │   ├── requirements.py        # Discovery, FRD/TDD generation
│   │   │   ├── data_orchestration.py  # Pipeline design, DAG generation
│   │   │   └── migration.py           # BPC/HFM translation agent
│   │   ├── graphs/                    # LangGraph workflow definitions
│   │   │   ├── code_gen_flow.py       # Generator → Critic → Test loop
│   │   │   ├── discovery_flow.py      # 6-phase requirements discovery
│   │   │   ├── pipeline_flow.py       # Data pipeline generation
│   │   │   └── migration_flow.py      # Source analysis → translate → validate
│   │   ├── mcp_client/                # MCP client for consuming tools
│   │   ├── prompts/                   # System prompts per agent role
│   │   ├── memory/                    # Tiered memory (session/project/team/global)
│   │   └── main.py
│   │
│   ├── knowledge/                     # Python — Knowledge base & RAG
│   │   ├── graphrag/                  # Microsoft GraphRAG integration
│   │   ├── indexer/                   # Document indexing pipeline
│   │   ├── retriever/                 # Hybrid search (vector + keyword + graph)
│   │   ├── reranker/                  # Cross-encoder re-ranking
│   │   └── domains/                   # 8 knowledge domain schemas
│   │
│   ├── testing/                       # Python — Test execution engine
│   │   ├── generators/                # Unit, integration, regression, UAT generators
│   │   ├── runners/                   # Test execution orchestration
│   │   ├── synthetic/                 # Synthetic data generation
│   │   ├── deepeval/                  # DeepEval evaluation pipeline
│   │   └── confirmation_rules/        # OneStream Confirmation Rule integration
│   │
│   ├── alm/                           # Python — ALM & governance
│   │   ├── gitops/                    # Git integration, branch management
│   │   ├── drift/                     # Drift detection engine
│   │   ├── migration_engine/          # Smart Migration (replaces Extract/Load)
│   │   ├── approval/                  # Workflow engine, SoD enforcement
│   │   ├── audit/                     # Immutable audit trail, hash chaining
│   │   └── compliance/                # OPA policy integration, evidence generation
│   │
│   ├── data-orchestration/            # Python — Pipeline engine
│   │   ├── designer/                  # Pipeline definition model
│   │   ├── scheduler/                 # DAG-based scheduling engine
│   │   ├── connectors/                # Pre-built connector catalogue
│   │   │   ├── database/              # SQL Server, Oracle, PostgreSQL, MySQL
│   │   │   ├── file/                  # CSV, Excel, XML, JSON, SFTP
│   │   │   ├── erp/                   # SAP, Oracle EBS, Workday, Dynamics
│   │   │   ├── api/                   # REST, SOAP, OData, GraphQL
│   │   │   └── cloud/                 # Azure Blob, S3, GCS (via SIC)
│   │   ├── lineage/                   # Column-level lineage tracking
│   │   ├── healing/                   # Self-healing, retry, dead-letter
│   │   └── sla/                       # SLA monitoring & alerting
│   │
│   └── observability/                 # Langfuse + metrics
│       ├── langfuse/                  # Langfuse self-hosted config
│       └── dashboards/                # Grafana dashboard definitions
│
├── knowledge-base/                    # OneStream domain knowledge (CHECK IN)
│   ├── api-reference/                 # BRApi, HS namespace documentation
│   ├── code-patterns/                 # VB.NET/C# pattern templates
│   ├── deprecated-apis/               # Per-version deprecated API registry
│   ├── best-practices/                # OneStream certified patterns
│   ├── migration-patterns/            # BPC Script Logic → VB.NET mappings
│   │   ├── bpc/                       # SAP BPC patterns
│   │   └── hfm/                       # Oracle HFM patterns
│   └── dimension-models/              # Standard dimension designs
│
├── infrastructure/
│   ├── terraform/                     # Cloud infrastructure (AWS/Azure)
│   ├── kubernetes/                    # K8s manifests
│   ├── docker/                        # Dockerfiles per service
│   └── vllm/                          # On-premises vLLM deployment config
│
├── policies/                          # OPA policy files
│   ├── sox/                           # SOX ITGC controls
│   ├── dora/                          # DORA Article mappings
│   └── deployment/                    # Deployment gate policies
│
└── tests/
    ├── e2e/                           # End-to-end tests
    ├── integration/                   # Service integration tests
    └── fixtures/                      # Test data, mock OneStream responses
```
## Coding Standards
### Python (Backend Services)
- Python 3.12+, type hints on all functions
- FastAPI for HTTP services, Pydantic for validation
- async/await for IO-bound operations
- Ruff for linting, Black for formatting
- pytest for testing, pytest-asyncio for async tests
- Structured logging with structlog
### TypeScript (Frontend + Node.js)
- Strict TypeScript, no `any` types
- ESLint + Prettier
- Functional React components with hooks only
- Vitest for unit tests, Playwright for E2E
- Named exports, barrel files for modules
### VB.NET/C# (Generated Code)
- All generated rules must include:
  - Structured Try/Catch/Finally with step identification
  - BRApi.ErrorLog.LogMessage for error reporting
  - Parameterised configuration via substitution variables
  - Inline documentation with requirement ID cross-references
- Target .NET 8 by default; .NET Framework 4.8 when environment specifies legacy
- Never use deprecated APIs: BRApi.Utilities.EncryptText/DecryptText, WinSCP, ERPConnect45.dll, System.Data.SqlClient (on .NET 8)
## OneStream API Integration
### Authentication
- Platform v8.0+ (.NET 8): Personal Access Tokens (PATs) via OneStream IdentityServer (OIS)
- Legacy: SSO/NTLM
- All REST API calls use PAT in Authorization header
### REST API Versions
- v5.2.0: Synchronous operations
- v7.2.0: Async support
- JSON serialisation: PascalCase mandatory
- Base URL pattern: `https://{environment}.onestream.com/OneStreamWeb/api/v{version}/`
### Connectivity
- Cloud-to-on-prem: Smart Integration Connector (SIC) — NOT VPN/ExpressRoute
- Environment registry stores: URL, API version, platform version (.NET 8 or legacy), PAT reference (Vault path)
## MCP Server Design
Each MCP server exposes tools following the MCP specification:
```typescript
// Example: onestream-rules MCP server
{
  name: "onestream_rules",
  tools: [
    { name: "list_rules", description: "List business rules by type", inputSchema: {...} },
    { name: "get_rule", description: "Get rule source code", inputSchema: {...} },
    { name: "create_rule", description: "Create new business rule", inputSchema: {...} },
    { name: "update_rule", description: "Update rule source code", inputSchema: {...} },
    { name: "compile_rule", description: "Compile and validate rule", inputSchema: {...} },
    { name: "check_deprecated", description: "Check for deprecated API usage", inputSchema: {...} },
  ]
}
```
Transport: stdio (for Claude Code/Cline) and HTTP+SSE (for web IDE).
## Agent Orchestration Patterns
### Default: Generator-Critic Loop (for code generation)
```
Planning Agent → Code Generator → Code Reviewer (critic) → [pass/fail]
                                        ↓ (if fail)
                                  Code Generator (retry with feedback)
                                        ↓
                                  Test Engineer (parallel)
```
### The Verification Agent (Code Reviewer)
This is the MOST IMPORTANT agent. It receives:
- 2x the context window budget of the generator
- Full OneStream API reference for the target platform version
- Deprecated API registry
- Best-practice compliance checklist
- The original requirement from the RTM
- Generated test cases for cross-reference
It checks: correctness, best-practice conformance, deprecated API usage, security, performance, error handling completeness.
## Data Orchestration Pipeline Model
```python
@dataclass
class Pipeline:
    id: str
    name: str
    description: str
    stages: list[Stage]          # Ordered DAG of stages
    schedule: Schedule           # Cron, event-driven, or conditional
    sla: SLADefinition          # Target completion time, alert thresholds
    lineage: LineageGraph        # Column-level source-to-target mapping
    retry_policy: RetryPolicy    # Backoff, max attempts, dead-letter config

@dataclass
class Stage:
    id: str
    type: StageType              # EXTRACT, TRANSFORM, VALIDATE, LOAD
    connector: ConnectorConfig   # Source/target connection details
    dependencies: list[str]      # Stage IDs this depends on
    transformation: str          # SQL/Python/VB.NET transformation logic
    validation_rules: list[Rule] # Data quality checks
```
## Key Constraints
1. **No business data storage** — The platform stores metadata, code, configs, and audit logs. It NEVER persists customer financial data. Data flows through pipelines but is not retained.
2. **Just-in-time credentials** — Environment PATs retrieved from Vault at execution time, never cached in application memory beyond the request lifecycle.
3. **Immutable audit trail** — Every state change (code generation, approval, deployment, pipeline execution) is append-only with hash chaining. No updates, no deletes.
4. **Segregation of duties** — Enforced by OPA policies. The person who writes code cannot approve it. The person who approves cannot deploy it.
5. **Platform version detection** — On first connection to a OneStream environment, detect platform version and configure all code generation, API calls, and validation accordingly.
## Build Order (Recommended)
### Phase 1: Foundation (Weeks 1-4)
1. Repo scaffolding + Docker compose + CI/CD skeleton
2. PostgreSQL schema (projects, environments, rules, RTM, audit)
3. OneStream REST API client library (PAT auth, version detection)
4. MCP server: `onestream-rules` (list, get, create, update, compile)
5. Basic React shell with Monaco editor
### Phase 2: Intelligence (Weeks 5-8)
6. LangGraph orchestrator with planning + code generator agents
7. Code reviewer (verification) agent with DeepEval scoring
8. Knowledge base: pgvector indexing + basic RAG retrieval
9. Roslyn compilation service (VB.NET/C# validation)
10. Chat interface with streaming responses
### Phase 3: Data & Testing (Weeks 9-12)
11. Data orchestration engine (pipeline model, DAG scheduler, connectors)
12. Test generation engine (unit, integration, regression)
13. RTM implementation (auto-registration, gap detection)
14. Yjs collaboration integration
15. Pipeline designer UI (DAG editor)
### Phase 4: Governance (Weeks 13-16)
16. ALM: Git integration, change requests, approval workflows
17. Drift detection engine
18. OPA policy integration (SOX/DORA)
19. Immutable audit trail with hash chaining
20. Compliance report generation
## Environment Variables
```env
# OneStream
ONESTREAM_DEFAULT_API_VERSION=7.2.0
ONESTREAM_PAT_VAULT_PATH=secret/onestream/environments
# AI
ANTHROPIC_API_KEY=                     # Cloud deployment
VLLM_ENDPOINT=http://localhost:8000    # On-prem deployment
LLM_PROVIDER=anthropic                 # or "vllm"
LLM_MODEL=claude-sonnet-4-20250514
# Database
DATABASE_URL=postgresql://...
PGVECTOR_ENABLED=true
NEO4J_URI=bolt://localhost:7687
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://localhost:5672
EVENTSTOREDB_URL=esdb://localhost:2113
# Observability
LANGFUSE_HOST=http://localhost:3001
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
# Security
VAULT_ADDR=http://localhost:8200
OPA_ENDPOINT=http://localhost:8181
JWT_SECRET=
```
