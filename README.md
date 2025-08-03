# llm-mpd

> Narrator for Music Player Daemon (MPD)

`llm-mpd` collects details about the current and upcoming tracks, sends them to an LLM to craft a spoken introduction, synthesizes the narration with OpenAI TTS, and inserts the resulting audio clip into your MPD playlist so it plays between songs.

## Features
- Automatically generated, voice-acted narrations between tracks  
- Vision support: album-art descriptions incorporated into the script  
- Works with MPD random mode and adds padding to accommodate crossfade
- Tool calling (e.g. local weather) for timely shout-outs  
- Fully configurable through [LLM templates](https://llm.datasette.io/en/stable/templates.html) and CLI flags

## Installation

Prerequisites  
* Python ≥ 3.9  
* Running MPD server with write access to its `music_directory`  
* `ffmpeg` available on your `$PATH`  
* OpenAI API key (for TTS)

```bash
# Install the core LLM framework
pipx install llm

# Install this plugin
llm install git+https://github.com/mlang/llm-mpd
```

## Setup

1. Create a writable sub-directory inside your MPD music directory, for example:  
   ```bash
   mkdir -p /music/openai-speech
   chown mpd:mpd /music/openai-speech   # adjust user/group if needed
   ```
2. Set your OpenAI key (or pass it with `--tts-api-key`):  
   ```bash
   llm keys set openai
   ```

## Usage

Start the narrator:

```bash
llm mpd --clips-directory openai-speech
```

Common options:

| Flag | Default | Purpose |
|------|---------|---------|
| `--template` | `mpd:default` | Select an LLM template |
| `--param KEY VALUE` | – | Override template variables |
| `--tool` | – | Expose an LLM tool (e.g. weather) |
| `--tts-model` | `gpt-4o-mini-tts` | OpenAI TTS model |
| `--always` | off | Announce every song, not just those with art |

Run `llm mpd --help` for the full list.

## Customisation

Templates live in the LLM template system.  
The bundled `mpd:default` template supports:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `name`    | Nova    | On-air persona |
| `station` | Radio Mario | Station name |
| `location`| Graz    | Listener city |
| `region`  | Austria | Listener region |
| `language`| Austrian German | Language to speak |

Override any of these:

```bash
llm mpd \
  --clips-directory openai-speech \
  --param name DJ-Wanda \
  --param language "Canadian French"
```

## Suggested Plugins

Enable weather references in narrations:

```bash
llm install git+https://github.com/mlang/llm-sky
llm mpd --tool 'Local("Graz")' --clips-directory openai-speech
```

## Contributing

Issues and pull requests are welcome.  

## License

Apache-2.0 – see [LICENSE](LICENSE).
