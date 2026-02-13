"""
Kagane Downloader V2 - Beautiful Interactive CLI
A manga downloader for kagane.org using the fast API
"""

import sys
from pathlib import Path
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
from src.scraper import KaganeScraper, Series, Book

# Initialize Rich console
console = Console()

# App metadata
APP_NAME = "Kagane Downloader"
APP_VERSION = "2.0.0"

# Create Typer app
app = typer.Typer(
    name="kagane",
    help="Beautiful CLI manga downloader for kagane.org (API-based)",
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True
)


def display_banner():
    """Display the application banner"""
    banner = Text()
    banner.append("+" + "=" * 59 + "+\n", style="bold cyan")
    banner.append("|", style="bold cyan")
    banner.append("              KAGANE DOWNLOADER V2                         ", style="bold magenta")
    banner.append("|\n", style="bold cyan")
    banner.append("|", style="bold cyan")
    banner.append("           Fast API-Based Manga Downloads                  ", style="dim white")
    banner.append("|\n", style="bold cyan")
    banner.append("+" + "=" * 59 + "+", style="bold cyan")
    
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
    
    table.add_row("1", "[>] Download Manga by URL")
    table.add_row("2", "[*] Settings")
    table.add_row("3", "[X] Exit")
    
    console.print(Panel(table, title="[bold cyan]Main Menu[/]", border_style="cyan"))
    
    while True:
        choice = Prompt.ask(
            "[bold yellow]Select option[/]",
            choices=["1", "2", "3"],
            default="1"
        )
        return int(choice)


def display_series_info(series: Series):
    """Display series information in a beautiful panel"""
    info_text = Text()
    info_text.append("Title: ", style="cyan")
    info_text.append(f"{series.title}\n", style="bold white")
    
    info_text.append("Format: ", style="cyan")
    info_text.append(f"{series.format or 'Unknown'}\n", style="white")
    
    info_text.append("Status: ", style="cyan")
    status = series.publication_status or series.upload_status or "Unknown"
    status_style = "green" if status.lower() in ["ongoing", "active"] else "yellow" if status.lower() == "hiatus" else "white"
    info_text.append(f"{status}\n", style=status_style)
    
    info_text.append("Chapters: ", style="cyan")
    info_text.append(f"{series.current_books}\n", style="white")
    
    info_text.append("Views: ", style="cyan")
    info_text.append(f"{series.total_views or 'Unknown'}\n", style="white")
    
    info_text.append("Language: ", style="cyan")
    info_text.append(f"{series.translated_language.upper() if series.translated_language else 'Unknown'}\n", style="white")
    
    if series.content_rating and series.content_rating.lower() not in ["safe", ""]:
        info_text.append("Content: ", style="cyan")
        info_text.append(f"{series.content_rating}\n", style="red bold")
    
    info_text.append("Genres: ", style="cyan")
    genre_names = [g.genre_name for g in series.genres if not g.is_spoiler]
    info_text.append(", ".join(genre_names) if genre_names else "None", style="dim white")
    
    console.print(Panel(info_text, title="[bold magenta]Series Information[/]", border_style="magenta"))


def display_books(books: list[Book], max_display: int = 0):
    """Display books/chapters in a table with optional limit"""
    # If max_display is 0, show all chapters
    display_count = len(books) if max_display == 0 else min(max_display, len(books))
    
    table = Table(
        title=f"[bold cyan]Available Chapters[/] [dim]({display_count} of {len(books)})[/]",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True
    )
    
    table.add_column("#", style="bold yellow", width=4, justify="right")
    table.add_column("Ch.", style="cyan", width=6, justify="right")
    table.add_column("Title", style="white", max_width=45)
    table.add_column("Pages", style="dim", width=6, justify="center")
    table.add_column("Views", style="dim", width=8, justify="center")
    
    for idx in range(display_count):
        book = books[idx]
        title_display = book.title[:42] + "..." if len(book.title) > 45 else book.title
        table.add_row(
            str(idx + 1),
            book.chapter_no,
            title_display,
            str(book.page_count) if book.page_count else "-",
            str(book.views) if book.views else "-"
        )
    
    console.print(table)
    
    if max_display > 0 and len(books) > max_display:
        console.print(f"[dim]Showing first {display_count} of {len(books)} chapters (change in settings)[/]")
    else:
        console.print(f"[dim]Showing all {len(books)} chapters[/]")


