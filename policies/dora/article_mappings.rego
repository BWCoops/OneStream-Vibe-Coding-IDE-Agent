# DORA (Digital Operational Resilience Act) — Policy mappings
# Applies to EU-regulated financial entities using this platform.
package dora.resilience

import rego.v1

# ── Article 9: ICT Risk Management Framework ──
# All changes must have a risk assessment before deployment.
deny contains msg if {
    input.action == "deploy"
    not input.change_request.risk_assessment_completed
    msg := sprintf("DORA Art.9: Risk assessment required for change request '%s' before deployment", [input.change_request.cr_number])
}

# ── Article 10: ICT Systems Availability ──
# Deployments to PROD require a rollback plan.
deny contains msg if {
    input.action == "deploy"
    input.target_environment.type == "PROD"
    not input.deployment.rollback_plan_defined
    msg := sprintf("DORA Art.10: Rollback plan required for PROD deployment of '%s'", [input.change_request.cr_number])
}

# ── Article 11: ICT Incident Management ──
# Pipeline failures must generate incident records.
incident_required if {
    input.event == "pipeline_failure"
    input.pipeline.sla_breached
}

incident_required if {
    input.event == "deployment_failure"
    input.target_environment.type in {"UAT", "PROD"}
}

# ── Article 12: ICT Change Management ──
# All changes must be traceable with immutable audit trail.
deny contains msg if {
    input.action == "deploy"
    not input.change_request.audit_trail_hash
    msg := sprintf("DORA Art.12: Immutable audit trail entry required for '%s'", [input.change_request.cr_number])
}

# ── Article 14: Testing of ICT Tools ──
# Regular testing of all ICT tools and systems.
deny contains msg if {
    input.action == "deploy"
    input.target_environment.type == "PROD"
    not input.artefact.integration_tests_passed
    msg := sprintf("DORA Art.14: Integration tests must pass before PROD deployment of '%s'", [input.artefact.name])
}

# ── Article 15: Third-Party ICT Risk ──
# External connector configurations must be reviewed.
third_party_review_required if {
    input.action == "deploy"
    input.artefact.uses_external_connectors
}

# ── Article 25: Reporting Obligations ──
# Significant ICT incidents must be reported.
reporting_required if {
    incident_required
    input.severity in {"critical", "high"}
}

allow if {
    count(deny) == 0
}
