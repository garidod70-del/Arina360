class ApiConfig {
  // Set either --dart-define=ARENA_API_BASE_URL=https://host
  // or the legacy --dart-define=API_BASE_URL=https://host/api/v1.
  static const String _configuredUrl = String.fromEnvironment(
    'ARENA_API_BASE_URL',
    defaultValue: String.fromEnvironment('API_BASE_URL', defaultValue: ''),
  );

  static String get baseUrl {
    var value = _configuredUrl.trim();
    while (value.endsWith('/')) {
      value = value.substring(0, value.length - 1);
    }
    // ApiClient appends /api/v1 to every endpoint. Accept both a host URL
    // and a URL that already includes the API prefix without duplicating it.
    if (value.toLowerCase().endsWith('/api/v1')) {
      value = value.substring(0, value.length - '/api/v1'.length);
    }
    return value;
  }

  static bool get isConfigured => baseUrl.isNotEmpty;

  static bool get usesHttps =>
      Uri.tryParse(baseUrl)?.scheme.toLowerCase() == 'https';
}
