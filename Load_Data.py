#Stage 5 done on crossing import
import json
import pyomo.environ as pyo
#from pyomo.opt import SolverStatus, TerminationCondition
#import pyomo.contrib as pyc
import math
from pathlib import Path
from collections import Counter
import sys

#Parameters
MAX_DISTANCE_MULTIPLIER =2.0
MAX_RING_DIFFERENCE = 2
Station_pair_json_path="./data/station_pairs.json"
Potential_stations_json_path="./Potential_Locations/potential_station_locations.json"
MPS_path="./model_output/station_placement_v3.mps"
Assignment_path="./model_output/station_assignments_3.json"
SOLVER_TIME_LIMIT=480 #seconds
Flag_Output_MPS=False
Flag_Output_Results=True
KEY_STATION_MODE = "degree"   # "manual" or "degree"
KEY_STATION = "Stepford Central"
#KEY_STATION = None


def get_station_pairs():
    #Get station pairs
    with open(Station_pair_json_path, "r", encoding="utf-8") as sp:
        station_pairs = json.load(sp)
    return station_pairs

def print_station_pairs(station_pairs, airlink_edges, airlink_stations):    
    print("From potential locations file: ", Station_pair_json_path)
    print("Station pairs loaded: ", len(station_pairs))
    print("Station edges loaded: ", len(airlink_edges))
    print("Station names loaded: ", len(airlink_stations))

def get_potential_locations():
    #Get potential locations
    with open(Potential_stations_json_path, "r", encoding="utf-8") as pl: 
        potential_locations=json.load(pl)
    return potential_locations

def get_reference_locations(locations):
    #for each ring, find the location with the smallest theta (closest to the horizontal axis)
    by_ring = {}
    for location in locations:
        ring = location["Ring"]
        theta_distance = min(location["Theta"],  2 * math.pi - location["Theta"] )
        if (ring not in by_ring  or theta_distance < by_ring[ring][0] ):
            by_ring[ring] = (theta_distance, location["Location"] )
    return [by_ring[ring][1] for ring in sorted(by_ring)]

def print_potential_locations(potential_locations,maximum_distance_apart):
    print("From station pairs file: ", Potential_stations_json_path)
    print("No of potential locations loaded: ", int(potential_locations["NoStations"]))
    print("Maximum distance between adjacent stations constraint: ", maximum_distance_apart)

def get_edges(station_pairs: list[dict], operatorfilter: str = "") -> list[tuple[str, str]]:
    #Get list of station pairs data. If operator name filter supplied then filter to that operator only
    if operatorfilter=="" :
        airlink_edges = [(row["FirstStation"], row["SecondStation"]) for row in station_pairs]
    else:
        airlink_edges = [(row["FirstStation"], row["SecondStation"]) for row in station_pairs if row["Operator"] == operatorfilter]
    return airlink_edges

def get_station_name_list(edges:list[tuple[str, str]])->list[str]:    
    #List of stations in operator routes
    stations_names = sorted({station for a, b in edges for station in (a, b)})
    return stations_names

def location_pair_distance(location1, location2):
    #print(location1['X'], location1['Y'], location2['X'],location2['Y'])
    #calc euclidean distance between locations. Actual distance will be mix of arcs and radii (larger)
    return math.hypot(float(location1['X']) - float(location2['X']),float(location1['Y']) - float(location2['Y']))
    

def check_valid_location(location1, location2, maximum_distance, max_ring_difference):
    #exclude where pair is same location 
    if location1["Location"] == location2["Location"]:
        return False            
    #exclude where pair are further than max_ring_difference apart (no. of rings apart) 
    if abs(location1["Ring"] - location2["Ring"]) > max_ring_difference:
        return False
    # exclude where pair are more than maximum_distance apart    
    if location_pair_distance(location1,location2) > maximum_distance:
        return False
    return True

