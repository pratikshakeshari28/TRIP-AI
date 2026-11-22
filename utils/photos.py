"""Destination photos from Wikipedia (free, no API key).
 
get_photos(["Goa India", "Taj Mahal Agra"]) returns {query: image_url or None}.
- Lookups run in parallel, so a page with 10 photos loads in about one request time.
- Found URLs are saved in database/photo_cache.json, so they are instant next time.
- If the internet is down, it pauses lookups for 2 minutes and the app shows
  a gradient instead of a photo. The app never crashes because of photos.
"""
 
import json
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
 
CACHE_PATH = Path(__file__).resolve().parents[1] / "database" / "photo_cache.json"
_HEADERS = {"User-Agent": "TripAI-Hackathon/1.0 (student travel planner demo)"}
 
_lock = threading.Lock()
_cache = None
_offline_until = 0.0
 
 
def _load():
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            _cache = {}
    return _cache
 
 
def _save(cache):
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")
    except Exception:
        pass
 
 
def _fetch(query, width):
    url = (
        "https://en.wikipedia.org/w/api.php?action=query&format=json"
        "&generator=search&gsrlimit=1"
        f"&gsrsearch={urllib.parse.quote(query)}"
        f"&prop=pageimages&piprop=thumbnail&pithumbsize={width}"
    )
    request = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(request, timeout=6) as response:
        data = json.load(response)
 
    for page in (data.get("query") or {}).get("pages", {}).values():
        thumb = (page.get("thumbnail") or {}).get("source")
        if thumb:
            return thumb
    return ""  
 
 
def get_photos(queries, width=900):
    global _offline_until
 
    with _lock:
        cache = _load()
        wanted = [q for q in dict.fromkeys(queries) if q and q not in cache]
        if time.time() < _offline_until:
            wanted = []
 
        if wanted:
            def work(query):
                try:
                    return query, _fetch(query, width)
                except Exception:
                    return query, None  # network problem, do not cache
 
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(work, wanted))
 
            failed = False
            for query, url in results:
                if url is None:
                    failed = True
                else:
                    cache[query] = url
            if failed:
                _offline_until = time.time() + 120
            _save(cache)
 
        return {q: (cache.get(q) or None) for q in queries}
 
