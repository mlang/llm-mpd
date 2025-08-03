from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from subprocess import Popen, PIPE
from sys import exit, stderr
from time import sleep
from typing import IO, Generator


from click import command, option
from llm import (
    get_default_model, get_key, get_model, hookimpl, Attachment, Template
)
from mpd import MPDClient # type: ignore
from mpd.base import CommandError # type: ignore
from openai import OpenAI


@hookimpl
def register_commands(cli):
    cli.add_command(mpd_cmd)

@hookimpl
def register_template_loaders(register):
    register("mpd", mpd_template_loader)

def mpd_template_loader(name: str) -> Template:
    if name == 'default':
        return Template(name=name,
            system="""\
Your name is $name. You are a moderator working with $station, a local radio station received in $location, $region.
You are good with words. Puns, rhymes and playing with words is one of your specialties.

You will see information about the previous and next song being played.
Present the upcoming song.  If you are being shown the coverart of the next song, make a detailed description of the artwork part of your announcement.
If you know about the artist or label, also add information about them to your song introduction.
If you can acquire information about the local environment, like weather or celestial events, make them a part of your moderation, but be brief about it.

Your native tongue is $language which is also what your audience knows best.
""",
            defaults=dict(
                name='Nova',
                station='Radio Mario',
                location='Graz',
                region='Austria',
                language='austrian german'
            ),
            prompt="""\
Date: $date
Previous: $prev
Next: $input
""",
            model="o4-mini"
        )

    raise RuntimeError("Unknown template")


@command()
@option('-t', '--template', default='mpd:default', show_default=True,
    help="Template to use"
)
@option("-p", "--param", multiple=True, type=(str, str),
    help="Parameters for template"
)
@option('tools', '-T', '--tool', multiple=True,
    help="Tools to make available to the model"
)
@option('-m', '--model',
    help="Use this chat model instead of the default provided in the template"
)
@option('--tts-model', default='gpt-4o-mini-tts', show_default=True,
    help="OpenAI TTS model to use"
)
@option('--tts-voice', default='nova', show_default=True,
    help="Voice to use"
)
@option('--tts-api-key',
    help="API key to use for Text-to-speech"
)
@option('--audio-format', default='flac', show_default=True)
@option('--mpd-socket', default='/run/mpd/socket', show_default=True)
@option('--clips-directory', required=True,
    help="Directory relative to MPD music directory to store speech clips in"
)
@option('-a', '--always', is_flag=True,
    help="Announce every song, not just those with album art"
)
def mpd_cmd(*,
    template, param, tools, model,
    tts_model, tts_voice, tts_api_key, audio_format,
    mpd_socket, clips_directory,
    always
):
    """A moderator for Music Player Daemon."""

    from llm.cli import _gather_tools

    mpd = MPDClient()
    try:
        mpd.connect(mpd_socket)
    except FileNotFoundError:
        print("Unable to connect to MPD socket, is MPD running?", file=stderr)
        exit(1)

    # NOTE:
    # Contrary to what the method name suggests, ``mpd.config()`` does **not**
    # return the full MPD configuration.  When connected via a UNIX-domain
    # socket it simply yields the *string* value of ``music_directory``.
    # Over a regular TCP connection the call is unsupported and will raise
    # an error.  Keep this in mind before refactoring this line.
    music_directory = Path(mpd.config())

    clips_directory = Path(clips_directory)

    if not (music_directory / clips_directory).is_dir():
        print(f"{music_directory / clips_directory} is not a directory.", file=stderr)
        exit(3)

    from llm.cli import load_template
    template = load_template(template)

    tools = _gather_tools(tools, [])

    model = get_model(model or template.model or get_default_model())
    if not ({'image/png', 'image/jpeg'} & model.attachment_types):
        print("The choosen model does not support jpeg or png attachments",
            file=stderr
        )
        exit(2)
    conversation = model.conversation(tools=tools)

    openai = OpenAI(api_key=get_key(tts_api_key, 'openai', 'OPENAI_API_KEY'))

    while True:
        status = mpd.status()
        if remaining := rolling_and_enough_time(status, 120):
            prev = mpd.currentsong()
            nextsongid = status["nextsongid"]
            next = mpd.playlistid(nextsongid)[0]
            del_internal_tags((prev, next))

            if none_from_us((prev, next), clips_directory):
                date = datetime.now() + timedelta(seconds=remaining)
                padding = int(status.get("xfade", "0"))
                padding -= padding // 5
                attachments = get_attachments(mpd, next['file'])

                if always or attachments:
                    prompt, system = template.evaluate(next,
                        {'date': date, 'prev': prev, **dict(param)}
                    )
                    if len(conversation.responses) > 20:
                        conversation = model.conversation(tools=tools)
                    announcement = conversation.chain(prompt,
                        system=system,
                        attachments=attachments,
                        tools=tools,
                        stream=False
                    ).text()

                    filename = music_directory / clips_directory / f'{date.strftime("%Y%m%dT%H%M%S")}.{audio_format}'
                    with openai.audio.speech.with_streaming_response.create(
                        input=announcement,
                        model=tts_model,
                        voice=tts_voice,
                        response_format=audio_format
                    ) as response:
                        with adjust_and_stream_to_file(
                            fmt=audio_format, padding=padding,
                            filename=filename
                        ) as pipe:
                            for chunk in response.iter_bytes(4096):
                                pipe.write(chunk)

                    clip = filename.relative_to(music_directory)
                    job = mpd.update(str(clip))
                    while mpd.status().get("updating_db") == job:
                        sleep(1)

                    if nextsongid == mpd.status().get('nextsongid'):
                        insert(mpd, str(clip))

        mpd.idle('player')


