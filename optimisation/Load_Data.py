import json
import pyomo.environ as pyo
#from pyomo.opt import SolverStatus, TerminationCondition
#import pyomo.contrib as pyc
import math
from pathlib import Path
from collections import Counter
import sys

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

#def get_ring_pair(location1, location2, location_lookup):
#    #Because one link might be stored inner→outer and another outer→inner
#    ring1 = location_lookup[location1]["Ring"]
#    ring2 = location_lookup[location2]["Ring"]
#    return tuple(sorted((ring1, ring2)))

#def get_crossing_location_pairs(valid_location_pairs, location_lookup):
#    inter_ring_pairs = get_inter_ring_location_pairs(valid_location_pairs, location_lookup)
#    
#    # Group location pairs by the rings they span
#    pairs_by_rings = {}
#
#    for location1, location2 in inter_ring_pairs:
#        ring_pair = get_ring_pair(location1, location2, location_lookup)
#
#        pairs_by_rings.setdefault(ring_pair, []).append((location1, location2))
#
#    crossing_pairs = set()
#    for ring_pair, pairs in pairs_by_rings.items():
#        for i in range(len(pairs)):
#            location1a, location2a = pairs[i]
#            for j in range(i + 1, len(pairs)):
#                location1b, location2b = pairs[j]
#
#                if location_links_cross(location1a, location2a, location1b, location2b, location_lookup):
#                    crossing_pairs.add((location1a, location2a, location1b, location2b))
#    return crossing_pairs

def get_crossing_physical_links(physical_links, location_lookup):
    links = list(physical_links)
    crossing_pairs = set()
    for i in range(len(links)):
        link_a = links[i]
        for j in range(i + 1, len(links)):
            link_b = links[j]
            if physical_links_cross(link_a, link_b, location_lookup):
                crossing_pairs.add((link_a[0], link_a[1], link_b[0], link_b[1]))
    return crossing_pairs

def bounding_boxes_overlap(location1a, location2a, location1b, location2b, location_lookup):
    #avoid doing the orientation calculation on obviously unrelated segments by checking their bounding boxes first.
    p1 = location_lookup[location1a]
    p2 = location_lookup[location2a]
    p3 = location_lookup[location1b]
    p4 = location_lookup[location2b]
    min_ax = min(p1["X"], p2["X"])
    max_ax = max(p1["X"], p2["X"])
    min_ay = min(p1["Y"], p2["Y"])
    max_ay = max(p1["Y"], p2["Y"])
    min_bx = min(p3["X"], p4["X"])
    max_bx = max(p3["X"], p4["X"])
    min_by = min(p3["Y"], p4["Y"])
    max_by = max(p3["Y"], p4["Y"])
    return not (max_ax < min_bx or max_bx < min_ax or max_ay < min_by or max_by < min_ay )

def get_used_crossings(used_links, location_lookup):
    crossings = []
    for i in range(len(used_links)):
        link_a = used_links[i]
        for j in range(i + 1, len(used_links)):
            link_b = used_links[j]
            if physical_links_cross(link_a, link_b, location_lookup):
                crossing = canonical_crossing(link_a,link_b)
                #crossings.append((link_a[0], link_a[1], link_b[0], link_b[1]))
                crossings.append((crossing[0][0], crossing[0][1], crossing[1][0], crossing[1][1]))
    return crossings




Path("./model_output").mkdir(parents=True, exist_ok=True)

    
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
#crossing_location_pairs = get_crossing_location_pairs(valid_location_pairs,location_lookup)
#print("Crossing location-pair combinations:", len(crossing_location_pairs))


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
#crossing_z_pairs = get_crossing_z_pairs(crossing_location_pairs, z_by_location_pair)
#print("Crossing z constraints:",len(crossing_z_pairs))

physical_links = {physical_link(location1, location2) for (station1, station2, location1, location2) in valid_z}
z_by_physical_link = {link: []  for link in physical_links}
for (station1, station2, location1, location2) in valid_z:
    link = physical_link(location1, location2)
    z_by_physical_link[link].append((station1, station2, location1, location2))

#crossing_physical_links=get_crossing_physical_links(physical_links, location_lookup)
#print("Physical links:", len(physical_links))
#print("Crossing physical-link pairs:", len(crossing_physical_links))

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
model=build_model(airlink_stations, airlink_edges, location_names, valid_station_locations, valid_z, blocking_constraints, z_start_indices, z_end_indices, location_pair_distances, KEY_STATION, z_by_physical_link,physical_links, crossing_physical_links)
print("NVARS: ", model.nvariables())
print("NCONSTRAINTS: ", model.nconstraints())

if Flag_Output_MPS==True:
    output_mps(model)
    
solver = pyo.SolverFactory("appsi_highs")
solver.options["time_limit"] = SOLVER_TIME_LIMIT

added_crossings = set()
for iteration in range(MAX_CROSSING_ITERATIONS):
    results = solver.solve(model, tee=True, load_solutions=False)
    if len(results.solution) == 0:
        print("No feasible solution found.")
        break
    model.solutions.load_from(results)
    used_links = get_used_physical_links(model)
    crossings = get_used_crossings(used_links, location_lookup)    
    new_crossings = [crossing for crossing in crossings if crossing not in added_crossings]

    print(f"Iteration {iteration + 1}: " f"{len(crossings)} crossings, " f"{len(new_crossings)} new")
    if not crossings:
        print("Crossing-free solution found.")
        break

    for crossing in new_crossings:
        l1a, l2a, l1b, l2b = crossing        
        model.crossing_links.add(model.w[l1a, l2a] + model.w[l1b, l2b]<= 1)
        added_crossings.add(crossing)
    
    #results = solver.solve(model,tee=True,load_solutions=False)
print("Termination:",results.solver.termination_condition)
if len(results.solution) > 0:
    model.solutions.load_from(results)
    assignments = get_station_assignments(model, location_lookup)
    outputs.output_assignments(assignments)
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

