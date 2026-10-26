import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'config.dart';

/// Exception métier portant le message renvoyé par l'API.
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

/// Client HTTP minimal : JWT, en-tête de profil, rafraîchissement, erreurs normalisées.
class ApiClient {
  ApiClient({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  String? _accessToken;
  String? _refreshToken;
  String? _profileId;
  Future<void> Function()? onUnauthorized;

  String get baseUrl => AppConfig.apiBaseUrl;

  void setTokens({String? accessToken, String? refreshToken}) {
    _accessToken = accessToken ?? _accessToken;
    _refreshToken = refreshToken ?? _refreshToken;
  }

  void clearTokens() {
    _accessToken = null;
    _refreshToken = null;
  }

  String? get accessToken => _accessToken;
  String? get refreshToken => _refreshToken;

  void setProfileId(String? profileId) => _profileId = profileId;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
        if (_profileId != null) 'X-Profile-Id': _profileId!,
      };

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final cleaned = path.startsWith('/') ? path.substring(1) : path;
    final uri = Uri.parse('$baseUrl/$cleaned');
    if (query == null || query.isEmpty) return uri;
    final params = <String, String>{};
    query.forEach((key, value) {
      if (value == null) return;
      if (value is bool) {
        params[key] = value ? 'true' : 'false';
      } else {
        params[key] = value.toString();
      }
    });
    return uri.replace(queryParameters: {...uri.queryParameters, ...params});
  }

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) => _send('GET', path, query: query);

  Future<dynamic> post(String path, {Object? body, Map<String, dynamic>? query}) =>
      _send('POST', path, body: body, query: query);

  Future<dynamic> put(String path, {Object? body}) => _send('PUT', path, body: body);

  Future<dynamic> patch(String path, {Object? body}) => _send('PATCH', path, body: body);

  Future<dynamic> delete(String path) => _send('DELETE', path);

  Future<dynamic> _send(
    String method,
    String path, {
    Object? body,
    Map<String, dynamic>? query,
    bool retry = true,
  }) async {
    final request = http.Request(method, _uri(path, query));
    request.headers.addAll(_headers);
    if (body != null) request.body = jsonEncode(body);

    late http.Response response;
    try {
      final streamed = await _client.send(request).timeout(AppConfig.httpTimeout);
      response = await http.Response.fromStream(streamed);
    } on TimeoutException {
      throw ApiException('Le serveur met trop de temps à répondre');
    } catch (error) {
      throw ApiException('Serveur injoignable : vérifiez l’adresse de l’API ($baseUrl)');
    }

    if (response.statusCode == 401 && retry && _refreshToken != null) {
      final refreshed = await _tryRefresh();
      if (refreshed) return _send(method, path, body: body, query: query, retry: false);
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(utf8.decode(response.bodyBytes));
    }

    throw ApiException(_messageFrom(response), statusCode: response.statusCode);
  }

  Future<bool> _tryRefresh() async {
    try {
      final response = await _client
          .post(
            _uri('/auth/refresh'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'refresh_token': _refreshToken}),
          )
          .timeout(const Duration(seconds: 15));
      if (response.statusCode != 200) return false;
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      _accessToken = data['access_token'] as String?;
      _refreshToken = data['refresh_token'] as String? ?? _refreshToken;
      return _accessToken != null;
    } catch (_) {
      return false;
    }
  }

  String _messageFrom(http.Response response) {
    try {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      if (decoded is Map<String, dynamic>) {
        final error = decoded['error'];
        if (error is Map<String, dynamic> && error['message'] is String) {
          return error['message'] as String;
        }
        if (decoded['detail'] is String) return decoded['detail'] as String;
      }
    } catch (_) {
      // corps non JSON : message générique ci-dessous
    }
    if (response.statusCode == 401) return 'Authentification requise';
    if (response.statusCode == 403) return 'Accès refusé';
    if (response.statusCode == 404) return 'Ressource introuvable';
    if (response.statusCode == 429) return 'Trop de requêtes, patientez un instant';
    return 'Erreur serveur (${response.statusCode})';
  }

  void dispose() => _client.close();
}
