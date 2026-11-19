
def get_station_neighbours(stations, edges):
    #find list of stations that are connected to station
    station_neighbours = {station: set() for station in stations}
    for station1, station2 in edges:
        station_neighbours[station1].add(station2)
        station_neighbours[station2].add(station1)
    return station_neighbours

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
build x lookup dictionaries
build z lookup dictionaries
build physical links
build blockers
#############
