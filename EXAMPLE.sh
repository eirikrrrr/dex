#!/bin/bash

# You can put a crontab entry like this to run the crawler every day at 2am
# 0 2 * * * /path/to/dex scan asurascans series
# 10 2 * * * /path/to/dex scan asurascans chapters

    
echo -e "\n\nList chapters \n"
dex chapters "Crimson"  # By name
dex chapters --index 19 # By series ID (from DB)

echo -e "\n\nList series \n"
dex series "Crimson"
dex series "A Wimp’s Strategy Guide"

echo -e "\n\nExport data to CSV | JSON"
dex series --all --limit 10 --export csv  --output /tmp/export.csv
dex series --all --limit 20 --export json --output /tmp/export.json
dex series --all --export csv  --output /tmp/export.csv
