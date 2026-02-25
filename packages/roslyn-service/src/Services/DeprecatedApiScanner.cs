using OneStream.IDE.RoslynService.Models;

namespace OneStream.IDE.RoslynService.Services;

public class DeprecatedApiScanner
{
    private static readonly List<DeprecatedApiEntry> DeprecatedApis =
    [
        new("BRApi.Utilities.EncryptText", "8.0", "System.Security.Cryptography (AES/RSA via .NET native)", "error",
            "Removed in .NET 8 runtime. Will cause compilation failure."),
        new("BRApi.Utilities.DecryptText", "8.0", "System.Security.Cryptography (AES/RSA via .NET native)", "error",
            "Removed in .NET 8 runtime. Will cause compilation failure."),
        new("WinSCP", "8.0", "SSH.NET (Renci.SshNet)", "error",
            "WinSCP COM interop not supported on .NET 8."),
        new("ERPConnect45", "8.0", "ERPConnectStandard20.dll", "error",
            "Assembly targets .NET Framework 4.5."),
        new("System.Data.SqlClient", "8.0", "Microsoft.Data.SqlClient", "warning",
            "System.Data.SqlClient is no longer updated."),
    ];

    public DeprecatedScanResult Scan(string sourceCode, string? platformVersion)
    {
        var majorVersion = ParseMajorVersion(platformVersion);
        var findings = new List<DeprecatedApiFinding>();

        var lines = sourceCode.Split('\n');
        for (var lineIdx = 0; lineIdx < lines.Length; lineIdx++)
        {
            foreach (var api in DeprecatedApis)
            {
                var depMajor = ParseMajorVersion(api.DeprecatedIn);
                if (majorVersion < depMajor) continue;

                if (lines[lineIdx].Contains(api.Api, StringComparison.OrdinalIgnoreCase))
                {
                    findings.Add(new DeprecatedApiFinding(
                        Api: api.Api,
                        Severity: api.Severity,
                        Replacement: api.Replacement,
                        Note: api.Note,
                        Line: lineIdx + 1
                    ));
                }
            }
        }

        return new DeprecatedScanResult(
            DeprecatedApisFound: findings.Count,
            Issues: findings
        );
    }

    private static int ParseMajorVersion(string? version)
    {
        if (string.IsNullOrEmpty(version)) return 8;
        var parts = version.Split('.');
        return int.TryParse(parts[0], out var major) ? major : 8;
    }
}

public record DeprecatedApiEntry(
    string Api,
    string DeprecatedIn,
    string Replacement,
    string Severity,
    string Note
);
