"""
Kagane Downloader - Beautiful Interactive CLI
A manga downloader for kagane.org with concurrent downloads
"""

import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text
from rich.style import Style
from rich import box

from config import Config, get_config, save_config
from src.scraper import BrowserManager, MangaScraper, ChapterDownloader, MangaInfo, Chapter
from src.converter import create_pdf, create_cbz

# Initialize Rich console
console = Console()

# App metadata
APP_NAME = "Kagane Downloader"
APP_VERSION = "1.0.0"

# Create Typer app
app = typer.Typer(
    name="kagane",
    help="Beautiful CLI manga downloader for kagane.org",
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True
)


def display_banner():
    """Display the application banner"""
    banner = Text()
    banner.append("╔═══════════════════════════════════════════════════════════╗\n", style="bold cyan")
    banner.append("║", style="bold cyan")
    banner.append("              🎴 KAGANE DOWNLOADER 🎴                      ", style="bold magenta")
    banner.append("║\n", style="bold cyan")
    banner.append("║", style="bold cyan")
    banner.append("           Beautiful Manga Downloads for You               ", style="dim white")
    banner.append("║\n", style="bold cyan")
    banner.append("╚═══════════════════════════════════════════════════════════╝", style="bold cyan")
    
    console.print(banner)
    console.print()


def display_main_menu() -> int:
    """Display main menu and get user choice"""
    table = Table(
        show_header=False,
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 2)
    )
    table.add_column("Option", style="bold yellow", width=4)
    table.add_column("Action", style="white")
    
    table.add_row("1", "📥 Download Manga by URL")
    table.add_row("2", "⚙️  Settings")
    table.add_row("3", "🚪 Exit")
    
    console.print(Panel(table, title="[bold cyan]Main Menu[/]", border_style="cyan"))
    
    while True:
        choice = Prompt.ask(
            "[bold yellow]Select option[/]",
            choices=["1", "2", "3"],
            default="1"
        )
        return int(choice)


def display_manga_info(manga: MangaInfo):
    """Display manga information in a beautiful panel"""
    info_text = Text()
    info_text.append(f"📖 Title: ", style="cyan")
    info_text.append(f"{manga.title}\n", style="bold white")
    
    info_text.append(f"✍️  Author: ", style="cyan")
    info_text.append(f"{manga.author or 'Unknown'}\n", style="white")
    
    info_text.append(f"📡 Source: ", style="cyan")
    info_text.append(f"{manga.source or 'Unknown'}\n", style="white")
    
    info_text.append(f"📊 Status: ", style="cyan")
    status_style = "green" if manga.status == "ONGOING" else "yellow"
    info_text.append(f"{manga.status or 'Unknown'}\n", style=status_style)
    
    info_text.append(f"📚 Chapters: ", style="cyan")
    info_text.append(f"{manga.total_chapters or len(manga.chapters)}\n", style="white")
    
    info_text.append(f"👁️  Views: ", style="cyan")
    info_text.append(f"{manga.views or 'Unknown'}\n", style="white")
    
    if manga.is_erotica:
        info_text.append(f"🔞 Content: ", style="cyan")
        info_text.append("18+ Erotica\n", style="red bold")
    
    info_text.append(f"🏷️  Genres: ", style="cyan")
    info_text.append(", ".join(manga.genres) if manga.genres else "None", style="dim white")
    
    console.print(Panel(info_text, title="[bold magenta]Manga Information[/]", border_style="magenta"))


def display_chapters(chapters: list[Chapter], max_display: int = 0):
    """Display chapters in a table with optional limit"""
    # If max_display is 0, show all chapters
    display_count = len(chapters) if max_display == 0 else min(max_display, len(chapters))
    
    table = Table(
        title=f"[bold cyan]Available Chapters[/] [dim]({display_count} of {len(chapters)})[/]",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True
    )
    
    table.add_column("#", style="bold yellow", width=4, justify="right")
    table.add_column("Ch.", style="cyan", width=6, justify="right")
    table.add_column("Title", style="white", max_width=45)
    table.add_column("Pages", style="dim", width=6, justify="center")
    table.add_column("Date", style="dim", width=12)
    
    for idx in range(display_count):
        ch = chapters[idx]
        title_display = ch.title[:42] + "..." if len(ch.title) > 45 else ch.title
        table.add_row(
            str(idx + 1),
            ch.number,
            title_display,
            ch.pages or "-",
            ch.date or "-"
        )
    
    console.print(table)
    
    if max_display > 0 and len(chapters) > max_display:
        console.print(f"[dim]Showing first {display_count} of {len(chapters)} chapters (change in settings)[/]")
    else:
        console.print(f"[dim]Showing all {len(chapters)} chapters[/]")


