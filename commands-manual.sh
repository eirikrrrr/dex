#!/bin/bash

echo -e "List chapters \n"
dex chapters "Crimson"  # By name
dex chapters --index 19 # By series ID (from DB)

echo -e "List series \n"
dex series "Crimson"
dex series "A Wimp’s Strategy Guide"

echo -e "Export data to CSV | JSON"
dex series --all --limit 10 --export csv  --output /tmp/export.csv
dex series --all --limit 20 --export json --output /tmp/export.csv
dex series --all --export csv  --output /tmp/export.csv


# dex scan asurascans chapters
# dex scan asurascans series --max-pages 18 # This site only have 18 pages at asurascans.com/browse endpoint