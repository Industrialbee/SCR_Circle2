#from data import load_config
import get_data as get_data
import geometry as geo
import preprocessing as prep
import outputs as outputs

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
#import config data
config = get_data.load_config(PROJECT_ROOT / "config" / "model_config.json")

#import data and construct stations / edges
NetworkData=get_data.build_network_data(PROJECT_ROOT / config.filepaths["Station_pair_json_path"], PROJECT_ROOT /config.filepaths["Potential_stations_json_path"], operator=config.operator)
if config.output["write_station_json"]: outputs.print_station_pairs(NetworkData.station_pairs, NetworkData.edges, NetworkData.stations, PROJECT_ROOT /config.filepaths["Station_pair_json_path"])

#an adjacent pair of stations may be at most X nominal station spacings apart
maximum_distance_apart = ( config.geometry["max_distance_multiplier"] * NetworkData.target_spacing)
if config.output["write_location_json"]:outputs.print_potential_locations(PROJECT_ROOT /config.filepaths["Potential_stations_json_path"], NetworkData.locations,maximum_distance_apart)
#dataprep=prep.preprocess(config, NetworkData.locations, NetworkData.stations, NetworkData.edges)


