# OneStream Business Rule Coding Standards

## Mandatory Patterns

### 1. Error Handling
Every business rule MUST use structured Try/Catch/Finally:
- `stepName` variable tracks current execution step
- Catch block logs via `BRApi.ErrorLog.LogMessage(si, stepName & ": " & ex.Message)`
- Catch block re-throws the exception (never swallow errors silently)
- Finally block cleans up resources

### 2. Configuration via Substitution Variables
Never hardcode:
- Connection strings: Use `BRApi.Utilities.GetSubstVarValue(si, "V#Name", defaultValue)`
- Environment-specific values: Entity names, account mappings, thresholds
- File paths and URLs

### 3. Inline Documentation
- Include requirement ID references: `' REQ-XXX: Description`
- Document non-obvious business logic
- Include rule header with: Rule name, Type, Requirements, Target runtime

### 4. Parameterised Queries
- NEVER concatenate user input into SQL strings
- Always use parameterised queries: `cmd.Parameters.AddWithValue("@Name", value)`
- Set explicit `CommandTimeout` for long-running queries

## Performance Patterns

### Do
- Use `DataTable` bulk operations over row-by-row processing
- Use `Using` statements for all IDisposable resources
- Cache member lookups when processing multiple rows
- Use `BRApi.Finance.Data.GetDataTableForCellsModifiedSinceLastCertify` for incremental processing

### Don't
- Don't loop through all members when you can filter at the API level
- Don't create new database connections inside loops
- Don't load entire dimension hierarchies when you need specific members
- Don't use `String.Format` for SQL — use parameterised queries

## .NET 8 Migration Checklist
- Replace `System.Data.SqlClient` with `Microsoft.Data.SqlClient`
- Replace `WinSCP` with `SSH.NET` (Renci.SshNet)
- Replace `ERPConnect45.dll` with `ERPConnectStandard20.dll`
- Remove `BRApi.Utilities.EncryptText`/`DecryptText` — use `System.Security.Cryptography`
- Use PAT authentication (not NTLM) for REST API calls
