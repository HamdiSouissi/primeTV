import 'package:flutter_test/flutter_test.dart';
import 'package:primetv_mobile/core/config.dart';
import 'package:primetv_mobile/models/models.dart';

void main() {
  group('Channel', () {
    test('désérialise une chaîne complète', () {
      final channel = Channel.fromJson({
        'id': 'abc',
        'name': 'beIN SPORTS 1',
        'stream_type': 'hls',
        'quality': 'HD',
        'priority': 77,
        'is_encrypted': true,
        'encryption': 'clearkey',
        'drm_systems': <String>[],
        'category': {'name': 'Sport', 'slug': 'sport'},
        'language': {'name': 'Arabic', 'code': 'ar', 'flag': '🇸🇦'},
      });

      expect(channel.name, 'beIN SPORTS 1');
      expect(channel.category?.slug, 'sport');
      expect(channel.language?.code, 'ar');
      expect(channel.isEncrypted, isTrue);
      expect(channel.hasDrm, isFalse);
      expect(channel.priority, 77);
    });

    test('tolère les champs manquants', () {
      final channel = Channel.fromJson({'id': 'x'});
      expect(channel.name, 'Chaîne');
      expect(channel.streamType, 'hls');
      expect(channel.isRadio, isFalse);
    });

    test('détecte les DRM', () {
      final channel = Channel.fromJson({'id': 'y', 'name': 'DRM', 'drm_systems': ['widevine']});
      expect(channel.hasDrm, isTrue);
    });
  });

  test('ChannelPage pagine correctement', () {
    final page = ChannelPage.fromJson({
      'items': [
        {'id': '1', 'name': 'A'},
        {'id': '2', 'name': 'B'},
      ],
      'total': 12,
      'page': 2,
      'pages': 3,
    });
    expect(page.items.length, 2);
    expect(page.total, 12);
    expect(page.pages, 3);
  });

  test('AppConfig construit une URL absolue pour le proxy', () {
    final absolute = AppConfig.absoluteMediaUrl('/api/v1/streams/proxy?url=x');
    expect(absolute.startsWith('http'), isTrue);
    expect(absolute.contains('/api/v1/streams/proxy'), isTrue);
  });

  test('AppConfig conserve les URLs déjà absolues', () {
    const url = 'https://example.com/live.m3u8';
    expect(AppConfig.absoluteMediaUrl(url), url);
  });
}
