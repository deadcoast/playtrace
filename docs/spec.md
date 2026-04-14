# Playtrace CLI

- A forensic-style executable usage aggregator with a product-grade terminal experience on top.

## Architecture

The architecture should be split into six layers:

- collect
- parse
- normalize
- merge
- classify
- present

That separation is what will keep the system honest. Windows artifacts are messy and incomplete, so your pipeline needs to preserve raw evidence first, then derive higher-level metrics later. The strongest exact runtime source is still the Security log’s process creation/termination events when enabled, while Prefetch, UserAssist, SRUM, and AmCache are better treated as supporting evidence with different confidence levels.

### 1. CLI architecture

Structure the CLI as a single binary with subcommands:

```bash
playtrace scan
playtrace report
playtrace inspect <title-or-exe>
playtrace sessions <title-or-exe>
playtrace sources
playtrace export --format json|csv|html
playtrace config
playtrace doctor
```

### Command roles

`scan`

Runs the artifact collection and builds a local evidence database.

Example:

```bash
playtrace scan --sources security,prefetch,userassist,srum,amcache
```

`report`
Shows the polished overview dashboard.

Example:

```bash
playtrace report --sort runtime --top 25
```

`inspect`

Shows one title in depth: source breakdown, session evidence, child processes, confidence, launcher chain.

Example:

```bash
playtrace inspect "Elden Ring"
sessions
```

Shows exact or inferred sessions.

Example:

```bash
playtrace sessions "Helldivers 2" --last 30d
```

`sources`

Lets advanced users see what the app found from each Windows source.

Example:

```bash
playtrace sources --exe helldivers2.exe
```

`doctor`

Checks privileges, whether audit logs are present, whether Prefetch is enabled, whether SRUM export works, and whether the user can expect exact runtime or only inferred history. Microsoft documents that security process events depend on auditing configuration, and powercfg /srumutil is the supported export path for SRUM.

---

### Data pipeline

The pipeline should be:

```plaintext
Windows Artifacts
   ↓
Collectors
   ↓
Raw Evidence Store
   ↓
Parsers
   ↓
Normalized Evidence Records
   ↓
Entity Resolution / Merge Engine
   ↓
Title Classification Layer
   ↓
Metrics Engine
   ↓
CLI Renderer / Exporters
```

`Principle`

Do not compute “hours played” during collection.

Collect first, preserve raw facts, then derive:

- exact runtime
- inferred runtime
- launches
- interaction
- confidence
- title mapping

This lets you revise merge rules later without losing the original evidence.

---

### Inputs and collectors

Each source gets its own collector module.

A. Security log collector

Reads:

- Event ID 4688: process created
- Event ID 4689: process exited

This is your exact-session source when available. Microsoft’s audit docs cover both process creation and termination events.

Collector output:

```json
{
  "source": "security",
  "event_id": 4688,
  "timestamp": "2026-04-11T18:42:03Z",
  "pid": 15320,
  "parent_pid": 9012,
  "exe_path": "D:\\SteamLibrary\\steamapps\\common\\ELDEN RING\\Game\\eldenring.exe",
  "command_line": "\"...\\eldenring.exe\"",
  "user_sid": "S-1-5-21-...",
  "machine": "DESKTOP-01"
}
```

And:

```json
{
  "source": "security",
  "event_id": 4689,
  "timestamp": "2026-04-11T22:13:51Z",
  "pid": 15320,
  "exe_path": "D:\\SteamLibrary\\steamapps\\common\\ELDEN RING\\Game\\eldenring.exe"
}
```

B. Prefetch collector

Reads .pf files from the Prefetch directory and extracts:

- executable name
- run count
- recent run timestamps
- referenced path data

Prefetch is one of the best retroactive execution artifacts and commonly includes multiple recent timestamps on modern Windows.

Collector output:

```json
{
  "source": "prefetch",
  "exe_name": "ELDENRING.EXE",
  "run_count": 34,
  "last_run_times": [
    "2026-04-11T18:42:05Z",
    "2026-04-10T20:11:07Z"
  ],
  "pf_file": "ELDENRING.EXE-1A2B3C4D.pf"
}
```

C. UserAssist collector

Reads the per-user registry hive and extracts:

- ROT13-decoded entry path
- run count
- focus time
- last execution time

UserAssist is best treated as an interactive GUI-launch and focus artifact, not exact runtime.

Collector output:

