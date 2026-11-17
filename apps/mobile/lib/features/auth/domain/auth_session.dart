class AuthSession {
  const AuthSession({
    required this.accessToken,
    required this.phone,
    required this.roles,
  });

  final String accessToken;
  final String phone;
  final List<String> roles;

  factory AuthSession.fromJson(Map<String, dynamic> json) {
    final user = json['user'] as Map<String, dynamic>;
    return AuthSession(
      accessToken: json['access_token'] as String,
      phone: user['phone'] as String,
      roles: (user['roles'] as List<dynamic>).cast<String>(),
    );
  }
}
