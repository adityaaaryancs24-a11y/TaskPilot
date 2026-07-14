import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
# Just look at data files directly
data_dir = os.path.join(os.path.dirname(__file__), "data")
owners = set()
for fname in [
    "jira_samples.json",
    "defects.json",
    "github_samples.json",
    "slack_samples.json",
    "emails.json",
]:
    fpath = os.path.join(data_dir, fname)
    if os.path.exists(fpath):
        with open(fpath) as f:
            for item in json.load(f):
                o = item.get("owner")
                if o:
                    owners.add(str(o))
print(f"Unique owners in data files ({len(owners)}):")
for o in sorted(owners):
    print(f"  {o}")
