# splicecrate

Organize your [Splice](https://splice.com) sample library into a browsable directory structure for hardware samplers like the [1010music Blackbox](https://1010music.com/blackbox).

Splice stores samples in pack-based folders that are painful to navigate on a small screen. splicecrate reads your Splice `sounds.db` database, categorizes samples by instrument type, and builds a clean folder hierarchy — then syncs it to your SD card.

## Features

- **20 instrument categories** derived from your actual sample tags — kicks, snares, bass, synth, vocals, piano, and more
- **Incremental updates** — only copies new or changed samples, never deletes existing files (safe for samples no longer available on Splice)
- **Two-phase workflow** — stage locally (fast), then sync to SD card (skip files already present)
- **Smart organization** — percussive samples stay flat for quick browsing; melodic samples are sorted by key and type
- **Dry-run mode** — preview what will be copied before committing

## Directory structure

```
SD card/
  kicks/
    kick-sample.wav
  snares/
    snr-001.wav
  grooves/
    loop/
      120-drum-break.wav
    oneshot/
      fill-smash.wav
  bass/
    oneshot/
      C/
        C-bass-hit.wav
    loop/
      G#-120-bass-loop.wav
  808/
    oneshot/
      F/
        F-808-sub.wav
  synth/
    loop/
      A-140-synth-pad.wav
  vocals/
    loop/
      130-vocal-chop.wav
  other/
    oneshot/
      misc-sample.wav
```

## Setup

**Get your sounds database:**

1. Open the Splice desktop app
2. Go to Settings and click **Download logs**
3. Extract the zip and copy your `sounds.db`:
   ```
   unzip ~/Downloads/SpliceLogs-*.zip -d SpliceLogs
   cp SpliceLogs/users/default/YOUR_USERNAME/sounds.db .
   ```

**Optional config file** at `~/.splorganizer/splorganizer.toml`:

```toml
splice_dir = "C:/Users/you/Documents/Splice/Samples"
stage_dir = "C:/Users/you/Documents/Splice/Splorganized"
dest_dir = "E:/"
sounds_db = "C:/path/to/sounds.db"
```

All paths can also be passed as CLI flags.

## Usage

```bash
# See what you've got
python -m splorganize --db sounds.db status

# Preview what would be organized
python -m splorganize --db sounds.db organize --dry-run

# Organize samples to local staging directory
python -m splorganize --db sounds.db organize

# Preview what would sync to SD card
python -m splorganize --dest-dir E:/ sync --dry-run

# Sync staged files to SD card
python -m splorganize --dest-dir E:/ sync
```

### Commands

| Command | Description |
|---------|-------------|
| `organize` | Read sounds.db and copy new/changed samples to local staging directory |
| `sync` | Copy staged files to SD card, skipping files already present |
| `status` | Show category counts and how many samples are new since last run |

### Flags

| Flag | Description |
|------|-------------|
| `--db PATH` | Path to sounds.db |
| `--stage-dir PATH` | Local staging directory |
| `--dest-dir PATH` | SD card mount point |
| `--dry-run` | Preview without copying |
| `-v, --verbose` | Enable debug logging |

## Categories

Categories are defined in `hierarchy.json` and matched against sample tags and filenames in sounds.db.

**Percussive** (flat directories, no key sorting):
kicks, snares, hats, claps, cymbals, percussion, grooves, fx

**Melodic** (sorted by sample type and musical key):
808, bass, synth, leads, stabs, piano, keys, guitar, orchestral, sax, pads, vocals

Samples matching multiple categories are copied to all of them. Anything unmatched goes to `other/`.

## Requirements

- Python 3.11+
- No external dependencies (stdlib only)

## Credits

Originally forked from [splorganizer](https://github.com/ebai101/splorganizer) by Ethan Bailey.

## License

[MIT](LICENSE)

---

*Not affiliated with Splice or 1010music.*