def get_valid_location_pairs(locations, target_spacing, max_distance_multiplier, max_ring_difference):
    #get valid locations. rather than compare every location (n^2), restrict to those in proximity
    valid_pairs = []
    maximum_distance = (target_spacing * max_distance_multiplier)
    for location1 in locations:
        for location2 in locations:
            #exclude where pair is same location 
            #if location1["Location"] == location2["Location"]:
            #    continue            
            #exclude where pair are further than max_ring_difference apart (no. of rings apart) 
            #if abs(location1["Ring"] - location2["Ring"]) > max_ring_difference:
            #    continue
            # exclude where pair are more than maximum_distance apart    
            #if location_pair_distance(location1,location2) > maximum_distance:
            #    continue
            if check_valid_location(location1, location2, maximum_distance, max_ring_difference)==True:
                valid_pairs.append((location1["Location"],location2["Location"]))
    return valid_pairs
    
def one_location_per_station_rule(model, station):
    #A station occupies exactly one location
    #return sum(model.x[station, location] for location in model.LOCATIONS) == 1
    return sum(model.x[station, location] for location in x_locations_by_station[station]) == 1

def one_station_per_location_rule(model, location):
    #A location can only have one station (or be empty)
    #return sum(model.x[station, location] for station in model.STATIONS) <= 1
    #return sum(model.x[station, location] for station in x_stations_by_location[location]) <= 1
    eligible_stations = x_stations_by_location[location]
    if not eligible_stations:
        return pyo.Constraint.Skip
    return sum(model.x[station, location] for station in eligible_stations) <= 1

def edge_start_location_rule(model, station1, station2, location1):
    # If station1 of an edge is assigned to location1, exactly one z variable for that edge must start at location1.
        #return sum(model.z[station1, station2, location1, location2] for location2 in outgoing_locations[location1]) == model.x[station1, location1]
    valid_end_locations = z_outgoing.get((station1, station2, location1), [])
    return sum(model.z[station1, station2, location1, location2] for location2 in valid_end_locations) == model.x[station1, location1]

def edge_end_location_rule(model, station1, station2, location2):
    # If station2 of an edge is assigned to location2, exactly one z variable for that edge must end at location2.
    #return sum(model.z[station1, station2, location1, location2] for location1 in incoming_locations[location2]) == model.x[station2, location2]
    valid_start_locations = z_incoming.get((station1, station2, location2), [])
    return sum(model.z[station1, station2, location1, location2] for location1 in valid_start_locations) == model.x[station2, location2]
    
def key_station_reference_rule(model):
    #return sum(model.x[model.KEY_STATION, location] for location in reference_locations) == 1
    #valid_reference_locations = [location for location in reference_locations if location in x_locations_by_station[pyo.value(model.KEY_STATION)]]
    #return sum(model.x[model.KEY_STATION, location] for location in valid_reference_locations) == 1
    key_station = pyo.value(model.KEY_STATION)
    valid_reference_locations = [location for location in reference_locations if location in x_locations_by_station[key_station]]
    if not valid_reference_locations:
        raise ValueError(f"No reference location available for key station {KEY_STATION}")
    return sum(model.x[key_station, location] for location in valid_reference_locations) == 1
    
#def blocking_location_rule(model, station1, station2, location1, location2, blocker):
#Blocking locations + at most one station occupying a location can't be more than 1
#    #return (model.z[station1, station2, location1, location2]   + sum(model.x[station, blocker] for station in model.STATIONS)  <= 1 )
#    #def blocking_location_rule(model, station1, station2, location1, location2, blocker):
#    return (model.z[station1, station2, location1, location2] + sum(model.x[station, blocker] for station in x_stations_by_location[blocker]) <= 1)

def blocking_location_rule(model, station1, station2, location1, location2):
    #Blocking locations + at most one station occupying a location can't be more than 1
    blockers = blocking_locations[(location1, location2)]
    #blocker_occupancy = sum(model.x[station, blocker] for blocker in blockers for station in x_stations_by_location[blocker])
    #return (blocker_occupancy<=len(blockers) * (1- model.z[station1, station2, location1, location2]))
    return (sum(model.y[blocker] for blocker in blockers ) <=len(blockers) * (1 -model.z[station1, station2, location1, location2]))

