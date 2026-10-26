/// Modèles de données de l'API PrimeTV (désérialisation défensive).
library;

int _asInt(dynamic value, [int fallback = 0]) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value) ?? fallback;
  return fallback;
}

bool _asBool(dynamic value, [bool fallback = false]) {
  if (value is bool) return value;
  if (value is num) return value != 0;
  if (value is String) return value.toLowerCase() == 'true';
  return fallback;
}

String _asString(dynamic value, [String fallback = '']) =>
    value is String ? value : (value?.toString() ?? fallback);

class User {
  const User({required this.id, required this.email, required this.username, this.fullName, this.role = 'user'});

  final String id;
  final String email;
  final String username;
  final String? fullName;
  final String role;

  factory User.fromJson(Map<String, dynamic> json) => User(
        id: _asString(json['id']),
        email: _asString(json['email']),
        username: _asString(json['username']),
        fullName: json['full_name'] as String?,
        role: _asString(json['role'], 'user'),
      );
}

class Profile {
  const Profile({required this.id, required this.name, this.isKids = false, this.isDefault = false, this.language = 'fr'});

  final String id;
  final String name;
  final bool isKids;
  final bool isDefault;
  final String language;

  factory Profile.fromJson(Map<String, dynamic> json) => Profile(
        id: _asString(json['id']),
        name: _asString(json['name'], 'Principal'),
        isKids: _asBool(json['is_kids']),
        isDefault: _asBool(json['is_default']),
        language: _asString(json['language'], 'fr'),
      );
}

class Category {
  const Category({required this.name, required this.slug, this.color, this.icon});

  final String name;
  final String slug;
  final String? color;
  final String? icon;

  factory Category.fromJson(Map<String, dynamic> json) => Category(
        name: _asString(json['name']),
        slug: _asString(json['slug']),
        color: json['color'] as String?,
        icon: json['icon'] as String?,
      );
}

class Language {
  const Language({required this.name, required this.code, this.flag});

  final String name;
  final String code;
  final String? flag;

  factory Language.fromJson(Map<String, dynamic> json) => Language(
        name: _asString(json['name']),
        code: _asString(json['code']),
        flag: json['flag'] as String?,
      );
}

class Channel {
  const Channel({
    required this.id,
    required this.name,
    this.logo,
    this.streamType = 'hls',
    this.quality,
    this.isRadio = false,
    this.isEncrypted = false,
    this.encryption = 'unknown',
    this.drmSystems = const [],
    this.status = 'unknown',
    this.priority = 0,
    this.category,
    this.language,
    this.groupTitle,
    this.isFavorite = false,
  });

  final String id;
  final String name;
  final String? logo;
  final String streamType;
  final String? quality;
  final bool isRadio;
  final bool isEncrypted;
  final String encryption;
  final List<String> drmSystems;
  final String status;
  final int priority;
  final Category? category;
  final Language? language;
  final String? groupTitle;
  final bool isFavorite;

  bool get hasDrm => drmSystems.any((system) => ['widevine', 'playready', 'fairplay'].contains(system));

