# ani-manga-blocklist
The biggest, most complete and refined blocklist (anime+manga+novels) you will find on the net (~6500 unique domains).
It's meant to be used for DNS content filternig, but you can adapt it otherwise as well.


# I want to contribute (website is not on the list)
Make sure to download the list, and do a grep before contributing the domain.
Furthermore, after downloading the list , do a 
```
cat list.txt | sort -u > newlist.txt
```
To make sure that the domains are sorted and unique.

# Repository Structure
- `refined-blacklist.txt`: Maintained and refined blocklist (AI + manual checks).
- `src/`: Python utilities (`git-scrapper.py`, `url-scrapper.py`, `open-domains.py`).
- `lists/`: Supplementary and generated blocklists (`joined-blacklist.txt`, `big-anime-blacklist.txt`, `android.txt`, etc.).

# Utilities
- `src/git-scrapper.py`
  Scrapes source repositories for domains and merges them with `refined-blacklist.txt`.
  ```bash
  python src/git-scrapper.py
  ```

- `src/url-scrapper.py`
  A multi-threaded script to scrape external URLs from a given site:
  - You can specify depth of scan for internal links (`--depth`)
  - Supports verbose mode (`-v`)
  - Supports ignore files (`--ignore-file`)
  - Saves crawled external domains (`--output`, defaults to `lists/external_domains.txt`)

  Example:
  ```bash
  python src/url-scrapper.py wotaku.wiki --depth 3 --output lists/links.txt --ignore-file nocrawl.txt -v
  ```
  Requires `beautifulsoup4` and `requests`.

- `src/open-domains.py`
  A utility to manually verify domains by opening them in Brave browser in batches.
  ```bash
  python src/open-domains.py lists/extracted_domains.txt
  ```
