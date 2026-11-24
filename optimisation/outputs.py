
def print_station_pairs(station_pairs, edges, stations, Station_pair_json_path):    
    print("From station pairs file: ", Station_pair_json_path)
    print("Station pairs loaded: ", len(station_pairs))
    print("Station edges loaded: ", len(edges))
    print("Station names loaded: ", len(stations))

def print_potential_locations(Potential_stations_json_path,potential_locations,maximum_distance_apart):
    print("From potential locations file: ", Potential_stations_json_path)
    print("No of potential locations loaded: ", int(potential_locations["NoStations"]))
    print("Maximum distance between adjacent stations constraint: ", maximum_distance_apart)

def  output_assignments(assignments):
    for row in assignments:
        print(row["Station"], "->", row["Location"])
    with open(Assignment_path,"w",encoding="utf-8") as f:
        json.dump(assignments, f, indent=2)
    print("Station assignments file saved to: ",Assignment_path) 


