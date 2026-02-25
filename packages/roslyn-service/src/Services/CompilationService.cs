using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.VisualBasic;
using OneStream.IDE.RoslynService.Models;

namespace OneStream.IDE.RoslynService.Services;

public class CompilationService
{
    private static readonly MetadataReference[] CommonReferences =
    [
        MetadataReference.CreateFromFile(typeof(object).Assembly.Location),
        MetadataReference.CreateFromFile(typeof(Console).Assembly.Location),
        MetadataReference.CreateFromFile(typeof(System.Linq.Enumerable).Assembly.Location),
        MetadataReference.CreateFromFile(typeof(System.Collections.Generic.List<>).Assembly.Location),
        MetadataReference.CreateFromFile(typeof(System.Data.DataTable).Assembly.Location),
    ];

    public Task<CompilationResult> CompileAsync(CompilationRequest request)
    {
        var diagnostics = request.Language.ToLowerInvariant() switch
        {
            "vb.net" or "vb" or "visualbasic" => CompileVisualBasic(request.SourceCode),
            "csharp" or "c#" or "cs" => CompileCSharp(request.SourceCode),
            _ => [new DiagnosticInfo("error", $"Unsupported language: {request.Language}", "LANG001", 0, 0)]
        };

        var errors = diagnostics.Where(d => d.Severity == "error").ToList();
        var warnings = diagnostics.Where(d => d.Severity == "warning").ToList();

        return Task.FromResult(new CompilationResult(
            Success: errors.Count == 0,
            Errors: errors,
            Warnings: warnings,
            AllDiagnostics: diagnostics
        ));
    }

    private List<DiagnosticInfo> CompileCSharp(string sourceCode)
    {
        var syntaxTree = CSharpSyntaxTree.ParseText(sourceCode);
        var compilation = CSharpCompilation.Create(
            "OneStreamRule",
            syntaxTrees: [syntaxTree],
            references: CommonReferences,
            options: new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary)
        );

        return ExtractDiagnostics(compilation);
    }

    private List<DiagnosticInfo> CompileVisualBasic(string sourceCode)
    {
        var syntaxTree = VisualBasicSyntaxTree.ParseText(sourceCode);
        var compilation = VisualBasicCompilation.Create(
            "OneStreamRule",
            syntaxTrees: [syntaxTree],
            references: CommonReferences,
            options: new VisualBasicCompilationOptions(OutputKind.DynamicallyLinkedLibrary)
        );

        return ExtractDiagnostics(compilation);
    }

    private static List<DiagnosticInfo> ExtractDiagnostics(Compilation compilation)
    {
        using var ms = new MemoryStream();
        var emitResult = compilation.Emit(ms);

        return emitResult.Diagnostics
            .Where(d => d.Severity >= DiagnosticSeverity.Warning)
            .Select(d =>
            {
                var lineSpan = d.Location.GetLineSpan();
                return new DiagnosticInfo(
                    Severity: d.Severity == DiagnosticSeverity.Error ? "error" : "warning",
                    Message: d.GetMessage(),
                    Code: d.Id,
                    Line: lineSpan.StartLinePosition.Line + 1,
                    Column: lineSpan.StartLinePosition.Character + 1
                );
            })
            .ToList();
    }
}
