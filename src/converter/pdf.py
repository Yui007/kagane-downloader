"""
PDF generation from chapter images
"""

from pathlib import Path
from typing import Optional

import img2pdf
from PIL import Image


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
    if output_path is None:
        output_path = image_dir.parent / f"{image_dir.name}.pdf"
    
    # Get all image files sorted
    image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
    images = sorted(
        [f for f in image_dir.iterdir() if f.is_file() and f.suffix.lower() in image_extensions],
        key=lambda p: p.stem
    )
    
    if not images:
        raise ValueError(f"No images found in {image_dir}")
    
    # Convert images to PDF-compatible format
    pdf_images = []
    temp_files = []
    
    for img_path in images:
        # Handle formats that img2pdf might not support directly
        if img_path.suffix.lower() in {'.webp', '.gif'}:
            # Convert to PNG first
            with Image.open(img_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Convert to RGB for PDF compatibility
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    temp_path = img_path.with_suffix('.temp.png')
                    rgb_img.save(temp_path, 'PNG')
                    temp_files.append(temp_path)
                    pdf_images.append(temp_path)
                else:
                    temp_path = img_path.with_suffix('.temp.png')
                    img.save(temp_path, 'PNG')
                    temp_files.append(temp_path)
                    pdf_images.append(temp_path)
        else:
            # Check if image has alpha channel
            with Image.open(img_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    temp_path = img_path.with_suffix('.temp.png')
                    rgb_img.save(temp_path, 'PNG')
                    temp_files.append(temp_path)
                    pdf_images.append(temp_path)
                else:
                    pdf_images.append(img_path)
    
    # Create PDF
    with open(output_path, 'wb') as f:
        f.write(img2pdf.convert([str(p) for p in pdf_images]))
    
    # Clean up temp files
    for temp_file in temp_files:
        try:
            temp_file.unlink()
        except Exception:
            pass
    
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
