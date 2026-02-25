namespace OneStream.IDE.RoslynService.Models;

public record CompilationResult(
    bool Success,
    List<DiagnosticInfo> Errors,
    List<DiagnosticInfo> Warnings,
    List<DiagnosticInfo> AllDiagnostics
);

public record DiagnosticInfo(
    string Severity,
    string Message,
    string Code,
    int Line,
    int Column
);

public record DeprecatedScanResult(
    int DeprecatedApisFound,
    List<DeprecatedApiFinding> Issues
);

public record DeprecatedApiFinding(
    string Api,
    string Severity,
    string Replacement,
    string Note,
    int Line
);
