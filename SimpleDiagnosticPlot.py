#Simple diagnostic plot 
#Plot the location and rings
#Check stations plotted on locations with labels
#Plot straight line links between stations 
#Check that stations are plotted 
#Save to file

#Inputs
#Potential_Locations/potential_station_locations.json
#data/station_pairs.json
#model_output/station_assignments.json

import json
import matplotlib.pyplot as plt

# Parameters
OPERATOR = "AirLink"
STATION_PAIRS_PATH = "./data/station_pairs.json"
POTENTIAL_LOCATIONS_PATH = ("./Potential_Locations/potential_station_locations.json")
ASSIGNMENTS_PATH = ("./model_output/station_assignments.json")
OUTPUT_PATH = ("./model_output/diagnostic_layout.png")
SHOW_ALL_LOCATIONS = True

# Load data
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

station_pairs = load_json(STATION_PAIRS_PATH)
potential_locations = load_json(POTENTIAL_LOCATIONS_PATH)
assignments = load_json(ASSIGNMENTS_PATH)

# Prepare data
operator_edges = [(row["FirstStation"],row["SecondStation"]) for row in station_pairs if row["Operator"] == OPERATOR]
assignment_lookup = {row["Station"]: row for row in assignments}

# Unique ring radii
ring_radii = sorted({row["Radius"]  for row in potential_locations["Locations"]})

# Create plot
fig, ax = plt.subplots(figsize=(10, 10))

# Draw rings
for radius in ring_radii:
    ring = plt.Circle((0, 0), radius, fill=False, linewidth=0.5, alpha=0.4)
    ax.add_patch(ring)

# Draw all potential locations
if SHOW_ALL_LOCATIONS:
    x_all = [row["X"] for row in potential_locations["Locations"] ]
    y_all = [row["Y"] for row in potential_locations["Locations"] ]
    ax.scatter( x_all, y_all, s=5, alpha=0.25)

# Draw network edges
for station1, station2 in operator_edges:
    if (station1 not in assignment_lookup or station2 not in assignment_lookup ):
        continue
    loc1 = assignment_lookup[station1]
    loc2 = assignment_lookup[station2]
    ax.plot([loc1["X"], loc2["X"]], [loc1["Y"], loc2["Y"]], linewidth=1.5, zorder=2 )

# Draw stations
station_x = [row["X"] for row in assignments]
station_y = [row["Y"] for row in assignments]
ax.scatter(station_x, station_y,s=50, zorder=3)

# Add labels
for row in assignments:
    ax.annotate(row["Station"], (row["X"], row["Y"]), xytext=(5, 5), textcoords="offset points", fontsize=8, zorder=4)

# Formatting
ax.set_aspect("equal", adjustable="box")
ax.set_title(f"{OPERATOR} diagnostic station layout")
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.grid(True, linewidth=0.3, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_PATH, dpi=200, bbox_inches="tight")
plt.show()
