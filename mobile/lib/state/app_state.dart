import 'package:flutter/foundation.dart';

import '../core/api_client.dart';
import '../core/storage.dart';
import '../models/models.dart';
import '../services/api_service.dart';

/// État global : session, profils, favoris et préférences.
class AppState extends ChangeNotifier {
  AppState({ApiClient? client, SecureStore? secureStore, PreferencesStore? preferences})
      : _client = client ?? ApiClient(),
        _secureStore = secureStore ?? SecureStore(),
        _preferences = preferences ?? PreferencesStore();

  final ApiClient _client;
  final SecureStore _secureStore;
  final PreferencesStore _preferences;

  late final ApiService api = ApiService(_client);

  User? user;
  List<Profile> profiles = const [];
  String? profileId;
  Set<String> favorites = <String>{};
  bool darkMode = true;
  bool authenticated = false;
  bool booting = true;

  Profile? get activeProfile {
    if (profiles.isEmpty) return null;
    return profiles.firstWhere((profile) => profile.id == profileId, orElse: () => profiles.first);
  }

  /// Restaure la session au démarrage.
  Future<void> bootstrap() async {
    darkMode = await _preferences.isDarkMode();
    final tokens = await _secureStore.readTokens();
    if (tokens != null) {
      _client.setTokens(accessToken: tokens.$1, refreshToken: tokens.$2);
      try {
        user = await api.me();
        authenticated = true;
        profileId = await _preferences.getProfileId();
        _client.setProfileId(profileId);
        await refreshProfiles();
        await refreshFavorites();
      } on ApiException {
        await _secureStore.clear();
        _client.clearTokens();
        authenticated = false;
      }
    }
    booting = false;
    notifyListeners();
  }

  Future<void> login(String email, String password) async {
    final (access, refresh, loggedUser) = await api.login(email, password);
    await _persistSession(access, refresh, loggedUser);
  }

  Future<void> register({
    required String email,
    required String username,
    required String password,
    String? fullName,
  }) async {
    final (access, refresh, loggedUser) =
        await api.register(email: email, username: username, password: password, fullName: fullName);
    await _persistSession(access, refresh, loggedUser);
  }

  Future<void> _persistSession(String access, String refresh, User loggedUser) async {
    _client.setTokens(accessToken: access, refreshToken: refresh);
    await _secureStore.saveTokens(access, refresh);
    user = loggedUser;
    authenticated = true;
    await refreshProfiles();
    if (profileId == null && profiles.isNotEmpty) {
      await selectProfile(profiles.first);
    } else {
      _client.setProfileId(profileId);
    }
    await refreshFavorites();
    notifyListeners();
  }

  Future<void> refreshProfiles() async {
    profiles = await api.profiles();
    if (profiles.isNotEmpty && profileId == null) {
      profileId = profiles.firstWhere((p) => p.isDefault, orElse: () => profiles.first).id;
      await _preferences.setProfileId(profileId);
      _client.setProfileId(profileId);
    }
    notifyListeners();
  }

  Future<void> selectProfile(Profile profile) async {
    profileId = profile.id;
    _client.setProfileId(profile.id);
    await _preferences.setProfileId(profile.id);
    await refreshFavorites();
    notifyListeners();
  }

  Future<void> refreshFavorites() async {
    try {
      final list = await api.favorites();
      favorites = list.map((channel) => channel.id).toSet();
      notifyListeners();
    } on ApiException {
      favorites = <String>{};
    }
  }

  Future<bool> toggleFavorite(Channel channel) async {
    final isFavorite = favorites.contains(channel.id);
    if (isFavorite) {
      await api.removeFavorite(channel.id);
      favorites.remove(channel.id);
    } else {
      await api.addFavorite(channel.id);
      favorites.add(channel.id);
    }
    notifyListeners();
    return !isFavorite;
  }

  Future<void> setDarkMode(bool value) async {
    darkMode = value;
    await _preferences.setDarkMode(value);
    notifyListeners();
  }

  Future<void> logout() async {
    await _secureStore.clear();
    _client.clearTokens();
    await _preferences.setProfileId(null);
    user = null;
    profiles = const [];
    profileId = null;
    favorites = <String>{};
    authenticated = false;
    notifyListeners();
  }

  @override
  void dispose() {
    _client.dispose();
    super.dispose();
  }
}