def location_occupancy_rule(model, location):
    eligible_stations = x_stations_by_location[location]
    if not eligible_stations:
        return model.y[location] == 0
    return (model.y[location]==sum(model.x[station, location] for station in eligible_stations))

def model_objective_rule(model):
    #return sum(
    #    location_pair_distances[location1, location2]* model.z[station1,station2,location1,location2]  
    #    for station1, station2 in model.EDGES for location1, location2 in model.LOCATION_PAIRS)
    return sum(
        location_pair_distances[location1, location2] * model.z[station1, station2, location1, location2]
        for (station1, station2, location1, location2) in model.Z_INDEX)

#def build_model(airlink_stations, airlink_edges, location_names, valid_location_pairs, location_pair_distances,key_station ):
def build_model(airlink_stations, airlink_edges, location_names, valid_station_locations, valid_z, blocking_constraints, z_start_indices, z_end_indices, location_pair_distances, key_station, crossing_z_pairs):
    #Define model
    model = pyo.ConcreteModel(name="Station placement")
    
    #Add location names / station names to model
    model.STATIONS = pyo.Set(initialize=airlink_stations,   ordered=True)
    model.LOCATIONS = pyo.Set(initialize=location_names,    ordered=True)

    #model.KEY_STATION=pyo.Param(initialize=key_station)
    
    model.EDGES = pyo.Set(dimen=2, initialize=airlink_edges, ordered=True)
    model.STATION_LOCATIONS = pyo.Set(dimen=2, initialize=valid_station_locations)

    model.Z_INDEX = pyo.Set(dimen=4, initialize=valid_z)
    model.Z_START_INDEX = pyo.Set(dimen=3, initialize=z_start_indices)
    model.Z_END_INDEX = pyo.Set(dimen=3, initialize=z_end_indices)
    
    #Create a station * location binary matrix
    #model.x = pyo.Var(model.STATIONS, model.LOCATIONS, within=pyo.Binary)
    #model.z=pyo.Var(model.EDGES, model.LOCATION_PAIRS, within=pyo.Binary)
    model.x = pyo.Var(model.STATION_LOCATIONS, within=pyo.Binary)
    model.y = pyo.Var(model.LOCATIONS, bounds=(0, 1))
    model.z = pyo.Var(model.Z_INDEX, within=pyo.Binary)
    
    model.BLOCKING_INDEX = pyo.Set(dimen=4, initialize=blocking_constraints)
    model.blocking_location = pyo.Constraint(model.BLOCKING_INDEX, rule=blocking_location_rule)

    model.CROSSING_Z_INDEX = pyo.Set(dimen=8, initialize=crossing_z_pairs)
    model.crossing_z = pyo.Constraint(model.CROSSING_Z_INDEX, rule=crossing_z_rule)

    #station/location constraints
    model.one_location_per_station = pyo.Constraint( model.STATIONS, rule=one_location_per_station_rule)
    #model.one_station_per_location = pyo.Constraint(model.LOCATIONS,   rule=one_station_per_location_rule)
    model.location_occupancy = pyo.Constraint(model.LOCATIONS,rule=location_occupancy_rule)
    
    #model.edge_start_location = pyo.Constraint(model.EDGES,model.LOCATIONS,rule=edge_start_location_rule)
    #model.edge_end_location = pyo.Constraint(model.EDGES,model.LOCATIONS,rule=edge_end_location_rule)
    model.edge_start_location = pyo.Constraint(model.Z_START_INDEX, rule=edge_start_location_rule)
    model.edge_end_location = pyo.Constraint(model.Z_END_INDEX, rule=edge_end_location_rule)

    #"Key station" constraint - fixes this station to smallest theta, not smallest ring) - reduces rotational freedom of model 
    #model.key_station_reference = pyo.Constraint(rule=key_station_reference_rule)
    valid_reference_locations = [location for location in reference_locations if location in x_locations_by_station[key_station]]
    model.key_station_reference = pyo.Constraint(expr=sum(model.x[key_station, location] for location in valid_reference_locations) == 1)
       
    #Real objective - minimise distance between the chosen location of A and the chosen location of B
    model.objective = pyo.Objective(rule=model_objective_rule, sense=pyo.minimize)    
    return model

