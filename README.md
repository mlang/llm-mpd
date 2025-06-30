# llm-mpd

LLM presenter/moderator for Music Player Daemon.

## Installation

```bash
llm install git+https://github.com/mlang/llm-mpd
```

## Setup

`llm mpd` should be run on the same machine as your MPD server. This is mainly because it needs to be able to write to a folder inside your `music_directory`. This folder is called `clips-directory` and needs to be manually created before running `llm mpd`.

You also need to make sure the user you are planning to run `llm mpd` as has write access to the `clips-directory`.

Here's how you can create the directory:

```bash
mkdir /music/openai-speech
```

## Usage

Run the following command to start `llm mpd`:

```bash
llm mpd --clips-directory openai-speech
```

### Suggested Plugins

`llm mpd` supports tools. For instance, if you'd like your moderator to be able to query the weather at your location, you can install the following plugin and use it:

```bash
llm install git+https://github.com/mlang/llm-sky
llm mpd --tool 'Local("Graz")' --clips-directory openai-speech
```
