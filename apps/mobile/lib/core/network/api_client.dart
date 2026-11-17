import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;

  const ApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  String get _baseUrl {
    var value = ApiConfig.baseUrl.trim();
    while (value.endsWith('/')) {
      value = value.substring(0, value.length - 1);
    }
    return value;
  }

  Future<Map<String, dynamic>> post(
    String path, {
    required Map<String, dynamic> body,
  }) async {
    if (!ApiConfig.isConfigured) {
      throw const ApiException(
        0,
        'Серверийн хаяг тохируулаагүй байна. ARENA_API_BASE_URL шаардлагатай.',
      );
    }
    final uri = Uri.parse('$_baseUrl/api/v1$path');
    final response = await _client
        .post(
          uri,
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 20));
    final decoded = response.body.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(
        response.statusCode,
        decoded['detail']?.toString() ?? 'Сервертэй холбогдоход алдаа гарлаа.',
      );
    }
    return decoded;
  }

  Future<Map<String, dynamic>> get(String path, {required String token}) async {
    if (!ApiConfig.isConfigured) {
      throw const ApiException(0, 'Серверийн хаяг тохируулаагүй байна.');
    }
    final response = await _client
        .get(
          Uri.parse('$_baseUrl/api/v1$path'),
          headers: {'Authorization': 'Bearer $token'},
        )
        .timeout(const Duration(seconds: 20));
    final decoded = response.body.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(
        response.statusCode,
        decoded['detail']?.toString() ?? 'Сервертэй холбогдоход алдаа гарлаа.',
      );
    }
    return decoded;
  }

  void close() => _client.close();
}
