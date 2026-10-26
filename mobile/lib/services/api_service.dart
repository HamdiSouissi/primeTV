import '../core/api_client.dart';
import '../models/models.dart';

/// Façade typée de l'API REST PrimeTV.
class ApiService {
  ApiService(this.client);

  final ApiClient client;

  // ---------------------------------------------------------------- Auth
  Future<(String, String, User)> login(String email, String password) async {
    final data = await client.post('/auth/login', body: {'email': email, 'password': password});
    final map = data as Map<String, dynamic>;
    return (
      map['access_token'] as String,
      map['refresh_token'] as String,
      User.fromJson(map['user'] as Map<String, dynamic>),
    );
  }

  Future<(String, String, User)> register({
    required String email,
    required String username,
    required String password,
    String? fullName,
  }) async {
    final data = await client.post('/auth/register', body: {
      'email': email,
      'username': username,
      'password': password,
      if (fullName != null && fullName.isNotEmpty) 'full_name': fullName,
    });
    final map = data as Map<String, dynamic>;
    return (
      map['access_token'] as String,
      map['refresh_token'] as String,
      User.fromJson(map['user'] as Map<String, dynamic>),
    );
  }

  Future<User> me() async {
    final data = await client.get('/auth/me');
    return User.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Profile>> profiles() async {
    final data = await client.get('/profiles');
    return (data as List<dynamic>)
        .whereType<Map<String, dynamic>>()
        .map(Profile.fromJson)
        .toList(growable: false);
  }

  Future<Profile> createProfile(String name, {bool isKids = false, String? pin}) async {
    final data = await client.post('/profiles', body: {
      'name': name,
      'is_kids': isKids,
      if (pin != null && pin.isNotEmpty) 'pin': pin,
    });
    return Profile.fromJson(data as Map<String, dynamic>);
  }

  // ---------------------------------------------------------------- Catalogue
  Future<DashboardStats> dashboard() async {
    final data = await client.get('/stats/dashboard');
    return DashboardStats.fromJson(data as Map<String, dynamic>);
  }

  Future<ChannelPage> channels({
    String? search,
    String? category,
    String? language,
    bool? radio,
    bool? encrypted,
    String sort = 'priority',
    int page = 1,
    int pageSize = 30,
  }) async {
    final data = await client.get('/channels', query: {
      'q': (search == null || search.trim().isEmpty) ? null : search.trim(),
      'category': category,
      'language': language,
      'radio': radio,
      'encrypted': encrypted,
      'sort': sort,
      'page': page,
      'page_size': pageSize,
    });
    return ChannelPage.fromJson(data as Map<String, dynamic>);
  }

  Future<Channel> channel(String id) async {
    final data = await client.get('/channels/$id');
    return Channel.fromJson(data as Map<String, dynamic>);
  }

  Future<Playback> playback(String channelId, {bool proxy = true}) async {
    final data = await client.get('/channels/$channelId/play', query: {'proxy': proxy});
    return Playback.fromJson(data as Map<String, dynamic>);
  }

  Future<void> setChannelKey(String channelId, String kid, String key) =>
      client.put('/channels/$channelId/keys', body: {'kid': kid, 'key': key});

  Future<Map<String, dynamic>> nowNext(String channelId) async {
    final data = await client.get('/channels/$channelId/epg');
    return data as Map<String, dynamic>;
  }

  // ---------------------------------------------------------------- Favoris / historique
  Future<List<Channel>> favorites() async {
    final data = await client.get('/favorites');
    return (data as List<dynamic>).whereType<Map<String, dynamic>>().map((item) {
      final channel = item['channel'];
      if (channel is Map<String, dynamic>) {
        return Channel.fromJson({...channel, 'is_favorite': true});
      }
      return null;
    }).whereType<Channel>().toList(growable: false);
  }

  Future<void> addFavorite(String channelId) => client.post('/favorites', body: {'channel_id': channelId});

  Future<void> removeFavorite(String channelId) => client.delete('/favorites/$channelId');

  Future<void> recordHistory(String channelId, int positionSeconds, int durationSeconds) =>
      client.post('/history', body: {
        'channel_id': channelId,
        'position_seconds': positionSeconds,
        'duration_seconds': durationSeconds,
        'device': 'android',
      });

  Future<List<Channel>> continueWatching() async {
    final data = await client.get('/history/continue');
    return (data as List<dynamic>).whereType<Map<String, dynamic>>().map((item) {
      final channel = item['channel'];
      if (channel is Map<String, dynamic>) return Channel.fromJson(channel);
      return null;
    }).whereType<Channel>().toList(growable: false);
  }

  // ---------------------------------------------------------------- Sources
  Future<List<Playlist>> playlists() async {
    final data = await client.get('/playlists');
    return (data as List<dynamic>).whereType<Map<String, dynamic>>().map(Playlist.fromJson).toList(growable: false);
  }

  Future<Map<String, dynamic>> importUrl(String url, {String? name}) async {
    final data = await client.post('/playlists', body: {
      'source_type': 'url',
      'url': url,
      if (name != null && name.isNotEmpty) 'name': name,
      'replace': true,
    });
    return data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> importText(String content, {String? name}) async {
    final data = await client.post('/playlists', body: {
      'source_type': 'text',
      'content': content,
      if (name != null && name.isNotEmpty) 'name': name,
      'replace': true,
    });
    return data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> syncPlaylist(String id) async {
    final data = await client.post('/playlists/$id/sync');
    return data as Map<String, dynamic>;
  }

  Future<void> deletePlaylist(String id) => client.delete('/playlists/$id');

  // ---------------------------------------------------------------- Scan
  Future<ScanJob> startScan({bool probe = true, String? playlistId}) async {
    final data = await client.post('/scan', body: {
      'probe': probe,
      if (playlistId != null) 'playlist_id': playlistId,
    });
    return ScanJob.fromJson(data as Map<String, dynamic>);
  }

  Future<ScanJob?> latestScan() async {
    final data = await client.get('/scan/latest');
    if (data is Map<String, dynamic>) return ScanJob.fromJson(data);
    return null;
  }

  Future<ScanJob> scanJob(String id) async {
    final data = await client.get('/scan/jobs/$id');
    return ScanJob.fromJson(data as Map<String, dynamic>);
  }

  // ---------------------------------------------------------------- EPG
  Future<List<Map<String, dynamic>>> guide({int hours = 24}) async {
    final data = await client.get('/epg/guide', query: {'hours': hours});
    return (data as List<dynamic>).whereType<Map<String, dynamic>>().toList(growable: false);
  }
}
