var builder = WebApplication.CreateBuilder(args);
builder.Services.AddCors(options =>
{
    options.AddPolicy("AdminWeb", policy =>
        policy.WithOrigins(
                builder.Configuration["AdminWeb:Origin"] ?? "http://localhost:5173")
            .AllowAnyHeader()
            .AllowAnyMethod());
});
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();
app.UseCors("AdminWeb");
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.MapGet("/api/health", () => Results.Ok(new
{
    name = "ARENA 360 API",
    status = "healthy",
    version = "0.1.0",
    timestampUtc = DateTimeOffset.UtcNow
})).WithName("HealthCheck");

app.MapGet("/api/modules", () => Results.Ok(new[]
{
    new { key = "referees", name = "Шүүгч", status = "foundation" },
    new { key = "competitions", name = "Тэмцээн", status = "planned" },
    new { key = "clubs", name = "Клуб, секц", status = "planned" },
    new { key = "venues", name = "Заал түрээс", status = "planned" },
    new { key = "training", name = "Сургалт", status = "planned" },
    new { key = "fitness", name = "Фитнес", status = "planned" },
    new { key = "marketplace", name = "Спорт бараа", status = "planned" }
})).WithName("ListModules");

app.Run();
