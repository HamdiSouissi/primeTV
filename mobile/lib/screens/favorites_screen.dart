import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import 'player_screen.dart';

/// Favoris du profil actif (synchronisés avec le serveur).
class FavoritesScreen extends StatefulWidget {
  const FavoritesScreen({super.key});

  @override
  State<FavoritesScreen> createState() => _FavoritesScreenState();
}

class _FavoritesScreenState extends State<FavoritesScreen> {
  late Future<List<Channel>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<AppState>().api.favorites();
  }

  Future<void> _refresh() async {
    setState(() => _future = context.read<AppState>().api.favorites());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<List<Channel>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return EmptyView(
              icon: Icons.cloud_off,
              title: 'Favoris indisponibles',
              description: '${snapshot.error}',
              action: FilledButton(onPressed: _refresh, child: const Text('Réessayer')),
            );
          }
          final favorites = snapshot.data ?? const <Channel>[];
          if (favorites.isEmpty) {
            return const EmptyView(
              icon: Icons.favorite_border,
              title: 'Aucun favori',
              description: 'Ajoutez des chaînes avec le cœur pour les retrouver ici. Chaque profil a sa propre liste.',
            );
          }
          return ListView.builder(
            padding: const EdgeInsets.fromLTRB(14, 8, 14, 20),
            itemCount: favorites.length,
            itemBuilder: (context, index) {
              final channel = favorites[index];
              return ChannelTile(
                channel: channel,
                isFavorite: state.favorites.contains(channel.id),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(builder: (_) => PlayerScreen(channel: channel)),
                ),
                onToggleFavorite: () async {
                  await state.toggleFavorite(channel);
                  await _refresh();
                },
              );
            },
          );
        },
      ),
    );
  }
}
