import geometry as geo
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class PlacementData:
    stations:list
    edges:list
    location_names:list
    location_lookup:dict
    valid_station_locations:list
    valid_z:list
    x_locations_by_station:dict
    x_stations_by_location:dict
    z_outgoing:dict
    z_incoming:dict
    blocking_locations:dict
    blocking_constraints:list
    location_pair_distances:dict
    reference_locations:list
    key_station:str
    physical_links:set
    z_by_physical_link:dict
    z_start_indices:list
    z_end_indices:list
    
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

def get_station_neighbours(stations, edges):
    #find list of stations that are connected to station
    station_neighbours = {station: set() for station in stations}
    for station1, station2 in edges:
        station_neighbours[station1].add(station2)
        station_neighbours[station2].add(station1)
    return station_neighbours

def get_valid_location_pairs(potential_locations, target_spacing, max_distance_multiplier, max_ring_difference):
    #get valid potential_locations. rather than compare every location (n^2), restrict to those in proximity
    valid_pairs = []
    maximum_distance = (target_spacing * max_distance_multiplier)
    for location1 in potential_locations:
        for location2 in potential_locations:
            if geo.check_valid_location(location1, location2, maximum_distance, max_ring_difference)==True:
                valid_pairs.append((location1["Location"],location2["Location"]))
    return valid_pairs

def check_feasible_location(station, location, station_degree, location_neighbour_count):
    #for station, check if number of reachable potential_locations >= number of connecting stations    
    return (location_neighbour_count[location] >= station_degree[station] )

def get_valid_station_locations(stations, potential_locations, station_degree, location_neighbour_count,use_degree_feasibility=True):
    valid_station_locations = []
    for station in stations:
        for location in potential_locations:
            if (use_degree_feasibility and not check_feasible_location(station, location, station_degree, location_neighbour_count)):
                continue
            valid_station_locations.append((station, location))
    return valid_station_locations

def check_common_neighbours_count(station1, station2,location1, location2,station_neighbours,location_neighbours):
    #check if there are at least as many valid potential_locations reachable from both location1 and location2 as there are stations connected to station1 and station2
    common_stations = (station_neighbours[station1] & station_neighbours[station2] )
    common_locations = (location_neighbours[location1] & location_neighbours[location2] )
    return (len(common_locations) >= len(common_stations))

def check_combined_neighbour_capacity(station1, station2, location1, location2, station_neighbours, location_neighbours):
    required_neighbours = (station_neighbours[station1] | station_neighbours[station2] ) - {station1, station2}
    available_locations = (location_neighbours[location1] | location_neighbours[location2]  ) - {location1, location2}
    return (len(available_locations)>= len(required_neighbours)  )

def get_valid_z_indices(edges, valid_location_pairs, x_locations_by_station, station_neighbours, location_neighbours,use_common_neighbour=True):
    valid_z = []
    for station1, station2 in edges:
        for location1, location2 in valid_location_pairs:
            if use_common_neighbour != True:
                continue
            if location1 not in x_locations_by_station[station1]:
                continue
            if location2 not in x_locations_by_station[station2]:
                continue
            if not check_common_neighbours_count(station1, station2, location1, location2, station_neighbours, location_neighbours):
                continue
            if not check_combined_neighbour_capacity(station1, station2, location1, location2, station_neighbours, location_neighbours):
                continue
            valid_z.append((station1, station2, location1, location2 ))
    return valid_z

###########
#build x lookup dictionaries
#build z lookup dictionaries
#build physical links
#build blockers
#############

