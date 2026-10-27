import json
#import numpy as np
import pyomo.environ as pyo

def get_edges (station_pairs: list[str,str], operatorfilter:str="")-> list[tuple[str,str]]:
    #Get list of station pairs data. If operator name filter supplied then filter to that operator only
    if operatorfilter=="" :
        airlink_edges = [(row["FirstStation"], row["SecondStation"]) for row in station_pairs]
    else:
        airlink_edges = [(row["FirstStation"], row["SecondStation"]) for row in station_pairs if row["Operator"] == operatorfilter]
    return airlink_edges

def get_station_name_list(edges:list[str,str])->list[str]:    
    #List of stations in operator routes
    stations_names = sorted({station for a, b in edges for station in (a, b)})
    return stations_names

def one_location_per_station_rule(model, station):
    #A station occupies exactly one location
    return sum(model.x[station, location] for location in model.LOCATIONS) == 1

def one_station_per_location_rule(model, location):
    #A location can only have one station (or be empty)
    return sum(model.x[station, location] for station in model.STATIONS) <= 1

def one_pair_per_edges_rule(edge,location1, location2):
    #A station pair occupies only one edge
    return sum(model.z[edge,location1, location2] for edge in model.EDGES) == 1

def location_pair_distance(location1, location2):
#dummy function - will need to precompute before use
    return 1
    
def model_objective_rule (model):
    return sum(sum(sum(location_pair_distance(l1,l2)*model.z[e, l1, l2] for l2 in model.LOCATION2) for l1 in model.LOCATION1) for e in model.EDGES) 


with open("./data/station_pairs.json", "r", encoding="utf-8") as sp:
    station_pairs = json.load(sp)

airlink_edges=get_edges(station_pairs, "AirLink")
airlink_stations=get_station_name_list(airlink_edges)
print(airlink_edges)
print(airlink_stations)
NoStations=len(airlink_stations)

with open(".//Potential_Locations/potential_station_locations.json", "r", encoding="utf-8") as pl: 
    potential_locations=json.load(pl)

NoPotentialLocations=int(potential_locations["NoStations"])
print(NoPotentialLocations)

#StationLocationMx = np.zeros((len(airlink_stations), int(potential_locations["NoStations"])), dtype=int)
#print(StationLocationMx)

#Define model
model = pyo.ConcreteModel(name="Station placement")
#model.x(NoStations, NoPotentialLocations)

#Create location names then add location names / station names to model
location_names = [row["Location"] for row in potential_locations["Locations"]]
model.STATIONS = pyo.Set(initialize=airlink_stations,   ordered=True)
model.LOCATIONS = pyo.Set(initialize=location_names,    ordered=True)

#Create a station * location binary matrix
model.x = pyo.Var(model.STATIONS, model.LOCATIONS, within=pyo.Binary)

model.one_location_per_station = pyo.Constraint( model.STATIONS, rule=one_location_per_station_rule)
model.one_station_per_location = pyo.Constraint(model.LOCATIONS,   rule=one_station_per_location_rule)

#Dummy objective - test valid model)
#model.objective = pyo.Objective(expr=0, sense=pyo.minimize)

#solver = pyo.SolverFactory("highs")
#solver = pyo.SolverFactory("appsi_highs")
#results = solver.solve(model, tee=True)

for station in model.STATIONS:
    for location in model.LOCATIONS:
        if pyo.value(model.x[station, location]) > 0.5:
            print(station, "->", location)

#calculate edges (distance between stations)
model.LOCATION1 = model.LOCATIONS
model.LOCATION2 = model.LOCATIONS
model.EDGES=pyo.Set(initialize=airlink_edges,    ordered=True)
model.z=pyo.Var(EDGES, LOCATION1, LOCATION2)

model.one_station_pair_per_edges = pyo.Constraint( model.EDGES, rule=one_pair_per_edges_rule)

#Real objective - minimise distance between the chosen location of A and the chosen location of B
#min sum_e sum_{l_1} sum_{l_2} d_{l_1,l_2} ;z_{e,l_1,l_2}
#model.objective = pyo.Objective(expr=0, sense=pyo.minimize)

model.objective = pyo.Objective(expr=model_objective_rule, sense=pyo.minimize)

solver = pyo.SolverFactory("appsi_highs")
results = solver.solve(model, tee=True)

