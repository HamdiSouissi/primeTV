/// Configuration de l'application mobile.
///
/// L'URL de l'API est injectée au build :
///   flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000/api/v1
///   flutter build web --dart-define=API_BASE_URL=/api/v1
class AppConfig {
  const AppConfig._();

  static const String appName = 'PrimeTV';
  static const String version = '1.0.0';

  /// Émulateur Android : 10.0.2.2 pointe vers la machine hôte.
  /// Sur un appareil physique, utilisez l'IP LAN du serveur.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );

  static const Duration httpTimeout = Duration(seconds: 45);
  static const int pageSize = 30;

  /// Convertit une URL de média relative (proxy `/api/v1/...`) en URL absolue.
  static String absoluteMediaUrl(String url) {
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    final base = Uri.tryParse(apiBaseUrl);
    if (base == null || base.host.isEmpty) return url; // Web : même origine
    final origin = Uri(scheme: base.scheme, host: base.host, port: base.hasPort ? base.port : null);
    return origin.resolve(url).toString();
  }
}
