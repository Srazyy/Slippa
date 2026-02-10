"""
CLI interface for Slippa.
Handles user interaction and orchestrates the pipeline.
"""

import os
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from slippa import __version__, __app_name__
from slippa.downloader import download_video
from slippa.transcriber import transcribe_audio
from slippa.clipper import find_clips
from slippa.cutter import cut_clips


console = Console()


def print_banner():
    """Print the Slippa welcome banner."""
    banner = f"""
[bold cyan]{__app_name__}[/bold cyan] v{__version__}
[dim]AI-powered YouTube clip generator — runs 100% locally[/dim]
    """.strip()
    console.print(Panel(banner, border_style="cyan"))


def main():
    """Main CLI flow."""
    print_banner()
    console.print()

    # Step 1: Get video source
    source = Prompt.ask(
        "[bold]Enter a YouTube URL or path to a local video file[/bold]"
    )

    if not source:
        console.print("[red]No input provided. Exiting.[/red]")
        return

    # Step 2: Download or validate video
    console.print()
    if source.startswith(("http://", "https://", "www.")):
        console.print("[yellow]📥 Downloading video from YouTube...[/yellow]")
        video_path = download_video(source)
    else:
        if not os.path.exists(source):
            console.print(f"[red]File not found: {source}[/red]")
            return
        video_path = source

    console.print(f"[green]✅ Video ready:[/green] {video_path}")

    # Step 3: Transcribe
    console.print()
    console.print("[yellow]🎤 Transcribing audio (this may take a while)...[/yellow]")
    transcription = transcribe_audio(video_path)
    console.print(f"[green]✅ Transcription complete![/green] ({len(transcription)} segments)")

    # Step 4: Find clips
    console.print()
    console.print("[yellow]🧠 Analyzing transcript for clip-worthy moments...[/yellow]")
    clips = find_clips(transcription)

    if not clips:
        console.print("[red]No good clips found. Try a different video.[/red]")
        return

    console.print(f"[green]✅ Found {len(clips)} potential clips![/green]")

    # Show clip summary
    for i, clip in enumerate(clips):
        duration = clip["end"] - clip["start"]
        console.print(
            f"  [cyan]Clip {i + 1}:[/cyan] "
            f"{clip['start']:.1f}s → {clip['end']:.1f}s "
            f"([dim]{duration:.1f}s[/dim])"
        )

    # Step 5: Cut clips
    console.print()
    if Confirm.ask(f"Cut these {len(clips)} clips?", default=True):
        console.print("[yellow]✂️  Cutting clips...[/yellow]")
        clip_paths = cut_clips(video_path, clips)
        console.print(f"[green]✅ Saved {len(clip_paths)} clips to [bold]clips/[/bold][/green]")

        # Step 6: Upload (placeholder for Phase 4)
        # console.print()
        # if Confirm.ask("Upload clips to YouTube?", default=False):
        #     from slippa.uploader import upload_clips
        #     upload_clips(clip_paths)

    console.print()
    console.print("[bold green]🎉 Done![/bold green]")
