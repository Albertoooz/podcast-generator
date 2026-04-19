"""CLI: init, generate, ui, TTS helpers, list-voices, list-profiles, list-speakers."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich import print as rprint

from app import __version__
from app.config_loader import (
    default_episodes_dict,
    list_episode_profile_names,
    list_library_speaker_ids,
)
from app.graph.workflow import create_podcast
from app.models.speaker import Speaker
from app.tts.registry import get_tts_provider
from app.tts.voice_library import add_voice, list_voices

cli = typer.Typer(no_args_is_help=True, add_completion=False)


def _root() -> Path:
    return Path(__file__).resolve().parent


def _resources() -> Path:
    return _root() / "resources"


def _project_root() -> Path:
    return _root().parent


@cli.command("init")
def init_cmd(
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory to write templates (default: cwd)",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
) -> None:
    """Copy default prompts and configs into the working directory."""
    target = output_dir or Path.cwd()
    target.mkdir(parents=True, exist_ok=True)
    res = _resources()
    proj_prompts = _project_root() / "prompts"
    prompts_src = proj_prompts if proj_prompts.is_dir() else res / "prompts"
    if prompts_src.is_dir():
        dest = target / "prompts"
        if dest.exists() and not force:
            rprint(f"[yellow]Skip[/yellow] {dest} (exists; use --force)")
        else:
            shutil.copytree(prompts_src, dest, dirs_exist_ok=True)
            rprint(f"[green]Copied[/green] prompts -> {dest}")
    dest_cfg = target / "configs"
    dest_cfg.mkdir(parents=True, exist_ok=True)
    for cfg in ("episodes.json", "speakers_library.json", "voices.json"):
        repo_cfg = _project_root() / "configs" / cfg
        bundled = repo_cfg if repo_cfg.exists() else res / cfg
        dest_file = dest_cfg / cfg
        if cfg == "episodes.json" and not bundled.exists():
            if not dest_file.exists() or force:
                dest_file.write_text(
                    json.dumps(default_episodes_dict(), indent=2) + "\n",
                    encoding="utf-8",
                )
                rprint(f"[green]Wrote[/green] {dest_file}")
        elif cfg == "speakers_library.json" and not bundled.exists():
            if not dest_file.exists() or force:
                dest_file.write_text('{"speakers": {}}\n', encoding="utf-8")
                rprint(f"[green]Wrote[/green] {dest_file}")
        elif cfg == "voices.json" and not bundled.exists():
            if not dest_file.exists() or force:
                dest_file.write_text('{"voices": {}}\n', encoding="utf-8")
                rprint(f"[green]Wrote[/green] {dest_file}")
        elif bundled.exists() and (not dest_file.exists() or force):
            shutil.copy(bundled, dest_file)
            rprint(f"[green]Wrote[/green] {dest_file}")
    example = target / "example_usage.py"
    if not example.exists() or force:
        example.write_text(
            """import asyncio
from app.graph.workflow import create_podcast

async def main():
    r = await create_podcast(
        content="Short topic text...",
        episode_profile="diverse_panel",
        episode_name="demo",
        output_dir="output/demo",
    )
    print(r)

