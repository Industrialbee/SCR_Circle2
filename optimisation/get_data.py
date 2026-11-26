import json
from dataclasses import dataclass

@dataclass(frozen=True)
class NetworkData:
    station_pairs: list[dict]
    edges: list[tuple[str, str]]
    stations: list[str]
    locations: list[dict]
    target_spacing: float

@dataclass(frozen=True)
class ConfigData:
    operator:str
    geometry: dict
    filepaths: dict
    constraints:dict
    symmetry:dict
    solver:dict
    output:dict

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_edges(station_pairs: list[dict], operatorfilter: str = "") -> list[tuple[str, str]]:
    #Get list of station pairs data. If operator name filter supplied then filter to that operator only
    if operatorfilter=="" :
        edges = [(row["FirstStation"], row["SecondStation"]) for row in station_pairs]
    else:
        edges = [(row["FirstStation"], row["SecondStation"]) for row in station_pairs if row["Operator"] == operatorfilter]
    return edges

def get_station_names(edges:list[tuple[str, str]])->list[str]:    
    #List of stations in operator routes
    stations_names = sorted({station for a, b in edges for station in (a, b)})
    return stations_names

def build_network_data(station_pairs_path, locations_path, operator=""):
    station_pairs = load_json(station_pairs_path)
    potential = load_json(locations_path)
    edges = get_edges(station_pairs, operator)
    return NetworkData(station_pairs =station_pairs , edges=edges, stations=get_station_names(edges), locations=potential, target_spacing=potential["TargetSpacing"])

def load_config(path):
    config=load_json(path)
    return ConfigData(operator=config["operator"], geometry=config["geometry"],filepaths=config["filepaths"],constraints=config["constraints"],symmetry=config["symmetry"],
    solver=config["solver"],output=config["output"])
    #return ConfigData(config)




