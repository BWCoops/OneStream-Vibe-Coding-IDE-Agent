# SOX Section 404 — IT General Controls (ITGC)
# Policy-as-code for segregation of duties and change management.
package sox.itgc

import rego.v1

# ── CC1: Segregation of Duties ──
# The person who writes code cannot approve it.
# The person who approves cannot deploy it.

deny contains msg if {
    input.action == "approve_change_request"
    input.actor == input.change_request.requested_by
    msg := sprintf("SOX SoD violation: actor '%s' cannot approve their own change request '%s'", [input.actor, input.change_request.cr_number])
}

deny contains msg if {
    input.action == "deploy"
    input.actor == input.change_request.approved_by
    msg := sprintf("SOX SoD violation: actor '%s' cannot deploy a change they approved '%s'", [input.actor, input.change_request.cr_number])
}

deny contains msg if {
    input.action == "deploy"
    input.actor == input.change_request.requested_by
    msg := sprintf("SOX SoD violation: actor '%s' cannot deploy their own change request '%s'", [input.actor, input.change_request.cr_number])
}

# ── CC2: Change Request Approval Required ──
deny contains msg if {
    input.action == "deploy"
    not input.change_request.status == "approved"
    msg := sprintf("SOX CC2: Change request '%s' must be approved before deployment (current status: '%s')", [input.change_request.cr_number, input.change_request.status])
}

# ── CC3: Minimum Approver Count ──
default min_approvers := 1

min_approvers := 2 if {
    input.target_environment.type == "PROD"
}

deny contains msg if {
    input.action == "deploy"
    count(input.change_request.approvals) < min_approvers
    msg := sprintf("SOX CC3: Change request '%s' requires at least %d approvals for %s environment (has %d)", [input.change_request.cr_number, min_approvers, input.target_environment.type, count(input.change_request.approvals)])
}

# ── CC4: Emergency Change Audit ──
# Emergency changes are allowed but must be flagged for post-hoc review.
emergency_audit_required if {
    input.change_request.type == "emergency"
}

# ── CC5: Code Compilation Required ──
deny contains msg if {
    input.action == "approve_change_request"
    not input.artefact.compilation_status == "success"
    msg := sprintf("SOX CC5: Artefact '%s' must compile successfully before approval", [input.artefact.name])
}

# ── CC6: Test Execution Required ──
deny contains msg if {
    input.action == "approve_change_request"
    input.target_environment.type in {"UAT", "PROD"}
    input.artefact.test_pass_rate < 100
    msg := sprintf("SOX CC6: All tests must pass before approval for %s (current pass rate: %d%%)", [input.target_environment.type, input.artefact.test_pass_rate])
}

# Final decision
allow if {
    count(deny) == 0
}
