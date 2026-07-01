import json
import os
import re
import subprocess
from datetime import datetime

def skip_match(teamA:str, teamB:str):
	return (
		"." in teamA
		or re.match("(L|W)(L|U)(\\d|F)", teamA) 
		or re.match("G\\d\\.\\D", teamA)
	)

def match_to_text(label, first_day, day):
	first_day = datetime.strptime(first_day, "%Y-%m-%d")
	day = datetime.strptime(day, "%Y-%m-%d")
	n_days = (day - first_day).days + 1

	if re.match("G\\d", label):
		return f"Day {n_days} - Group Phase"
	return f"Day {n_days} - {label}"

ABSOLUTE_PATH = "/var/tmp/ssl-streaming-package/services/obs_live_data/youtube_thumbnails"
TEMPLATE_SVG = os.path.join(ABSOLUTE_PATH, "template_with_placeholder.svg")

schedule = json.load(open("../data/schedule.json", "r"))
schedule = schedule["schedule"]

logos = os.listdir("../logos")
teams = set()
matches = set()

first_day = schedule[0]["day"]

for match in schedule:
	teamA, teamB = match['teamA'], match['teamB']
	
	if skip_match(teamA, teamB):
		continue

	print(match['label'], match['day'], teamA.rjust(25), "-", teamB)
	teams.add(teamA)
	teams.add(teamB)
	matches.add((match_to_text(match["label"], first_day, match['day']), teamA, teamB))

for m in sorted(matches):
	print(m)

teams_logos = {}
trimmed = lambda s: s.replace(" ", "").replace("-", "").lower()
for team in sorted(teams):
	logos_ = [l for l in logos if trimmed(team) in trimmed(l)]
	if len(logos_) == 0:
		print(f"Missing logo for {team}: {logos_}")
		teams_logos[team] = None
	elif 1 < len(logos_):
		print(f"Multiple logos for {team}: {logos_}")
		teams_logos[team] = None
	else:
		teams_logos[team] = logos_[0]


os.makedirs(os.path.join(ABSOLUTE_PATH, "png"), exist_ok=True)

for match in sorted(matches):
	day, teamA, teamB = match
	logoA = teams_logos[teamA] or "blue.png"
	logoB = teams_logos[teamB] or "blue.png"

	svg_out = os.path.join(ABSOLUTE_PATH, "svg", f"{day}_{teamA}_vs_{teamB}.svg")
	png_out = os.path.join(ABSOLUTE_PATH, "png", f"{day}_{teamA}_vs_{teamB}.png")

	print(f"Generating thumbnail for {day} - {teamA} vs {teamB}")
	with open(TEMPLATE_SVG, "r") as f:
		svg = f.read()
	
	svg = svg.replace("PLACEHOLDER_BOTTOM_TEXT", day)
	path_logoA = os.path.join(ABSOLUTE_PATH, "../logos", logoA)
	if not os.path.exists(path_logoA):
		print(f"Missing logo for {teamA}: {path_logoA}")
	path_logoB = os.path.join(ABSOLUTE_PATH, "../logos", logoB)
	if not os.path.exists(path_logoB):
		print(f"Missing logo for {teamB}: {path_logoB}")
	svg = svg.replace("PLACEHOLDER_TEAM_LEFT", logoA)
	svg = svg.replace("PLACEHOLDER_TEAM_RIGHT", logoB)

	with open(svg_out, "w") as f:
		f.write(svg)

	subprocess.run(
		[
			"inkscape",
			"--export-type=png",
			f"--export-filename={png_out}",
			"-w", "1920",
			"-h", "1080",
			svg_out,
		],
		check=True,
	)