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
from pathlib import Path

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

def build_assignment_lookup(assignments):
    return {row["Station"]: row for row in assignments}

def get_operator_edges(station_pairs, operator):
    return [(row["FirstStation"], row["SecondStation"]) for row in station_pairs if row["Operator"] == operator]

# Draw rings
def plot_rings(ax, locations):
    radii = sorted({row["Radius"] for row in locations})
    for radius in radii:
        circle = plt.Circle((0, 0),radius,fill=False,linewidth=0.7,alpha=0.25)
        ax.add_patch(circle)

# Draw all potential locations
def plot_candidate_locations(ax, locations):
    x = [row["X"] for row in locations]
    y = [row["Y"] for row in locations]
    ax.scatter( x, y, s=5, alpha=0.25)

# Draw network edges
def plot_edges(ax, edges, assignment_lookup):
    for station1, station2 in edges:
        loc1 = assignment_lookup[station1]
        loc2 = assignment_lookup[station2]
        ax.plot([loc1["X"], loc2["X"]], [loc1["Y"], loc2["Y"]], linewidth=1.5, zorder=2 )

# Draw stations
def plot_stations(ax, assignments):
    station_x = [row["X"] for row in assignments]
    station_y = [row["Y"] for row in assignments]
    ax.scatter(station_x, station_y,s=50, zorder=3)

    # Add labels
    for row in assignments:
        ax.annotate(row["Station"], (row["X"], row["Y"]), xytext=(5, 5), textcoords="offset points", fontsize=8, zorder=4)
        
def create_diagnostic_plot(assignments,station_pairs,potential_locations):
    # Prepare data
    assignment_lookup = build_assignment_lookup(assignments)
    edges = [(a, b) for a, b in get_operator_edges(station_pairs, OPERATOR) if a in assignment_lookup  and b in assignment_lookup]
    # Create plot
    fig, ax = plt.subplots(figsize=(10, 10))
    plot_rings(ax,potential_locations["Locations"] )
    if SHOW_ALL_LOCATIONS:
        plot_candidate_locations(ax,potential_locations["Locations"])
    plot_edges(ax,edges,assignment_lookup )
    plot_stations(ax,assignments)
    
    # Formatting
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(f"{OPERATOR} station-placement diagnostic")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, linewidth=0.3, alpha=0.3)
    fig.tight_layout()
    Path(OUTPUT_PATH).parent.mkdir(parents=True,exist_ok=True )
    fig.savefig(OUTPUT_PATH, dpi=200 )
    plt.show()

if __name__ == "__main__":
    assignments = load_json(ASSIGNMENTS_PATH )
    station_pairs = load_json(STATION_PAIRS_PATH )
    potential_locations = load_json(POTENTIAL_LOCATIONS_PATH )

    create_diagnostic_plot(assignments,station_pairs,potential_locations )
