import re
import requests
import sys
from bs4 import BeautifulSoup
import argparse
import wget

parser = argparse.ArgumentParser()
parser.add_argument('dumps_page')
parser.add_argument('pattern')
parser.add_argument('-d', '--dry-run', action='store_true', default=False)
args = parser.parse_args()

r = requests.get(args.dumps_page)
soup = BeautifulSoup(r.text, 'html.parser')

if not soup:
    print('No matching files found')
    sys.exit(1)

file_anchors = soup.find_all(href=re.compile(args.pattern))

for file_anchor in file_anchors:
    source = args.dumps_page + file_anchor['href'].split('/')[-1]
    dest = source.split('/')[-1]
    print(source, '=>', dest)
    if not args.dry_run:
        wget.download(source, dest)