def output_mps(model):
    model.write(MPS_path, format="mps",  io_options={"symbolic_solver_labels": True})
    print("Model MPS file saved to: ",MPS_path) 

def get_station_assignments(model, location_lookup):
    assignments = []
    #for station in model.STATIONS:
    #    for location in model.LOCATIONS:
    for station, location in model.STATION_LOCATIONS:
        if pyo.value(model.x[station, location]) > 0.5:
            loc = location_lookup[location]
            assignments.append({"Station": station, "Location": location, "Ring": loc["Ring"], "Slot": loc["Slot"], "X": loc["X"], "Y": loc["Y"]})
    return assignments

def  output_assignments(assignments):
    for row in assignments:
        print(row["Station"], "->", row["Location"])
    with open(Assignment_path,"w",encoding="utf-8") as f:
        json.dump(assignments, f, indent=2)
    print("Station assignments file saved to: ",Assignment_path) 

def get_key_station(edges, mode="degree", key_station=None):
    #If key_station not already defined by user then find statoin with highest degree of connections
    if mode == "manual":
        if key_station is None:
            raise ValueError("manual_station must be supplied in manual mode")
        return key_station
    elif mode == "degree":
        degree = {}
        for station1, station2 in edges:
            degree[station1] = degree.get(station1, 0) + 1
            degree[station2] = degree.get(station2, 0) + 1
        return max( degree, key=lambda station: (degree[station], station))
    else:
        raise ValueError(f"Unknown key station mode: {mode}")

#def get_count_station_degree(edges, station):
#    #Get number of stations that "station" connects to    
#    return sum(station in stat for stat in edges)

#def get_count_station_degree(station, neighbours):
#    return {station: len(neighbours) for station, neighbours in station_neighbours.items()}

#def get_valid_location_count(locations, valid_location_pairs):     
#count number of valid locations that are reachable from each location
#    location_count={}    
#    for loc in locations:   
#        location_count[loc]=sum(loc in locs for locs in valid_location_pairs)
#    return location_count

#def check_feasible_location(station, edges, location, valid_locations):
#for station, check if number of reachable locations >= number of connecting stations    
#    if valid_location_count(location,valid_locations)>=get_count_station_degree(edges, station):
#        return True
#    else: 
#        return False

def check_feasible_location(station, location, station_degree, location_neighbour_count):
    #for station, check if number of reachable locations >= number of connecting stations    
    return (location_neighbour_count[location] >= station_degree[station] )

def get_station_neighbours(stations, edges):
    #find list of stations that are connected to station
    station_neighbours = {station: set() for station in stations}
    for station1, station2 in edges:
        station_neighbours[station1].add(station2)
        station_neighbours[station2].add(station1)
    return station_neighbours

def check_common_neighbours_count(station1, station2,location1, location2,station_neighbours,location_neighbours):
    #check if there are at least as many valid locations reachable from both location1 and location2 as there are stations connected to station1 and station2
    common_stations = (station_neighbours[station1] & station_neighbours[station2] )
    common_locations = (location_neighbours[location1] & location_neighbours[location2] )
    return (len(common_locations) >= len(common_stations))

def get_valid_station_locations(stations, locations, station_degree, location_neighbour_count):
    valid_station_locations = []
    for station in stations:
        for location in locations:
            if check_feasible_location(station, location, station_degree, location_neighbour_count):
                valid_station_locations.append((station, location))
    return valid_station_locations

def check_combined_neighbour_capacity(station1, station2, location1, location2, station_neighbours, location_neighbours):
    required_neighbours = (station_neighbours[station1] | station_neighbours[station2] ) - {station1, station2}
    available_locations = (location_neighbours[location1] | location_neighbours[location2]  ) - {location1, location2}
    return (len(available_locations)>= len(required_neighbours)  )

