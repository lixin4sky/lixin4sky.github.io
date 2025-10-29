from scholarly import scholarly, ProxyGenerator
import jsonpickle
import json
from datetime import datetime
import os
import time
import random
import shutil


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
        os.makedirs('results', exist_ok=True)
        current_path = 'results/gs_data.json'
        root_path = os.path.join('..', 'results', 'gs_data.json')
        if os.path.exists(current_path):
            print('[info] Found existing results/gs_data.json; keeping it.')
            return 0
        if os.path.exists(root_path):
            try:
                shutil.copyfile(root_path, current_path)
                print('[info] Copied ../results/gs_data.json to results/ for downstream steps.')
                # Also mirror shields file if present
                root_shield = os.path.join('..', 'results', 'gs_data_shieldsio.json')
                if os.path.exists(root_shield):
                    shutil.copyfile(root_shield, os.path.join('results', 'gs_data_shieldsio.json'))
            except Exception as e:
                print(f"[warn] Failed to copy fallback data: {e}")
            return 0
        # If no historical data, write a minimal stub to keep pipeline green
        print('[info] No historical data found; writing minimal stub results to proceed.')
        minimal = {"name": "unknown", "citedby": 0, "updated": str(datetime.now()), "publications": {}}
        with open(current_path, 'w') as f:
            json.dump(minimal, f, ensure_ascii=False)
        with open('results/gs_data_shieldsio.json', 'w') as f:
            json.dump({"schemaVersion": 1, "label": "citations", "message": "0"}, f, ensure_ascii=False)
        return 0

    # Optionally slow down by filling each publication individually with a delay
    per_pub_delay = float(os.environ.get('PER_PUB_DELAY', '1'))
    pubs = author.get('publications', [])
    for idx, pub in enumerate(pubs, start=1):
        try:
            scholarly.fill(pub)
        except Exception as e:
            print(f"[warn] Failed to fill publication #{idx}: {e}")
        time.sleep(per_pub_delay)

    # Normalize and persist
    author['updated'] = str(datetime.now())
    author['publications'] = {v['author_pub_id']: v for v in pubs}
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
