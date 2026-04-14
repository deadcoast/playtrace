# Playtrace CLI Brainstorming

## Logic

Start with these five sources, in this order.

### 1) Security Event Log: 4688 + 4689

This is your **gold standard** for exact sessions. Event **4688** is emitted when a process starts, and event **4689** when it exits. Microsoft’s docs explicitly describe those events, and the process-creation docs note that auditing must already have been enabled for this to exist. If command-line auditing was enabled too, 4688 can also include the full command line, which is great for distinguishing launcher wrappers from the actual game exe. ([Microsoft Learn][1])

Use this for:

* exact launch timestamps
* exact exit timestamps
* exact runtime per PID
* parent/child process relationships
* launcher → game transitions

This should drive:

* `confirmed_launches`
* `confirmed_runtime_minutes`
* `session_count`

## 2) Prefetch

Prefetch is probably your best **retroactive execution artifact** when exact event logs are unavailable. It records the executable name, timestamps for runs, run counts, and path-related data. On Windows 8+, Prefetch can contain up to **eight recent run timestamps** for an exe. ([Magnet Forensics][2])

Use this for:

* “this exe definitely ran on this machine”
* approximate launch count
* first/last seen hints
* multiple recent executions even when event logs are missing

This should drive:

* `strong_launch_count`
* `last_run_times[]`
* `prefetch_path_hash`

## 3) UserAssist

UserAssist is useful, but only as a **user-interaction signal**. It lives under the user hive and tracks GUI-launched programs. It can include **run count**, **focus time**, and **last execution timestamp**. But it is not a pure execution ledger; it can be updated by shell interactions that do not necessarily mean the program fully ran. ([ElcomSoft blog][3])

Use this for:

* “the user likely clicked/launched this”
* per-user attribution
* foreground engagement hints
* focus time as “active window” time, not runtime

This should drive:

* `gui_launch_count`
* `focus_time_ms`
* `interactive_score`

Do **not** market UserAssist focus time as total runtime. It is closer to “foreground attention” than “hours played.” ([ElcomSoft blog][3])

## 4) SRUM

SRUM is the best native source for **coarse historical app activity** beyond simple execution traces. Microsoft exposes it with `powercfg /srumutil`, which dumps SRUM data to CSV or XML. Forensics references note SRUM tracks application usage, network usage, and energy state, stores its database at `C:\Windows\System32\sru\SRUDB.dat`, writes on an hourly cadence and at shutdown, and includes the **full application path** and **executing SID** in key categories. ([Microsoft Learn][4])

Use this for:

* full-path attribution
* user SID attribution
* coarse time windows of activity
* network-heavy sessions by exe
* supplemental evidence when the exe has been deleted

This should drive:

* `activity_windows[]`
* `network_bytes_sent/received`
* `srum_seen`
* `user_sid`

SRUM is powerful, but it is still a **time-window artifact**, not a precise playtime ledger. Treat it as corroboration, not exact runtime. ([Magnet Forensics][5])

## 5) AmCache and ShimCache

Use these as supporting sources. AmCache is useful because it ties execution-related history to file metadata and hash, and it can give you a **first execution** anchor. ShimCache is weaker: it helps show historical presence/loading, but not exact execution timing. ([Magnet Forensics][6])

Use these for:

* file identity
* renamed exe detection
* “first seen” type anchoring
* support when other artifacts are missing

This should drive:

* `sha1`
* `volume_guid`
* `first_seen_time`
* `metadata_confidence`

## Optional: BAM/DAM

BAM/DAM is useful for non-GUI and background processes, but it is short-lived and not a great backbone for a consumer-facing tool. It can help catch silent/background executions that UserAssist misses, but published analysis notes rough **~7 day** retention on many systems and other caveats. ([ElcomSoft blog][3])

I would include it as a bonus source, not a core one. ([ElcomSoft blog][3])

## What not to build around

Do **not** make the primary model “installed apps,” “Start menu entries,” or launcher UIs.

Those are presentation layers. Your primary key should be:

`normalized_exe_identity = { path, sha1 if available, product name, file description, signer, original filename }`

That gives you one canonical object for:

* `eldenring.exe`
* `eldenring.exe` launched through Steam
* `eldenring.exe` renamed or moved
* helper exes and runtimes that need filtering

