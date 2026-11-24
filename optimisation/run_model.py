#from data import load_config
import get_data as get_data
import geometry as geo
import preprocessing as prep
import outputs as outputs

#import config data
config = get_data.load_config("../config/model_config.json")

#import data and construct stations / edges
NetworkData=get_data.build_network_data(config.filepaths["Station_pair_json_path"], config.filepaths["Potential_stations_json_path"], operator=config.operator)
if config.output["write_station_json"]: outputs.print_station_pairs(NetworkData.station_pairs, NetworkData.edges, NetworkData.stations, config.filepaths["Station_pair_json_path"])

#an adjacent pair of stations may be at most X nominal station spacings apart
maximum_distance_apart = ( config.geometry["max_distance_multiplier"] * NetworkData.target_spacing)
if config.output["write_location_json"]:outputs.print_potential_locations(config.filepaths["Potential_stations_json_path"], NetworkData.locations,maximum_distance_apart)
#dataprep=prep.preprocess(config, NetworkData.locations, NetworkData.stations, NetworkData.edges)


