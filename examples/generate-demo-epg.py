#!/usr/bin/env python3
"""Génère un XMLTV de démonstration qui « colle » à examples/demo-playlist.m3u.

Le fichier produit couvre 48 h à partir de l'heure courante : pratique pour
tester le guide TV, l'association automatique par `tvg-id` et l'affichage
« en cours / à suivre » sans dépendre d'un fournisseur EPG.

Usage :
    python3 examples/generate-demo-epg.py [-o examples/demo-epg.xml] [--hours 24]
"""
from __future__ import annotations

import argparse
import textwrap
from datetime import UTC, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

# Identifiants alignés sur examples/demo-playlist.m3u
CHANNELS: list[tuple[str, str, str]] = [
    ("demo.sport.hd", "PrimeTV Demo Sport HD", "Sport"),
    ("demo.sport.multi", "PrimeTV Demo Sport Multibitérate", "Sport"),
    ("demo.sport.dash", "PrimeTV Demo DASH", "Sport"),
    ("demo.docs.uhd", "PrimeTV Demo Documentaire", "Documentaires"),
    ("demo.docs.mp4", "PrimeTV Demo MP4", "Documentaires"),
    ("demo.movies.sintel", "PrimeTV Demo Film", "Cinéma"),
    ("demo.movies.elephants", "PrimeTV Demo Film 2", "Cinéma"),
    ("demo.kids.bunny", "PrimeTV Demo Jeunesse", "Jeunesse"),
    ("demo.radio.groove", "PrimeTV Demo Radio Groove", "Radio"),
    ("demo.radio.drone", "PrimeTV Demo Radio Ambient", "Radio"),
    ("demo.radio.indie", "PrimeTV Demo Radio Indie", "Radio"),
    ("demo.news.ar", "PrimeTV Demo News AR", "Actualités"),
    ("demo.news.fr", "PrimeTV Demo News FR", "Actualités"),
    ("demo.religion", "PrimeTV Demo Religion", "Religion"),
    ("demo.encrypted", "PrimeTV Demo Chiffré (AES-128)", "Technique"),
]

# Grilles par catégorie : (titre, description, durée en minutes)
GRIDS: dict[str, list[tuple[str, str, int]]] = {
    "Sport": [
        ("Multiplex — Direct", "Résumé technique de flux HLS/DASH de test.", 60),
        ("Magazine sportif", "Analyse et actualité sportive (contenu de démonstration).", 45),
        ("Rencontre de démonstration", "Diffusion d'un flux public Big Buck Bunny.", 90),
    ],
    "Documentaires": [
        ("Nature & territoires", "Découverte des écosystèmes (extrait libre de droits).", 50),
        ("Sciences", "Vulgarisation scientifique (contenu de démonstration).", 40),
        ("Histoire", "Archives et récits (contenu de démonstration).", 55),
    ],
    "Cinéma": [
        ("Sintel", "Court-métrage libre de la Blender Foundation.", 15),
        ("Elephants Dream", "Court-métrage libre de la Blender Foundation.", 11),
        ("Tears of Steel", "Court-métrage libre de la Blender Foundation.", 12),
    ],
    "Jeunesse": [
        ("Dessins animés", "Programme jeunesse (flux de test).", 25),
        ("Ateliers créatifs", "Activités pour les enfants (démonstration).", 20),
    ],
    "Radio": [
        ("Sélection musicale", "Playlist électronique / ambient de SomaFM.", 120),
        ("Session live", "Concert de démonstration.", 60),
    ],
    "Actualités": [
        ("Journal", "Bulletin d'information (contenu de démonstration).", 30),
        ("Débat", "Émission de débat (contenu de démonstration).", 45),
    ],
    "Religion": [
        ("Culte", "Programme religieux (contenu de démonstration).", 60),
        ("Chants", "Chants et lectures (contenu de démonstration).", 30),
    ],
    "Technique": [
        ("Test de chiffrement", "Manifeste AES-128 public : vérifie la détection DRM.", 60),
        ("Test de sous-titres", "Vérifie le rendu des pistes de sous-titres.", 30),
    ],
}


def xmltv_time(moment: datetime) -> str:
    """Format XMLTV : 'YYYYMMDDHHMMSS +0000'."""
    return moment.strftime("%Y%m%d%H%M%S +0000")


def build(hours: int) -> str:
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE tv SYSTEM "xmltv.dtd">',
        "",
        "<!-- Généré par examples/generate-demo-epg.py — contenu de démonstration. -->",
        f'<tv generator-info-name="PrimeTV demo" generator-info-url="https://github.com/HamdiSouissi/primeTV">',
    ]
    for channel_id, name, group in CHANNELS:
        lines.append(f'  <channel id="{escape(channel_id)}">')
        lines.append(f"    <display-name>{escape(name)}</display-name>")
        lines.append(f"    <display-name>{escape(group)}</display-name>")
        lines.append("  </channel>")
    lines.append("")

    for channel_id, _name, group in CHANNELS:
        grid = GRIDS.get(group, GRIDS["Documentaires"])
        cursor = now
        end = now + timedelta(hours=hours)
        index = 0
        while cursor < end:
            title, description, minutes = grid[index % len(grid)]
            stop = min(cursor + timedelta(minutes=minutes), end)
            suffix = " — rediffusion" if index >= len(grid) else ""
            lines += [
                f'  <programme start="{xmltv_time(cursor)}" stop="{xmltv_time(stop)}" channel="{escape(channel_id)}">',
                f"    <title lang=\"fr\">{escape(title + suffix)}</title>",
                f"    <desc lang=\"fr\">{escape(description)}</desc>",
                f"    <category lang=\"fr\">{escape(group)}</category>",
                "    <icon src=\"https://dummyimage.com/320x180/1e293b/94a3b8&amp;text=PrimeTV\"/>",
                f"    <episode-num system=\"onscreen\">{index + 1}</episode-num>",
                "  </programme>",
            ]
            cursor = stop
            index += 1
        lines.append("")
    lines.append("</tv>")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="XMLTV de démonstration pour PrimeTV")
    parser.add_argument("-o", "--output", default=str(Path(__file__).with_name("demo-epg.xml")))
    parser.add_argument("--hours", type=int, default=24, help="Fenêtre générée (défaut : 24)")
    args = parser.parse_args()
    target = Path(args.output)
    target.write_text(build(max(1, args.hours)), encoding="utf-8")
    print(textwrap.dedent(f"""
        XMLTV écrit : {target}
        Chaînes : {len(CHANNELS)} · fenêtre : {args.hours} h
        Import : Interface → EPG → Importer un fichier (ou POST /api/v1/epg/upload)
    """).strip())


if __name__ == "__main__":
    main()
