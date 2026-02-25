# Oracle HFM → OneStream VB.NET Migration Patterns

## HFM Calculation Rules → OneStream Finance Rules

### HFM VBScript:
```vb
Sub Calculate()
    HS.Clear "A#NetIncome"
    HS.Exp "A#Revenue - A#COGS - A#OpEx = A#NetIncome"
End Sub
```

### OneStream VB.NET:
```vb
' Finance Rule — Calculate Net Income
Dim revenue As Decimal = api.Data.GetDataCell(
    si, "A#Revenue").CellAmount
Dim cogs As Decimal = api.Data.GetDataCell(
    si, "A#COGS").CellAmount
Dim opex As Decimal = api.Data.GetDataCell(
    si, "A#OpEx").CellAmount

Dim netIncome As Decimal = revenue - cogs - opex
api.Data.SetDataCellValue(si, netIncomeId, netIncome)
```

## HFM HS.GetCell → BRApi.Finance.Data.GetDataCell

### HFM VBScript:
```vb
Dim dblValue
dblValue = HS.GetCell("S#Actual.Y#2024.P#January.E#Corp.A#Revenue.V#<Entity Currency>")
```

### OneStream VB.NET:
```vb
Dim cell As DataCell = BRApi.Finance.Data.GetDataCell(
    si, "S#Actual.Y#2024.P#M1.E#Corp.A#Revenue.V#Periodic.C#Local")
Dim amount As Decimal = cell.CellAmount
```

## HFM Member Lists → OneStream Member Filters

### HFM:
```vb
HS.MemberSet "Entity", "IDescendants(Total_Entity)"
```

### OneStream VB.NET:
```vb
Dim members = BRApi.Finance.Members.GetBaseMembers(
    si, BRApi.Finance.Dim.DimTypeId.Entity, "Total_Entity")
```

## HFM Consolidation Rules → OneStream Consolidation

### HFM VBScript:
```vb
Sub Consolidate()
    HS.Con "A#Revenue", "*", "+"
    HS.Con "A#COGS", "*", "+"
End Sub
```

### OneStream VB.NET:
```vb
' OneStream handles consolidation through the built-in consolidation engine.
' Custom consolidation logic is implemented in Consolidation business rules.
' Standard aggregation (sum children) is automatic — no code needed.
' IC eliminations use dedicated IC Elimination rules.
```

## HFM Journals → OneStream Data Management

### HFM:
```vb
' Journals in HFM are UI-based entries stored in the HFM database.
```

### OneStream:
```vb
' OneStream uses Data Management rules for journal-like entries.
' Adjustments are handled via specific scenarios (Adj, Reclassification).
' No separate journal module — it's integrated into the consolidation flow.
```

## Common Migration Gotchas

1. **HS.GetCell string POV** → OneStream uses structured member references, not string concatenation
2. **HFM "Entity Currency" view** → OneStream uses `V#Periodic` + `C#Local` or `C#Translated`
3. **HFM Equity Pickup** → OneStream uses Ownership dimension with ownership percentages
4. **HFM Process Management** → OneStream uses Workflow Profiles for close process
5. **HFM Data Forms** → OneStream uses Cube Views for data entry
6. **HFM Custom dimensions** → OneStream uses UD1-UD8 user-defined dimensions
7. **HFM Rules file (.rle)** → OneStream uses in-platform Business Rules (compiled VB.NET)
8. **HFM Sub Translate** → OneStream FX Translation uses Currency dimension + translation tables
