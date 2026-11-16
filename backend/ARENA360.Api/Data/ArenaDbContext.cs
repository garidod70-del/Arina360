using ARENA360.Api.Models;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace ARENA360.Api.Data;

public sealed class ArenaDbContext(DbContextOptions<ArenaDbContext> options)
    : IdentityDbContext<ArenaUser>(options)
{
}