  factory Channel.fromJson(Map<String, dynamic> json) => Channel(
        id: _asString(json['id']),
        name: _asString(json['name'], 'Chaîne'),
        logo: json['logo'] as String?,
        streamType: _asString(json['stream_type'], 'hls'),
        quality: json['quality'] as String?,
        isRadio: _asBool(json['is_radio']),
        isEncrypted: _asBool(json['is_encrypted']),
        encryption: _asString(json['encryption'], 'unknown'),
        drmSystems: (json['drm_systems'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(growable: false),
        status: _asString(json['status'], 'unknown'),
        priority: _asInt(json['priority']),
        category: json['category'] is Map<String, dynamic>
            ? Category.fromJson(json['category'] as Map<String, dynamic>)
            : null,
        language: json['language'] is Map<String, dynamic>
            ? Language.fromJson(json['language'] as Map<String, dynamic>)
            : null,
        groupTitle: json['group_title'] as String?,
        isFavorite: _asBool(json['is_favorite']),
      );
}

class ChannelPage {
  const ChannelPage({required this.items, required this.total, required this.page, required this.pages});

  final List<Channel> items;
  final int total;
  final int page;
  final int pages;

  factory ChannelPage.fromJson(Map<String, dynamic> json) => ChannelPage(
        items: (json['items'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(Channel.fromJson)
            .toList(growable: false),
        total: _asInt(json['total']),
        page: _asInt(json['page'], 1),
        pages: _asInt(json['pages'], 1),
      );
}

class Playback {
  const Playback({
    required this.channelId,
    required this.url,
    required this.streamType,
    required this.isEncrypted,
    required this.encryption,
    this.directUrl,
    this.drmSystems = const [],
    this.hasKeys = false,
    this.message,
    this.variants = const [],
  });

  final String channelId;
  final String url;
  final String? directUrl;
  final String streamType;
  final bool isEncrypted;
  final String encryption;
  final List<String> drmSystems;
  final bool hasKeys;
  final String? message;
  final List<Map<String, dynamic>> variants;

  factory Playback.fromJson(Map<String, dynamic> json) => Playback(
        channelId: _asString(json['channel_id']),
        url: _asString(json['url']),
        directUrl: json['direct_url'] as String?,
        streamType: _asString(json['stream_type'], 'hls'),
        isEncrypted: _asBool(json['is_encrypted']),
        encryption: _asString(json['encryption'], 'unknown'),
        drmSystems: (json['drm_systems'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(growable: false),
        hasKeys: _asBool(json['has_keys']),
        message: json['message'] as String?,
        variants: (json['variants'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .toList(growable: false),
      );
}

class Playlist {
  const Playlist({
    required this.id,
    required this.name,
    required this.channelCount,
    required this.sourceType,
    this.lastSyncAt,
    this.lastError,
  });

  final String id;
  final String name;
  final int channelCount;
  final String sourceType;
  final String? lastSyncAt;
  final String? lastError;

  factory Playlist.fromJson(Map<String, dynamic> json) => Playlist(
        id: _asString(json['id']),
        name: _asString(json['name']),
        channelCount: _asInt(json['channel_count']),
        sourceType: _asString(json['source_type'], 'url'),
        lastSyncAt: json['last_sync_at'] as String?,
        lastError: json['last_error'] as String?,
      );
}

class DashboardStats {
  const DashboardStats({
    required this.channels,
    required this.radios,
    required this.bouquets,
    required this.activeStreams,
    required this.encryptedStreams,
    required this.favorites,
    this.byCategory = const [],
  });

  final int channels;
  final int radios;
  final int bouquets;
  final int activeStreams;
  final int encryptedStreams;
  final int favorites;
  final List<Map<String, dynamic>> byCategory;

  factory DashboardStats.fromJson(Map<String, dynamic> json) => DashboardStats(
        channels: _asInt(json['channels']),
        radios: _asInt(json['radios']),
        bouquets: _asInt(json['bouquets']),
        activeStreams: _asInt(json['active_streams']),
        encryptedStreams: _asInt(json['encrypted_streams']),
        favorites: _asInt(json['favorites']),
        byCategory: (json['by_category'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .toList(growable: false),
      );
}

class ScanJob {
  const ScanJob({
    required this.id,
    required this.status,
    required this.progress,
    required this.total,
    required this.active,
    required this.offline,
    required this.encrypted,
    required this.drmProtected,
  });

  final String id;
  final String status;
  final int progress;
  final int total;
  final int active;
  final int offline;
  final int encrypted;
  final int drmProtected;

  double get ratio => total == 0 ? 0 : progress / total;

  factory ScanJob.fromJson(Map<String, dynamic> json) => ScanJob(
        id: _asString(json['id']),
        status: _asString(json['status'], 'queued'),
        progress: _asInt(json['progress']),
        total: _asInt(json['total']),
        active: _asInt(json['active']),
        offline: _asInt(json['offline']),
        encrypted: _asInt(json['encrypted']),
        drmProtected: _asInt(json['drm_protected']),
      );
}
