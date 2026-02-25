' ===================================================================
' Rule: Dashboard Extender Template
' Type: Dashboard Extender
' Description: Custom dashboard component that provides
'              dynamic data grids and visualizations.
' Target: .NET 8 (Platform v9.x)
' ===================================================================

Imports System
Imports System.Data
Imports System.Collections.Generic
Imports OneStream.Shared.Common
Imports OneStream.Shared.Wcf

Namespace OneStream.BusinessRule.Dashboard.ExtenderTemplate
    Public Class MainClass
        Public Function Main(ByVal si As SessionInfo, ByVal globals As BRGlobals,
                           ByVal api As Object, ByVal args As DashboardExtenderArgs) As Object

            Dim stepName As String = "Initialization"

            Try
                ' Step 1: Determine action type
                stepName = "Action Routing"
                Select Case args.FunctionType
                    Case Is = DashboardExtenderFunctionType.CustomCalculate
                        Return HandleCustomCalculate(si, globals, api, args)
                    Case Is = DashboardExtenderFunctionType.GetCustomGridDataSet
                        Return HandleGetGridData(si, globals, api, args)
                    Case Else
                        Return Nothing
                End Select

            Catch ex As Exception
                BRApi.ErrorLog.LogMessage(si, stepName & ": " & ex.Message)
                Throw
            End Try
        End Function

        ' REQ-DASH-001: Provide consolidation summary grid
        Private Function HandleGetGridData(ByVal si As SessionInfo, ByVal globals As BRGlobals,
                                          ByVal api As Object, ByVal args As DashboardExtenderArgs) As DataTable

            Dim stepName As String = "Grid Data Retrieval"

            Try
                Dim dt As New DataTable()
                dt.Columns.Add("Entity", GetType(String))
                dt.Columns.Add("Account", GetType(String))
                dt.Columns.Add("Amount", GetType(Decimal))
                dt.Columns.Add("Status", GetType(String))

                ' Retrieve data from OneStream cube
                stepName = "Cube Query"
                ' Build POV-based data retrieval
                Dim scenarioId As Integer = args.NameValuePairs.XFGetValue("ScenarioId", 0)
                Dim timeId As Integer = args.NameValuePairs.XFGetValue("TimeId", 0)

                ' Populate grid with aggregated data
                stepName = "Data Population"
                ' This would be populated with actual cube data retrieval

                Return dt

            Catch ex As Exception
                BRApi.ErrorLog.LogMessage(si, "GetGridData." & stepName & ": " & ex.Message)
                Throw
            End Try
        End Function

        Private Function HandleCustomCalculate(ByVal si As SessionInfo, ByVal globals As BRGlobals,
                                              ByVal api As Object, ByVal args As DashboardExtenderArgs) As Object
            ' Handle custom dashboard calculations
            Return Nothing
        End Function
    End Class
End Namespace
