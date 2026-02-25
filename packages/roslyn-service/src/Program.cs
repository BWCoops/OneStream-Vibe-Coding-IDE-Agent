using OneStream.IDE.RoslynService.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSingleton<CompilationService>();
builder.Services.AddSingleton<DeprecatedApiScanner>();

var app = builder.Build();

app.MapGet("/health", () => Results.Ok(new { Status = "healthy", Service = "roslyn-service" }));

app.MapPost("/api/compile", async (CompilationRequest request, CompilationService compiler) =>
{
    var result = await compiler.CompileAsync(request);
    return Results.Ok(result);
});

app.MapPost("/api/check-deprecated", async (DeprecatedCheckRequest request, DeprecatedApiScanner scanner) =>
{
    var result = scanner.Scan(request.SourceCode, request.PlatformVersion);
    return Results.Ok(result);
});

app.Run();

public record CompilationRequest(
    string SourceCode,
    string Language, // "vb.net" or "csharp"
    string TargetRuntime // "net8.0" or "net48"
);

public record DeprecatedCheckRequest(
    string SourceCode,
    string? PlatformVersion
);