def get_valid_z_indices(edges, valid_location_pairs, eligible_locations, station_neighbours, location_neighbours):
    valid_z = []
    for station1, station2 in edges:
        for location1, location2 in valid_location_pairs:
            if location1 not in eligible_locations[station1]:
                continue
            if location2 not in eligible_locations[station2]:
                continue
            if not check_common_neighbours_count(station1, station2, location1, location2, station_neighbours, location_neighbours):
                continue
            if not check_combined_neighbour_capacity(station1, station2, location1, location2, station_neighbours, location_neighbours):
                continue
            valid_z.append((station1, station2, location1, location2 ))
    return valid_z

def get_ring_locations(locations):
    ring_locations = {}
    for location in locations:
        ring = location["Ring"]
        if ring not in ring_locations:
            ring_locations[ring] = []
        ring_locations[ring].append((location["Slot"], location["Location"]))
    for ring in ring_locations:
        ring_locations[ring].sort()
    return {ring: [location for slot, location in locations] for ring, locations in ring_locations.items() }

def get_blocking_locations(location1,  location2, location_lookup, ring_locations):
    loc1 = location_lookup[location1]
    loc2 = location_lookup[location2]
    # Version 1: only same-ring blocking
    if loc1["Ring"] != loc2["Ring"]:
        return set()
    ring = loc1["Ring"]
    locations = ring_locations[ring]
    index1 = locations.index(location1)
    index2 = locations.index(location2)
    n = len(locations)
    # Travel clockwise from location1 to location2
    clockwise = []
    i = (index1 + 1) % n
    while i != index2:
        clockwise.append(locations[i])
        i = (i + 1) % n
    # Travel anticlockwise from location1 to location2
    anticlockwise = []
    i = (index1 - 1) % n
    while i != index2:
        anticlockwise.append(locations[i])
        i = (i - 1) % n
    # Use blockers on the shorter arc
    if len(clockwise) < len(anticlockwise):
        return set(clockwise)
    if len(anticlockwise) < len(clockwise):
        return set(anticlockwise)
    # Exact tie: either route is possible, so don't
    # impose a blocking direction yet
    return set()

def orientation(p1, p2, p3):
    #Orientation of three XY points.
    #Returns: > 0 : anticlockwise, < 0 : clockwise, = 0 : collinear
    return ((p2["X"] - p1["X"]) * (p3["Y"] - p1["Y"]) - (p2["Y"] - p1["Y"]) * (p3["X"] - p1["X"]))

def location_links_cross(location1a, location2a, location1b, location2b,location_lookup):
    #Return True if the two straight-line location links cross in their interiors.
    #Links sharing an endpoint are not counted as crossings.
    # Shared endpoint: meeting at a station/location is allowed
    if (location1a in {location1b, location2b} or location2a in {location1b, location2b}):
        return False
    p1 = location_lookup[location1a]
    p2 = location_lookup[location2a]
    p3 = location_lookup[location1b]
    p4 = location_lookup[location2b]

    o1 = orientation(p1, p2, p3)
    o2 = orientation(p1, p2, p4)
    o3 = orientation(p3, p4, p1)
    o4 = orientation(p3, p4, p2)

    # Strict crossing only.
    # Collinear/touching cases are not treated as crossings here.
    return (o1 * o2 < 0 and o3 * o4 < 0)

def get_inter_ring_location_pairs(valid_location_pairs, location_lookup):
    #classify inter-ring pairs
    inter_ring_pairs = []
    for location1, location2 in valid_location_pairs:
        ring1 = location_lookup[location1]["Ring"]
        ring2 = location_lookup[location2]["Ring"]
        if ring1 == ring2:
            continue
        inter_ring_pairs.append((location1, location2))
    return inter_ring_pairs

