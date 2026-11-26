
import get_data 
import geometry as geo
import preprocessing as prep
import outputs 

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def main():
    #import config data
    config = get_data.load_config(PROJECT_ROOT / "config" / "model_config.json" )

    #import data and construct stations / edges
    network_data=get_data.build_network_data(PROJECT_ROOT / config.filepaths["Station_pair_json_path"], PROJECT_ROOT /config.filepaths["Potential_stations_json_path"], operator=config.operator)
    if config.output["write_station_json"]: outputs.print_station_pairs(network_data.station_pairs, network_data.edges, network_data.stations, PROJECT_ROOT /config.filepaths["Station_pair_json_path"])

    #an adjacent pair of stations may be at most X nominal station spacings apart
    maximum_distance_apart = ( config.geometry["max_distance_multiplier"] * network_data.target_spacing)
    if config.output["write_location_json"]:outputs.print_potential_locations(PROJECT_ROOT /config.filepaths["Potential_stations_json_path"], network_data.locations,maximum_distance_apart)
    prepared_data=prep.preprocess(config, network_data)
    
    geo.geo_unit_tests
    
        # Load network data
        # Preprocess
        # Build model
        # Solve
        # Output results
    
if __name__ == "__main__":
    main()

