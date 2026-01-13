import html
import urllib.request
import io
import ssl
import re
from typing import List, Dict
from pathlib import Path

FALLBACK_AVATAR = "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
TEMPLATE_DIR = Path(__file__).parent / "templates"
README_START_MARKER = "<!-- thanks-contributors-flag-start -->"
README_END_MARKER = "<!-- thanks-contributors-flag-end -->"

# Try to import PIL, but make it optional
try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def _normalize(contributors: List[Dict]) -> List[Dict]:
    normalized = []
    for c in contributors:
        normalized.append(
            {
                "name": c.get("name") or "Unknown",
                "email": c.get("email"),
                "avatar_url": c.get("avatar_url") or FALLBACK_AVATAR,
                "html_url": c.get("html_url") or "#",
                "contributions": int(c.get("contributions") or 0),
            }
        )
    return normalized


def _download_avatar(url: str) -> Image.Image:
    """Download avatar image from URL and return as PIL Image"""
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(url, context=ssl_context, timeout=5) as response:
            image_data = response.read()
        
        img = Image.open(io.BytesIO(image_data))
        return img.convert("RGBA")
    except Exception as e:
        # Return a placeholder image if download fails
        img = Image.new("RGBA", (80, 80), (200, 200, 200, 255))
        return img


def _make_circular(img: Image.Image, size: int) -> Image.Image:
    """Convert image to circular avatar with 3x anti-aliasing"""
    # Render at 3x resolution for smoother edges
    hi_size = size * 3
    img = img.resize((hi_size, hi_size), Image.Resampling.LANCZOS)
    
    # Create circular mask at high resolution
    mask = Image.new("L", (hi_size, hi_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([(0, 0), (hi_size, hi_size)], fill=255)
    
    # Create output with alpha channel at high resolution
    output = Image.new("RGBA", (hi_size, hi_size), (0, 0, 0, 0))
    output.paste(img.convert("RGBA"), (0, 0), mask)
    
    # Downsample to final size for smooth anti-aliased result
    output = output.resize((size, size), Image.Resampling.LANCZOS)
    return output


def render_wall(contributors: List[Dict], html_path: str, png_path: str, md_path: str = None, readme_path: str = None):
    data = _normalize(contributors)
    data.sort(key=lambda x: x.get("contributions", 0), reverse=True)

    _render_html(data, html_path)
    if HAS_PIL:
        _render_png(data, png_path)
    if md_path:
        _render_markdown(data, md_path)
    if readme_path:
        _update_readme(data, readme_path)


def _render_png(contributors: List[Dict], out_path: str):
    """Render contributors as PNG image grid using PIL with circular avatars and centered layout"""
    if not HAS_PIL:
        return
    
    if not contributors:
        img = Image.new("RGBA", (400, 80), color=(0, 0, 0, 0))
        img.save(out_path, "PNG")
        return
    
    num_contributors = len(contributors)
    avatar_size = 80
    padding = 16
    gap = 10  # Gap between avatars

    # Choose layout targeting a 2:1 aspect ratio (w:h)
    best = None
    for cols in range(1, num_contributors + 1):
      rows = (num_contributors + cols - 1) // cols
      width = cols * (avatar_size + gap) - gap + padding * 2
      height = rows * (avatar_size + gap) - gap + padding * 2
      ratio = width / height if height else 1
      score = abs(ratio - 2)  # closeness to 2:1
      area = width * height
      candidate = (score, area, cols, rows, width, height)
      if best is None or candidate < best:
        best = candidate

    _, _, columns, rows, width, height = best
    
    # Create transparent background image
    img = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
    
    for idx, c in enumerate(contributors):
        col = idx % columns
        row = idx // columns
        x = padding + col * (avatar_size + gap)
        y = padding + row * (avatar_size + gap)
        
        avatar_url = c.get("avatar_url") or FALLBACK_AVATAR
        try:
            # Download and process avatar
            avatar = _download_avatar(avatar_url)
            # Convert to circular with 3x anti-aliasing (returns avatar_size)
            avatar = _make_circular(avatar, avatar_size)
            # Paste onto main image with alpha channel
            img.paste(avatar, (x, y), avatar)
        except Exception:
            # If avatar fails, use placeholder circle
            placeholder = Image.new("RGBA", (avatar_size, avatar_size), color=(0, 0, 0, 0))
            placeholder_draw = ImageDraw.Draw(placeholder)
            placeholder_draw.ellipse([(0, 0), (avatar_size, avatar_size)], fill=(48, 54, 61, 255))
            img.paste(placeholder, (x, y), placeholder)
    
    img.save(out_path, "PNG")


def _render_html(contributors: List[Dict], out_path: str):
    if not contributors:
        html_out = """<html><head><meta charset=\"utf-8\"><title>Contributors</title></head><body><p>No contributors</p></body></html>"""
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_out)
        return

    items = []
    for c in contributors:
        name = html.escape(c.get("name") or "")
        email = html.escape(c.get("email") or "")
        avatar = c.get("avatar_url") or FALLBACK_AVATAR
        link = c.get("html_url") or "#"
        items.append(
            f"<a class='item' href='{link}' target='_blank' title='{name}'><img src='{avatar}' alt='{name}'><div class='name'>{name}</div><div class='email'>{email}</div></a>"
        )

    # Load HTML template
    template_path = TEMPLATE_DIR / "contributors.html"
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
    
    # Replace placeholder with items
    html_out = template_content.format(items=''.join(items))
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)


