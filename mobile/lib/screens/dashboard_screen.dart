import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../models/models.dart';
import '../state/app_state.dart';
import '../theme/app_theme.dart';
import '../widgets/common.dart';
import 'player_screen.dart';

/// Tableau de bord : indicateurs, sport & arabe en tête, reprise de lecture.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late Future<_DashboardData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_DashboardData> _load() async {
    final api = context.read<AppState>().api;
    final results = await Future.wait([
      api.dashboard(),
      api.channels(category: 'sport', pageSize: 8),
      api.channels(language: 'ar', pageSize: 8),
      api.continueWatching(),
    ]);
    return _DashboardData(
      stats: results[0] as DashboardStats,
      sport: (results[1] as ChannelPage).items,
      arabic: (results[2] as ChannelPage).items,
      history: results[3] as List<Channel>,
    );
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  void _openPlayer(Channel channel) {
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => PlayerScreen(channel: channel)));
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<_DashboardData>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return EmptyView(
              icon: Icons.cloud_off,
              title: 'Tableau de bord indisponible',
              description: snapshot.error is ApiException
                  ? (snapshot.error as ApiException).message
                  : 'Vérifiez la connexion à l’API.',
              action: FilledButton(onPressed: _refresh, child: const Text('Réessayer')),
            );
          }
          final data = snapshot.data!;
          return ListView(
            padding: const EdgeInsets.fromLTRB(14, 6, 14, 24),
            children: [
              Text(
                'Bonjour ${state.user?.fullName?.split(' ').first ?? state.user?.username ?? ''}',
                style: const TextStyle(fontSize: 13, color: Colors.white54, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 2),
              Text(
                '${data.stats.channels} chaînes disponibles',
                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 14),
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                childAspectRatio: 1.75,
                mainAxisSpacing: 10,
                crossAxisSpacing: 10,
                children: [
                  StatCard(label: 'Chaînes', value: '${data.stats.channels}', icon: Icons.live_tv, hint: '${data.stats.radios} radios'),
                  StatCard(label: 'Bouquets', value: '${data.stats.bouquets}', icon: Icons.folder_copy),
                  StatCard(label: 'Actifs', value: '${data.stats.activeStreams}', icon: Icons.wifi, hint: 'dernier scan'),
                  StatCard(label: 'Chiffrés', value: '${data.stats.encryptedStreams}', icon: Icons.lock_outline),
                ],
              ),
              const SizedBox(height: 18),
              _Section(
                title: 'Sport en direct',
                subtitle: 'Les chaînes sportives en priorité',
                children: data.sport,
                state: state,
                onTap: _openPlayer,
              ),
              _Section(
                title: 'Chaînes arabes',
                subtitle: 'News, sport, religion et divertissement',
                children: data.arabic,
                state: state,
                onTap: _openPlayer,
              ),
              if (data.history.isNotEmpty) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Text('Reprendre', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                    const Spacer(),
                    Icon(Icons.history, size: 16, color: Colors.white.withOpacity(0.4)),
                  ],
                ),
                const SizedBox(height: 8),
                SizedBox(
                  height: 82,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: data.history.length,
                    separatorBuilder: (_, __) => const SizedBox(width: 8),
                    itemBuilder: (context, index) {
                      final channel = data.history[index];
                      return GestureDetector(
                        onTap: () => _openPlayer(channel),
                        child: Container(
                          width: 190,
                          padding: const EdgeInsets.all(9),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.05),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: Colors.white.withOpacity(0.07)),
                          ),
                          child: Row(
                            children: [
                              ChannelLogo(channel: channel, width: 46, height: 38),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  channel.name,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.brand.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppTheme.brand.withOpacity(0.25)),
                ),
                child: const Text(
                  '⚖️ PrimeTV est un lecteur : n’utilisez que des sources que vous êtes autorisé à regarder. '
                  'Les flux protégés par DRM ne sont pas contournés.',
                  style: TextStyle(fontSize: 10.5, height: 1.45, color: Colors.white70),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _DashboardData {
  const _DashboardData({
    required this.stats,
    required this.sport,
    required this.arabic,
    required this.history,
  });

  final DashboardStats stats;
  final List<Channel> sport;
  final List<Channel> arabic;
  final List<Channel> history;
}

class _Section extends StatelessWidget {
  const _Section({
    required this.title,
    required this.subtitle,
    required this.children,
    required this.state,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final List<Channel> children;
  final AppState state;
  final void Function(Channel) onTap;

  @override
  Widget build(BuildContext context) {
    if (children.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 14),
        Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
        Text(subtitle, style: TextStyle(fontSize: 11, color: Colors.white.withOpacity(0.5))),
        const SizedBox(height: 8),
        for (final channel in children)
          ChannelTile(
            channel: channel,
            isFavorite: state.favorites.contains(channel.id),
            onTap: () => onTap(channel),
            onToggleFavorite: () => state.toggleFavorite(channel),
          ),
      ],
    );
  }
}
