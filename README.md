# llm-mpd

LLM Presenter/Moderator for Music Player Daemon.

## Installation

```bash
llm install git+https://github.com/mlang/llm-mpd
```

## Setup

`llm mpd` should be run on the same machine as your MPD server. This is required because it must be able to write to a folder inside your `music_directory`. This folder is called `clips-directory` and needs to be manually created before running `llm mpd`.

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

### Customization

`llm mpd` uses [LLM Templates](https://llm.datasette.io/en/stable/templates.html) to define the instructions for the moderator.

The default template provides a number of parameters to customize:

| Parameter | Default | Description |
|-----------|---------|-------------|
| name      | Nova    | The on-air name/persona the model should adopt |
| station   | Radio Mario | Name of the radio station being presented |
| location  | Graz    | City or locality of the listeners |
| region    | Austria | Wider region/country of the listeners |
| language  | Austrian German | Language the moderator should speak |


If you'd like to customize the system prompt or default model,
write your own template file and specify the template name when starting `llm mpd`.
Custom templates should make use of the variables `$date`, `$prev` and `$input`.
`$input` will contain information about the upcoming song.

### Suggested Plugins

`llm mpd` supports tools. For instance, if you'd like your moderator to be able to query the weather at your location, you can install the following plugin and use it:

```bash
llm install git+https://github.com/mlang/llm-sky
llm mpd --tool 'Local("Graz")' --clips-directory openai-speech
```