def _render_markdown(contributors: List[Dict], out_path: str):
    """Render contributors as Markdown with clickable avatars and names"""
    if not contributors:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("## All Contributors\n\nNo contributors yet.\n")
        return

    # Build table with 10 columns
    cols_per_row = 10
    rows = []
    
    for i in range(0, len(contributors), cols_per_row):
        row_contributors = contributors[i:i + cols_per_row]
        
        # Build table row
        row_cells = []
        for c in row_contributors:
            name = c.get("name") or "Unknown"
            avatar = c.get("avatar_url") or FALLBACK_AVATAR
            link = c.get("html_url") or "#"
            
            cell = f'''<td align="center">
        <a href="{link}">
            <img src="{avatar}" width="50;" alt="{name}"/>
            <br />
            <sub><b>{name}</b></sub>
        </a>
    </td>'''
            row_cells.append(cell)
        
        # Fill empty cells if needed
        while len(row_cells) < cols_per_row:
            row_cells.append('<td></td>')
        
        rows.append('<tr>\n    ' + '\n    '.join(row_cells) + '\n</tr>')
    
    table_content = '<table>\n' + '\n'.join(rows) + '\n</table>'

    # Load markdown template
    template_path = TEMPLATE_DIR / "contributors.md"
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
    
    # Replace placeholder with table
    md_out = template_content.format(items=table_content)
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md_out)


def _update_readme(contributors: List[Dict], readme_path: str):
    """Update README.md with contributors section"""
    readme_file = Path(readme_path).resolve()  # Resolve to absolute path
    
    print(f"DEBUG: Updating README at: {readme_file}")
    print(f"DEBUG: README exists: {readme_file.exists()}")
    print(f"DEBUG: Current working directory: {Path.cwd()}")
    
    if not readme_file.exists():
        print(f"WARNING: README file '{readme_file}' does not exist; skipping update.")
        return
    
    print(f"INFO: Updating README: {readme_file}")
    
    # Generate contributors table (same layout as _render_markdown)
    cols_per_row = 8
    rows = []
    
    for i in range(0, len(contributors), cols_per_row):
        row_contributors = contributors[i:i + cols_per_row]
        
        row_cells = []
        for c in row_contributors:
            name = c.get("name") or "Unknown"
            avatar = c.get("avatar_url") or FALLBACK_AVATAR
            link = c.get("html_url") or "#"
            
            cell = f'''<td align="center">
        <a href="{link}">
            <img src="{avatar}" width="50;" alt="{name}"/>
            <br />
            <sub><b>{name}</b></sub>
        </a>
    </td>'''
            row_cells.append(cell)
        
        while len(row_cells) < cols_per_row:
            row_cells.append('<td></td>')
        
        rows.append('<tr>\n    ' + '\n    '.join(row_cells) + '\n</tr>')
    
    table_content = '<table>\n' + '\n'.join(rows) + '\n</table>'
    
    contributors_content = f"{README_START_MARKER}\n{table_content}\n{README_END_MARKER}"
    
    # Read existing README
    with open(readme_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check if markers exist
    pattern = re.compile(
        re.escape(README_START_MARKER) + r".*?" + re.escape(README_END_MARKER),
        re.DOTALL
    )
    
    if pattern.search(content):
        # Replace existing section
        new_content = pattern.sub(contributors_content, content)
    else:
        # Append to the end
        if not content.endswith("\n"):
            content += "\n"
        new_content = content + "\n" + contributors_content + "\n"
    
    # Write back to README
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print(f"✓ Updated README: {readme_file}")