def get_ring_pair(location1, location2, location_lookup):
    #Because one link might be stored inner→outer and another outer→inner
    ring1 = location_lookup[location1]["Ring"]
    ring2 = location_lookup[location2]["Ring"]
    return tuple(sorted((ring1, ring2)))

def get_crossing_location_pairs(valid_location_pairs, location_lookup):
    inter_ring_pairs = get_inter_ring_location_pairs(valid_location_pairs, location_lookup)
    
    # Group location pairs by the rings they span
    pairs_by_rings = {}

    for location1, location2 in inter_ring_pairs:
        ring_pair = get_ring_pair(location1, location2, location_lookup)

        pairs_by_rings.setdefault(ring_pair, []).append((location1, location2))

    crossing_pairs = set()
    for ring_pair, pairs in pairs_by_rings.items():
        for i in range(len(pairs)):
            location1a, location2a = pairs[i]
            for j in range(i + 1, len(pairs)):
                location1b, location2b = pairs[j]

                if location_links_cross(location1a, location2a, location1b, location2b, location_lookup):
                    crossing_pairs.add((location1a, location2a, location1b, location2b))
    return crossing_pairs

def get_crossing_z_pairs(crossing_location_pairs, z_by_location_pair):
    crossing_z_pairs = []
    for (location1a, location2a, location1b, location2b) in crossing_location_pairs:
        z_list_a = z_by_location_pair.get((location1a, location2a), [])
        z_list_b = z_by_location_pair.get((location1b, location2b), [])
        for z_a in z_list_a:
            for z_b in z_list_b:
                station1a, station2a, _, _ = z_a
                station1b, station2b, _, _ = z_b

                # Same real edge - only one placement can be selected anyway
                if (station1a == station1b and station2a == station2b ):
                    continue

                # Edges sharing a station meet at that station, so don't treat them as a crossing conflict
                if ({station1a, station2a} & {station1b, station2b}):
                    continue
                    
                crossing_z_pairs.append(z_a + z_b)
    return crossing_z_pairs

def crossing_z_rule(model, station1a, station2a, location1a, location2a, station1b, station2b, location1b, location2b):
    return (model.z[station1a, station2a, location1a, location2a]  + model.z[station1b, station2b, location1b, location2b] <= 1)

Path("./model_output").mkdir(parents=True, exist_ok=True)

station_pairs=get_station_pairs()
airlink_edges=get_edges(station_pairs, "AirLink")
airlink_stations=get_station_name_list(airlink_edges)
print_station_pairs(station_pairs, airlink_edges, airlink_stations)

potential_locations=get_potential_locations()
#an adjacent pair of stations may be at most X nominal station spacings apart
maximum_distance_apart = ( MAX_DISTANCE_MULTIPLIER * potential_locations["TargetSpacing"])
print_potential_locations(potential_locations,maximum_distance_apart)

#Build location lookup
location_lookup = {row["Location"]: row for row in potential_locations["Locations"]}

#Build an ordered list of locations on each ring
ring_locations = get_ring_locations(potential_locations["Locations"])

#Define list of valid (in near proximity) location pairs 
valid_location_pairs = get_valid_location_pairs(potential_locations["Locations"], potential_locations["TargetSpacing"],MAX_DISTANCE_MULTIPLIER,MAX_RING_DIFFERENCE)

#Create location names
location_names = [row["Location"] for row in potential_locations["Locations"]]

#Create count of number of valid locations reachable from each location
#valid_location_count=get_valid_location_count(location_names, valid_location_pairs)

#Print valid location pairs count - check it works
print(f"Valid location pairs: {len(valid_location_pairs):,} " f"of {len(location_names) ** 2:,}")
print(f"z variables: "f"{len(airlink_edges) * len(valid_location_pairs):,}")

#Compute neighbouring location lists
outgoing_locations = {location: set() for location in location_names}
incoming_locations = {location: set() for location in location_names}
for location1, location2 in valid_location_pairs:
    outgoing_locations[location1].add(location2)
    incoming_locations[location2].add(location1)
location_neighbours = outgoing_locations

