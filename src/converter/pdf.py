"""
PDF generation from chapter images
"""

from pathlib import Path
from typing import Optional


def create_pdf(
    image_dir: Path, 
    output_path: Optional[Path] = None,
    delete_images: bool = False
) -> Path:
    """
    Create a PDF from images in a directory.
    
    Args:
        image_dir: Directory containing images
        output_path: Path for the output PDF (default: same dir with .pdf extension)
        delete_images: Whether to delete source images after PDF creation
        
    Returns:
        Path to the created PDF file
    """
    import img2pdf
    import tempfile
    from PIL import Image

    if output_path is None:
        output_path = image_dir.parent / f"{image_dir.name}.pdf"
    
    # Remove an empty PDF left behind by an older failed conversion
    if output_path.exists() and output_path.stat().st_size == 0:
        output_path.unlink()
    
    # Remove temp files left behind by older failed conversions
    for stale in image_dir.glob('*.temp.png'):
        try:
            stale.unlink()
        except OSError:
            pass
    
    # Get all image files sorted
    image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
    images = sorted(
        [
            f for f in image_dir.iterdir()
            if f.is_file()
            and f.suffix.lower() in image_extensions
            and not f.name.endswith('.temp.png')
        ],
        key=lambda p: p.stem
    )
    
    if not images:
        raise ValueError(f"No images found in {image_dir}")
    
    pdf_images = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        for img_path in images:
            with Image.open(img_path) as img:
                # Skip sliver images (e.g. 1080x2 separators) that img2pdf rejects
                if min(img.size) < 10:
                    continue
                
                # Handle formats that img2pdf might not support directly
                if img_path.suffix.lower() in {'.webp', '.gif'} or img.mode in ('RGBA', 'LA', 'P'):
                    rgba_img = img.convert('RGBA')
                    rgb_img = Image.new('RGB', rgba_img.size, (255, 255, 255))
                    rgb_img.paste(rgba_img, mask=rgba_img.getchannel('A'))
                    temp_path = Path(temp_dir) / f"{len(pdf_images):04d}.png"
                    rgb_img.save(temp_path, 'PNG')
                    pdf_images.append(temp_path)
                else:
                    pdf_images.append(img_path)
        
        if not pdf_images:
            raise ValueError(f"No usable images found in {image_dir}")
        
        # Build in memory first so a failure never leaves a 0-byte PDF behind
        pdf_data = img2pdf.convert([str(p) for p in pdf_images])
    
    output_path.write_bytes(pdf_data)
    
    # Delete original images if requested
    if delete_images:
        for img_path in images:
            try:
                img_path.unlink()
            except Exception:
                pass
        
        # Try to remove the directory if empty
        try:
            image_dir.rmdir()
        except Exception:
            pass
    
    return output_path
