import geometry as geo
from dataclasses import dataclass


@dataclass(frozen=True)
class NetworkData:
    station_pairs: list[dict]
    edges: list[tuple[str, str]]
    stations: list[str]
    locations: list[dict]
    target_spacing: float

#class PlacementData:
#    x_locations_by_stations
#    x_stations_by_location
#    z_outgoing
#    z_incoming
#    blocking_locations
#    location_pair_distance
#    reference_locations
#    z_by_physical_link
    
def get_reference_locations(locations):
    #for each ring, find the location with the smallest theta (closest to the horizontal axis)
    by_ring = {}
    for location in locations:
        ring = location["Ring"]
        theta_distance = min(location["Theta"],  2 * math.pi - location["Theta"] )
        if (ring not in by_ring  or theta_distance < by_ring[ring][0] ):
            by_ring[ring] = (theta_distance, location["Location"] )
    return [by_ring[ring][1] for ring in sorted(by_ring)]

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

def get_valid_location_pairs(locations, target_spacing, max_distance_multiplier, max_ring_difference):
    #get valid locations. rather than compare every location (n^2), restrict to those in proximity
    valid_pairs = []
    maximum_distance = (target_spacing * max_distance_multiplier)
    for location1 in locations:
        for location2 in locations:
            if geo.check_valid_location(location1, location2, maximum_distance, max_ring_difference)==True:
                valid_pairs.append((location1["Location"],location2["Location"]))
    return valid_pairs

def check_feasible_location(station, location, station_degree, location_neighbour_count):
    #for station, check if number of reachable locations >= number of connecting stations    
    return (location_neighbour_count[location] >= station_degree[station] )

def get_valid_station_locations(stations, locations, station_degree, location_neighbour_count):
    valid_station_locations = []
    for station in stations:
        for location in locations:
            if check_feasible_location(station, location, station_degree, location_neighbour_count):
                valid_station_locations.append((station, location))
    return valid_station_locations

def check_common_neighbours_count(station1, station2,location1, location2,station_neighbours,location_neighbours):
    #check if there are at least as many valid locations reachable from both location1 and location2 as there are stations connected to station1 and station2
    common_stations = (station_neighbours[station1] & station_neighbours[station2] )
    common_locations = (location_neighbours[location1] & location_neighbours[location2] )
    return (len(common_locations) >= len(common_stations))

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

###########
#build x lookup dictionaries
#build z lookup dictionaries
#build physical links
#build blockers
#############

def preprocess(config, potential_locations, stations, edges):
    #an adjacent pair of stations may be at most X nominal station spacings apart
    maximum_distance_apart = ( config.geometry["max_distance_multiplier"]* potential_locations["TargetSpacing"])
    #print_potential_locations(config, potential_locations,maximum_distance_apart)
    
    #Build location lookup
    location_lookup = {row["Location"]: row for row in potential_locations["Locations"]}

    #Build an ordered list of locations on each ring
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
    incoming_locations = {location: set() for location in location_names}
    for location1, location2 in valid_location_pairs:
        outgoing_locations[location1].add(location2)
        incoming_locations[location2].add(location1)
    location_neighbours = outgoing_locations

    #Create count of number of valid locations reachable from each location
    location_neighbour_count = {location: len(neighbours) for location, neighbours in outgoing_locations.items()}

    #sum of distances between pairs of stations sited at paired locations
    #location_pair_distances = {(l1, l2): location_pair_distance(location_lookup[l1], location_lookup[l2]) for l1, l2 in valid_location_pairs}
    station_neighbours=get_station_neighbours(stations, edges)
    station_degree = {station: len(neighbours) for station, neighbours in station_neighbours.items()}
    valid_station_locations = get_valid_station_locations(stations,location_names,station_degree,location_neighbour_count)
    location_pair_distances = {(l1, l2): geo.location_pair_distance(location_lookup[l1], location_lookup[l2]) for l1, l2 in valid_location_pairs}

    #print("Station degrees:")
    #for station in stations:
    #    print(station, station_degree[station])

    eligible_locations = {station: set() for station in stations}
    for station, location in valid_station_locations:
        eligible_locations[station].add(location)
    
    #Get reference locations and key station
    reference_locations=get_reference_locations( potential_locations["Locations"])
    KEY_STATION=get_key_station(edges,  mode=config.symmetry["keystation_mode"], key_station=config.symmetry["key_station"])
    print("Key station:", KEY_STATION)
    print("Reference locations:", reference_locations)