```json
{
  "source": "userassist",
  "user_sid": "S-1-5-21-...",
  "entry": "C:\\Program Files (x86)\\Steam\\steam.exe",
  "run_count": 19,
  "focus_time_ms": 24034000,
  "last_run": "2026-04-11T18:41:50Z"
}
```

D. SRUM collector

Runs powercfg /srumutil /csv and ingests CSV exports. Microsoft documents powercfg /srumutil as the supported way to dump SRUM data.

You want:

- application resource usage
- network usage by app
- user SID
- time window

Collector output:

```json
{
  "source": "srum",
  "window_start": "2026-04-11T18:00:00Z",
  "window_end": "2026-04-11T19:00:00Z",
  "exe_path": "D:\\SteamLibrary\\steamapps\\common\\ELDEN RING\\Game\\eldenring.exe",
  "user_sid": "S-1-5-21-...",
  "bytes_sent": 412340,
  "bytes_received": 12034440
}
```

E. AmCache collector

Reads AmCache entries for:

- path
- file metadata
- hash
- first-seen style evidence

This is very useful for identity stabilization and renamed/moved executables.

Collector output:

```json
{
  "source": "amcache",
  "exe_path": "D:\\SteamLibrary\\steamapps\\common\\ELDEN RING\\Game\\eldenring.exe",
  "sha1": "abc123...",
  "product_name": "ELDEN RING",
  "company_name": "FromSoftware, Inc.",
  "file_description": "ELDEN RING",
  "original_filename": "eldenring.exe"
}
```

---

### Parsers

Each source should parse into a shared internal evidence contract.

Core evidence record

```typescript
type EvidenceRecord = {
  source: "security" | "prefetch" | "userassist" | "srum" | "amcache";
  evidence_type:
    | "process_start"
    | "process_exit"
    | "execution_count"
    | "recent_execution"
    | "interactive_launch"
    | "foreground_usage"
    | "activity_window"
    | "identity";

  timestamp?: string;
  window_start?: string;
  window_end?: string;

  exe_path?: string;
  exe_name?: string;
  original_filename?: string;
  product_name?: string;
  company_name?: string;
  sha1?: string;
  user_sid?: string;

  pid?: number;
  parent_pid?: number;
  command_line?: string;

  run_count?: number;
  focus_time_ms?: number;
  bytes_sent?: number;
  bytes_received?: number;

  raw_ref: string;
}
```

Why this matters

You do not want source-specific logic leaking all over the app. The parser’s job is to convert raw artifacts into a consistent internal language:

- starts
- exits
- counts
- focus
- windows
- identity

---

### Normalization layer

This is the most important engineering piece.

Windows sources will disagree on:

full path vs filename only
case sensitivity
8.3 paths
moved games
launcher wrappers
symlinked drives
missing hashes

So create a normalized executable identity.

Normalized executable key

Use weighted identity fields:

```typescript
type NormalizedExeIdentity = {
  canonical_path?: string;
  exe_name: string;
  original_filename?: string;
  sha1?: string;
  product_name?: string;
  company_name?: string;
  signer?: string;
}
```

- Normalization steps
- lowercase path
- expand environment variables
- normalize slash direction
- resolve short names if possible
- trim quotes around command lines
- split executable from command-line args
- normalize UNC vs local path forms
- collapse duplicate identities by hash when available
- fallback to (exe_name + product_name + company_name) when path changes

`Example`

These should likely merge:

- D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe
- d:\steamlibrary\steamapps\common\elden ring\game\ELDENRING.EXE

These may also merge if hash or original filename matches:

- E:\Games\ER\eldenring.exe
- D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe

---

### Merge rules

You need two levels of merge:

- executable merge
- title merge

A. Executable merge

Group all evidence by normalized exe identity.

Rules:

- exact match on SHA1 → merge
- exact canonical path match → merge
- same original_filename + product_name + company_name with high similarity → probably merge
- same exe name alone → do not auto-merge unless supported by another signal

B. Title merge

One game can involve:

- launcher exe
- anti-cheat exe
- game exe
- helper exe
- updater
- crash reporter

So build a graph per session:

- parent PID
- child PID
- start/exit times
- runtime lengths
- known launcher names

Then derive a primary title executable.

Primary-child rule

If a known launcher starts, prefer:

- the child process with the longest runtime
- executable outside the launcher install directory
- executable with game-like metadata
- executable seen in Prefetch and SRUM
- executable not classified as helper/runtime