#Create count of number of valid locations reachable from each location
location_neighbour_count = {location: len(neighbours) for location, neighbours in outgoing_locations.items()}

#sum of distances between pairs of stations sited at paired locations
#location_pair_distances = {(l1, l2): location_pair_distance(location_lookup[l1], location_lookup[l2]) for l1, l2 in valid_location_pairs}
station_neighbours=get_station_neighbours(airlink_stations, airlink_edges)
station_degree = {station: len(neighbours) for station, neighbours in station_neighbours.items()}
valid_station_locations = get_valid_station_locations(airlink_stations,location_names,station_degree,location_neighbour_count)
location_pair_distances = {(l1, l2): location_pair_distance(location_lookup[l1], location_lookup[l2]) for l1, l2 in valid_location_pairs}

print("Station degrees:")
for station in airlink_stations:
    print(station, station_degree[station])

eligible_locations = {station: set() for station in airlink_stations}
for station, location in valid_station_locations:
    eligible_locations[station].add(location)
    
#for station in airlink_stations:
#    for location in location_names:
#        if (location_neighbour_count[location]>= station_degree[station]):
#            eligible_locations[station].add(location)

valid_z = get_valid_z_indices(airlink_edges, valid_location_pairs, eligible_locations, station_neighbours, location_neighbours)

#Precompute blockers for every valid location pair
blocking_locations = {(location1, location2): get_blocking_locations(location1, location2, location_lookup, ring_locations) for location1, location2 in valid_location_pairs}

#precompute a flat constraint-index list for blocking constraint
blocking_constraints = []
for (station1, station2, location1, location2) in valid_z:
    if blocking_locations[(location1, location2)]:
        blocking_constraints.append((station1, station2, location1, location2))
print("Blocking constraints:",len(blocking_constraints))

#precompute crossing location-pair combinations
crossing_location_pairs = get_crossing_location_pairs(valid_location_pairs,location_lookup)
print("Crossing location-pair combinations:", len(crossing_location_pairs))

#Get reference locations and key station
reference_locations=get_reference_locations( potential_locations["Locations"])
KEY_STATION=get_key_station(airlink_edges,  mode=KEY_STATION_MODE, key_station=KEY_STATION)
print("Key station:", KEY_STATION)
print("Reference locations:", reference_locations)

dense_x = (len(airlink_stations) * len(location_names))
dense_z = (len(airlink_edges)  * len(valid_location_pairs))
print(f"Dense x: {dense_x:,}")
print(f"Valid station/location x: " f"{len(valid_station_locations):,}")
print(f"Dense z: {dense_z:,}")
print(f"Pruned z: {len(valid_z):,}")
print(f"x retained: " f"{100 * len(valid_station_locations) / dense_x:.1f}%")
print(f"z retained: " f"{100 * len(valid_z) / dense_z:.1f}%")

required_counts = []
available_counts = []

for station1, station2 in airlink_edges:
    required = (station_neighbours[station1] | station_neighbours[station2]) - {station1, station2}
    for location1, location2 in valid_location_pairs:
        available = (location_neighbours[location1] | location_neighbours[location2]) - {location1, location2}
        required_counts.append(len(required))
        available_counts.append(len(available))

print("Required edge-neighbour slots:", min(required_counts), max(required_counts))
print("Available candidate slots:", min(available_counts), max(available_counts))

#Blocking diagnostics
pairs_with_blockers = {pair: blockers for pair, blockers in blocking_locations.items() if blockers}
print("Location pairs with blockers:", len(pairs_with_blockers), "of", len(valid_location_pairs))
print("Maximum blocking locations:", max((len(blockers) for blockers in blocking_locations.values()), default=0))
for pair, blockers in list(pairs_with_blockers.items())[:10]:print(pair, "blocks", blockers)

#locations_by_station = {station: set() for station in airlink_stations}
#stations_by_location = {location: set() for location in location_names}
#for station, location in valid_station_locations:
#    locations_by_station[station].add(location)
#    stations_by_location[location].add(station)

