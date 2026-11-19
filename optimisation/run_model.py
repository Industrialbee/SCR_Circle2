from data import load_config
import data as get_data
import geometry as geo

Station_pair_json_path="../data_gather/station_pairs.json"
Potential_stations_json_path="../potential_locations/potential_station_locations.json"

#import data and construct stations / edges
config = get_data.load_config("../config/model_config.json")
station_pairs=get_data.load_station_pairs(Station_pair_json_path)
potential_locations=get_data.load_potential_locations(Potential_stations_json_path)
airlink_edges=get_data.get_edges(station_pairs, config["operator"])
airlink_stations=get_data.get_station_names(airlink_edges)
get_data.print_station_pairs(station_pairs, airlink_edges, airlink_stations, Station_pair_json_path)


