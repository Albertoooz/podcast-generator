# ffmpeg — what it is and why this project needs it

## What is it?

**ffmpeg** is a widely used open-source **command-line** tool for processing **audio and video**: encode/decode, concatenate segments, change formats, and more. It runs on Windows, macOS, and Linux and is installed **separately** from Python (it is not a pip package).

## Why do we need it here?

The last pipeline step **merges individual MP3 clips** into a single episode file. That is done with [pydub](https://github.com/jiaaro/pydub), and **pydub uses ffmpeg** (or `avconv`) under the hood to:

- read MP3 files from the `clips/` directory,
- concatenate them into one track,
- write the result to `output/<episode>/audio/<episode>.mp3`.

If ffmpeg is not on your `PATH`, you may see warnings (e.g. “Couldn't find ffmpeg”) and the combine step can fail or produce an empty or broken file.

## Install (short)

| OS | Example |
|----|---------|
| **macOS** | `brew install ffmpeg` |
| **Ubuntu / Debian** | `sudo apt install ffmpeg` |
| **Windows** | [ffmpeg.org](https://ffmpeg.org/download.html) — add the `bin` folder to `PATH` |

After installing, run: `ffmpeg -version`.

## Can I generate a podcast without it?

**LLM + TTS** parts may still run, but **final audio merging** relies on pydub + ffmpeg. Install ffmpeg if you want the full flow through a finished MP3.