def get_chapter_selection(chapters: list[Chapter]) -> list[Chapter]:
    """Get user's chapter selection with range support"""
    console.print()
    console.print("[bold cyan]Chapter Selection:[/]")
    console.print("  • Enter a single number (e.g., [yellow]5[/])")
    console.print("  • Enter a range (e.g., [yellow]1-10[/])")
    console.print("  • Enter [yellow]all[/] for all chapters")
    console.print("  • Enter [yellow]q[/] to cancel")
    console.print()
    
    while True:
        selection = Prompt.ask("[bold yellow]Your selection[/]").strip().lower()
        
        if selection == 'q':
            return []
        
        if selection == 'all':
            return chapters.copy()
        
        # Check for range
        if '-' in selection:
            try:
                parts = selection.split('-')
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                
                if 1 <= start <= len(chapters) and 1 <= end <= len(chapters):
                    if start <= end:
                        return chapters[start - 1:end]
                    else:
                        return chapters[end - 1:start]
                else:
                    console.print(f"[red]Range must be between 1 and {len(chapters)}[/]")
            except (ValueError, IndexError):
                console.print("[red]Invalid range format. Use: start-end (e.g., 1-10)[/]")
        else:
            # Single chapter
            try:
                num = int(selection)
                if 1 <= num <= len(chapters):
                    return [chapters[num - 1]]
                else:
                    console.print(f"[red]Please enter a number between 1 and {len(chapters)}[/]")
            except ValueError:
                console.print("[red]Invalid input. Enter a number, range, 'all', or 'q'[/]")