def preprocess(config, network_data):
    potential_locations = network_data.locations
    stations = network_data.stations
    edges = network_data.edges
    
    #an adjacent pair of stations may be at most X nominal station spacings apart
    maximum_distance_apart = ( config.geometry["max_distance_multiplier"]* potential_locations["TargetSpacing"])
    #print_potential_locations(config, potential_locations,maximum_distance_apart)
    
    #Build location lookup
    location_lookup = {row["Location"]: row for row in potential_locations["Locations"]}

    #Build an ordered list of potential_locations on each ring
    ring_locations = geo.get_ring_locations(potential_locations["Locations"])

    #Define list of valid (in near proximity) location pairs 
    valid_location_pairs = get_valid_location_pairs(potential_locations["Locations"], potential_locations["TargetSpacing"], config.geometry["max_distance_multiplier"], config.geometry["max_ring_difference"])

    #Create location names
    location_names = [row["Location"] for row in potential_locations["Locations"]]
    
    #Print valid location pairs count - check it works
    print(f"Valid location pairs: {len(valid_location_pairs):,} " f"of {len(location_names) ** 2:,}")
    print(f"z variables: "f"{len(edges) * len(valid_location_pairs):,}")

    #Compute neighbouring location lists
    outgoing_locations = {location: set() for location in location_names}
    #incoming_locations = {location: set() for location in location_names}
    for location1, location2 in valid_location_pairs:
        outgoing_locations[location1].add(location2)
        #incoming_locations[location2].add(location1)
    location_neighbours = outgoing_locations

    #Create count of number of valid locations reachable from each location
    location_neighbour_count = {location: len(neighbours) for location, neighbours in outgoing_locations.items()}

    #sum of distances between pairs of stations sited at paired locations
    #location_pair_distances = {(l1, l2): location_pair_distance(location_lookup[l1], location_lookup[l2]) for l1, l2 in valid_location_pairs}
    station_neighbours=get_station_neighbours(stations, edges)
    station_degree = {station: len(neighbours) for station, neighbours in station_neighbours.items()}
    valid_station_locations = get_valid_station_locations(stations,location_names,station_degree,location_neighbour_count, config.preprocessing["degree_feasibility"])
    location_pair_distances = {(l1, l2): geo.location_pair_distance(location_lookup[l1], location_lookup[l2]) for l1, l2 in valid_location_pairs}

    #print("Station degrees:")
    #for station in stations:
    #    print(station, station_degree[station])

    #eligible_locations = {station: set() for station in stations}
    #for station, location in valid_station_locations:
    #    eligible_locations[station].add(location)
    x_locations_by_station = {station: set() for station in stations}
    x_stations_by_location = {location: set() for location in location_names}
    for station, location in valid_station_locations:
        x_locations_by_station[station].add(location)
        x_stations_by_location[location].add(station)

    #Get reference locations and key station
    reference_locations=geo.get_reference_locations( potential_locations["Locations"])
    key_station=get_key_station(edges,  mode=config.symmetry["key_station_mode"], key_station=config.symmetry["key_station"])
    print("Key station:", key_station)
    print("Reference locations:", reference_locations)

    valid_z = get_valid_z_indices(edges, valid_location_pairs, x_locations_by_station, station_neighbours, location_neighbours, config.preprocessing["common_neighbour"])
    
    # edges with no valid z placements
    if config.constraints["key_station_symmetry"]:
        z_count_by_edge = {(station1, station2): 0 for station1, station2 in edges}
        for station1, station2, location1, location2 in valid_z:
            z_count_by_edge[(station1, station2)] += 1
        for edge, count in z_count_by_edge.items():
            if count == 0:
                print("NO VALID Z FOR EDGE:", edge)

    # key station reference sanity check
    valid_reference_locations = [location for location in reference_locations if location in x_locations_by_station[key_station]]
    print("Valid reference locations for key station:", valid_reference_locations)

    
    for station in stations:
        if not x_locations_by_station[station]:
            raise ValueError(f"No eligible locations for station: {station}")

    z_outgoing = {}
    z_incoming = {}
    for (station1, station2, location1, location2) in valid_z:
        z_outgoing.setdefault((station1, station2, location1), []).append(location2)
        z_incoming.setdefault((station1, station2, location2), []).append(location1)

    blocking_locations = {}
    blocking_constraints = []
    if config.constraints["same_ring_blocking"]:
        #Precompute blockers for every valid location pair
        blocking_locations = {(location1, location2): geo.get_blocking_locations(location1, location2, location_lookup, ring_locations) for location1, location2 in valid_location_pairs}

        #precompute a flat constraint-index list for blocking constraint
        blocking_constraints = []
        for (station1, station2, location1, location2) in valid_z:
            if blocking_locations[(location1, location2)]:
                blocking_constraints.append((station1, station2, location1, location2))
        print("Blocking constraints:",len(blocking_constraints))

    #
    if config.preprocessing["common_neighbour"]:
        physical_links = {geo.physical_link(location1, location2) for (station1, station2, location1, location2) in valid_z}
        z_by_physical_link = {link: []  for link in physical_links}
        for (station1, station2, location1, location2) in valid_z:
            link = geo.physical_link(location1, location2)
            z_by_physical_link[link].append((station1, station2, location1, location2))

    z_start_indices = []
    z_end_indices = []
    for station1, station2 in edges:
        for location1 in x_locations_by_station[station1]:
            z_start_indices.append((station1, station2, location1))

        for location2 in x_locations_by_station[station2]:
            z_end_indices.append((station1, station2, location2))
    return PlacementData(stations=stations,edges=edges,location_names=location_names,location_lookup=location_lookup,valid_station_locations=valid_station_locations,valid_z=valid_z,x_locations_by_station=x_locations_by_station,x_stations_by_location=x_stations_by_location,z_outgoing=z_outgoing,z_incoming=z_incoming,blocking_locations=blocking_locations,blocking_constraints=blocking_constraints,location_pair_distances=location_pair_distances,reference_locations=reference_locations,key_station=key_station,physical_links=physical_links,z_by_physical_link=z_by_physical_link,z_start_indices=z_start_indices,z_end_indices=z_end_indices)

