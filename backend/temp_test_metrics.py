import requests

r = requests.get("http://localhost:8000/api/team-metrics")
d = r.json()
teams = d.get("teams", {})
print(f"Teams: {len(teams)}")
for k, v in sorted(teams.items()):
    print(
        f"  {k}: {v['total_tasks']} tasks, {v['blocked']} blocked, {len(v['members'])} members"
    )
    for m, s in sorted(v["members"].items()):
        print(f"    {m}: {s['tasks']} tasks ({s['blocked']} blocked)")