This is how you stop reporting steam.exe instead of eldenring.exe.

---

### Classification layer

You need a classifier with these buckets:

```typescript
type Classification =
  | "game"
  | "launcher"
  | "helper"
  | "runtime"
  | "overlay"
  | "anti_cheat"
  | "unknown";
```

This is where raw executables become something the user can actually understand.

The classifier should assign each normalized executable one of:

- `game`
- `launcher`
- `helper`
- `runtime`
- `overlay`
- `system`
- `unknown`

And optionally a subtype:

- `anti_cheat`
- `crash_reporter`
- `updater`
- `browser_wrapper`
- `installer`
- `emulator`
- `dedicated_server`

#### Inputs to classification

Use all of these together:

- executable path
- file name
- original file name
- product name
- file description
- signer / publisher
- parent process chain
- child process behavior
- session duration
- network usage
- focus time
- install directory patterns
- known launcher fingerprints
- known runtime/helper fingerprints

#### Practical heuristics

Examples:

A process is likely a **launcher** if:

- it is `steam.exe`, `epicgameslauncher.exe`, `gog galaxy`, `battle.net`, `ea app`, `ubisoft connect`, etc.
- it frequently spawns a child that runs much longer
- it has high GUI presence but low direct gameplay-like runtime patterns

A process is likely a **game** if:

- it is launched by a launcher and becomes the longest-lived child
- it has repeated sessions
- it has foreground/focus activity
- it lives in known game library paths
- it has graphics/game-like metadata
- it is not a known helper/runtime

A process is likely a **helper/runtime** if:

- it is a redistributable/runtime/browser subprocess
- it has many launches but tiny durations
- it is signed by common middleware vendors
- it runs alongside a game but rarely owns the main session

#### Suggested classifier pipeline

Run classification in layers:

1. **Hard rules**

   - known launcher names
   - known helpers
   - system paths
   - known anti-cheat binaries

2. **Relationship rules**

   - parent-child graph
   - longest child runtime
   - recurring co-launch patterns

3. **Behavioral scoring**

   - session duration
   - foreground time
   - repeated use pattern
   - network-heavy windows
   - launch frequency

4. **Confidence assignment**

   - `high`
   - `medium`
   - `low`

That lets you show users not just a result, but how certain the tool is.

---

### Title resolution

This is separate from classification.

The user does not want:

```text
eldenring.exe
steam_app_1245620_tmp.exe
start_protected_game.exe
```

They want:

```text
Elden Ring
```

So after classification, resolve a human title.

#### Resolution priority

1. explicit mapping file
2. product name from file metadata
3. original filename mapping
4. install path inference
5. parent launcher context
6. fallback to exe stem

#### Example mapping object

```json
{
  "normalized_key": "sha1:abc123...",
  "title": "Elden Ring",
  "title_source": "manual_map",
  "launcher": "Steam",
  "confidence": "high"
}
```

#### Path-based inference examples

Useful patterns:

- `SteamLibrary\steamapps\common\<Game Name>\`
- `Epic Games\<Game Name>\`
- `GOG Galaxy\Games\<Game Name>\`
- emulator ROM folders
- custom library roots discovered from repeated game installs

#### Manual override support

This is essential.

The CLI should support:

```bash
playtrace map "D:\Games\weirdlauncher\gamebin\start.exe" --title "My Game"
```

A serious tool needs this because some titles will always be weird.

---

### Merge rules Logic

This is the heart of the application.

You will collect overlapping evidence from multiple native Windows sources. Merge rules decide what becomes one “activity record.”

#### Primary merge identity

Use a layered identity:

1. hash if available
2. full normalized path
3. original file name + product name + signer
4. exe file name + stable library root

Do not rely only on filename.

#### Entity model

You want three core entities:

- `Executable`
- `Session`
- `TitleAggregate`

##### Executable

Represents one normalized binary identity.

##### Session

Represents one launch-run-exit period, exact or inferred.

##### TitleAggregate

Represents the user-facing game/app entry that rolls up related executables.

#### Session merge logic

When exact logs exist:

- pair `start` and `end` by PID
- store as `session_confidence = exact`

When only launch evidence exists:

- create a partial session candidate
- infer end using corroborating sources if possible
- otherwise leave duration null

#### Parent-child resolution

If a launcher spawns multiple children:

- prefer the child with the longest sustained runtime
- boost if it has focus time
- boost if it recurs across multiple sessions
- suppress helpers that always co-occur with the main child

This is what turns launcher mess into one meaningful title.

#### Multi-source deduping

Same launch may appear in:

- Security logs
- Prefetch
- UserAssist
- SRUM window

Use a time-bucket dedupe strategy:

- same normalized exe
- same user
- timestamps within merge window, such as 1 to 5 minutes depending on source type

Example:

- Security 4688 at 20:14:05
- Prefetch recent run at 20:14
- UserAssist last exec at 20:14:10

These become one launch event, not three.

#### Merge precedence

Use precedence like:

- exact session logs
- Prefetch
- UserAssist
- SRUM
- AmCache
- ShimCache / BAM

That way weaker evidence never overwrites stronger evidence.

---

### Confidence model

The output should make uncertainty visible and useful.

#### Per-metric confidence

Each title can have:

- `runtime_confidence`
- `launch_count_confidence`
- `title_confidence`
- `classification_confidence`

#### Example scoring

Runtime:

- exact 4688/4689 pairs: `exact`
- inferred from time windows: `estimated`
- no duration source: `unknown`

Launch count:

- security logs + prefetch alignment: `high`
- prefetch only: `medium`
- userassist only: `medium-low`
- weak corroboration only: `low`

Title resolution:

- explicit map: `high`
- metadata + path: `high`
- path only: `medium`
- exe name fallback: `low`

#### Why this matters

This is a selling point, not a drawback.

Other tools often fake precision. Yours can say:

```text
Runtime: 42h 18m   [exact]
Launches: 34       [high confidence]
Title: Elden Ring  [high confidence]
```

That feels premium.

---

### Output schema

You want both an internal machine-friendly schema and a polished display schema.

#### Internal aggregate object

```json
{
  "title_id": "title_01HZX...",
  "title": "Elden Ring",
  "classification": "game",
  "classification_confidence": "high",
  "launcher": "Steam",
  "runtime": {
    "confirmed_seconds": 152280,
    "estimated_seconds": 0,
    "foreground_seconds": 40020,
    "confidence": "exact"
  },
  "launches": {
    "confirmed": 27,
    "inferred": 7,
    "gui": 19,
    "confidence": "high"
  },
  "timeline": {
    "first_seen": "2025-11-03T21:14:00Z",
    "last_seen": "2026-04-11T18:52:00Z"
  },
  "executables": [
    {
      "path": "D:\\SteamLibrary\\steamapps\\common\\ELDEN RING\\Game\\eldenring.exe",
      "sha1": "abc123",
      "product_name": "ELDEN RING",
      "signer": "FromSoftware Inc."
    }
  ],
  "evidence": {
    "sources": ["security_log", "prefetch", "userassist", "srum", "amcache"],
    "session_count_exact": 27,
    "session_count_partial": 3
  },
  "tags": ["soulslike", "singleplayer"],
  "notes": []
}
```

#### Session object

```json
{
  "session_id": "sess_01HZX...",
  "title_id": "title_01HZX...",
  "exe_key": "sha1:abc123",
  "user_sid": "S-1-5-21-...",
  "started_at": "2026-04-11T16:10:03Z",
  "ended_at": "2026-04-11T18:52:41Z",
  "duration_seconds": 9758,
  "confidence": "exact",
  "evidence_sources": ["security_log"],
  "parent_chain": ["steam.exe"],
  "foreground_seconds": 5120,
  "network_bytes_rx": 10485760,
  "network_bytes_tx": 1024000
}
```

---

### CLI command architecture

You want the tool to feel like a polished terminal product, not a forensic dump.

A good shape:

```bash
playtrace scan
playtrace report
playtrace sessions
playtrace titles
playtrace inspect
playtrace map
playtrace config
playtrace doctor
playtrace export
```

#### Recommended commands

`playtrace scan`

- ingest raw sources
- parse
- normalize
- merge
- classify
- store snapshot

`playtrace report`

- default premium dashboard
- top titles
- recent sessions
- confidence summary
- anomalies / unmapped titles

`playtrace titles`

- sortable title table
- filter by classification, confidence, launcher, date range

`playtrace sessions`

- detailed session list
- grouped by title or day

`playtrace inspect <title|exe>`

- deep dive view
- evidence provenance
- raw source summary
- parent-child process chain
- title mapping info

`playtrace map`

- manually assign title or classification
- ignore helpers
- merge variants

`playtrace doctor`

- detect missing privileges
- tell user whether security logs are available
- tell user whether prefetch is enabled
- tell user whether SRUM export succeeded
- explain coverage gaps

`playtrace export`

- JSON
- CSV
- Markdown report

---

### Storage layer

Use local SQLite.

This is the right fit for:

- CLI speed
- zero-config local use
- structured queries
- incremental rescans
- cached normalization/mapping

#### Suggested tables

- `artifacts`
- `executables`
- `sessions`
- `titles`
- `title_executables`
- `mappings`
- `scan_runs`
- `evidence_links`

You want rescans to be incremental, not full rebuilds every run.

#### Example approach

Each scan:

- records source timestamps
- fingerprints parsed artifacts
- only reparses changed inputs when possible
- updates aggregates idempotently

---

### Parser modules

Keep parsers isolated from the rest of the app.

Suggested package structure:

```text
playtrace/
  cli/
  core/
  parsers/
    security_log.py
    prefetch.py
    userassist.py
    srum.py
    amcache.py
    bam.py
  normalize/
  classify/
  merge/
  store/
  render/
  config/
