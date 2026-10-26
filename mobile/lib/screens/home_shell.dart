import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import 'channels_screen.dart';
import 'dashboard_screen.dart';
import 'favorites_screen.dart';
import 'settings_screen.dart';
import 'sources_screen.dart';

/// Navigation principale (5 onglets Material 3).
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  static const _titles = ['Accueil', 'Chaînes', 'Favoris', 'Sources', 'Réglages'];

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final pages = const [
      DashboardScreen(),
      ChannelsScreen(),
      FavoritesScreen(),
      SourcesScreen(),
      SettingsScreen(),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Text(_titles[_index], style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 20)),
            const Spacer(),
            if (state.activeProfile != null)
              ActionChip(
                avatar: const Icon(Icons.person_outline, size: 15),
                label: Text(state.activeProfile!.name, style: const TextStyle(fontSize: 11)),
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<Profile>(builder: (_) => const _ProfileSwitcher()),
                ),
              ),
          ],
        ),
      ),
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (index) => setState(() => _index = index),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard_outlined), selectedIcon: Icon(Icons.dashboard), label: 'Accueil'),
          NavigationDestination(icon: Icon(Icons.live_tv_outlined), selectedIcon: Icon(Icons.live_tv), label: 'Chaînes'),
          NavigationDestination(icon: Icon(Icons.favorite_border), selectedIcon: Icon(Icons.favorite), label: 'Favoris'),
          NavigationDestination(icon: Icon(Icons.cloud_download_outlined), selectedIcon: Icon(Icons.cloud_download), label: 'Sources'),
          NavigationDestination(icon: Icon(Icons.settings_outlined), selectedIcon: Icon(Icons.settings), label: 'Réglages'),
        ],
      ),
    );
  }
}

/// Sélecteur de profil affiché en feuille modale.
class _ProfileSwitcher extends StatelessWidget {
  const _ProfileSwitcher();

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(title: const Text('Choisir un profil')),
      body: ListView(
        children: [
          for (final profile in state.profiles)
            ListTile(
              leading: CircleAvatar(
                backgroundColor: profile.isKids ? Colors.orangeAccent : Colors.blueAccent,
                child: Icon(profile.isKids ? Icons.child_care : Icons.person, size: 18),
              ),
              title: Text(profile.name),
              subtitle: Text([
                if (profile.isDefault) 'par défaut',
                if (profile.isKids) 'enfant',
                'langue ${profile.language.toUpperCase()}',
              ].join(' · ')),
              trailing: state.profileId == profile.id ? const Icon(Icons.check, color: Colors.greenAccent) : null,
              onTap: () async {
                await state.selectProfile(profile);
                if (context.mounted) Navigator.of(context).pop(profile);
              },
            ),
        ],
      ),
    );
  }
}