asyncio.run(main())
""",
            encoding="utf-8",
        )
        rprint(f"[green]Wrote[/green] {example}")


@cli.command("generate")
def generate_cmd(
    content: str = typer.Option(..., "--content", "-c", help="Source text"),
    episode_name: str = typer.Option(..., "--episode", "-e"),
    output_dir: str = typer.Option("output/episode", "--output", "-o"),
    episode_profile: str = typer.Option(
        ...,
        "--profile",
        "-p",
        help="Episode id from configs/episodes.json",
    ),
    briefing: str | None = typer.Option(None, "--briefing", "-b"),
) -> None:
    """Run podcast generation pipeline."""
    result = asyncio.run(
        create_podcast(
            content=content,
            briefing=briefing,
            episode_name=episode_name,
            output_dir=output_dir,
            episode_profile=episode_profile,
        )
    )
    rprint(result)


@cli.command("ui")
def ui_cmd(
    port: int = typer.Option(8501, "--port"),
    host: str = typer.Option("127.0.0.1", "--host"),
) -> None:
    """Launch Streamlit UI."""
    app_path = _root() / "ui" / "streamlit_app.py"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.address",
        host,
    ]
    raise SystemExit(subprocess.call(cmd))


@cli.command("try-mistral-tts")
def try_mistral_tts_cmd(
    text: str = typer.Option(
        "Hello from Mistral Voxtral.", "--text", "-t", help="Text to synthesize"
    ),
    voice_id: str = typer.Option(
        "casual_male",
        "--voice",
        "-v",
        help="Preset voice_id (see Mistral / HF Voxtral README); used with or without --sample",
    ),
    sample: Path | None = typer.Option(
        None,
        "--sample",
        "-s",
        help="Optional WAV/MP3 reference (2–5s) for zero-shot cloning; sent as ref_audio",
    ),
    out: Path = typer.Option(
        Path("output/mistral_try.mp3"),
        "--out",
        "-o",
        help="Output audio file (.mp3 / .wav)",
    ),
) -> None:
    """Call Mistral cloud TTS (needs MISTRAL_API_KEY). Tests API + optional voice sample."""

    async def _run() -> None:
        if sample is not None and not sample.is_file():
            raise typer.BadParameter(f"Sample file not found: {sample}")
        sp = Speaker(
            name="Test",
            voice_id=voice_id,
            backstory="Test",
            personality="Test",
            style_description="",
            voice_sample_path=str(sample.resolve()) if sample else None,
        )
        provider = get_tts_provider("voxtral_cloud")
        await provider.synthesize(text, sp, out)
        rprint(f"[green]Wrote[/green] {out.resolve()}")

    asyncio.run(_run())


@cli.command("clone-voice")
def clone_voice_cmd(
    sample: Path | None = typer.Argument(
        None,
        help="Path to WAV/MP3 sample (required for sample-based providers)",
    ),
    label: str = typer.Option("Voice", "--label", "-L", help="Human label"),
    provider: str = typer.Option(
        "voxtral_cloud",
        "--provider",
        "-p",
        help="TTS provider id (voxtral_cloud, openai, elevenlabs, ...)",
    ),
    provider_voice_id: str | None = typer.Option(
        None,
        "--voice-id",
        "-v",
        help="Provider voice id or preset (required for openai/elevenlabs)",
    ),
    style: str = typer.Option("", "--style", "-s", help="Style / delivery description"),
    language: str | None = typer.Option(None, "--language", "-l"),
    voice_id: str | None = typer.Option(None, "--id", help="Optional library key"),
) -> None:
    """Register a voice in configs/voices.json."""
    if provider.lower() in ("openai", "elevenlabs") and not provider_voice_id:
        rprint("[red]--voice-id is required for openai and elevenlabs[/red]")
        raise typer.Exit(1)
    if provider.lower() not in ("openai", "elevenlabs") and sample is None:
        rprint("[red]sample path is required for this provider[/red]")
        raise typer.Exit(1)
    if sample is not None and not sample.is_file():
        rprint(f"[red]File not found: {sample}[/red]")
        raise typer.Exit(1)
    vid = add_voice(
        label,
        provider,
        provider_voice_id=provider_voice_id,
        sample_path=sample,
        style_description=style,
        language=language,
        voice_id=voice_id,
    )
    rprint(f"[green]Registered voice:[/green] {vid}")


@cli.command("list-voices")
def list_voices_cmd() -> None:
    """List registered cloned voices."""
    for v in list_voices():
        rprint(v)


@cli.command("list-profiles")
def list_profiles_cmd() -> None:
    """List episode profile names from configs/episodes.json."""
    rprint(", ".join(list_episode_profile_names()) or "(no profiles)")


@cli.command("list-speakers")
def list_speakers_cmd() -> None:
    """List global speaker ids from speakers_library.json."""
    for s in list_library_speaker_ids():
        rprint(s)


@cli.command("version")
def version_cmd() -> None:
    rprint(__version__)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
