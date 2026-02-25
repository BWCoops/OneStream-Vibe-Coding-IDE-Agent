# SAP BPC Script Logic → OneStream VB.NET Migration Patterns

## LOOKUP → BRApi.Finance.Members

### BPC Script Logic:
```
*LOOKUP MemberTable
*DIM Entity WHAT=EntityLookup WHERE=Entity=[Entity]
```

### OneStream VB.NET:
```vb
Dim memberId As Integer = BRApi.Finance.Members.GetMemberId(
    si, BRApi.Finance.Dim.DimTypeId.Entity, entityName)
Dim memberInfo = BRApi.Finance.Members.GetMemberInfo(si, memberId)
```

## WHEN/IS → Select Case

### BPC Script Logic:
```
*WHEN ACCOUNT
*IS "Revenue"
  *REC(EXPRESSION="%VALUE% * 1.1", ACCOUNT="RevenueAdj")
*ENDWHEN
```

### OneStream VB.NET:
```vb
Select Case accountName
    Case "Revenue"
        Dim adjustedAmount As Decimal = amount * 1.1D
        BRApi.Finance.Data.SetDataCellValue(si, scenarioId, timeId, entityId, adjAccountId, adjustedAmount)
End Select
```

## XDIM_MEMBERSET → BRApi Dimension Queries

### BPC Script Logic:
```
*XDIM_MEMBERSET ENTITY = BAS(Total_Entity)
```

### OneStream VB.NET:
```vb
Dim members As List(Of MemberInfo) = BRApi.Finance.Members.GetBaseMembers(
    si, BRApi.Finance.Dim.DimTypeId.Entity, "Total_Entity")
For Each member In members
    ' Process each base (leaf) member
Next
```

## *COMMIT → BRApi.Finance.Data writes

### BPC Script Logic:
```
*COMMIT
```

### OneStream VB.NET:
```vb
' OneStream auto-commits within the rule execution context.
' No explicit commit needed — data is written via SetDataCellValue.
' For bulk operations, use DataTable-based writes.
```

## Common Gotchas in Migration
1. BPC uses "stored" vs "calculated" members — OneStream uses parent/leaf hierarchy
2. BPC CURR_TRANS → OneStream FX Translation rules (different engine)
3. BPC ownership model → OneStream Ownership dimension
4. BPC journal entries → OneStream Data Management rules
5. BPC security → OneStream RBAC + workflow security
