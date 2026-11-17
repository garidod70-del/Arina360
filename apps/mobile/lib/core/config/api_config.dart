class ApiConfig {
  // Build with --dart-define=ARENA_API_BASE_URL=https://your-api-host
  static const String baseUrl = String.fromEnvironment(
    'ARENA_API_BASE_URL',
    defaultValue: '',
  );

  static bool get isConfigured => baseUrl.trim().isNotEmpty;
}
