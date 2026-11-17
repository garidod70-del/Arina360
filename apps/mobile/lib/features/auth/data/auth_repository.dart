import '../../../core/network/api_client.dart';

class AuthRepository {
  AuthRepository(this._api);

  final ApiClient _api;

  Future<Map<String, dynamic>> register({
    required String phone,
    required String password,
  }) {
    return _api.post('/auth/register', body: {
      'phone': phone,
      'password': password,
    });
  }

  Future<Map<String, dynamic>> login({
    required String phone,
    required String password,
  }) {
    return _api.post('/auth/login', body: {
      'phone': phone,
      'password': password,
    });
  }

  Future<Map<String, dynamic>> currentUser(String token) {
    return _api.get('/auth/me', token: token);
  }
}
