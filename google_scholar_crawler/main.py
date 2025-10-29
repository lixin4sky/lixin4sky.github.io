from scholarly import scholarly, ProxyGenerator
import jsonpickle
import json
from datetime import datetime
import os
import time
import random


def init_proxy():
    pg = ProxyGenerator()
    try:
        # Free proxies are unreliable but better than hitting rate limits immediately
        if not pg.FreeProxies():
            print("[warn] No free proxies acquired; proceeding without proxies.")
        scholarly.use_proxy(pg)
    except Exception as e:
        print(f"[warn] Failed to initialize proxies: {e}")


def fetch_author(author_id: str, max_retries: int = 5, base_delay: float = 2.0) -> dict | None:
    """Fetch author data with retries and jitter. Returns None on persistent failure."""
    init_proxy()
    for attempt in range(1, max_retries + 1):
        try:
            author: dict = scholarly.search_author_id(author_id)
            scholarly.fill(author, sections=['basics', 'indices', 'counts', 'publications'])
            # Basic sanity checks
            if not author or 'name' not in author or 'publications' not in author:
                raise RuntimeError("Unexpected response while fetching author data")
            return author
        except Exception as e:
            wait = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1.0)
            print(f"[warn] Attempt {attempt}/{max_retries} failed: {e}. Retrying in {wait:.1f}s...")
            time.sleep(wait)
            # Re-initialize proxies between attempts to rotate
            init_proxy()
    return None


def main():
    author_id = os.environ.get('GOOGLE_SCHOLAR_ID')
    if not author_id:
        print('[error] Missing env GOOGLE_SCHOLAR_ID; skip crawling to avoid failure.')
        return 0

    author = fetch_author(author_id)

    # On failure, keep previous data if available to avoid breaking the workflow
    if author is None:
        print('[warn] Failed to fetch from Google Scholar (likely blocked or CAPTCHA).')
        print('[warn] Reusing existing results/gs_data.json if present and exiting successfully.')
        return 0

    # Normalize and persist
    author['updated'] = str(datetime.now())
    author['publications'] = {v['author_pub_id']: v for v in author.get('publications', [])}
    print(json.dumps(author, indent=2))

    os.makedirs('results', exist_ok=True)
    with open('results/gs_data.json', 'w') as outfile:
        json.dump(author, outfile, ensure_ascii=False)

    shieldio_data = {
        "schemaVersion": 1,
        "label": "citations",
        "message": f"{author.get('citedby', 0)}",
    }
    with open('results/gs_data_shieldsio.json', 'w') as outfile:
        json.dump(shieldio_data, outfile, ensure_ascii=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
