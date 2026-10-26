import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/config.dart';
import '../state/app_state.dart';
import '../theme/app_theme.dart';
import '../widgets/common.dart';

/// Réglages : compte, profils, thème et informations.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    return ListView(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 24),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                const CircleAvatar(radius: 24, backgroundColor: AppTheme.brand, child: Icon(Icons.person)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(state.user?.fullName ?? state.user?.username ?? 'Utilisateur',
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                      Text(state.user?.email ?? '', style: TextStyle(fontSize: 11, color: Colors.white.withOpacity(0.5))),
                      const SizedBox(height: 4),
                      Tag(
                        label: state.user?.role == 'admin' ? 'Administrateur' : 'Utilisateur',
                        icon: Icons.verified_user_outlined,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        const Text('Profils', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
        ...state.profiles.map(
          (profile) => Card(
            margin: const EdgeInsets.symmetric(vertical: 4),
            child: ListTile(
              leading: Icon(profile.isKids ? Icons.child_care : Icons.person_outline),
              title: Text(profile.name),
              subtitle: Text([
                if (profile.isDefault) 'par défaut',
                if (profile.isKids) 'enfant',
                'langue ${profile.language.toUpperCase()}',
              ].join(' · ')),
              trailing: state.profileId == profile.id
                  ? const Icon(Icons.check_circle, color: Colors.greenAccent)
                  : const Icon(Icons.chevron_right),
              onTap: () => state.selectProfile(profile),
            ),
          ),
        ),
        TextButton.icon(
          onPressed: () => _createProfile(context),
          icon: const Icon(Icons.add, size: 18),
          label: const Text('Ajouter un profil'),
        ),
        const SizedBox(height: 8),
        const Text('Apparence', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
        Card(
          child: SwitchListTile(
            value: state.darkMode,
            onChanged: state.setDarkMode,
            title: const Text('Mode sombre'),
            subtitle: const Text('Interface sombre recommandée pour le direct', style: TextStyle(fontSize: 11)),
          ),
        ),
        const SizedBox(height: 14),
        const Text('À propos', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('PrimeTV ${AppConfig.version} — open source (MIT)',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                const SizedBox(height: 6),
                Text('API : ${AppConfig.apiBaseUrl}',
                    style: TextStyle(fontSize: 10.5, color: Colors.white.withOpacity(0.5))),
                const SizedBox(height: 6),
                const Text(
                  '⚖️ Plateforme de lecture : aucun contenu ni clé n’est fourni. Utilisez uniquement des '
                  'sources que vous êtes autorisé à regarder. Les DRM ne sont pas contournés.',
                  style: TextStyle(fontSize: 10.5, height: 1.45),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        OutlinedButton.icon(
          onPressed: () => state.logout(),
          style: OutlinedButton.styleFrom(foregroundColor: Colors.redAccent),
          icon: const Icon(Icons.logout, size: 18),
          label: const Text('Se déconnecter'),
        ),
      ],
    );
  }

  Future<void> _createProfile(BuildContext context) async {
    final nameController = TextEditingController();
    var isKids = false;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: const Text('Nouveau profil'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Nom du profil')),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                value: isKids,
                onChanged: (value) => setDialogState(() => isKids = value),
                title: const Text('Profil enfant'),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Annuler')),
            FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Créer')),
          ],
        ),
      ),
    );
    if (confirmed == true && nameController.text.trim().isNotEmpty) {
      final state = context.read<AppState>();
      await state.api.createProfile(nameController.text.trim(), isKids: isKids);
      await state.refreshProfiles();
    }
    nameController.dispose();
  }
}
