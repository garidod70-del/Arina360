using Microsoft.AspNetCore.Identity;

namespace ARENA360.Api.Models;

public sealed class ArenaUser : IdentityUser
{
    public string FullName { get; set; } = string.Empty;
    public DateTimeOffset CreatedAtUtc { get; set; } = DateTimeOffset.UtcNow;
}
