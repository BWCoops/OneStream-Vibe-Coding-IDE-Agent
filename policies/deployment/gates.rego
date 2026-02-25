# Deployment Gate Policies
# Enforces quality gates before environment promotion.
package deployment.gates

import rego.v1

# ── Gate 1: Compilation ──
deny contains msg if {
    not input.artefact.compiled_successfully
    msg := sprintf("Gate 1: Artefact '%s' must compile successfully", [input.artefact.name])
}

# ── Gate 2: Deprecated API Check ──
deny contains msg if {
    input.artefact.deprecated_api_count > 0
    input.artefact.deprecated_api_severity == "error"
    msg := sprintf("Gate 2: Artefact '%s' uses %d deprecated APIs with severity 'error'", [input.artefact.name, input.artefact.deprecated_api_count])
}

# ── Gate 3: Code Review Passed ──
deny contains msg if {
    not input.artefact.review_passed
    msg := sprintf("Gate 3: Code review not passed for '%s' (score: %.2f)", [input.artefact.name, input.artefact.review_score])
}

# ── Gate 4: Test Coverage ──
deny contains msg if {
    input.target_environment.type in {"UAT", "PROD"}
    input.artefact.test_coverage_pct < 80
    msg := sprintf("Gate 4: Test coverage %.1f%% below 80%% threshold for %s deployment", [input.artefact.test_coverage_pct, input.target_environment.type])
}

# ── Gate 5: RTM Traceability ──
deny contains msg if {
    input.target_environment.type == "PROD"
    not input.artefact.rtm_linked
    msg := sprintf("Gate 5: Artefact '%s' must be linked to a requirement (RTM) for PROD deployment", [input.artefact.name])
}

# ── Gate 6: Environment Promotion Order ──
valid_promotion if {
    input.source_environment.type == "DEV"
    input.target_environment.type == "TEST"
}

valid_promotion if {
    input.source_environment.type == "TEST"
    input.target_environment.type == "UAT"
}

valid_promotion if {
    input.source_environment.type == "UAT"
    input.target_environment.type == "PROD"
}

deny contains msg if {
    not valid_promotion
    msg := sprintf("Gate 6: Invalid promotion path %s -> %s. Must follow DEV -> TEST -> UAT -> PROD", [input.source_environment.type, input.target_environment.type])
}

# ── Gate 7: Change Request Required ──
deny contains msg if {
    input.target_environment.type in {"UAT", "PROD"}
    not input.change_request
    msg := "Gate 7: Change request required for UAT/PROD deployments"
}

# ── Gate 8: Data Pipeline SLA Validation ──
deny contains msg if {
    input.artefact.type == "data_pipeline"
    not input.artefact.sla_defined
    input.target_environment.type == "PROD"
    msg := sprintf("Gate 8: Pipeline '%s' must have SLA defined for PROD", [input.artefact.name])
}

allow if {
    count(deny) == 0
}

# Summary of all violations
summary := {
    "allowed": allow,
    "violations": deny,
    "violation_count": count(deny),
}
