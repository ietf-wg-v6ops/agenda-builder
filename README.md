# agenda-builder

Generate an IETF working-group session agenda (markdown) from a "call for
draft presentations" CSV, using live session data (room, time, Meetecho
link) pulled from the [IETF Datatracker](https://datatracker.ietf.org/).

The output matches the format IETF datatracker uses for published WG
agendas — for example
[`agenda-125-v6ops-06.md`](https://datatracker.ietf.org/meeting/125/materials/agenda-125-v6ops-06.md).

## Requirements

- [`uv`](https://docs.astral.sh/uv/) — the script is a single file with
  [PEP 723](https://peps.python.org/pep-0723/) inline metadata, so `uv`
  provisions Python 3.11+ and the one dependency (`requests`)
  automatically. No virtualenv to create, nothing to `pip install`.

## Usage

```bash
uv run build_agenda.py --csv "path/to/call-for-drafts.csv" --meeting 126
```

This:

1. Looks up IETF meeting 126 on datatracker to get its timezone.
2. Finds the `v6ops` working group's scheduled session for that meeting
   (room, start time, duration).
3. Reads the CSV and turns each row into an agenda bullet.
4. Writes `agenda-126-v6ops.md` in the current directory.

### Flags

| Flag | Required | Default | Description |
|---|---|---|---|
| `--csv` | yes | — | Path to the call-for-drafts CSV |
| `--meeting` | yes | — | IETF meeting number, e.g. `126` |
| `--group` | no | `v6ops` | Working group acronym — drives the datatracker lookup and the Meetecho link, so this script works for any WG's CSV, not just v6ops |
| `--output` | no | `agenda-{meeting}-{group}.md` | Output markdown file path |
| `--chairs-item` | no | `Chairs Opening and WG status, 10m` | Text for the fixed opening bullet, before any drafts |
| `--minute-taker` | no | `TBD` | Name of the minute taker |

### Example: a different working group

```bash
uv run build_agenda.py --csv drafts.csv --meeting 126 --group v6man --output agenda-126-v6man.md
```

## CSV format

The script expects a Google-Forms-style export with (at least) these
columns — column order doesn't matter, and header whitespace is trimmed
before matching:

| Column | Used for |
|---|---|
| `Draft Topic (e.g. Use of the IPv6 Flow Label for WLCG Packet Marking)` | Bullet topic text |
| `Presenter Name (if someone other than requestor)` | Bullet presenter text |
| `Time slot duration` | Converted from `"10 minutes"` to `"10m"` |
| `URL for Draft` | An `http(s)://` URL is extracted and rendered as a `Draft:` line; if the field has no URL (e.g. "No draft; only sharing observations"), the `Draft:` line is simply omitted |
| `Adopted WG Draft?` | `Yes` (case-insensitive) routes the row to `## WG Drafts`; anything else routes it to `## Individual Drafts`. Row order within each section follows CSV row order |

A row missing a topic or presenter is a hard error — the script won't
silently skip or guess at malformed input.

## Output format

```markdown
# IPv6 Operations (v6ops) - IETF 126 Agenda

Mon. 9:00-11:00, Grand Ballroom 1

[Meetecho (Full Client)](https://meetings.conf.meetecho.com/ietf126/?session=35105)
[Meetecho (Onsite Tool)](https://meetings.conf.meetecho.com/onsite126/?session=35105)

Minute taker: TBD

* Chairs Opening and WG status, 10m

## WG Drafts

* Stateful NAT64: Network Address and Protocol Translation from IPv6 Clients to IPv4 Servers, Jordi Palet, 10m
  Draft: [https://datatracker.ietf.org/doc/draft-ietf-v6ops-rfc6146-bis/](https://datatracker.ietf.org/doc/draft-ietf-v6ops-rfc6146-bis/)

## Individual Drafts

* Enhanced Dual Stack: Selecting IPv6/IPv4 based on Performance, Xipeng Xiao, 15m
  Draft: [https://datatracker.ietf.org/doc/draft-xiao-v6ops-eds/](https://datatracker.ietf.org/doc/draft-xiao-v6ops-eds/)
```

A section with zero rows is omitted entirely (no empty `## WG Drafts` or
`## Individual Drafts` header).

## Errors

The script fails hard, with a clean one-line message on stderr and a
non-zero exit code — no silent fallbacks or placeholder data — for:

- an unreachable datatracker API or an unrecognized meeting number,
- no scheduled session found yet for the given `--group` at the given
  `--meeting` (the session hasn't been put on the agenda yet),
- a malformed session record on datatracker (missing/invalid schedule
  data),
- a CSV row missing a topic or presenter.

## Development

Run the test suite (also via `uv`, no separate install step):

```bash
uv run --with pytest --with requests pytest tests/test_build_agenda.py -v
```

The project layout:

```
build_agenda.py              # the script: parsing, datatracker fetchers, rendering, CLI
conftest.py                  # empty on purpose — its presence makes pytest resolve
                              # build_agenda from the repo root without a package layout
tests/test_build_agenda.py   # unit + end-to-end tests (network calls are mocked)
tests/fixtures/sample.csv    # small fixture CSV used by the CSV-parsing tests
```

All automated tests mock `requests.get` — no test hits the real network.
