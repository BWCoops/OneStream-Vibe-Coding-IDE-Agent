# BRApi Quick Reference — OneStream XF

## BRApi.Finance.Data
```vb
' Read a single data cell
Dim cell As DataCell = BRApi.Finance.Data.GetDataCell(si, pov)
Dim amount As Decimal = cell.CellAmount
Dim status As DataCellStatus = cell.CellStatus

' Write a data cell
BRApi.Finance.Data.SetDataCellValue(si, targetPov, amount)

' Get data cells for a range
Dim cells As List(Of DataCell) = BRApi.Finance.Data.GetDataCells(si, povList)
```

## BRApi.Finance.Members
```vb
' Get member ID by name
Dim memberId As Integer = BRApi.Finance.Members.GetMemberId(
    si, BRApi.Finance.Dim.DimTypeId.Entity, "US_East")

' Get member info
Dim memberInfo As MemberInfo = BRApi.Finance.Members.GetMemberInfo(si, memberId)

' Get base (leaf) members
Dim baseMembers As List(Of MemberInfo) = BRApi.Finance.Members.GetBaseMembers(
    si, BRApi.Finance.Dim.DimTypeId.Entity, "Total_Entity")

' Get children
Dim children As List(Of MemberInfo) = BRApi.Finance.Members.GetChildren(
    si, BRApi.Finance.Dim.DimTypeId.Account, "TotalPL")

' Check if member is base (leaf)
Dim isBase As Boolean = memberInfo.IsBase
```

## BRApi.Finance.Dim
```vb
' Dimension Type IDs
BRApi.Finance.Dim.DimTypeId.Entity
BRApi.Finance.Dim.DimTypeId.Account
BRApi.Finance.Dim.DimTypeId.Scenario
BRApi.Finance.Dim.DimTypeId.Time
BRApi.Finance.Dim.DimTypeId.View
BRApi.Finance.Dim.DimTypeId.Currency
BRApi.Finance.Dim.DimTypeId.Consolidation
BRApi.Finance.Dim.DimTypeId.UD1  ' through UD8
```

## BRApi.ErrorLog
```vb
' Log informational message
BRApi.ErrorLog.LogMessage(si, "Step 1: Loading configuration")

' Log error
BRApi.ErrorLog.LogMessage(si, $"Error in step {stepName}: {ex.Message}")
```

## BRApi.Database
```vb
' Execute SQL query (use Microsoft.Data.SqlClient on .NET 8)
Using conn As New Microsoft.Data.SqlClient.SqlConnection(connString)
    conn.Open()
    Using cmd As New SqlCommand(sql, conn)
        cmd.Parameters.AddWithValue("@param", value)
        Using reader = cmd.ExecuteReader()
            While reader.Read()
                ' Process rows
            End While
        End Using
    End Using
End Using
```

## Substitution Variables
```vb
' Read substitution variables for configuration
Dim varValue As String = BRApi.Finance.SubVars.GetSubVarValue(
    si, "YearTarget")
```

## HS (Host Server) Namespace
```vb
' Application server information
Dim appName As String = HS.AppServer.ApplicationName

' Current user info
Dim userName As String = HS.User.UserName
```

## Common POV String Format
```
S#Actual.Y#2024.P#M1.E#Corp.A#Revenue.V#Periodic.C#Local.Con#None
```
- `S#` = Scenario
- `Y#` = Year
- `P#` = Period (M1-M12, or named: January, Q1, YearTotal)
- `E#` = Entity
- `A#` = Account
- `V#` = View (YTD, Periodic, QTD)
- `C#` = Currency (Local, USD, Translated)
- `Con#` = Consolidation (None, Proportion, Elimination)