def get_book_selection(books: list[Book]) -> list[Book]:
    """Get user's chapter selection with range support"""
    console.print()
    console.print("[bold cyan]Chapter Selection:[/]")
    console.print("  - Enter a single number (e.g., [yellow]5[/])")
    console.print("  - Enter a range (e.g., [yellow]1-10[/])")
    console.print("  - Enter [yellow]all[/] for all chapters")
    console.print("  - Enter [yellow]q[/] to cancel")
    console.print()
    
    while True:
        selection = Prompt.ask("[bold yellow]Your selection[/]").strip().lower()
        
        if selection == 'q':
            return []
        
        if selection == 'all':
            return books.copy()
        
        # Check for range
        if '-' in selection:
            try:
                parts = selection.split('-')
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                
                if 1 <= start <= len(books) and 1 <= end <= len(books):
                    if start <= end:
                        return books[start - 1:end]
                    else:
                        return books[end - 1:start]
                else:
                    console.print(f"[red]Range must be between 1 and {len(books)}[/]")
            except (ValueError, IndexError):
                console.print("[red]Invalid range format. Use: start-end (e.g., 1-10)[/]")
        else:
            # Single chapter
            try:
                num = int(selection)
                if 1 <= num <= len(books):
                    return [books[num - 1]]
                else:
                    console.print(f"[red]Please enter a number between 1 and {len(books)}[/]")
            except ValueError:
                console.print("[red]Invalid input. Enter a number, range, 'all', or 'q'[/]")


def download_manga_flow():
    """Main flow for downloading manga using API"""
    console.print()
    
    url = Prompt.ask(
        "[bold cyan]Enter manga URL or series ID[/]",
        default=""
    )
    
    if not url:
        console.print("[red]Invalid URL. Please enter a kagane.org manga URL or series ID.[/]")
        return
    
    config = get_config()
    
    try:
        # Fetch series info using API (much faster!)
        with console.status("[bold cyan]Fetching series information via API...[/]", spinner="dots"):
            scraper = KaganeScraper()
            series = scraper.get_series(url)
        
        if not series.title:
            console.print("[red][X] Failed to load series information[/]")
            return
        
        console.print("[green][OK][/] Series loaded successfully")
        console.print()
        
        # Display series info
        display_series_info(series)
        
        if not series.series_books:
            console.print("[red]No chapters found![/]")
            return
        
        # Display chapters
        console.print()
        display_books(series.series_books, config.max_display_chapters)
        
        # Get chapter selection
        selected = get_book_selection(series.series_books)
        
        if not selected:
            console.print("[yellow]Download cancelled.[/]")
            return
        
        console.print(f"\n[cyan]Selected {len(selected)} chapter(s) for download[/]")
        
        # Show selected chapters info
        console.print("\n[bold]Selected Chapters:[/]")
        for book in selected[:5]:  # Show first 5
            console.print(f"  - Ch. {book.chapter_no}: {book.title} ({book.page_count} pages)")
        if len(selected) > 5:
            console.print(f"  ... and {len(selected) - 5} more")
        
        console.print()
        
        if not Confirm.ask("[bold yellow]Proceed with download?[/]", default=True):
            console.print("[yellow]Download cancelled.[/]")
            scraper.close()
            return
        
        # Download chapters
        download_chapters_api(series, selected, config)
        
        scraper.close()
        
    except ValueError as e:
        console.print(f"[red]Error: {e}[/]")
    except Exception as e:
        if config.enable_logs:
            console.print(f"[red]Error: {e}[/]")
        else:
            console.print("[red]An error occurred. Enable logs in settings for details.[/]")


