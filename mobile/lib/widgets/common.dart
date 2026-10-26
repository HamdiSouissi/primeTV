import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../models/models.dart';
import '../theme/app_theme.dart';

/// Logo de chaîne avec repli sur les initiales.
class ChannelLogo extends StatelessWidget {
  const ChannelLogo({super.key, required this.channel, this.width = 64, this.height = 44});

  final Channel channel;
  final double width;
  final double height;

  @override
  Widget build(BuildContext context) {
    final initials = channel.name
        .replaceAll(RegExp(r'[^\p{L}\p{N} ]', unicode: true), ' ')
        .trim()
        .split(RegExp(r'\s+'))
        .take(2)
        .map((part) => part.isEmpty ? '' : part.characters.first.toUpperCase())
        .join();

    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
      ),
      clipBehavior: Clip.antiAlias,
      alignment: Alignment.center,
      child: channel.logo == null || channel.logo!.isEmpty
          ? Text(initials, style: const TextStyle(fontWeight: FontWeight.bold))
          : CachedNetworkImage(
              imageUrl: channel.logo!,
              fit: BoxFit.contain,
              placeholder: (_, __) => const SizedBox.shrink(),
              errorWidget: (_, __, ___) => Text(initials, style: const TextStyle(fontWeight: FontWeight.bold)),
            ),
    );
  }
}

/// Pastille d'information compacte.
class Tag extends StatelessWidget {
  const Tag({super.key, required this.label, this.color, this.icon});

  final String label;
  final Color? color;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final tone = color ?? AppTheme.brand;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: tone.withOpacity(0.16),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 11, color: tone),
            const SizedBox(width: 3),
          ],
          Text(label, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: tone)),
        ],
      ),
    );
  }
}

/// Ligne de chaîne : logo, nom, badges et bouton favori.
class ChannelTile extends StatelessWidget {
  const ChannelTile({
    super.key,
    required this.channel,
    required this.isFavorite,
    required this.onTap,
    required this.onToggleFavorite,
  });

  final Channel channel;
  final bool isFavorite;
  final VoidCallback onTap;
  final VoidCallback onToggleFavorite;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Row(
            children: [
              ChannelLogo(channel: channel),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      channel.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      [
                        channel.category?.name ?? 'Non classée',
                        if (channel.language != null) '${channel.language!.flag ?? ''} ${channel.language!.name}',
                      ].join(' · '),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 11, color: Colors.white.withOpacity(0.55)),
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 4,
                      runSpacing: 4,
                      children: [
                        Tag(label: channel.streamType.toUpperCase()),
                        if (channel.quality != null) Tag(label: channel.quality!, color: Colors.lightBlueAccent),
                        if (channel.isRadio) const Tag(label: 'Radio', color: Colors.tealAccent, icon: Icons.radio),
                        if (channel.isEncrypted)
                          Tag(
                            label: channel.encryption.toUpperCase(),
                            color: Colors.purpleAccent,
                            icon: Icons.lock_outline,
                          ),
                        if (channel.status == 'active')
                          const Tag(label: 'En ligne', color: Colors.greenAccent),
                      ],
                    ),
                  ],
                ),
              ),
              IconButton(
                onPressed: onToggleFavorite,
                tooltip: isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris',
                icon: Icon(
                  isFavorite ? Icons.favorite : Icons.favorite_border,
                  color: isFavorite ? Colors.pinkAccent : Colors.white38,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Carte statistique du tableau de bord.
class StatCard extends StatelessWidget {
  const StatCard({super.key, required this.label, required this.value, this.icon, this.hint});

  final String label;
  final String value;
  final IconData? icon;
  final String? hint;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (icon != null) Icon(icon, size: 16, color: AppTheme.brand),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    label.toUpperCase(),
                    style: TextStyle(fontSize: 10, letterSpacing: 0.6, color: Colors.white.withOpacity(0.55)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(value, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
            if (hint != null)
              Text(hint!, style: TextStyle(fontSize: 11, color: Colors.white.withOpacity(0.5))),
          ],
        ),
      ),
    );
  }
}

/// État vide illustré.
class EmptyView extends StatelessWidget {
  const EmptyView({super.key, required this.icon, required this.title, this.description, this.action});

  final IconData icon;
  final String title;
  final String? description;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 42, color: AppTheme.brand.withOpacity(0.8)),
            const SizedBox(height: 12),
            Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700), textAlign: TextAlign.center),
            if (description != null) ...[
              const SizedBox(height: 6),
              Text(
                description!,
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: Colors.white.withOpacity(0.55)),
              ),
            ],
            if (action != null) ...[const SizedBox(height: 14), action!],
          ],
        ),
      ),
    );
  }
}
