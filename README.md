# ani-manga-blocklist
The biggest, most complete and refined blocklist (anime+manga+novels) you will find on the net (~4200 unique domains).
It's meant to be used for DNS content filternig, but you can adapt it otherwise as well.


# I want to contribute (website is not on the list)
Make sure to download the list, and do a grep before contributing the domain.
Furthermore, after downloading the list , do a 
```
cat list.txt | sort -u > newlist.txt
```
To make sure that the domains are sorted and unique.

# Which list should I be using?
refined-blacklist.txt - which is maintained and refined through AI and also manually checked

# Utilities
- url-scrapper.py
It's a script used to scrap URL's from a main site with very good options :
  - Multi-threaded
  - You can specify the depth of scan for the internal links
  - It supports verbose mode where it logs all internal links and external ones
  - Supports an "exclude" --ignore-file option where you can specify the domains to be ignored from the scan
  - It has good error handling
  - It saves the crawled external domains into an output file with a DNS-compatible format (--output)

Example : 
```
python url-extractor.py wotaku.wiki --depth 3 --output links.txt --ignore-file nocrawl.txt -v
```
To work it needs python-beautifulsoup4 and python-requests libraries.

- open-domains.py
A small utility used to manually verify the generated output by opening the links 20 by 20.
