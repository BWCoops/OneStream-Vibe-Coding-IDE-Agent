# Standard Entity Dimension Hierarchy

## Typical Corporate Structure
```
Total_Entity (Top)
├── Corporate (Parent)
│   ├── Corp_HQ (Base)
│   └── Shared_Services (Base)
├── North_America (Parent)
│   ├── US_East (Base)
│   ├── US_West (Base)
│   ├── US_Central (Base)
│   └── Canada (Base)
├── Europe (Parent)
│   ├── UK (Base)
│   ├── Germany (Base)
│   ├── France (Base)
│   └── Nordics (Parent)
│       ├── Sweden (Base)
│       ├── Norway (Base)
│       └── Denmark (Base)
├── Asia_Pacific (Parent)
│   ├── Japan (Base)
│   ├── China (Base)
│   ├── Australia (Base)
│   └── India (Base)
├── Eliminations (Parent)
│   ├── Elim_NA (Base)
│   ├── Elim_EU (Base)
│   ├── Elim_APAC (Base)
│   └── Elim_Global (Base)
└── Adjustments (Parent)
    ├── Adj_Corporate (Base)
    └── Adj_Reclassification (Base)
```

## Key Design Principles

1. **Base vs. Parent members** — Only base (leaf) members accept data input. Parent members aggregate from children.
2. **Elimination entities** — Separate entities for IC elimination at each regional level plus global.
3. **Adjustment entities** — For top-side journal-style adjustments that don't flow through normal consolidation.
4. **Currency treatment** — Each base entity has a default currency. Parents aggregate in the group reporting currency.

## OneStream-Specific Properties

| Property | Description | Example |
|----------|-------------|---------|
| DefaultCurrency | Entity's local currency | USD, EUR, GBP |
| ConsolidationMethod | How entity consolidates | Full, Proportional, Equity |
| OwnershipPercent | Parent's ownership % | 100, 51, 33.33 |
| SecurityClass | RBAC access control | Class_NA, Class_EU |
| AllowInput | Whether data entry is allowed | True (base), False (parent) |
| IntercompanyFlag | Whether entity has IC activity | True, False |

## Common Patterns in Finance Rules

```vb
' Iterate base entities under a parent
Dim baseEntities = BRApi.Finance.Members.GetBaseMembers(
    si, BRApi.Finance.Dim.DimTypeId.Entity, "North_America")

For Each entity In baseEntities
    ' Skip elimination entities
    If Not entity.MemberName.StartsWith("Elim_") Then
        ' Process operational entity
    End If
Next
```