def del_internal_tags(songs):
    for key in ('duration', 'format', 'id', 'last-modified', 'pos', 'prio', 'time'):
        for song in songs:
            if key in song:
                del song[key]


def none_from_us(songs, clips_directory):
    for song in songs:
        if clips_directory in Path(song['file']).parents:
            return False

    return True


def rolling_and_enough_time(status, seconds):
    if "updating_db" not in status and status["state"] == "play":
        remaining = float(status["duration"]) - float(status["elapsed"])
        if remaining >= seconds and "nextsongid" in status:
            return remaining


@contextmanager
def adjust_and_stream_to_file(
    fmt: str, padding: int, filename: Path
) -> Generator[IO[bytes], None, None]:
    ffmpeg = ['ffmpeg',
        '-loglevel', 'error',
        '-f', fmt,
        '-i', 'pipe:0',
        '-filter_complex', ';'.join((
            '[0]loudnorm=I=-16:LRA=11:TP=-1[s0]',
            f"[s0]adelay={padding}s:all=True[s1]",
            f"[s1]apad=pad_dur={padding}[s2]"
        )),
        '-map', '[s2]',
        str(filename)
    ]
    proc = Popen(ffmpeg, stdin=PIPE)

    try:
        if proc.stdin is not None:
            with proc.stdin as pipe:
                yield pipe

            proc.wait()

    finally:
        if proc.poll() is None:
            proc.kill() 


def get_attachments(mpd, file) -> list[Attachment]:
    attachments = []

    try:
        attachments.append(Attachment(content=mpd.albumart(file)["binary"]))
    except CommandError:
        pass

    try:
        picture = mpd.readpicture(file)
        if picture:
            attachments.append(Attachment(content=picture["binary"]))
    except CommandError:
        pass

    return attachments


def insert(mpd, file):
    # https://mpd.readthedocs.io/en/latest/protocol.html#queuing
    status = mpd.status()
    id = mpd.addid(file)
    if 'nextsongid' in status:
        nextsong = mpd.playlistid(status['nextsongid'])[0]
        prio = min(int(nextsong.get('prio', '0')) + 1, 255)
        mpd.prioid(prio, id)
