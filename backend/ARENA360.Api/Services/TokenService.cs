using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using ARENA360.Api.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.IdentityModel.Tokens;

namespace ARENA360.Api.Services;

public sealed class TokenService(IConfiguration configuration, UserManager<ArenaUser> userManager)
{
    public async Task<(string Token, DateTimeOffset ExpiresAt)> CreateAsync(ArenaUser user)
    {
        var secret = configuration["Jwt:Secret"];
        if (string.IsNullOrWhiteSpace(secret) || Encoding.UTF8.GetByteCount(secret) < 32)
            throw new InvalidOperationException("JWT secret is not configured. Set Jwt__Secret to a random value of at least 32 bytes.");

        var issuer = configuration["Jwt:Issuer"] ?? "ARENA360";
        var audience = configuration["Jwt:Audience"] ?? "ARENA360";
        var expires = DateTimeOffset.UtcNow.AddHours(12);
        var roles = await userManager.GetRolesAsync(user);
        var claims = new List<Claim>
        {
            new(JwtRegisteredClaimNames.Sub, user.Id),
            new(JwtRegisteredClaimNames.Email, user.Email ?? string.Empty),
            new(ClaimTypes.Name, user.FullName),
            new(ClaimTypes.NameIdentifier, user.Id)
        };
        claims.AddRange(roles.Select(role => new Claim(ClaimTypes.Role, role)));

        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret));
        var credentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);
        var jwt = new JwtSecurityToken(issuer, audience, claims,
            expires: expires.UtcDateTime, signingCredentials: credentials);
        return (new JwtSecurityTokenHandler().WriteToken(jwt), expires);
    }
}
