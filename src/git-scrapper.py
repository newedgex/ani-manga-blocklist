import os
import re
import shutil
import stat
import subprocess
import tempfile
import urllib.request
from urllib.parse import urlparse

# ==========================================
# 1. Configuration & Target Repositories
# ==========================================

REPOSITORIES = [
    "https://github.com/keiyoushi/extensions-source.git",
    "https://github.com/aniyomiorg/aniyomi-extensions.git",
    "https://github.com/LNReader/lnreader-sources.git",
    "https://github.com/kodjodevf/mangayomi-extensions.git",
    "https://github.com/miru-project/repo.git",
    "https://gitlab.com/shosetsuorg/extensions.git",
    "https://github.com/Aidoku-Community/sources.git",
    "https://github.com/Smexhy/yomu-aidoku-sources.git",
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def resolve_path(path_str: str) -> str:
    if os.path.isabs(path_str):
        return path_str
    if os.path.exists(path_str):
        return os.path.abspath(path_str)
    return os.path.join(BASE_DIR, path_str)

INPUT_FILE = "refined-blacklist.txt"
OUTPUT_FILE = os.path.join("lists", INPUT_FILE)

# Exact match or subdomain match for legitimate platforms & CDNs
EXCLUDED_DOMAINS = {
    "github.com", "github.io", "githubusercontent.com", "gitlab.com",
    "google.com", "googleapis.com", "gstatic.com", "facebook.com",
    "apple.com", "microsoft.com", "twitter.com", "x.com", "twimg.com",
    "discord.gg", "discord.com", "discordapp.com", "reddit.com",
    "telegram.org", "t.me", "bing.com", "ibm.com", "vk.com",
    "dailymotion.com", "deviantart.com", "patreon.com", "ko-fi.com",
    "medium.com", "archiveofourown.org", "blogger.com", "blogspot.com",
    "tiktok.com", "youtube.com", "youtu.be",
    "cloudflare.com", "cloudflareclient.com", "fastly.net", "akamai.net",
    "cloudfront.net", "jsdelivr.net", "unpkg.com", "vercel.app",
    "shields.io", "ipify.org", "ddos-guard.net", "browserleaks.com",
    "imgur.com", "imgur.io", "ibb.co", "postimg.cc", "imgbox.com",
    "krakenfiles.com", "wikimedia.org", "mixdrop.co", "flaticon.com",
    "dummyimage.com", "placehold.co", "shadcn.com", "weserv.nl",
    "w3.org", "schema.org", "json-schema.org", "apache.org",
    "opensource.org", "creativecommons.org", "kotlinlang.org",
    "jetbrains.com", "android.com", "oracle.com", "mozilla.org",
    "npmjs.com", "pypi.org", "maven.org", "gitee.com", "git-scm.com",
    "gradle.org", "npmmirror.com", "jitpack.io", "stackoverflow.com",
    "pkg.go.dev", "vitejs.dev", "protobuf.dev", "semver.org",
    "eslint.org", "jsoup.org", "js.org", "wordpress.org",
    "opencollective.com", "openfontlicense.org", "contributor-covenant.org",
    "mobilelegends.com", "leagueoflegends.com", "themoviedb.org", "aidoku.app",
    "localhost", "127.0.0.1", "example.com", "android.googlesource.com",
    "pagead2.googlesyndication.com", "syndication.realsrv.com"
}

CODE_FILE_EXTENSIONS = {
    "json", "js", "ts", "kt", "kts", "xml", "html", "css", "py", 
    "md", "txt", "yml", "yaml", "png", "jpg", "jpeg", "gif", "svg", 
    "zip", "jar", "gradle", "properties", "sh", "bat", "exe", "dll"
}

# Regex to catch variables like "a.callee.object.name" or "w.init.callee.property"
VARIABLE_PATTERN = re.compile(r'^[a-z]\.[a-z0-9\.]+$', re.IGNORECASE)

# ==========================================
# 2. IANA Top Level Domain Fetcher
# ==========================================

def fetch_valid_tlds() -> set:
    print("-> Fetching official IANA TLD list...")
    tlds = set()
    url = "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            for line in response:
                line = line.decode('utf-8').strip().lower()
                if line and not line.startswith('#'):
                    tlds.add(line)
        print(f"   Loaded {len(tlds)} valid TLDs.")
    except Exception as e:
        print(f"   [!] Failed to fetch TLDs: {e}")
        tlds.update({"com", "net", "org", "io", "co", "to", "moe", "tv", "ru", "cc", "app", "name", "info"})
    return tlds

VALID_TLDS = fetch_valid_tlds()

# ==========================================
# 3. Helper Functions & Logic
# ==========================================

URL_PATTERN = re.compile(r'https?://[^\s\'"<>\[\]\(\)]+', re.IGNORECASE)
_NAKED_DOMAIN = r'[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)+\.[a-zA-Z]{2,24}'
NAKED_DOMAIN_PATTERN = re.compile(r'["\'\[\(](' + _NAKED_DOMAIN + r')["\'\]\)]', re.IGNORECASE)

def handle_remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def is_excluded(domain: str) -> bool:
    domain = domain.lower().strip()
    if domain in EXCLUDED_DOMAINS:
        return True
    for excluded in EXCLUDED_DOMAINS:
        if domain.endswith("." + excluded):
            return True
    return False

def extract_domains_from_file(file_path: str) -> set:
    found_domains = set()
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        candidates = []
        
        urls = URL_PATTERN.findall(content)
        for url in urls:
            try:
                parsed = urlparse(url)
                if parsed.hostname:
                    candidates.append(parsed.hostname)
            except Exception:
                pass

        naked_domains = NAKED_DOMAIN_PATTERN.findall(content)
        candidates.extend(naked_domains)

        for raw_domain in candidates:
            domain = raw_domain.lower().strip(".")
            if domain.startswith("www."):
                domain = domain[4:]

            if "." not in domain or domain.replace(".", "").isdigit():
                continue
            if "$" in domain or "{" in domain or "}" in domain:
                continue

            # NEW: Filter out single-letter variable chains (e.g. a.novel.name)
            if VARIABLE_PATTERN.match(domain):
                continue

            tld = domain.split(".")[-1]
            
            if tld in CODE_FILE_EXTENSIONS:
                continue

            if tld not in VALID_TLDS:
                continue

            if not is_excluded(domain):
                found_domains.add(domain)

    except Exception:
        pass

    return found_domains

# ==========================================
# 4. Main Orchestration
# ==========================================

def process_repositories():
    all_domains = set()

    resolved_input = resolve_path(INPUT_FILE) if INPUT_FILE else None
    if resolved_input and os.path.exists(resolved_input):
        print(f"-> Reading initial domains from '{resolved_input}'...")
        try:
            with open(resolved_input, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    domain = line.strip().lower()
                    if domain.startswith("www."):
                        domain = domain[4:]
                    if domain and not domain.startswith("#"):
                        all_domains.add(domain)
            print(f"   Loaded {len(all_domains)} initial domains from '{resolved_input}'.")
        except Exception as e:
            print(f"  [!] Failed to read input file: {e}")
    elif INPUT_FILE:
        print(f"  [!] Input file '{INPUT_FILE}' not found. Starting with empty set.")

    for idx, repo_url in enumerate(REPOSITORIES, 1):
        print(f"\n[{idx}/{len(REPOSITORIES)}] Processing: {repo_url}")
        temp_dir = tempfile.mkdtemp(prefix="repo_scan_")

        try:
            print("  -> Shallow cloning repository...")
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--single-branch", repo_url, temp_dir],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            if result.returncode != 0:
                print("  [!] Clone failed. Skipping repository.")
                continue

            print("  -> Scanning source files...")
            repo_domains = set()

            for root, _, files in os.walk(temp_dir):
                if ".git" in root.split(os.sep):
                    continue
                for file in files:
                    file_path = os.path.join(root, file)
                    extracted = extract_domains_from_file(file_path)
                    repo_domains.update(extracted)

            print(f"  -> Extracted {len(repo_domains)} new candidate domains.")
            all_domains.update(repo_domains)

        finally:
            print("  -> Deleting clone...")
            shutil.rmtree(temp_dir, onerror=handle_remove_readonly)

    sorted_domains = sorted(all_domains)
    resolved_output = resolve_path(OUTPUT_FILE)
    os.makedirs(os.path.dirname(os.path.abspath(resolved_output)), exist_ok=True)
    with open(resolved_output, "w", encoding="utf-8") as f:
        for domain in sorted_domains:
            f.write(f"{domain}\n")

    print("\n" + "=" * 40)
    print(f"DONE: {len(sorted_domains)} unique domains saved to '{resolved_output}'.")
    print("=" * 40)

if __name__ == "__main__":
    process_repositories()