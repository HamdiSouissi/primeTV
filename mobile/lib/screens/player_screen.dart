import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:video_player/video_player.dart';

import '../core/api_client.dart';
import '../core/config.dart';
import '../models/models.dart';
import '../state/app_state.dart';
import '../theme/app_theme.dart';

/// Lecteur vidéo (HLS/DASH/MP4 via ExoPlayer) avec reprise et clés ClearKey.
class PlayerScreen extends StatefulWidget {
  const PlayerScreen({super.key, required this.channel});

  final Channel channel;

  @override
  State<PlayerScreen> createState() => _PlayerScreenState();
}

class _PlayerScreenState extends State<PlayerScreen> {
  VideoPlayerController? _controller;
  Timer? _progressTimer;
  Playback? _playback;
  Map<String, dynamic>? _epg;
  String? _error;
  bool _loading = true;
  int _lastPosition = 0;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final api = context.read<AppState>().api;
    try {
      final playback = await api.playback(widget.channel.id);
      _playback = playback;
      if (playback.drmSystems.any((system) => ['widevine', 'playready', 'fairplay'].contains(system))) {
        setState(() {
          _error = playback.message ??
              'Flux protégé par DRM : PrimeTV ne contourne pas ces protections. Utilisez une source libre.';
          _loading = false;
        });
        return;
      }
      final url = AppConfig.absoluteMediaUrl(playback.url);
      final controller = VideoPlayerController.networkUrl(Uri.parse(url));
      await controller.initialize();
      await controller.play();
      _controller = controller;
      _progressTimer = Timer.periodic(const Duration(seconds: 20), (_) => _saveProgress());
      unawaited(_loadEpg());
      setState(() => _loading = false);
    } on ApiException catch (error) {
      setState(() {
        _error = error.message;
        _loading = false;
      });
    } catch (_) {
      setState(() {
        _error = 'Lecture impossible : format non pris en charge ou flux hors ligne.';
        _loading = false;
      });
    }
  }

  Future<void> _loadEpg() async {
    try {
      final data = await context.read<AppState>().api.nowNext(widget.channel.id);
      if (mounted) setState(() => _epg = data);
    } catch (_) {
      // EPG facultatif
    }
  }

  void _saveProgress() {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) return;
    final position = controller.value.position.inSeconds;
    if (position == _lastPosition) return;
    _lastPosition = position;
    unawaited(
      context
          .read<AppState>()
          .api
          .recordHistory(widget.channel.id, position, controller.value.duration.inSeconds)
          .catchError((Object _) {}),
    );
  }

  Future<void> _addKey() async {
    final kidController = TextEditingController();
    final keyController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Ajouter une clé ClearKey'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Enregistrez une clé que vous êtes en droit d’utiliser (contenu libre ou abonnement).',
              style: TextStyle(fontSize: 12),
            ),
            const SizedBox(height: 12),
            TextField(controller: kidController, decoration: const InputDecoration(labelText: 'Key ID (KID)')),
            const SizedBox(height: 8),
            TextField(controller: keyController, decoration: const InputDecoration(labelText: 'Clé')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Annuler')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Enregistrer')),
        ],
      ),
    );
    if (confirmed == true) {
      try {
        await context.read<AppState>().api.setChannelKey(
              widget.channel.id,
              kidController.text.trim(),
              keyController.text.trim(),
            );
        await _initialize();
      } on ApiException catch (error) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
        }
      }
    }
    kidController.dispose();
    keyController.dispose();
  }

  @override
  void dispose() {
    _progressTimer?.cancel();
    _saveProgress();
    _controller?.dispose();
    SystemChrome.setPreferredOrientations(DeviceOrientation.values);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final isFavorite = state.favorites.contains(widget.channel.id);
    final controller = _controller;
    final current = _epg?['current'] as Map<String, dynamic>?;

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.channel.name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
        actions: [
          IconButton(
            tooltip: 'Plein écran',
            icon: const Icon(Icons.fullscreen),
            onPressed: () async {
              await SystemChrome.setPreferredOrientations([DeviceOrientation.landscapeLeft, DeviceOrientation.landscapeRight]);
              await Future<void>.delayed(const Duration(milliseconds: 200));
              if (mounted) {
                Navigator.of(context).push(MaterialPageRoute<void>(
                  builder: (_) => _FullscreenPlayer(controller: controller, title: widget.channel.name),
                ));
              }
            },
          ),
          IconButton(
            tooltip: isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris',
            icon: Icon(isFavorite ? Icons.favorite : Icons.favorite_border, color: isFavorite ? Colors.pinkAccent : null),
            onPressed: () => state.toggleFavorite(widget.channel),
          ),
        ],
      ),
      body: ListView(
        children: [
          AspectRatio(
            aspectRatio: 16 / 9,
            child: Container(
              color: Colors.black,
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(18),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Icon(Icons.warning_amber, color: Colors.amberAccent, size: 32),
                                const SizedBox(height: 8),
                                Text(_error!, textAlign: TextAlign.center, style: const TextStyle(fontSize: 12)),
                                if (_playback?.isEncrypted == true) ...[
                                  const SizedBox(height: 8),
                                  OutlinedButton.icon(
                                    onPressed: _addKey,
                                    icon: const Icon(Icons.key, size: 16),
                                    label: const Text('Ajouter mes clés'),
                                  ),
                                ],
                                const SizedBox(height: 8),
                                TextButton.icon(
                                  onPressed: _initialize,
                                  icon: const Icon(Icons.refresh, size: 16),
                                  label: const Text('Réessayer'),
                                ),
                              ],
                            ),
                          ),
                        )
                      : Stack(
                          alignment: Alignment.bottomCenter,
                          children: [
                            if (controller != null && controller.value.isInitialized)
                              AspectRatio(
                                aspectRatio: controller.value.aspectRatio,
                                child: VideoPlayer(controller),
                              ),
                            if (controller != null)
                              VideoProgressIndicator(
                                controller,
                                allowScrubbing: false,
                                colors: const VideoProgressColors(playedColor: AppTheme.brand),
                              ),
                            Positioned(
                              left: 8,
                              top: 8,
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: Colors.redAccent.withOpacity(0.85),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: const Text('LIVE',
                                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: Colors.white)),
                              ),
                            ),
                            if (_playback?.isEncrypted == true)
                              Positioned(
                                right: 8,
                                top: 8,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: Colors.purpleAccent.withOpacity(0.25),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    _playback!.hasKeys ? 'Clés actives' : 'Flux chiffré',
                                    style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700),
                                  ),
                                ),
                              ),
                          ],
                        ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    if (widget.channel.category != null) Chip(label: Text(widget.channel.category!.name)),
                    if (widget.channel.language != null)
                      Chip(label: Text('${widget.channel.language!.flag ?? ''} ${widget.channel.language!.name}')),
                    if (widget.channel.quality != null) Chip(label: Text(widget.channel.quality!)),
                    Chip(label: Text(widget.channel.streamType.toUpperCase())),
                  ],
                ),
                const SizedBox(height: 12),
                if (current != null) ...[
                  Text('En cours', style: TextStyle(fontSize: 11, color: Colors.white.withOpacity(0.5))),
                  Text(current['title']?.toString() ?? '',
                      style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
                  if (current['description'] != null) ...[
                    const SizedBox(height: 4),
                    Text(current['description'].toString(),
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12, color: Colors.white.withOpacity(0.6))),
                  ],
                ] else
                  Text('Aucun programme EPG associé à cette chaîne.',
                      style: TextStyle(fontSize: 12, color: Colors.white.withOpacity(0.5))),
                const SizedBox(height: 16),
                if (_playback?.isEncrypted == true && !(_playback?.hasKeys ?? false))
                  OutlinedButton.icon(
                    onPressed: _addKey,
                    icon: const Icon(Icons.key, size: 16),
                    label: const Text('Gérer mes clés de déchiffrement'),
                  ),
                const SizedBox(height: 10),
                Text(
                  'Rappel : ne diffusez que des flux autorisés. PrimeTV n’héberge aucun contenu et ne contourne aucun DRM.',
                  style: TextStyle(fontSize: 10, color: Colors.white.withOpacity(0.4)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Lecture plein écran (paysage).
class _FullscreenPlayer extends StatelessWidget {
  const _FullscreenPlayer({required this.controller, required this.title});

  final VideoPlayerController? controller;
  final String title;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(
          children: [
            Center(
              child: controller != null && controller!.value.isInitialized
                  ? AspectRatio(aspectRatio: controller!.value.aspectRatio, child: VideoPlayer(controller!))
                  : const CircularProgressIndicator(),
            ),
            Positioned(
              top: 8,
              left: 8,
              child: SafeArea(
                child: IconButton(
                  icon: const Icon(Icons.fullscreen_exit),
                  onPressed: () {
                    SystemChrome.setPreferredOrientations(DeviceOrientation.values);
                    Navigator.of(context).pop();
                  },
                ),
              ),
            ),
            Positioned(
              left: 16,
              bottom: 16,
              child: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            ),
          ],
        ),
      ),
    );
  }
}