```

Each parser should output a standard intermediate record.

#### Example intermediate record

```json
{
  "source": "prefetch",
  "artifact_id": "pf_...",
  "observed_at": "2026-04-11T16:10:00Z",
  "user_sid": null,
  "exe_path": "D:\\SteamLibrary\\steamapps\\common\\ELDEN RING\\Game\\eldenring.exe",
  "exe_name": "eldenring.exe",
  "launch_count": 12,
  "run_timestamps": [
    "2026-04-11T16:10:00Z",
    "2026-04-10T22:03:00Z"
  ],
  "raw_confidence": "strong"
}
```

That makes downstream merging much easier.

---

### Rendering layer

This is where your product can win.

The CLI should feel like a crafted interface with hierarchy, rhythm, spacing, contrast, density control, and personality.

Do not treat terminal output as tables only.

Build a rendering system with three modes:

- `compact`
- `comfortable`
- `cinematic`

#### Compact

For power users:

- dense tables
- minimal decoration
- ideal for pipes and SSH

#### Comfortable

Default:

- balanced spacing
- summary cards
- key metrics highlighted
- easy scanning

#### Cinematic

Your “showpiece” mode:

- wider spacing
- section cards
- sparkline histories
- glyphs and dividers
- richer session and evidence storytelling

---

### CLI visual design system

This is the real differentiator.

#### Visual principles

- one strong primary accent
- restrained secondary colors
- semantic color only for meaning
- generous spacing
- stable alignment
- clean typographic hierarchy
- consistent panel framing
- minimal noise

#### Suggested information hierarchy

1. title
2. key metric
3. confidence / status
4. timeline context
5. evidence detail
6. raw diagnostics

The eye should always land on:

- what this is
- how much it was used
- how reliable that number is

#### Example home report layout

```bash
playtrace
Native Windows executable history and session analysis

Coverage
────────
Data sources: Security Log, Prefetch, UserAssist, SRUM
Runtime coverage: Exact for 61 titles
Estimated only: 24 titles
Unmapped: 9 executables

Top Titles
──────────
1. Elden Ring              42h 18m   exact      27 sessions
2. Hades                   31h 05m   high       44 launches
3. Cyberpunk 2077          24h 41m   exact      18 sessions
4. Balatro                 18h 11m   estimated  63 launches

Recent Activity
───────────────
Today
  18:10 → 20:52  Elden Ring          2h 42m   exact
  14:03 → 14:36  Balatro             33m      estimated

Needs Attention
───────────────
- 3 executables look like games but are not mapped to a title
- 1 title has split identity across two paths
- 8 helpers are being suppressed automatically
```

That is already more compelling than most tracker UIs.

---

### High-value terminal UI elements

Use these heavily.

#### a) Summary cards

Not boxed with heavy clutter. Clean cards.

Example:

```bash
[ Runtime ]
142h 21m
confirmed across 83 sessions

[ Launches ]
311
across 26 titles

