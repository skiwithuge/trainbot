# SNCF Train Bot Context

A localized Telegram assistant delivering scheduled commuter departure boards, delay alerts, and disruption updates for train travel between Antibes and Nice Ville.

## Language

**Commute**:
A regular travel corridor between Antibes and Nice Ville with direction determined by schedule (morning: Antibes to Nice Ville; evening: Nice Ville to Antibes).
_Avoid_: Trip, Journey, Route

**Departure**:
A scheduled passenger train service departing from the origin station towards the destination station.
_Avoid_: Train instance, Leg, Booking

**Regional Train**:
A rail-bound passenger service operating under regional transport governance (TER, ZOU!, or Région Sud regional rail services).
_Avoid_: Express, Long-distance train, Coach, Bus

**Disruption**:
An operational incident, schedule change, delay, cancellation, or notice affecting train circulation.
_Avoid_: Incident, Bug, Problem

**Allowed User**:
A Telegram user whose unique numeric account identifier is listed in the authorized access control list.
_Avoid_: Whitelisted client, Member, Admin

**On-Demand Query**:
An interactive request triggered by an allowed user via slash command or inline button to obtain real-time departure boards immediately.
_Avoid_: Manual check, Poll, Fetch
