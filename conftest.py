"""Repository root conftest — keeps pytest from collecting source files as tests."""

collect_ignore_glob = [
    "services/**",
    "packages/**",
    "infrastructure/**",
    "knowledge-base/**",
    "policies/**",
]