[ Coverage ]
84%
exact or strong evidence
```

#### b) Confidence badges

Examples:

- `exact`
- `high`
- `estimated`
- `partial`
- `unknown`

These should be visually distinct but subtle.

#### c) Mini sparklines

Show weekly or monthly activity as tiny bars or braille/sparkline glyphs.

Example:

```bash
Last 12 weeks  ▁▂▁▃▅▄▁▁▆▇▃▂
```

#### d) Session timeline strips

Example:

```bash
Fri 11 Apr   [■■■■■■■■■■■      ] 2h 42m
Thu 10 Apr   [■■■              ] 0h 47m
Wed 09 Apr   [■■■■■■           ] 1h 28m
```

#### e) Evidence provenance panel

Advanced users will love this.

```bash
Evidence
────────
Security Log    exact sessions      27
Prefetch        strong launches     34
UserAssist      gui launches        19
SRUM            activity windows    12
AmCache         first seen anchor   yes
```

This makes the tool feel transparent and serious.

---

### Report views worth building

#### Default report

Best overall experience.

#### Focus report

Ranks by foreground/focus time instead of runtime.

#### Reliability report

Shows where Windows evidence is strongest or weakest.

#### Launcher report

Shows launcher-to-title chains and helper suppression.

#### Discovery report

Surfaces likely games from unknown executables.

#### Drift report

Shows when a title split across multiple installs or exe identities.

These are excellent differentiators.

---

### Example polished command outputs

#### `playtrace report`

```bash
playtrace REPORT
Snapshot: 2026-04-14 21:42
Host: DESKTOP-9A2F
User: user

Overview
────────
Tracked titles        26
Confirmed runtime     142h 21m
Estimated runtime     18h 12m
Confirmed sessions    311
Unmapped executables  9

Most Played
───────────
Elden Ring         42h 18m   exact      27 sessions   Steam
Hades              31h 05m   high       44 launches   Steam
Balatro            18h 11m   estimated  63 launches   Steam
Cyberpunk 2077     24h 41m   exact      18 sessions   GOG

Momentum
────────
Last 30 days   ▁▁▂▃▅▆▄▁▂▃▇▆
Last 7 days    ▁▂▁▇▅▃▂
Today          2h 42m
```

#### `playtrace inspect "Elden Ring"`

```bash
ELDEN RING
Classification: game         confidence: high
Launcher: Steam
Title mapping: metadata + path + recurring child process

Runtime
───────
Confirmed       42h 18m
Estimated       0m
Foreground      11h 07m
Sessions        27 exact / 3 partial

Timeline
────────
First seen      2025-11-03 21:14
Last seen       2026-04-11 18:52

Executables
───────────
D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe
  signer        FromSoftware Inc.
  product       ELDEN RING
  identity      sha1:abc123

Evidence
────────
Security Log    27 paired sessions
Prefetch        34 strong launches
UserAssist      19 GUI launches, 11h 07m focus
SRUM            12 activity windows
AmCache         first execution anchor found
```

---

### Config philosophy

Config should be simple and powerful.

Support:

- ignored executables
- manual title maps
- launcher fingerprints
- helper fingerprints
- library roots
- theme
- density
- timezone
- confidence thresholds

Example config file:

```toml
[display]
theme = "midnight"
density = "comfortable"
show_sparklines = true
show_helpers = false

[classification]
promote_longest_child = true
suppress_known_helpers = true

[libraries]
roots = [
  "D:\\SteamLibrary",
  "E:\\Games",
  "C:\\Program Files\\Epic Games"
]
```

---

### Themes and CLI branding

Since CLI design is a selling point, give the interface identity.

A few theme ideas:

- `midnight` — dark, clean, premium
- `amber` — retro terminal but polished
- `ice` — cool, sharp, minimal
- `mono` — no color, elegant structure only

Do not rely on color alone. Use:

- spacing
- alignment
- headers
- weight via casing and symbols
- panel rhythm
- restrained dividers

The best CLI tools feel intentional even in monochrome.

---

### What makes this better than “other applications”

Your differentiator is not just “tracks usage.”

It is:

- reconstructs **past** patterns from native Windows evidence
- uses **multiple sources** instead of one brittle signal
- distinguishes **exact vs estimated**
- classifies **games vs helpers**
- resolves **launcher mess**
- provides a **beautiful terminal experience**
- stays transparent about uncertainty

That combination is genuinely strong.

---

### Implementation order

From here, the smartest build order is:

1. parser interfaces
2. security log exact sessions
3. prefetch parser
4. normalization layer
5. merge engine
6. title/classification rules
7. SQLite storage
8. default report renderer
9. inspect view
10. config and manual mapping
11. premium visual modes
12. remaining artifact parsers

That gets you to a compelling MVP without getting buried.

---
