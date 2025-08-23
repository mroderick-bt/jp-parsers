import re, time, html
from urllib.request import Request, urlopen
from pytube import Playlist, YouTube, extract

# --- helpers ---------------------------------------------------------------

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def to_watch_url(u: str) -> str:
    m = re.search(r'(?:v=|/shorts/)([A-Za-z0-9_-]{11})', u)
    return f"https://www.youtube.com/watch?v={m.group(1)}" if m else u

def fetch_html(url: str, timeout=20) -> str:
    req = Request(url, headers={"User-Agent": UA})
    return urlopen(req, timeout=timeout).read().decode("utf-8", errors="ignore")

def parse_title_channel_from_html(html_text: str) -> tuple[str|None, str|None]:
    # Title via og:title
    mt = re.search(r'<meta property="og:title" content="(.*?)">', html_text, re.I)
    title = html.unescape(mt.group(1)) if mt else None

    ch = None

    # 1) Microdata block: <span itemprop="author"> ... <link itemprop="name" content="CHANNEL">
    m1 = re.search(
        r'<span[^>]+itemprop=["\']author["\'][^>]*>.*?<link[^>]+itemprop=["\']name["\'][^>]+content=["\'](.*?)["\']',
        html_text, re.I | re.S
    )
    if m1:
        ch = html.unescape(m1.group(1))

    # 2) JSON: "ownerChannelName":"CHANNEL NAME"
    if not ch:
        m2 = re.search(r'"ownerChannelName"\s*:\s*"([^"]+)"', html_text)
        if m2:
            ch = html.unescape(m2.group(1))

    # 3) JSON deep: "videoOwnerRenderer": { ... "title": {"simpleText":"CHANNEL"} }
    if not ch:
        m3 = re.search(
            r'"videoOwnerRenderer"\s*:\s*\{.*?"title"\s*:\s*\{.*?"simpleText"\s*:\s*"([^"]+)"',
            html_text, re.S
        )
        if m3:
            ch = html.unescape(m3.group(1))

    return title, ch

def fetch_title_channel(video_url: str, try_pytube_first=True) -> tuple[str|None, str|None, str]:
    """
    Returns (title, channel, source) where source is 'pytube' or 'html'.
    Silently falls back to HTML if pytube raises.
    """
    if try_pytube_first:
        try:
            yt = YouTube(video_url)
            return yt.title, yt.author, "pytube"
        except Exception:
            # stay quiet; we'll fall back to HTML scraping
            pass

    try:
        html_text = fetch_html(video_url)
        title, channel = parse_title_channel_from_html(html_text)
        return title, channel, "html"
    except Exception:
        return None, None, "html"

# --- main scan -------------------------------------------------------------

def scan_playlist_titles_channels(playlist_url: str, progress_callback=None, polite_delay=0.25):
    print("Fetching playlist…", flush=True)
    pl = Playlist(playlist_url)
    # harmless workaround for some pytube versions:
    pl._video_regex = re.compile(r"watch\?v=([-\w]{11})")

    raw_urls = list(pl.video_urls)
    urls = [to_watch_url(u) for u in raw_urls]
    print(f"Found {len(urls)} videos", flush=True)

    out = []
    total = len(urls)
    for i, (raw, u) in enumerate(zip(raw_urls, urls), 1):
        if progress_callback: progress_callback(i-1, total)
        title, channel, source = fetch_title_channel(u, try_pytube_first=True)
        print(f"[{i}/{total}] {source} → {title or 'NO TITLE'}  |  {channel or 'NO CHANNEL'}", flush=True)
        out.append({"url": u, "title": title, "channel": channel, "source": source})
        if progress_callback: progress_callback(i, total)
        time.sleep(polite_delay)
    return out

# Example run:
if __name__ == "__main__":
    PLAYLIST_URL = "https://www.youtube.com/watch?v=-uv-FhIOPvE&list=PLZBgMlPaUrok9AcZIAuLvoUFyFQJAsz8J"
    items = scan_playlist_titles_channels(PLAYLIST_URL)
    print(f"Done. {sum(1 for x in items if x['title'])}/{len(items)} titles, "
          f"{sum(1 for x in items if x['channel'])}/{len(items)} channels.")