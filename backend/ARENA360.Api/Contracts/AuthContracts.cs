namespace ARENA360.Api.Contracts;

public sealed record RegisterRequest(
    string FullName,
    string Email,
    string PhoneNumber,
    string Password,
    string Role = "Organizer");

public sealed record LoginRequest(string Email, string Password);

public sealed record AuthResponse(
    string AccessToken,
    DateTimeOffset ExpiresAtUtc,
    string UserId,
    string FullName,
    string Email,
    string[] Roles);
