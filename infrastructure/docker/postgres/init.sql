-- OneStream IDE Agent — Core Schema
-- Run automatically on first docker compose up
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Environments ──
CREATE TABLE environments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('DEV', 'TEST', 'UAT', 'PROD')),
    url VARCHAR(500) NOT NULL,
    api_version VARCHAR(10) NOT NULL DEFAULT '7.2.0',
    platform_version VARCHAR(20), -- e.g. '9.1.0' (.NET 8) or '7.5.0' (legacy)
    dotnet_runtime VARCHAR(20), -- 'net8.0' or 'net48'
    pat_vault_path VARCHAR(200),
    sic_enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Projects ──
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    default_environment_id UUID REFERENCES environments(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Business Rules (generated artefacts) ──
CREATE TABLE artefacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id),
    type VARCHAR(50) NOT NULL, -- 'finance_rule', 'calculation_rule', 'connector_br', etc.
    name VARCHAR(200) NOT NULL,
    source_code TEXT,
    target_runtime VARCHAR(20) NOT NULL DEFAULT 'net8.0',
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    git_sha VARCHAR(40),
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Requirements Traceability Matrix ──
CREATE TABLE rtm_requirements (
    id VARCHAR(20) PRIMARY KEY, -- e.g. REQ-CON-042
    project_id UUID NOT NULL REFERENCES projects(id),
    category VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    priority VARCHAR(10) DEFAULT 'MEDIUM',
    status VARCHAR(30) NOT NULL DEFAULT 'Captured',
    frd_section VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE rtm_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requirement_id VARCHAR(20) NOT NULL REFERENCES rtm_requirements(id),
    artefact_id UUID REFERENCES artefacts(id),
    test_case_id UUID,
    deployment_id UUID,
    link_type VARCHAR(30) NOT NULL, -- 'implements', 'tests', 'deploys'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Change Requests (ALM) ──
CREATE TABLE change_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id),
    cr_number VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    type VARCHAR(20) NOT NULL DEFAULT 'standard', -- standard, emergency, expedited
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    requested_by VARCHAR(100),
    target_environment_id UUID REFERENCES environments(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Approval Records ──
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    change_request_id UUID NOT NULL REFERENCES change_requests(id),
    approver VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL,
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('approved', 'rejected', 'deferred')),
    comments TEXT,
    decided_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Immutable Audit Log ──
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    actor VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    details JSONB,
    previous_hash VARCHAR(64), -- SHA-256 of previous entry for chain integrity
    entry_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);

-- ── Data Pipelines ──
CREATE TABLE pipelines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    definition JSONB NOT NULL, -- Full pipeline DAG definition
    schedule JSONB, -- Cron, event-driven, or conditional
    sla_target_minutes INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE pipeline_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_id UUID NOT NULL REFERENCES pipelines(id),
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    sla_met BOOLEAN,
    error_details TEXT,
    lineage_snapshot JSONB -- Column-level lineage at execution time
);

-- ── Knowledge Base Embeddings ──
CREATE TABLE kb_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain VARCHAR(50) NOT NULL, -- 'api_reference', 'code_pattern', 'best_practice', etc.
    title VARCHAR(500),
    content TEXT NOT NULL,
    metadata JSONB,
    platform_version VARCHAR(20), -- NULL = all versions
    embedding vector(1536), -- Sentence transformer dimension
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kb_embeddings_domain ON kb_embeddings(domain);
CREATE INDEX idx_kb_embeddings_vector ON kb_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── Test Cases ──
CREATE TABLE test_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    artefact_id UUID REFERENCES artefacts(id),
    type VARCHAR(20) NOT NULL, -- 'unit', 'integration', 'regression', 'uat'
    name VARCHAR(500) NOT NULL,
    description TEXT,
    test_script TEXT,
    expected_result TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    last_result VARCHAR(20), -- 'pass', 'fail', 'error', 'skip'
    last_executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
