import json
import pyomo.environ as pyo
#from pyomo.opt import SolverStatus, TerminationCondition
#import pyomo.contrib as pyc
import math

#Parameters
MAX_DISTANCE_MULTIPLIER = 3.0
MAX_RING_DIFFERENCE = 1
Station_pair_json_path="./data/station_pairs.json"
Potential_stations_json_path="./Potential_Locations/potential_station_locations.json"
MPS_path="./model_output/station_placement.mps"
Assignment_path="./model_output/station_assignments.json"
SOLVER_TIME_LIMIT=60 #seconds
Flag_Output_MPS=True
Flag_Output_Results=True

def get_station_pairs():
    #Get station pairs
    with open(Station_pair_json_path, "r", encoding="utf-8") as sp:
        station_pairs = json.load(sp)
    return station_pairs

def print_station_pairs(station_pairs, airlink_edges, airlink_stations):    
    print("From station pairs file: ", Station_pair_json_path)
    print("Station pairs loaded: ", len(station_pairs))
    print("Station edges loaded: ", len(airlink_edges))
    print("Station names loaded: ", len(airlink_stations))

def get_potential_locations():
    #Get potential locations
    with open(Potential_stations_json_path, "r", encoding="utf-8") as pl: 
        potential_locations=json.load(pl)
    return potential_locations
    
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

def get_valid_location_pairs(locations, target_spacing, max_distance_multiplier, max_ring_difference):
    #get valid locations. rather than compare every location (n^2), restrict to those in proximity
    valid_pairs = []
    maximum_distance = (target_spacing * max_distance_multiplier)
    for location1 in locations:
        for location2 in locations:
            #exclude where pair is same location 
            if location1["Location"] == location2["Location"]:
                continue            
            #exclude where pair are further than max_ring_difference apart (no. of rings apart) 
            if abs(location1["Ring"] - location2["Ring"]) > max_ring_difference:
                continue
            # exclude where pair are more than maximum_distance apart    
            if location_pair_distance(location1,location2) > maximum_distance:
                continue
            valid_pairs.append((location1["Location"],location2["Location"]))
    return valid_pairs
    
def one_location_per_station_rule(model, station):
    #A station occupies exactly one location
    return sum(model.x[station, location] for location in model.LOCATIONS) == 1

def one_station_per_location_rule(model, location):
    #A location can only have one station (or be empty)
    return sum(model.x[station, location] for station in model.STATIONS) <= 1

def edge_start_location_rule(model, station1, station2, location1):
    # If station1 of an edge is assigned to location1, exactly one z variable for that edge must start at location1.
        return sum(model.z[station1, station2, location1, location2] for location2 in outgoing_locations[location1]) == model.x[station1, location1]

def edge_end_location_rule(model, station1, station2, location2):
    # If station2 of an edge is assigned to location2, exactly one z variable for that edge must end at location2.
    return sum(model.z[station1, station2, location1, location2] for location1 in incoming_locations[location2]) == model.x[station2, location2]
    
def model_objective_rule(model):
    #sum of distances between pairs of stations sited at paired locations
    location_pair_distances = {(l1, l2): location_pair_distance(location_lookup[l1], location_lookup[l2]) for l1, l2 in valid_location_pairs}
    return sum(
        location_pair_distances[location1, location2]* model.z[station1,station2,location1,location2]  
        for station1, station2 in model.EDGES for location1, location2 in model.LOCATION_PAIRS)

def build_model(airlink_stations, airlink_edges, location_names, valid_location_pairs):
    #Define model
    model = pyo.ConcreteModel(name="Station placement")
    
    #Add location names / station names to model
    model.STATIONS = pyo.Set(initialize=airlink_stations,   ordered=True)
    model.LOCATIONS = pyo.Set(initialize=location_names,    ordered=True)

    model.LOCATION_PAIRS = pyo.Set(dimen=2, initialize=valid_location_pairs)
    model.EDGES=pyo.Set(dimen=2, initialize=airlink_edges,    ordered=True)
    
    #Create a station * location binary matrix
    model.x = pyo.Var(model.STATIONS, model.LOCATIONS, within=pyo.Binary)

    model.z=pyo.Var(model.EDGES, model.LOCATION_PAIRS, within=pyo.Binary)
    
    #station/location constraints
    model.one_location_per_station = pyo.Constraint( model.STATIONS, rule=one_location_per_station_rule)
    model.one_station_per_location = pyo.Constraint(model.LOCATIONS,   rule=one_station_per_location_rule)
    
    model.edge_start_location = pyo.Constraint(model.EDGES,model.LOCATIONS,rule=edge_start_location_rule)
    model.edge_end_location = pyo.Constraint(model.EDGES,model.LOCATIONS,rule=edge_end_location_rule)
    
    #Real objective - minimise distance between the chosen location of A and the chosen location of B
    model.objective = pyo.Objective(rule=model_objective_rule, sense=pyo.minimize)    
    return model

def output_mps(model):
    model.write(MPS_path, format="mps",  io_options={"symbolic_solver_labels": True})
    print("Model MPS file saved to: ",MPS_path) 

def get_station_assignments(model, location_lookup):
    assignments = []
    for station in model.STATIONS:
        for location in model.LOCATIONS:
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

#Define list of valid (in near proximity) location pairs 
valid_location_pairs = get_valid_location_pairs(potential_locations["Locations"], potential_locations["TargetSpacing"],MAX_DISTANCE_MULTIPLIER,MAX_RING_DIFFERENCE)

#Create location names
location_names = [row["Location"] for row in potential_locations["Locations"]]

#Print valid location pairs count - check it works
print(f"Valid location pairs: {len(valid_location_pairs):,} " f"of {len(location_names) ** 2:,}")
print(f"z variables: "f"{len(airlink_edges) * len(valid_location_pairs):,}")

#Compute neighbouring location lists
outgoing_locations = {location: [] for location in location_names}
incoming_locations = {location: [] for location in location_names}
for l1, l2 in valid_location_pairs: 
    outgoing_locations[l1].append(l2)
    incoming_locations[l2].append(l1)

model = build_model(airlink_stations, airlink_edges, location_names, valid_location_pairs)
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