def download_chapters_concurrent(
    browser_manager: BrowserManager,
    manga: MangaInfo,
    chapters: list[Chapter],
    config: Config
):
    """Download chapters with concurrent browser tabs"""
    download_dir = Path(config.download_directory)
    download_dir.mkdir(parents=True, exist_ok=True)
    
    # Create downloader with concurrent settings
    downloader = ChapterDownloader(
        browser_manager,
        download_dir,
        config.image_load_delay,
        max_concurrent_chapters=config.max_concurrent_chapters,
        max_concurrent_images=config.max_concurrent_images,
        max_retries=config.max_retries
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        overall_task = progress.add_task(
            f"[cyan]Downloading {len(chapters)} chapter(s) ({config.max_concurrent_chapters} concurrent)...",
            total=len(chapters)
        )
        
        def update_progress(current, total, status):
            progress.update(overall_task, completed=current, description=f"[cyan]{status}")
        
        # Use concurrent tab-based download
        results = downloader.download_chapters_concurrent(
            chapters,
            manga.title,
            progress_callback=update_progress
        )
        
        progress.update(overall_task, completed=len(chapters))
    
    # Convert files if needed
    if config.download_format in ("pdf", "cbz"):
        with console.status(f"[cyan]Converting to {config.download_format.upper()}...[/]", spinner="dots"):
            for chapter, success, chapter_dir in results:
                if success and chapter_dir and chapter_dir.exists():
                    try:
                        if config.download_format == "pdf":
                            create_pdf(
                                chapter_dir,
                                delete_images=not config.keep_images
                            )
                        elif config.download_format == "cbz":
                            create_cbz(
                                chapter_dir,
                                manga=manga,
                                chapter=chapter,
                                delete_images=not config.keep_images
                            )
                    except Exception as e:
                        if config.enable_logs:
                            console.print(f"[red]Error converting Ch.{chapter.number}: {e}[/]")
    
    # Display results
    console.print()
    success_count = sum(1 for _, success, _ in results if success)
    
    if success_count == len(chapters):
        console.print(Panel(
            f"[bold green]✓ Successfully downloaded {success_count}/{len(chapters)} chapters![/]",
            border_style="green"
        ))
    elif success_count > 0:
        console.print(Panel(
            f"[bold yellow]⚠ Downloaded {success_count}/{len(chapters)} chapters (some failed)[/]",
            border_style="yellow"
        ))
    else:
        console.print(Panel(
            f"[bold red]✗ Failed to download any chapters[/]",
            border_style="red"
        ))


def download_manga_flow():
    """Main flow for downloading manga"""
    console.print()
    
    url = Prompt.ask(
        "[bold cyan]Enter manga URL[/]",
        default=""
    )
    
    if not url or 'kagane.org' not in url:
        console.print("[red]Invalid URL. Please enter a kagane.org manga URL.[/]")
        return
    
    config = get_config()
    
    with console.status("[bold cyan]Initializing browser...[/]", spinner="dots"):
        browser = BrowserManager()
        browser.init_browser()
    
    console.print("[green]✓[/] Browser initialized")
    
    try:
        # Scrape manga info
        with console.status("[bold cyan]Loading manga information...[/]", spinner="dots"):
            scraper = MangaScraper(browser)
            manga = scraper.scrape_manga(url)
        
        if not manga.title:
            console.print("[red]✗ Failed to load manga information[/]")
            return
        
        console.print("[green]✓[/] Manga loaded successfully")
        console.print()
        
        # Display manga info
        display_manga_info(manga)
        
        if not manga.chapters:
            console.print("[red]No chapters found![/]")
            return
        
        # Display chapters
        console.print()
        display_chapters(manga.chapters, config.max_display_chapters)
        
        # Get chapter selection
        selected = get_chapter_selection(manga.chapters)
        
        if not selected:
            console.print("[yellow]Download cancelled.[/]")
            return
        
        console.print(f"\n[cyan]Selected {len(selected)} chapter(s) for download[/]")
        
        if not Confirm.ask("[bold yellow]Proceed with download?[/]", default=True):
            console.print("[yellow]Download cancelled.[/]")
            return
        
        # Download chapters
        download_chapters_concurrent(browser, manga, selected, config)
        
    finally:
        with console.status("[cyan]Closing browser...[/]", spinner="dots"):
            browser.close_browser()
        console.print("[green]✓[/] Browser closed")


def settings_menu():
    """Display and modify settings"""
    config = get_config()
    
    while True:
        console.print()
        
        table = Table(
            title="[bold cyan]Current Settings[/]",
            box=box.ROUNDED,
            border_style="cyan"
        )
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("1. Download Format", config.download_format.upper())
        table.add_row("2. Keep Images", "Yes" if config.keep_images else "No")
        table.add_row("3. Max Concurrent Chapter Downloads", str(config.max_concurrent_chapters))
        table.add_row("4. Max Concurrent Image Downloads", str(config.max_concurrent_images))
        table.add_row("5. Max Display Chapters", "All" if config.max_display_chapters == 0 else str(config.max_display_chapters))
        table.add_row("6. Download Directory", config.download_directory)
        table.add_row("7. Enable Logs", "Yes" if config.enable_logs else "No")
        table.add_row("8. Image Load Delay", f"{config.image_load_delay}s")
        table.add_row("9. Back to Main Menu", "-")
        
        console.print(table)
        
        choice = Prompt.ask(
            "[bold yellow]Select setting to modify[/]",
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
            default="9"
        )
        
        if choice == "1":
            format_choice = Prompt.ask(
                "[cyan]Download format[/]",
                choices=["images", "pdf", "cbz"],
                default=config.download_format
            )
            config.download_format = format_choice  # type: ignore
            
        elif choice == "2":
            config.keep_images = Confirm.ask("[cyan]Keep images after conversion?[/]", default=config.keep_images)
            
        elif choice == "3":
            config.max_concurrent_chapters = IntPrompt.ask(
                "[cyan]Max concurrent chapter downloads (browser tabs)[/]",
                default=config.max_concurrent_chapters
            )
            
        elif choice == "4":
            config.max_concurrent_images = IntPrompt.ask(
                "[cyan]Max concurrent image downloads per chapter[/]",
                default=config.max_concurrent_images
            )
            
        elif choice == "5":
            display_val = IntPrompt.ask(
                "[cyan]Max chapters to display (0 = show all)[/]",
                default=config.max_display_chapters
            )
            config.max_display_chapters = max(0, display_val)
            
        elif choice == "6":
            config.download_directory = Prompt.ask(
                "[cyan]Download directory[/]",
                default=config.download_directory
            )
            
        elif choice == "7":
            config.enable_logs = Confirm.ask("[cyan]Enable logs?[/]", default=config.enable_logs)
            
        elif choice == "8":
            config.image_load_delay = IntPrompt.ask(
                "[cyan]Image load delay (seconds)[/]",
                default=config.image_load_delay
            )
            
        elif choice == "9":
            save_config(config)
            console.print("[green]✓ Settings saved![/]")
            break
        
        save_config(config)
        console.print("[green]✓ Setting updated![/]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Kagane Downloader - Beautiful CLI manga downloader for kagane.org
    """
    # Only run interactive mode if no subcommand was invoked
    if ctx.invoked_subcommand is not None:
        return
    
    display_banner()
    
    while True:
        try:
            choice = display_main_menu()
            
            if choice == 1:
                download_manga_flow()
            elif choice == 2:
                settings_menu()
            elif choice == 3:
                console.print("\n[bold cyan]👋 Goodbye! Happy reading![/]\n")
                break
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/]")
            break
        except Exception as e:
            config = get_config()
            if config.enable_logs:
                console.print(f"[red]Error: {e}[/]")
            else:
                console.print("[red]An error occurred. Enable logs in settings for details.[/]")


@app.command()
def download(
    url: str = typer.Argument(..., help="Manga URL to download"),
    chapters: str = typer.Option("all", "-c", "--chapters", help="Chapters to download (e.g., '1-10', 'all', '5')"),
    format: str = typer.Option(None, "-f", "--format", help="Download format (images/pdf/cbz)"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose logging")
):
    """
    Download manga directly with command line arguments.
    """
    config = get_config()
    
    if verbose:
        config.enable_logs = True
    
    if format:
        config.download_format = format
    
    display_banner()
    
    console.print(f"[cyan]URL:[/] {url}")
    console.print(f"[cyan]Chapters:[/] {chapters}")
    console.print(f"[cyan]Format:[/] {config.download_format}")
    console.print()
    
    with console.status("[bold cyan]Initializing browser...[/]", spinner="dots"):
        browser = BrowserManager()
        browser.init_browser()
    
    console.print("[green]✓[/] Browser initialized")
    
    try:
        with console.status("[bold cyan]Loading manga information...[/]", spinner="dots"):
            scraper = MangaScraper(browser)
            manga = scraper.scrape_manga(url)
        
        if not manga.title:
            console.print("[red]✗ Failed to load manga information[/]")
            raise typer.Exit(1)
        
        console.print("[green]✓[/] Manga loaded successfully")
        display_manga_info(manga)
        
        if not manga.chapters:
            console.print("[red]No chapters found![/]")
            raise typer.Exit(1)
        
        # Parse chapter selection
        if chapters.lower() == "all":
            selected = manga.chapters.copy()
        elif "-" in chapters:
            parts = chapters.split("-")
            start = int(parts[0].strip())
            end = int(parts[1].strip())
            selected = manga.chapters[start - 1:end]
        else:
            num = int(chapters)
            selected = [manga.chapters[num - 1]]
        
        console.print(f"\n[cyan]Downloading {len(selected)} chapter(s)...[/]")
        
        download_chapters_concurrent(browser, manga, selected, config)
        
    finally:
        with console.status("[cyan]Closing browser...[/]", spinner="dots"):
            browser.close_browser()
        console.print("[green]✓[/] Browser closed")


if __name__ == "__main__":
    app()
