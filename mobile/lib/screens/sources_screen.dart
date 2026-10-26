import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../models/models.dart';
import '../state/app_state.dart';
import '../theme/app_theme.dart';
import '../widgets/common.dart';

/// Sources : playlists M3U/Xtream et scan du catalogue.
class SourcesScreen extends StatefulWidget {
  const SourcesScreen({super.key});

  @override
  State<SourcesScreen> createState() => _SourcesScreenState();
}

class _SourcesScreenState extends State<SourcesScreen> {
  late Future<List<Playlist>> _future;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _future = context.read<AppState>().api.playlists();
  }

  Future<void> _reload() async {
    setState(() => _future = context.read<AppState>().api.playlists());
    await _future;
  }

  Future<void> _showImportUrlDialog() async {
    final urlController = TextEditingController();
    final nameController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Importer une playlist'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Nom (optionnel)')),
            const SizedBox(height: 8),
            TextField(
              controller: urlController,
              keyboardType: TextInputType.url,
              decoration: const InputDecoration(labelText: 'URL M3U / M3U8 / HLS / DASH'),
            ),
            const SizedBox(height: 8),
            const Text('N’importez que des sources que vous êtes autorisé à utiliser.',
                style: TextStyle(fontSize: 10)),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Annuler')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Importer')),
        ],
      ),
    );
    if (confirmed == true && urlController.text.trim().isNotEmpty) {
      await _runImport(() => context.read<AppState>().api.importUrl(
            urlController.text.trim(),
            name: nameController.text.trim(),
          ));
    }
    urlController.dispose();
    nameController.dispose();
  }

  Future<void> _showImportTextDialog() async {
    final contentController = TextEditingController();
    final nameController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Coller une playlist M3U'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Nom')),
              const SizedBox(height: 8),
              TextField(
                controller: contentController,
                minLines: 6,
                maxLines: 10,
                style: const TextStyle(fontFamily: 'monospace', fontSize: 11),
                decoration: const InputDecoration(labelText: '#EXTM3U …'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Annuler')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Importer')),
        ],
      ),
    );
    if (confirmed == true && contentController.text.trim().isNotEmpty) {
      await _runImport(() => context.read<AppState>().api.importText(
            contentController.text,
            name: nameController.text.trim(),
          ));
    }
    contentController.dispose();
    nameController.dispose();
  }

  Future<void> _runImport(Future<Map<String, dynamic>> Function() action) async {
    setState(() => _busy = true);
    try {
      final result = await action();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Import terminé : ${result['created']} chaînes ajoutées')),
        );
      }
      await _reload();
    } on ApiException catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sync(Playlist playlist) async {
    await _runImport(() => context.read<AppState>().api.syncPlaylist(playlist.id));
  }

  Future<void> _scan() async {
    setState(() => _busy = true);
    try {
      final job = await context.read<AppState>().api.startScan();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Scan lancé (${job.total} chaînes) — résultats dans Tableau de bord')),
        );
      }
    } on ApiException catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 8, 14, 0),
          child: Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: _busy ? null : _showImportUrlDialog,
                  icon: const Icon(Icons.link, size: 18),
                  label: const Text('Importer une URL'),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filledTonal(
                onPressed: _busy ? null : _scan,
                tooltip: 'Scanner les flux',
                icon: const Icon(Icons.radar),
              ),
            ],
          ),
        ),
        Align(
          alignment: Alignment.centerRight,
          child: Padding(
            padding: const EdgeInsets.only(right: 14),
            child: TextButton.icon(
              onPressed: _busy ? null : _showImportTextDialog,
              icon: const Icon(Icons.content_paste, size: 16),
              label: const Text('Coller du M3U'),
            ),
          ),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _reload,
            child: FutureBuilder<List<Playlist>>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return EmptyView(
                    icon: Icons.cloud_off,
                    title: 'Sources indisponibles',
                    description: '${snapshot.error}',
                    action: FilledButton(onPressed: _reload, child: const Text('Réessayer')),
                  );
                }
                final playlists = snapshot.data ?? const <Playlist>[];
                if (playlists.isEmpty) {
                  return const EmptyView(
                    icon: Icons.cloud_download_outlined,
                    title: 'Aucune playlist',
                    description: 'Importez une URL M3U/M3U8, un portail Xtream depuis le web, ou collez du contenu M3U.',
                  );
                }
                return ListView.builder(
                  padding: const EdgeInsets.fromLTRB(14, 4, 14, 20),
                  itemCount: playlists.length,
                  itemBuilder: (context, index) {
                    final playlist = playlists[index];
                    return Card(
                      margin: const EdgeInsets.symmetric(vertical: 5),
                      child: ListTile(
                        leading: const Icon(Icons.playlist_play),
                        title: Text(playlist.name, maxLines: 1, overflow: TextOverflow.ellipsis),
                        subtitle: Text(
                          '${playlist.sourceType.toUpperCase()} · ${playlist.channelCount} chaînes'
                          '${playlist.lastError != null ? ' · ${playlist.lastError}' : ''}',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(fontSize: 11, color: Colors.white.withOpacity(0.5)),
                        ),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              tooltip: 'Synchroniser',
                              onPressed: _busy ? null : () => _sync(playlist),
                              icon: const Icon(Icons.sync, size: 20),
                            ),
                            IconButton(
                              tooltip: 'Supprimer',
                              onPressed: _busy
                                  ? null
                                  : () async {
                                      await context.read<AppState>().api.deletePlaylist(playlist.id);
                                      await _reload();
                                    },
                              icon: const Icon(Icons.delete_outline, size: 20, color: Colors.redAccent),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          color: AppTheme.brand.withOpacity(0.08),
          child: const Text(
            'Le scan teste chaque flux (HTTP + analyse HLS/DASH), met à jour les catégories et signale '
            'les chaînes chiffrées. Les clés ClearKey que vous fournissez restent sous votre responsabilité.',
            style: TextStyle(fontSize: 10, height: 1.4),
          ),
        ),
      ],
    );
  }
}
