"""Knowledge domain schemas for OneStream platform domains."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class KnowledgeDomain(str, Enum):
    """The 8 core OneStream knowledge domains."""
    BUSINESS_RULES = "business_rules"
    DATA_ADAPTERS = "data_adapters"
    DIMENSIONS = "dimensions"
    CONSOLIDATION = "consolidation"
    FINANCIAL_CLOSE = "financial_close"
    PLANNING = "planning"
    REPORTING = "reporting"
    PLATFORM_ADMIN = "platform_admin"


@dataclass
class DomainSchema:
    """Schema definition for a knowledge domain."""
    domain: KnowledgeDomain
    display_name: str
    description: str
    entity_types: list[str]
    relationship_types: list[str]
    key_apis: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


# Pre-defined domain schemas
DOMAIN_SCHEMAS: dict[KnowledgeDomain, DomainSchema] = {
    KnowledgeDomain.BUSINESS_RULES: DomainSchema(
        domain=KnowledgeDomain.BUSINESS_RULES,
        display_name="Business Rules",
        description="Finance rules, member rules, connector BRs, dashboard extenders, and event handlers",
        entity_types=["FinanceRule", "MemberRule", "ConnectorBR", "DashboardExtender", "EventHandler"],
        relationship_types=["CALLS_API", "USES_DIMENSION", "REFERENCES_ACCOUNT", "TRIGGERS"],
        key_apis=["BRApi.Finance", "BRApi.ErrorLog", "BRApi.Utilities", "HS.AppServer"],
        tags=["vb.net", "c#", "calculation", "consolidation"],
    ),
    KnowledgeDomain.DATA_ADAPTERS: DomainSchema(
        domain=KnowledgeDomain.DATA_ADAPTERS,
        display_name="Data Adapters",
        description="Data integration adapters for importing and exporting financial data",
        entity_types=["DataAdapter", "DataSource", "DataTarget", "TransformRule", "LoadRule"],
        relationship_types=["READS_FROM", "WRITES_TO", "TRANSFORMS", "MAPS_COLUMN"],
        key_apis=["BRApi.Finance.Data", "BRApi.Database"],
        tags=["etl", "data-load", "integration", "staging"],
    ),
    KnowledgeDomain.DIMENSIONS: DomainSchema(
        domain=KnowledgeDomain.DIMENSIONS,
        display_name="Dimensions",
        description="Dimension types, hierarchies, member properties, and metadata management",
        entity_types=["DimType", "Dimension", "Member", "MemberProperty", "Hierarchy"],
        relationship_types=["PARENT_OF", "HAS_PROPERTY", "BELONGS_TO_DIM", "MAPS_TO"],
        key_apis=["BRApi.Finance.Members", "BRApi.Finance.Dim"],
        tags=["entity", "account", "scenario", "time", "custom"],
    ),
    KnowledgeDomain.CONSOLIDATION: DomainSchema(
        domain=KnowledgeDomain.CONSOLIDATION,
        display_name="Consolidation",
        description="Financial consolidation including IC eliminations, FX translation, ownership",
        entity_types=["ConsolRule", "ICElimination", "FXTranslation", "OwnershipRule"],
        relationship_types=["ELIMINATES", "TRANSLATES", "OWNS_PCT", "CONSOLIDATES_INTO"],
        key_apis=["BRApi.Finance.Data", "BRApi.Finance.Members", "BRApi.Finance.Consolidation"],
        tags=["intercompany", "currency", "ownership", "minority-interest"],
    ),
    KnowledgeDomain.FINANCIAL_CLOSE: DomainSchema(
        domain=KnowledgeDomain.FINANCIAL_CLOSE,
        display_name="Financial Close",
        description="Close management, task lists, certifications, and workflow orchestration",
        entity_types=["CloseTask", "TaskList", "Certification", "WorkflowStep"],
        relationship_types=["DEPENDS_ON", "ASSIGNED_TO", "CERTIFIES", "FOLLOWS"],
        key_apis=["BRApi.Workflow"],
        tags=["close", "task-list", "certification", "sign-off"],
    ),
    KnowledgeDomain.PLANNING: DomainSchema(
        domain=KnowledgeDomain.PLANNING,
        display_name="Planning & Forecasting",
        description="Budgeting, forecasting, what-if scenarios, and planning forms",
        entity_types=["PlanningForm", "InputTemplate", "Scenario", "ForecastModel"],
        relationship_types=["INPUTS_TO", "CALCULATES", "COMPARES_WITH", "DRIVES"],
        key_apis=["BRApi.Finance.Data", "BRApi.Finance.Members"],
        tags=["budget", "forecast", "what-if", "driver-based"],
    ),
    KnowledgeDomain.REPORTING: DomainSchema(
        domain=KnowledgeDomain.REPORTING,
        display_name="Reporting & Dashboards",
        description="Dashboard creation, report generation, and data visualization",
        entity_types=["Dashboard", "Report", "DashboardComponent", "DataView"],
        relationship_types=["DISPLAYS", "QUERIES", "LINKS_TO", "PARAMETERIZED_BY"],
        key_apis=["BRApi.Dashboards", "HS.AppServer"],
        tags=["dashboard", "report", "visualization", "cube-view"],
    ),
    KnowledgeDomain.PLATFORM_ADMIN: DomainSchema(
        domain=KnowledgeDomain.PLATFORM_ADMIN,
        display_name="Platform Administration",
        description="Security, user management, system configuration, and maintenance",
        entity_types=["SecurityRole", "UserGroup", "SystemSetting", "Maintenance"],
        relationship_types=["HAS_ROLE", "MEMBER_OF", "CONFIGURES", "MONITORS"],
        key_apis=["BRApi.Security", "BRApi.Utilities"],
        tags=["security", "admin", "configuration", "maintenance"],
    ),
}


def get_domain_schema(domain: KnowledgeDomain) -> DomainSchema:
    """Get the schema for a knowledge domain."""
    return DOMAIN_SCHEMAS[domain]


def get_all_entity_types() -> list[str]:
    """Get all entity types across all domains."""
    types = []
    for schema in DOMAIN_SCHEMAS.values():
        types.extend(schema.entity_types)
    return types