def download_chapters_api(series: Series, books: list[Book], config: Config):
    """Download chapters using API-based approach"""
    from src.scraper import BrowserManager, APIChapterDownloader, get_image_urls_from_browser
    from src.converter import create_pdf, create_cbz
    
    download_dir = Path(config.download_directory)
    download_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize browser for capturing image URLs
    console.print("\n[cyan]Initializing browser for image capture...[/]")
    browser = BrowserManager()
    browser.init_browser(headless=config.headless_mode, enable_network_logs=True)
    driver = browser.get_driver()
    
    # Create downloader
    downloader = APIChapterDownloader(
        download_dir=download_dir,
        max_concurrent_images=config.max_concurrent_images,
        max_retries=config.max_retries
    )
    
    results = []
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            overall_task = progress.add_task(
                f"[cyan]Downloading {len(books)} chapter(s)...",
                total=len(books)
            )
            
            for idx, book in enumerate(books):
                progress.update(overall_task, description=f"[cyan]Loading Chapter {book.chapter_no}...")
                
                # Create chapter directory
                safe_title = downloader.sanitize_filename(series.title, max_length=50)
                safe_chapter = downloader.sanitize_filename(f"Chapter_{book.chapter_no}_{book.title}", max_length=80)
                chapter_dir = download_dir / safe_title / safe_chapter
                chapter_dir.mkdir(parents=True, exist_ok=True)
                
                try:
                    # Capture image URLs from browser
                    image_urls = get_image_urls_from_browser(
                        driver,
                        series.series_id,
                        book.book_id,
                        wait_time=config.image_load_delay
                    )
                    
                    if not image_urls:
                        results.append((book, False, chapter_dir, 0))
                        progress.update(overall_task, completed=idx + 1)
                        continue
                    
                    # Download images
                    pages_downloaded = downloader.download_from_urls(
                        image_urls, 
                        chapter_dir,
                        lambda c, t: progress.update(
                            overall_task, 
                            description=f"[cyan]Ch.{book.chapter_no}: {c}/{t} images"
                        )
                    )
                    
                    success = pages_downloaded > 0
                    results.append((book, success, chapter_dir, pages_downloaded))
                    
                except Exception as e:
                    if config.enable_logs:
                        console.print(f"[red]Error downloading Ch.{book.chapter_no}: {e}[/]")
                    results.append((book, False, chapter_dir, 0))
                
                progress.update(overall_task, completed=idx + 1)
        
        # Convert files if needed
        if config.download_format in ("pdf", "cbz"):
            with console.status(f"[cyan]Converting to {config.download_format.upper()}...[/]", spinner="dots"):
                for book, success, chapter_dir, _ in results:
                    if success and chapter_dir and chapter_dir.exists():
                        try:
                            if config.download_format == "pdf":
                                create_pdf(chapter_dir, delete_images=not config.keep_images)
                            elif config.download_format == "cbz":
                                create_cbz(chapter_dir, series=series, book=book, delete_images=not config.keep_images)
                        except Exception as e:
                            if config.enable_logs:
                                console.print(f"[red]Error converting Ch.{book.chapter_no}: {e}[/]")
        
        # Display results
        console.print()
        success_count = sum(1 for _, success, _, _ in results if success)
        
        if success_count == len(books):
            console.print(Panel(
                f"[bold green][OK] Successfully downloaded {success_count}/{len(books)} chapters![/]",
                border_style="green"
            ))
        elif success_count > 0:
            console.print(Panel(
                f"[bold yellow][!] Downloaded {success_count}/{len(books)} chapters (some failed)[/]",
                border_style="yellow"
            ))
        else:
            console.print(Panel(
                f"[bold red][X] Failed to download any chapters[/]",
                border_style="red"
            ))
        
    finally:
        browser.close_browser()
        downloader.close()


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
        table.add_row("3. Max Display Chapters", "All" if config.max_display_chapters == 0 else str(config.max_display_chapters))
        table.add_row("4. Download Directory", config.download_directory)
        table.add_row("5. Enable Logs", "Yes" if config.enable_logs else "No")
        table.add_row("6. Max Concurrent Chapter Downloads", str(config.max_concurrent_chapters))
        table.add_row("7. Max Concurrent Image Downloads", str(config.max_concurrent_images))
        table.add_row("8. Page Load Delay (seconds)", str(config.image_load_delay))
        table.add_row("9. Headless Mode", "Yes" if config.headless_mode else "No")
        table.add_row("10. Back to Main Menu", "-")
        
        console.print(table)
        
        choice = Prompt.ask(
            "[bold yellow]Select setting to modify[/]",
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
            default="10"
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
            display_val = IntPrompt.ask(
                "[cyan]Max chapters to display (0 = show all)[/]",
                default=config.max_display_chapters
            )
            config.max_display_chapters = max(0, display_val)
            
        elif choice == "4":
            config.download_directory = Prompt.ask(
                "[cyan]Download directory[/]",
                default=config.download_directory
            )
            
        elif choice == "5":
            config.enable_logs = Confirm.ask("[cyan]Enable logs?[/]", default=config.enable_logs)
        
        elif choice == "6":
            config.max_concurrent_chapters = IntPrompt.ask(
                "[cyan]Max concurrent chapter downloads[/]",
                default=config.max_concurrent_chapters
            )
        
        elif choice == "7":
            config.max_concurrent_images = IntPrompt.ask(
                "[cyan]Max concurrent image downloads per chapter[/]",
                default=config.max_concurrent_images
            )
        
        elif choice == "8":
            config.image_load_delay = IntPrompt.ask(
                "[cyan]Page load delay in seconds (time to wait for images to load)[/]",
                default=config.image_load_delay
            )
        
        elif choice == "9":
            config.headless_mode = Confirm.ask("[cyan]Run browser in headless mode (hidden)?[/]", default=config.headless_mode)

        elif choice == "10":
            save_config(config)
            console.print("[green][OK] Settings saved![/]")
            break
        
        save_config(config)
        console.print("[green][OK] Setting updated![/]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Kagane Downloader V2 - Beautiful CLI manga downloader for kagane.org
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
                console.print("\n[bold cyan]Goodbye! Happy reading![/]\n")
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
def info(
    url: str = typer.Argument(..., help="Manga URL or series ID"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose logging")
):
    """
    Display manga information without downloading.
    """
    config = get_config()
    
    if verbose:
        config.enable_logs = True
    
    display_banner()
    
    console.print(f"[cyan]Fetching:[/] {url}")
    console.print()
    
    try:
        with console.status("[bold cyan]Fetching series information...[/]", spinner="dots"):
            scraper = KaganeScraper()
            series = scraper.get_series(url)
        
        if not series.title:
            console.print("[red][X] Failed to load series information[/]")
            raise typer.Exit(1)
        
        console.print("[green][OK][/] Series loaded successfully")
        console.print()
        
        # Display series info
        display_series_info(series)
        
        # Display all chapters
        console.print()
        display_books(series.series_books, 0)  # Show all
        
        # Show additional info if verbose
        if verbose:
            console.print("\n[bold]Additional Information:[/]")
            console.print(f"  Series ID: {series.series_id}")
            console.print(f"  Source ID: {series.source_id}")
            console.print(f"  Tracker ID: {series.tracker_id}")
            console.print(f"  Created: {series.created_at}")
            console.print(f"  Updated: {series.updated_at}")
            
            if series.tags:
                console.print(f"\n  Tags ({len(series.tags)}):")
                tag_names = [t.tag_name for t in series.tags[:10] if not t.is_spoiler]
                console.print(f"    {', '.join(tag_names)}")
            
            if series.series_links:
                console.print(f"\n  External Links:")
                for link in series.series_links:
                    console.print(f"    - {link.label}: {link.url}")
        
        scraper.close()
        
    except ValueError as e:
        console.print(f"[red]Error: {e}[/]")
        raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (not implemented yet)")
):
    """
    Search for manga (placeholder for future implementation).
    """
    console.print("[yellow]Search functionality will be implemented when the search API is available.[/]")
    console.print(f"[dim]Query was: {query}[/]")


if __name__ == "__main__":
    app()
