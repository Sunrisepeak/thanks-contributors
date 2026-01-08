import html
import urllib.request
import io
import ssl
from typing import List, Dict

FALLBACK_AVATAR = "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"

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


def render_wall(contributors: List[Dict], html_path: str, png_path: str):
    data = _normalize(contributors)
    data.sort(key=lambda x: x.get("contributions", 0), reverse=True)

    _render_html(data, html_path)
    if HAS_PIL:
        _render_png(data, png_path)


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

    html_out = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <title>Contributors</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
      background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
      color: #c9d1d9;
      min-height: 100vh;
      padding: 60px 24px;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    
    /* Header */
    header {{ margin-bottom: 60px; text-align: center; }}
    h1 {{ 
      font-size: 42px; 
      font-weight: 700;
      margin-bottom: 8px;
    }}
    h1 a {{ 
      background: linear-gradient(135deg, #58a6ff 0%, #79c0ff 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      text-decoration: none;
      transition: all 0.3s;
      display: inline-block;
    }}
    h1 a:hover {{ 
      filter: brightness(1.2);
      text-shadow: 0 0 20px rgba(88, 166, 255, 0.5);
    }}
    header p {{ font-size: 16px; color: #8b949e; margin: 8px 0; }}
    header a {{ color: #58a6ff; text-decoration: none; transition: color 0.3s; }}
    header a:hover {{ color: #79c0ff; }}
    
    /* Sections */
    .section {{ margin-bottom: 80px; }}
    .section-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 20px;
    }}
    .copy-btn {{
      background: linear-gradient(135deg, #58a6ff, #79c0ff);
      color: #0d1117;
      border: none;
      border-radius: 10px;
      padding: 10px 14px;
      font-weight: 600;
      cursor: pointer;
      transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
      box-shadow: 0 10px 20px rgba(88, 166, 255, 0.25);
    }}
    .copy-btn:hover {{
      filter: brightness(1.05);
      transform: translateY(-2px);
      box-shadow: 0 8px 12px rgba(88, 166, 255, 0.35);
    }}
    .copy-btn:active {{
      transform: translateY(0);
      box-shadow: 0 2px 4px rgba(88, 166, 255, 0.25);
    }}
    
    /* Grid */
    .grid {{ 
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
      gap: 20px;
    }}
    .item {{ 
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
      padding: 12px;
      border-radius: 16px;
      text-decoration: none;
      color: inherit;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      background: rgba(22, 27, 34, 0.4);
      border: 1px solid rgba(48, 54, 61, 0.5);
      backdrop-filter: blur(10px);
    }}
    .item:hover {{ 
      background: rgba(88, 166, 255, 0.1);
      border-color: rgba(88, 166, 255, 0.6);
      transform: translateY(-8px);
      box-shadow: 0 12px 24px rgba(88, 166, 255, 0.15);
    }}
    .item img {{ 
      width: 72px;
      height: 72px;
      border-radius: 50%;
      object-fit: cover;
      border: 2px solid rgba(88, 166, 255, 0.2);
      transition: border-color 0.3s;
    }}
    .item:hover img {{ border-color: rgba(88, 166, 255, 0.8); }}
    .name {{ 
      font-weight: 600;
      font-size: 14px;
      text-align: center;
    }}
    .email {{ 
      font-size: 11px;
      color: #8b949e;
      text-align: center;
      word-break: break-all;
      line-height: 1.3;
    }}
    
    /* PNG Section */
    .png-wrapper {{
      background: rgba(22, 27, 34, 0.6);
      border: 1px solid rgba(88, 166, 255, 0.2);
      border-radius: 20px;
      padding: 40px;
      backdrop-filter: blur(10px);
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
    }}
    .png-wrapper .copy-btn {{
      margin-bottom: 24px;
    }}
    .png-wrapper img {{
      max-width: 100%;
      height: auto;
      border-radius: 12px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    }}
    
    /* Responsive */
    @media (max-width: 768px) {{
      h1 {{ font-size: 32px; }}
      .section-title {{ font-size: 18px; }}
      .grid {{ grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 12px; }}
      body {{ padding: 40px 16px; }}
      .png-wrapper {{ padding: 24px; }}
    }}
  </style>
</head>
<body>
  <div class='container'>
    <header>
      <h1><a href='https://github.com/Sunrisepeak/all-contributors' target='_blank'>All Contributors</a></h1>
      <p>一个自动统计组织或多个项目贡献者的开源工具 - 示例为 Sunrisepeak 维护的所有仓库</p>
      <p>Designed By <a href='https://github.com/Sunrisepeak' target='_blank'>Sunrisepeak</a></p>
    </header>
    
    <div class='section'>
      <div class='grid'>
        {''.join(items)}
      </div>
    </div>

    <div class='section'>
      <div class='png-wrapper'>
        <button class='copy-btn' id='copy-png-link'>复制贡献者图片链接</button>
        <img src='./contributors.png' alt='Contributors' />
      </div>
    </div>
  </div>
</body>
<script>
  (function() {{
    const btn = document.getElementById('copy-png-link');
    if (!btn) return;
    const url = new URL('./contributors.png', window.location.href).href;
    btn.addEventListener('click', async () => {{
      try {{
        await navigator.clipboard.writeText(url);
        const old = btn.textContent;
        btn.textContent = '已复制';
        setTimeout(() => btn.textContent = old, 1500);
      }} catch (e) {{
        btn.textContent = url;
      }}
    }});
  }})();
</script>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)
