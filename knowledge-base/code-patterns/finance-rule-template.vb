' ===================================================================
' Rule: Finance Rule Template
' Type: Finance Rule
' Description: Standard OneStream Finance Rule pattern with
'              structured error handling, substitution variables,
'              and BRApi logging.
' Target: .NET 8 (Platform v9.x)
' ===================================================================

Imports System
Imports System.Data
Imports System.Collections.Generic
Imports OneStream.Shared.Common
Imports OneStream.Shared.Wcf

Namespace OneStream.BusinessRule.Finance.FinanceRuleTemplate
    Public Class MainClass
        Public Function Main(ByVal si As SessionInfo, ByVal globals As BRGlobals,
                           ByVal api As FinanceRulesApi, ByVal args As FinanceRulesArgs) As Object

            Dim stepName As String = "Initialization"

            Try
                ' Step 1: Configuration via substitution variables
                stepName = "Configuration"
                Dim scenarioName As String = api.Pov.Scenario.Name
                Dim entityName As String = api.Pov.Entity.Name
                Dim periodName As String = api.Pov.Time.Name

                ' Step 2: Determine rule applicability
                stepName = "Applicability Check"
                If Not api.Pov.Scenario.Name.Equals("Actual", StringComparison.OrdinalIgnoreCase) Then
                    Return Nothing ' Only process for Actual scenario
                End If

                ' Step 3: Data retrieval
                stepName = "Data Retrieval"
                Dim dt As DataTable = BRApi.Finance.Data.GetDataTableForCellsModifiedSinceLastCertify(
                    si, api.Pov.Scenario.MemberId, api.Pov.Time.MemberId,
                    api.Pov.Entity.MemberId)

                If dt Is Nothing OrElse dt.Rows.Count = 0 Then
                    Return Nothing
                End If

                ' Step 4: Business logic (consolidation calculation)
                stepName = "Business Logic"
                For Each row As DataRow In dt.Rows
                    Dim accountId As Integer = CInt(row("AccountId"))
                    Dim amount As Decimal = CDec(row("Amount"))

                    ' Example: Apply intercompany elimination
                    ' REQ-CON-001: Eliminate intercompany revenue/expense
                    If IsIntercompanyAccount(si, accountId) Then
                        BRApi.Finance.Data.SetDataCellValue(
                            si, api.Pov.Scenario.MemberId,
                            api.Pov.Time.MemberId,
                            api.Pov.Entity.MemberId,
                            accountId, -amount)
                    End If
                Next

                ' Step 5: Logging
                stepName = "Completion Logging"
                BRApi.ErrorLog.LogMessage(si,
                    String.Format("Finance Rule completed: Entity={0}, Period={1}, Rows={2}",
                    entityName, periodName, dt.Rows.Count))

                Return Nothing

            Catch ex As Exception
                BRApi.ErrorLog.LogMessage(si, stepName & ": " & ex.Message)
                Throw
            Finally
                ' Cleanup resources
            End Try
        End Function

        Private Function IsIntercompanyAccount(ByVal si As SessionInfo, ByVal accountId As Integer) As Boolean
            ' Check if account is tagged as intercompany
            Dim memberInfo = BRApi.Finance.Members.GetMemberInfo(si, accountId)
            Return memberInfo IsNot Nothing AndAlso
                   memberInfo.Member.GetAttributeValue("IsIntercompany", "False").Equals("True")
        End Function
    End Class
End Namespace