#z_by_edge_start_location = {}
#z_by_edge_end_location = {}
#for station1, station2, location1, location2 in valid_z:
#    z_by_edge_start_location.setdefault((station1, station2, location1), []).append(location2)
#    z_by_edge_end_location.setdefault((station1, station2, location2), []).append(location1)

x_locations_by_station = {station: set() for station in airlink_stations}
x_stations_by_location = {location: set() for location in location_names}
for station, location in valid_station_locations:
    x_locations_by_station[station].add(location)
    x_stations_by_location[location].add(station)

for station in airlink_stations:
    if not x_locations_by_station[station]:
        raise ValueError(f"No eligible locations for station: {station}")

z_outgoing = {}
z_incoming = {}
for (station1, station2, location1, location2) in valid_z:
    z_outgoing.setdefault((station1, station2, location1), []).append(location2)
    z_incoming.setdefault((station1, station2, location2), []).append(location1)

z_start_indices = []
z_end_indices = []
for station1, station2 in airlink_edges:
    for location1 in eligible_locations[station1]:
        z_start_indices.append((station1, station2, location1))

    for location2 in eligible_locations[station2]:
        z_end_indices.append((station1, station2, location2))

z_by_location_pair = {}

for (station1, station2, location1, location2) in valid_z:
    z_by_location_pair.setdefault((location1, location2), []).append((station1, station2, location1, location2))

print("Pyomo x variables:", len(valid_station_locations))
print("Pyomo z variables:", len(valid_z))
print("Blocking constraints:", len(blocking_constraints))

#Convert location conflicts into z conflicts
crossing_z_pairs = get_crossing_z_pairs(crossing_location_pairs, z_by_location_pair)
print("Crossing z constraints:",len(crossing_z_pairs))

#Infeasible max_distance_multiplier 
# stations with no valid x locations
for station in airlink_stations:
    if not eligible_locations[station]:
        print("NO ELIGIBLE LOCATIONS:", station)

# edges with no valid z placements
z_count_by_edge = {(station1, station2): 0 for station1, station2 in airlink_edges}
for station1, station2, location1, location2 in valid_z:
    z_count_by_edge[(station1, station2)] += 1
for edge, count in z_count_by_edge.items():
    if count == 0:
        print("NO VALID Z FOR EDGE:", edge)

# key station reference sanity check
valid_reference_locations = [location for location in reference_locations if location in x_locations_by_station[KEY_STATION]]
print("Valid reference locations for key station:", valid_reference_locations)

if len(valid_reference_locations)==0:
    sys.exit("No valid location found for reference location. Try increasing MAX_DISTANCE_THRESHOLD")

#model = build_model(airlink_stations, airlink_edges, location_names, valid_location_pairs, location_pair_distances,KEY_STATION )
#model = build_model(airlink_stations, airlink_edges, location_names, valid_location_pairs, location_pair_distances,KEY_STATION )
model=build_model(airlink_stations, airlink_edges, location_names, valid_station_locations, valid_z, blocking_constraints, z_start_indices, z_end_indices, location_pair_distances, KEY_STATION, crossing_z_pairs)
print("NVARS: ", model.nvariables())
print("NCONSTRAINTS: ", model.nconstraints())

if Flag_Output_MPS==True:
    output_mps(model)
solver = pyo.SolverFactory("appsi_highs")
solver.options["time_limit"] = SOLVER_TIME_LIMIT

results = solver.solve(model,tee=True,load_solutions=False)
print("Termination:",results.solver.termination_condition)
if len(results.solution) > 0:
    model.solutions.load_from(results)
    assignments = get_station_assignments(model, location_lookup)
    output_assignments(assignments)
else:
    print("No feasible solution found.")

#results = solver.solve(model, tee=True)
#print("Termination:", results.solver.termination_condition)

if Flag_Output_Results==True:
    print(results)

#if results.has_feasible_solution()==True:
#   model.solutions.load_from(results)
#else:
 #   print("No feasible solution found.")

