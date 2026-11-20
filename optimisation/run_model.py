from data import load_config
import data as get_data
import geometry as geo
import preprocessing as prep

config = get_data.load_config("../config/model_config.json")

#import data and construct stations / edges
station_pairs=get_data.load_station_pairs(config["filepaths"]["Station_pair_json_path"])
airlink_edges=get_data.get_edges(station_pairs, config["operator"])
airlink_stations=get_data.get_station_names(airlink_edges)
potential_locations=get_data.load_potential_locations(config["filepaths"]["Potential_stations_json_path"])
get_data.print_station_pairs(station_pairs, airlink_edges, airlink_stations, config["filepaths"]["Station_pair_json_path"])
#an adjacent pair of stations may be at most X nominal station spacings apart
maximum_distance_apart = ( config["geometry"]["max_distance_multiplier"] * potential_locations["TargetSpacing"])
prep.print_potential_locations(config,potential_locations,maximum_distance_apart)

dataprep=prep.preprocess(config, potential_locations, airlink_stations, airlink_edges)


