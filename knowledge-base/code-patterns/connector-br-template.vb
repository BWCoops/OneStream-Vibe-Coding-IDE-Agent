' ===================================================================
' Rule: Connector Business Rule Template
' Type: Connector BR
' Description: Data adapter pattern for loading data from
'              external sources into OneStream.
' Target: .NET 8 (Platform v9.x)
' NOTE: Uses Microsoft.Data.SqlClient (NOT System.Data.SqlClient)
' ===================================================================

Imports System
Imports System.Data
Imports System.Collections.Generic
Imports Microsoft.Data.SqlClient
Imports OneStream.Shared.Common
Imports OneStream.Shared.Wcf

Namespace OneStream.BusinessRule.Connector.DataLoadTemplate
    Public Class MainClass
        Public Function Main(ByVal si As SessionInfo, ByVal globals As BRGlobals,
                           ByVal api As Object, ByVal args As ConnectorArgs) As Object

            Dim stepName As String = "Initialization"

            Try
                ' Step 1: Get connection parameters from substitution variables
                stepName = "Configuration"
                Dim connectionString As String = BRApi.Utilities.GetSubstVarValue(
                    si, "V#SQLConnectionString", String.Empty)

                If String.IsNullOrEmpty(connectionString) Then
                    Throw New ArgumentException("Substitution variable V#SQLConnectionString not configured")
                End If

                ' Step 2: Build parameterised query (prevent SQL injection)
                stepName = "Query Construction"
                Dim entityFilter As String = api.Pov.Entity.Name
                Dim periodFilter As String = api.Pov.Time.Name

                Dim query As String = "SELECT AccountCode, Amount, Currency " &
                                     "FROM dbo.FinancialData " &
                                     "WHERE Entity = @Entity AND Period = @Period"

                ' Step 3: Execute data retrieval
                ' REQ-DATA-001: Load financial data from source system
                stepName = "Data Retrieval"
                Dim dt As New DataTable()

                Using conn As New SqlConnection(connectionString)
                    Using cmd As New SqlCommand(query, conn)
                        cmd.Parameters.AddWithValue("@Entity", entityFilter)
                        cmd.Parameters.AddWithValue("@Period", periodFilter)
                        cmd.CommandTimeout = 120

                        conn.Open()
                        Using reader As SqlDataReader = cmd.ExecuteReader()
                            dt.Load(reader)
                        End Using
                    End Using
                End Using

                BRApi.ErrorLog.LogMessage(si,
                    String.Format("Connector BR: Retrieved {0} rows for Entity={1}, Period={2}",
                    dt.Rows.Count, entityFilter, periodFilter))

                ' Step 4: Map and load data
                stepName = "Data Mapping"
                Dim loadCount As Integer = 0

                For Each row As DataRow In dt.Rows
                    Dim accountCode As String = row("AccountCode").ToString()
                    Dim amount As Decimal = CDec(row("Amount"))

                    ' Map external account code to OneStream member
                    Dim memberId As Integer = BRApi.Finance.Members.GetMemberId(
                        si, BRApi.Finance.Dim.DimTypeId.Account, accountCode)

                    If memberId > 0 Then
                        BRApi.Finance.Data.SetDataCellValue(
                            si, api.Pov.Scenario.MemberId,
                            api.Pov.Time.MemberId,
                            api.Pov.Entity.MemberId,
                            memberId, amount)
                        loadCount += 1
                    Else
                        BRApi.ErrorLog.LogMessage(si,
                            String.Format("WARNING: Unmapped account '{0}' skipped", accountCode))
                    End If
                Next

                ' Step 5: Summary
                stepName = "Completion"
                BRApi.ErrorLog.LogMessage(si,
                    String.Format("Connector BR complete: {0}/{1} rows loaded",
                    loadCount, dt.Rows.Count))

                Return Nothing

            Catch ex As Exception
                BRApi.ErrorLog.LogMessage(si, stepName & ": " & ex.Message)
                Throw
            Finally
                ' Connection disposed via Using statement
            End Try
        End Function
    End Class
End Namespace
