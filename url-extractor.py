import sys
import argparse
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import os

# Global sets protected by locks for thread-safety
visited_lock = threading.Lock()
visited_urls = set()

external_lock = threading.Lock()
external_domains = set()

def strip_www(domain):
    return domain.lower().lstrip("www.")

def normalize_domain(input_domain):
    if not input_domain.startswith("http://") and not input_domain.startswith("https://"):
        input_domain = "http://" + input_domain
    parsed = urlparse(input_domain)
    base_domain = strip_www(parsed.netloc)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    return base_url, base_domain

def extract_links_from_html(html):
    """Extract hrefs from <a> tags and also attempt to find urls in the page using a regex."""
    soup = BeautifulSoup(html, "html.parser")
    hrefs = []
    # Extract from <a> tags
    for link in soup.find_all("a", href=True):
        href = link['href'].strip()
        if href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        hrefs.append(href)

    # Additionally, search whole HTML for URLs that might not be in <a> tags
    url_pattern = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
    all_urls = url_pattern.findall(html)
    for u in all_urls:
        if u not in hrefs:
            hrefs.append(u)

    return hrefs

def categorize_links(hrefs, base_url, base_domain):
    internal_urls = set()
    found_externals = set()
    for href in hrefs:
        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)
        if not parsed.netloc:
            continue
        link_domain = strip_www(parsed.netloc)
        if link_domain == base_domain:
            internal_urls.add(absolute_url)
        else:
            found_externals.add(link_domain)
    return internal_urls, found_externals

def process_url(url, depth, max_depth, base_url, base_domain, verbose, ignored_domains):
    # Check if already visited
    with visited_lock:
        if url in visited_urls:
            return []
        visited_urls.add(url)

    if verbose:
        print(f"[INFO] Crawling: {url} (depth: {depth})")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/96.0.4664.110 Safari/537.36"
        )
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        page_html = r.text
    except Exception as e:
        if verbose:
            print(f"[ERROR] Failed to retrieve {url}: {e}")
        return []

    hrefs = extract_links_from_html(page_html)
    internal_urls, externals = categorize_links(hrefs, base_url, base_domain)

    # Filter external domains by ignored domains
    externals = {d for d in externals if d not in ignored_domains}

    newly_found_externals = []
    with external_lock:
        for d in externals:
            if d not in external_domains:
                external_domains.add(d)
                newly_found_externals.append(d)

    if verbose and newly_found_externals:
        print(f"[INFO] Found external domains at {url}:")
        for domain in newly_found_externals:
            print(f"       - {domain}")

    next_tasks = []
    if depth < max_depth:
        new_internal_links = []
        with visited_lock:
            for link in internal_urls:
                if link not in visited_urls:
                    new_internal_links.append(link)

        if verbose and new_internal_links:
            print(f"[INFO] Discovered internal links at {url}:")
            for link in new_internal_links:
                print(f"       + {link}")

        for link in new_internal_links:
            next_tasks.append((link, depth + 1))

    return next_tasks

def main():
    parser = argparse.ArgumentParser(description="A multi-threaded web crawler that finds external domains.")
    parser.add_argument("domain", help="The starting domain to crawl.")
    parser.add_argument("--depth", type=int, default=1, help="Max depth to crawl. Default=1.")
    parser.add_argument("--output", default="external_domains.txt", help="Output file for external domains.")
    parser.add_argument("--ignore-file", default=None, help="File containing domains to ignore.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")

    args = parser.parse_args()

    base_url, base_domain = normalize_domain(args.domain)
    max_depth = args.depth
    output_file = args.output
    verbose = args.verbose

    # Load ignored domains if provided
    ignored_domains = set()
    if args.ignore_file and os.path.exists(args.ignore_file):
        try:
            with open(args.ignore_file, 'r') as f:
                for line in f:
                    d = line.strip()
                    if d:
                        ignored_domains.add(strip_www(d))
        except Exception as e:
            if verbose:
                print(f"[ERROR] Could not load ignore file {args.ignore_file}: {e}")

    if verbose:
        print(f"[START] Starting crawl at {base_url} up to depth {max_depth}")
        if ignored_domains:
            print("[INFO] Ignored domains loaded:")
            for d in ignored_domains:
                print(f"       - {d}")

    max_workers = 5  # Adjust as needed
    tasks = [(base_url, 0)]

    # We'll process tasks in a loop as they generate new tasks
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_url, url, depth, max_depth, base_url, base_domain, verbose, ignored_domains)
                   for url, depth in tasks]

        while futures:
            done, futures = as_completed(futures, timeout=None), []
            new_tasks = []
            for future in done:
                result = future.result()
                if result:
                    new_tasks.extend(result)
            for (u, d) in new_tasks:
                futures.append(executor.submit(process_url, u, d, max_depth, base_url, base_domain, verbose, ignored_domains))

    if verbose:
        print("[DONE] Crawling complete.")

    with open(output_file, 'w') as f:
        with external_lock:
            for domain in sorted(external_domains):
                f.write(domain + "\n")

    print(f"Found {len(external_domains)} external domains. Results saved to {output_file}.")

if __name__ == "__main__":
    main()
