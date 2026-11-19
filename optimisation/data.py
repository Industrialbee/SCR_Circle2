import json

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_station_pairs(Station_pair_json_path):
    #Load station pairs
    with open(Station_pair_json_path, "r", encoding="utf-8") as sp:
        station_pairs = json.load(sp)
    return station_pairs

def load_potential_locations(Potential_stations_json_path):
    #Load potential locations
    with open(Potential_stations_json_path, "r", encoding="utf-8") as pl: 
        potential_locations=json.load(pl)
    return potential_locations

def get_edges(station_pairs: list[dict], operatorfilter: str = "") -> list[tuple[str, str]]:
    #Get list of station pairs data. If operator name filter supplied then filter to that operator only
    if operatorfilter=="" :
        airlink_edges = [(row["FirstStation"], row["SecondStation"]) for row in station_pairs]
    else:
        airlink_edges = [(row["FirstStation"], row["SecondStation"]) for row in station_pairs if row["Operator"] == operatorfilter]
    return airlink_edges

def get_station_names(edges:list[tuple[str, str]])->list[str]:    
    #List of stations in operator routes
    stations_names = sorted({station for a, b in edges for station in (a, b)})
    return stations_names

def print_station_pairs(station_pairs, airlink_edges, airlink_stations, Station_pair_json_path):    
    print("From potential locations file: ", Station_pair_json_path)
    print("Station pairs loaded: ", len(station_pairs))
    print("Station edges loaded: ", len(airlink_edges))
    print("Station names loaded: ", len(airlink_stations))

