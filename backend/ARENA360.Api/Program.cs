using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using ARENA360.Api.Contracts;
using ARENA360.Api.Data;
using ARENA360.Api.Models;
using ARENA360.Api.Services;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

var connectionString = builder.Configuration.GetConnectionString("ArenaDb")
    ?? "Host=localhost;Port=5432;Database=arena360;Username=postgres;Password=postgres";

builder.Services.AddDbContext<ArenaDbContext>(options => options.UseNpgsql(connectionString));
builder.Services.AddIdentityCore<ArenaUser>(options =>
{
    options.User.RequireUniqueEmail = true;
    options.Password.RequiredLength = 8;
    options.Password.RequireDigit = true;
    options.Password.RequireUppercase = false;
    options.Password.RequireLowercase = true;
    options.Password.RequireNonAlphanumeric = false;
})
.AddRoles<IdentityRole>()
.AddEntityFrameworkStores<ArenaDbContext>()
.AddSignInManager()
.AddDefaultTokenProviders();

var jwtSecret = builder.Configuration["Jwt:Secret"] ?? new string('0', 32);
var signingKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtSecret));
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"] ?? "ARENA360",
            ValidateAudience = true,
            ValidAudience = builder.Configuration["Jwt:Audience"] ?? "ARENA360",
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            IssuerSigningKey = signingKey,
            ClockSkew = TimeSpan.FromSeconds(30),
            NameClaimType = ClaimTypes.Name,
            RoleClaimType = ClaimTypes.Role
        };
    });
builder.Services.AddAuthorization();
builder.Services.AddScoped<TokenService>();
builder.Services.AddCors(options =>
{
    options.AddPolicy("AdminWeb", policy =>
        policy.WithOrigins(builder.Configuration["AdminWeb:Origin"] ?? "http://localhost:5173")
            .AllowAnyHeader().AllowAnyMethod());
});
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();
app.UseCors("AdminWeb");
app.UseAuthentication();
app.UseAuthorization();
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.MapGet("/api/health", () => Results.Ok(new
{
    name = "ARENA 360 API",
    status = "healthy",
    version = "0.2.0",
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

var auth = app.MapGroup("/api/auth").WithTags("Authentication");
auth.MapPost("/register", async (
    RegisterRequest request,
    UserManager<ArenaUser> users,
    RoleManager<IdentityRole> roles,
    TokenService tokens) =>
{
    if (string.IsNullOrWhiteSpace(request.FullName) ||
        string.IsNullOrWhiteSpace(request.Email) ||
        string.IsNullOrWhiteSpace(request.PhoneNumber) ||
        string.IsNullOrWhiteSpace(request.Password))
        return Results.BadRequest(new { message = "Бүх талбарыг бөглөнө үү." });

    var role = string.Equals(request.Role, "Referee", StringComparison.OrdinalIgnoreCase)
        ? "Referee" : "Organizer";
    var email = request.Email.Trim().ToLowerInvariant();
    if (await users.FindByEmailAsync(email) is not null)
        return Results.Conflict(new { message = "Энэ и-мэйл бүртгэлтэй байна." });

    var user = new ArenaUser
    {
        UserName = email,
        Email = email,
        PhoneNumber = request.PhoneNumber.Trim(),
        FullName = request.FullName.Trim()
    };
    var created = await users.CreateAsync(user, request.Password);
    if (!created.Succeeded)
        return Results.BadRequest(new
        {
            message = "Бүртгэл үүсгэж чадсангүй.",
            errors = created.Errors.Select(e => e.Description)
        });

    if (!await roles.RoleExistsAsync(role))
        await roles.CreateAsync(new IdentityRole(role));
    await users.AddToRoleAsync(user, role);

    try
    {
        var (token, expires) = await tokens.CreateAsync(user);
        return Results.Ok(new AuthResponse(token, expires, user.Id, user.FullName, email, new[] { role }));
    }
    catch (InvalidOperationException ex)
    {
        return Results.Problem(ex.Message, statusCode: 503);
    }
});

auth.MapPost("/login", async (
    LoginRequest request,
    UserManager<ArenaUser> users,
    TokenService tokens) =>
{
    var user = await users.FindByEmailAsync(request.Email.Trim().ToLowerInvariant());
    if (user is null || !await users.CheckPasswordAsync(user, request.Password))
        return Results.Unauthorized();

    try
    {
        var (token, expires) = await tokens.CreateAsync(user);
        var userRoles = (await users.GetRolesAsync(user)).ToArray();
        return Results.Ok(new AuthResponse(token, expires, user.Id, user.FullName,
            user.Email ?? string.Empty, userRoles));
    }
    catch (InvalidOperationException ex)
    {
        return Results.Problem(ex.Message, statusCode: 503);
    }
});

app.MapGet("/api/account/me", async (ClaimsPrincipal principal, UserManager<ArenaUser> users) =>
{
    var id = principal.FindFirstValue(ClaimTypes.NameIdentifier);
    var user = id is null ? null : await users.FindByIdAsync(id);
    return user is null
        ? Results.NotFound()
        : Results.Ok(new
        {
            user.Id, user.FullName, user.Email, user.PhoneNumber,
            roles = await users.GetRolesAsync(user)
        });
}).RequireAuthorization();

app.Run();