The whole product should be **exe-first, app-second**.

## The honest limitation

If 4688/4689 were **not enabled historically**, Windows usually cannot give you exact retroactive runtime for every game. You can still recover:

* confirmed evidence that it ran
* how often it likely ran
* when it was last run
* whether the user interacted with it
* coarse activity windows
* sometimes network-heavy usage windows

But you usually **cannot reconstruct exact past “hours played”** natively with high confidence from Prefetch/UserAssist/SRUM alone. The only clean native path to exact runtime is matching process start and exit events from the security log. ([Microsoft Learn][1])

That means your CLI should never pretend otherwise.

## The right output model

I would present every title with **confidence tiers**.

For example:

```text
Game: Elden Ring
Executable: D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe

Confirmed runtime: 42h 18m
Confirmed sessions: 27
Strong launch count: 34
GUI launches: 19
Foreground time: 11h 07m
First seen: 2025-11-03 21:14
Last seen: 2026-04-11 18:52

Evidence:
  exact_sessions: Security.evtx (4688/4689)
  execution: Prefetch
  interaction: UserAssist
  activity: SRUM
  identity: AmCache

Confidence:
  runtime: exact
  launch_count: mixed
  title_mapping: high
```

That is much better than a fake single number.

## My recommended merge rules

Use a scoring system like this:

* **Exact**

  * 4688 + 4689 matched by PID and process name
* **Strong**

  * Prefetch run count / recent run timestamps
  * AmCache first execution
  * SRUM application usage for same path/SID
* **Interactive**

  * UserAssist run count / focus time
* **Weak**

  * ShimCache
  * BAM/DAM

Then merge on a normalized exe key and expose both:

* `confirmed_*`
* `inferred_*`

Example fields:

```text
confirmed_runtime_seconds
confirmed_launches
inferred_launches
foreground_seconds
first_seen
last_seen
title
exe_path
sha1
publisher
parent_launcher
evidence_sources[]
confidence_score
```

## Practical MVP

If I were building v1, I would ship only this:

1. Read Security log 4688/4689 and build exact sessions when available. ([Microsoft Learn][1])
2. Parse Prefetch and add run counts plus recent run timestamps. ([Magnet Forensics][2])
3. Parse UserAssist for per-user GUI launches and focus time. ([ElcomSoft blog][3])
4. Import SRUM via `powercfg /srumutil /csv` and merge full path + SID + coarse activity. ([Microsoft Learn][4])
5. Use AmCache to stabilize identity and first-seen metadata. ([Magnet Forensics][6])
6. Output a ranked list of “likely games” and hide helpers by default.

That gives you a serious CLI without pretending Windows knows more than it does.

## One design choice that will save you later

Add a field called something like:

`classification = game | launcher | helper | runtime | unknown`

Because once you start parsing native Windows artifacts, you will absolutely pick up:

* launchers
* anti-cheat
* crash reporters
* redistributables
* browser helpers
* overlay tools

Your value is not just collecting traces. It is **classifying the right exe as the title the user actually cares about**.

The strongest way to do that is:

* detect the child process launched by a known launcher
* prefer the longest-running child
* de-prioritize signed runtimes/helpers
* merge by original filename/product name/hash when possible

NEXT: the actual CLI architecture and data pipeline next — inputs, parsers, normalization, merge rules, and output schema.

[1]: https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4688 "4688(S) A new process has been created. - Windows 10 | Microsoft Learn"
[2]: https://www.magnetforensics.com/blog/forensic-analysis-of-prefetch-files-in-windows/ "Forensic Analysis of Prefetch files in Windows - Magnet Forensics"
[3]: https://blog.elcomsoft.com/2026/02/investigating-windows-registry/ "Investigating Windows Registry |  ElcomSoft blog"
[4]: https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options "Powercfg command-line options | Microsoft Learn"
[5]: https://www.magnetforensics.com/blog/srum-forensic-analysis-of-windows-system-resource-utilization-monitor/ "SRUM: Forensic Analysis of System Resource Utilization Monitor"
[6]: https://www.magnetforensics.com/blog/shimcache-vs-amcache-key-windows-forensic-artifacts/ "ShimCache vs AmCache: Key Windows Forensic Artifacts - Magnet Forensics"
