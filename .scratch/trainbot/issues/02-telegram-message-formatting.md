Type: prototype
Status: resolved
Blocked by: 01

# Telegram Message Formatting & Interactive UX Prototype

## Question

What message format (HTML or MarkdownV2), visual hierarchy, and inline keyboard controls provide the cleanest, most scannable commute update for Telegram users on mobile, clearly highlighting delays, cancellations, and disruption communications without cluttering the screen?

## Answer

Prototyped and tested in [formatter.py](file:///home/skiwithuge/workspace/antigravity/trainbot/src/trainbot/bot/formatter.py) and [test_formatter.py](file:///home/skiwithuge/workspace/antigravity/trainbot/tests/test_formatter.py):
1. **Formatting Syntax**: Telegram HTML mode was chosen over MarkdownV2 to eliminate escaping issues with special punctuation (dashes, dots, parentheses).
2. **Visual Hierarchy**:
   - Header with route and refresh timestamp (e.g. `🚄 TER : Antibes ➔ Nice-Ville` | `Mis à jour à 07:02`).
   - Train departure cards with clear timing:
     - On-time: `⏰ 07:15 (🟢 À l'heure)`
     - Delayed: `⏰ <s>07:15</s> 07:27 (🟠 Retard +12 min)`
     - Cancelled: `⏰ <s>07:15</s> 🔴 Supprimé`
   - Secondary metadata: train code, destination terminus, track/platform (e.g. `Voie A`).
   - Disruption callouts: grouped under `📢 Infos Trafic` at the bottom of the card.
3. **Interactive Controls**:
   - Two-column inline keyboard: `[🔄 Actualiser] [↔️ Vers Nice / Vers Antibes]`.
   - In-place message edits without chat clutter.
