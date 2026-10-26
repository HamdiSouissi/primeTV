import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/config.dart';
import '../models/models.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import 'player_screen.dart';

/// Catalogue : recherche, filtres par catégorie/langue, pagination.
class ChannelsScreen extends StatefulWidget {
  const ChannelsScreen({super.key});

  @override
  State<ChannelsScreen> createState() => _ChannelsScreenState();
}

class _ChannelsScreenState extends State<ChannelsScreen> {
  final _searchController = TextEditingController();
  Timer? _debounce;

  List<Channel> _channels = [];
  int _page = 1;
  int _pages = 1;
  bool _loading = true;
  String? _error;
  String? _category;
  String? _language;
  bool _radio = false;
  bool _encrypted = false;

  static const _categories = {
    'sport': 'Sport',
    'news': 'News',
    'movies': 'Movies',
    'kids': 'Kids',
    'music': 'Musique',
    'religion': 'Religion',
    'documentary': 'Documentaires',
  };

  static const _languages = {
    'ar': '🇸🇦 Arabe',
    'fr': '🇫🇷 Français',
    'en': '🇬🇧 Anglais',
    'tr': '🇹🇷 Turc',
    'es': '🇪🇸 Espagnol',
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load({int page = 1, bool append = false}) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await context.read<AppState>().api.channels(
            search: _searchController.text,
            category: _category,
            language: _language,
            radio: _radio ? true : null,
            encrypted: _encrypted ? true : null,
            page: page,
            pageSize: AppConfig.pageSize,
          );
      setState(() {
        _channels = append ? [..._channels, ...data.items] : data.items;
        _page = data.page;
        _pages = data.pages;
      });
    } on ApiException catch (error) {
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _onSearchChanged(String _) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () => _load());
  }

  void _openPlayer(Channel channel) {
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => PlayerScreen(channel: channel)));
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 4, 14, 0),
          child: TextField(
            controller: _searchController,
            onChanged: _onSearchChanged,
            decoration: InputDecoration(
              hintText: 'Rechercher une chaîne…',
              prefixIcon: const Icon(Icons.search, size: 20),
              suffixIcon: _searchController.text.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.close, size: 18),
                      onPressed: () {
                        _searchController.clear();
                        _load();
                      },
                    ),
            ),
          ),
        ),
        SizedBox(
          height: 46,
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            children: [
              FilterChip(
                label: const Text('Sport'),
                selected: _category == 'sport',
                onSelected: (selected) {
                  setState(() => _category = selected ? 'sport' : null);
                  _load();
                },
              ),
              const SizedBox(width: 6),
              for (final entry in _categories.entries)
                if (entry.key != 'sport') ...[
                  FilterChip(
                    label: Text(entry.value),
                    selected: _category == entry.key,
                    onSelected: (selected) {
                      setState(() => _category = selected ? entry.key : null);
                      _load();
                    },
                  ),
                  const SizedBox(width: 6),
                ],
              for (final entry in _languages.entries) ...[
                FilterChip(
                  label: Text(entry.value),
                  selected: _language == entry.key,
                  onSelected: (selected) {
                    setState(() => _language = selected ? entry.key : null);
                    _load();
                  },
                ),
                const SizedBox(width: 6),
              ],
              FilterChip(
                label: const Text('Radios'),
                selected: _radio,
                onSelected: (selected) {
                  setState(() => _radio = selected);
                  _load();
                },
              ),
              const SizedBox(width: 6),
              FilterChip(
                label: const Text('Chiffrées'),
                selected: _encrypted,
                onSelected: (selected) {
                  setState(() => _encrypted = selected);
                  _load();
                },
              ),
            ],
          ),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: () => _load(),
            child: Builder(
              builder: (context) {
                if (_loading && _channels.isEmpty) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (_error != null && _channels.isEmpty) {
                  return EmptyView(
                    icon: Icons.cloud_off,
                    title: 'Chargement impossible',
                    description: _error,
                    action: FilledButton(onPressed: () => _load(), child: const Text('Réessayer')),
                  );
                }
                if (_channels.isEmpty) {
                  return const EmptyView(
                    icon: Icons.tv_off,
                    title: 'Aucune chaîne',
                    description: 'Modifiez les filtres ou importez une playlist depuis l’onglet Sources.',
                  );
                }
                return ListView.builder(
                  padding: const EdgeInsets.fromLTRB(14, 4, 14, 20),
                  itemCount: _channels.length + (_page < _pages ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (index >= _channels.length) {
                      return Padding(
                        padding: const EdgeInsets.all(12),
                        child: Center(
                          child: _loading
                              ? const CircularProgressIndicator()
                              : OutlinedButton(
                                  onPressed: () => _load(page: _page + 1, append: true),
                                  child: const Text('Charger plus'),
                                ),
                        ),
                      );
                    }
                    final channel = _channels[index];
                    return ChannelTile(
                      channel: channel,
                      isFavorite: state.favorites.contains(channel.id),
                      onTap: () => _openPlayer(channel),
                      onToggleFavorite: () => state.toggleFavorite(channel),
                    );
                  },
                );
              },
            ),
          ),
        ),
      ],
    );
  }
}
