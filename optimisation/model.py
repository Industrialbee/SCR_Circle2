def one_location_per_station_rule(model, station):
    #A station occupies exactly one location
    #return sum(model.x[station, location] for location in model.LOCATIONS) == 1
    return sum(model.x[station, location] for location in x_locations_by_station[station]) == 1

def one_station_per_location_rule(model, location):
    #A location can only have one station (or be empty)
    #return sum(model.x[station, location] for station in model.STATIONS) <= 1
    #return sum(model.x[station, location] for station in x_stations_by_location[location]) <= 1
    eligible_stations = x_stations_by_location[location]
    if not eligible_stations:
        return pyo.Constraint.Skip
    return sum(model.x[station, location] for station in eligible_stations) <= 1

def edge_start_location_rule(model, station1, station2, location1):
    # If station1 of an edge is assigned to location1, exactly one z variable for that edge must start at location1.
        #return sum(model.z[station1, station2, location1, location2] for location2 in outgoing_locations[location1]) == model.x[station1, location1]
    valid_end_locations = z_outgoing.get((station1, station2, location1), [])
    return sum(model.z[station1, station2, location1, location2] for location2 in valid_end_locations) == model.x[station1, location1]

def edge_end_location_rule(model, station1, station2, location2):
    # If station2 of an edge is assigned to location2, exactly one z variable for that edge must end at location2.
    #return sum(model.z[station1, station2, location1, location2] for location1 in incoming_locations[location2]) == model.x[station2, location2]
    valid_start_locations = z_incoming.get((station1, station2, location2), [])
    return sum(model.z[station1, station2, location1, location2] for location1 in valid_start_locations) == model.x[station2, location2]
    
def key_station_reference_rule(model):
    #return sum(model.x[model.KEY_STATION, location] for location in reference_locations) == 1
    #valid_reference_locations = [location for location in reference_locations if location in x_locations_by_station[pyo.value(model.KEY_STATION)]]
    #return sum(model.x[model.KEY_STATION, location] for location in valid_reference_locations) == 1
    key_station = pyo.value(model.KEY_STATION)
    valid_reference_locations = [location for location in reference_locations if location in x_locations_by_station[key_station]]
    if not valid_reference_locations:
        raise ValueError(f"No reference location available for key station {KEY_STATION}")
    return sum(model.x[key_station, location] for location in valid_reference_locations) == 1
    
#def blocking_location_rule(model, station1, station2, location1, location2, blocker):
#Blocking locations + at most one station occupying a location can't be more than 1
#    #return (model.z[station1, station2, location1, location2]   + sum(model.x[station, blocker] for station in model.STATIONS)  <= 1 )
#    #def blocking_location_rule(model, station1, station2, location1, location2, blocker):
#    return (model.z[station1, station2, location1, location2] + sum(model.x[station, blocker] for station in x_stations_by_location[blocker]) <= 1)

def blocking_location_rule(model, station1, station2, location1, location2):
    #Blocking locations + at most one station occupying a location can't be more than 1
    blockers = blocking_locations[(location1, location2)]
    #blocker_occupancy = sum(model.x[station, blocker] for blocker in blockers for station in x_stations_by_location[blocker])
    #return (blocker_occupancy<=len(blockers) * (1- model.z[station1, station2, location1, location2]))
    return (sum(model.y[blocker] for blocker in blockers ) <=len(blockers) * (1 -model.z[station1, station2, location1, location2]))

def location_occupancy_rule(model, location):
    eligible_stations = x_stations_by_location[location]
    if not eligible_stations:
        return model.y[location] == 0
    return (model.y[location]==sum(model.x[station, location] for station in eligible_stations))

def model_objective_rule(model):
    #return sum(
    #    location_pair_distances[location1, location2]* model.z[station1,station2,location1,location2]  
    #    for station1, station2 in model.EDGES for location1, location2 in model.LOCATION_PAIRS)
    return sum(
        location_pair_distances[location1, location2] * model.z[station1, station2, location1, location2]
        for (station1, station2, location1, location2) in model.Z_INDEX)

#def build_model(airlink_stations, airlink_edges, location_names, valid_location_pairs, location_pair_distances,key_station ):
def build_model(airlink_stations, airlink_edges, location_names, valid_station_locations, valid_z, blocking_constraints, z_start_indices, z_end_indices, location_pair_distances, key_station, z_by_physical_link, physical_links, crossing_physical_links):
    #Define model
    model = pyo.ConcreteModel(name="Station placement")
    
    #Add location names / station names to model
    model.STATIONS = pyo.Set(initialize=airlink_stations,   ordered=True)
    model.LOCATIONS = pyo.Set(initialize=location_names,    ordered=True)

    #model.KEY_STATION=pyo.Param(initialize=key_station)
    
    model.EDGES = pyo.Set(dimen=2, initialize=airlink_edges, ordered=True)
    model.STATION_LOCATIONS = pyo.Set(dimen=2, initialize=valid_station_locations)

    model.Z_INDEX = pyo.Set(dimen=4, initialize=valid_z)
    model.Z_START_INDEX = pyo.Set(dimen=3, initialize=z_start_indices)
    model.Z_END_INDEX = pyo.Set(dimen=3, initialize=z_end_indices)
    
    #Create a station * location binary matrix
    #model.x = pyo.Var(model.STATIONS, model.LOCATIONS, within=pyo.Binary)
    #model.z=pyo.Var(model.EDGES, model.LOCATION_PAIRS, within=pyo.Binary)
    model.x = pyo.Var(model.STATION_LOCATIONS, within=pyo.Binary)
    model.y = pyo.Var(model.LOCATIONS, bounds=(0, 1))
    model.z = pyo.Var(model.Z_INDEX, within=pyo.Binary)
    
    model.BLOCKING_INDEX = pyo.Set(dimen=4, initialize=blocking_constraints)
    model.blocking_location = pyo.Constraint(model.BLOCKING_INDEX, rule=blocking_location_rule)

    #model.CROSSING_Z_INDEX = pyo.Set(dimen=8, initialize=crossing_z_pairs)
    #model.crossing_z = pyo.Constraint(model.CROSSING_Z_INDEX, rule=crossing_z_rule)

    model.PHYSICAL_LINKS = pyo.Set(dimen=2, initialize=physical_links)
    model.w = pyo.Var(model.PHYSICAL_LINKS, bounds=(0, 1))
    model.physical_link_usage = pyo.Constraint(model.PHYSICAL_LINKS, rule=physical_link_usage_rule)
    
    #model.CROSSING_LINK_INDEX = pyo.Set(dimen=4, initialize=crossing_physical_links)
    #model.crossing_links = pyo.Constraint(model.CROSSING_LINK_INDEX, rule=crossing_link_rule)
    model.crossing_links = pyo.ConstraintList()
    #for l1a, l2a, l1b, l2b in new_crossings:model.crossing_links.add(model.w[l1a, l2a] +    model.w[l1b, l2b]    <= 1)
    
    #station/location constraints
    model.one_location_per_station = pyo.Constraint( model.STATIONS, rule=one_location_per_station_rule)
    #model.one_station_per_location = pyo.Constraint(model.LOCATIONS,   rule=one_station_per_location_rule)
    model.location_occupancy = pyo.Constraint(model.LOCATIONS,rule=location_occupancy_rule)
    
    #model.edge_start_location = pyo.Constraint(model.EDGES,model.LOCATIONS,rule=edge_start_location_rule)
    #model.edge_end_location = pyo.Constraint(model.EDGES,model.LOCATIONS,rule=edge_end_location_rule)
    model.edge_start_location = pyo.Constraint(model.Z_START_INDEX, rule=edge_start_location_rule)
    model.edge_end_location = pyo.Constraint(model.Z_END_INDEX, rule=edge_end_location_rule)

    #"Key station" constraint - fixes this station to smallest theta, not smallest ring) - reduces rotational freedom of model 
    #model.key_station_reference = pyo.Constraint(rule=key_station_reference_rule)
    valid_reference_locations = [location for location in reference_locations if location in x_locations_by_station[key_station]]
    model.key_station_reference = pyo.Constraint(expr=sum(model.x[key_station, location] for location in valid_reference_locations) == 1)
       
    #Real objective - minimise distance between the chosen location of A and the chosen location of B
    model.objective = pyo.Objective(rule=model_objective_rule, sense=pyo.minimize)    
    return model

def output_mps(model):
    model.write(MPS_path, format="mps",  io_options={"symbolic_solver_labels": True})
    print("Model MPS file saved to: ",MPS_path) 

def get_station_assignments(model, location_lookup):
    assignments = []
    #for station in model.STATIONS:
    #    for location in model.LOCATIONS:
    for station, location in model.STATION_LOCATIONS:
        if pyo.value(model.x[station, location]) > 0.5:
            loc = location_lookup[location]
            assignments.append({"Station": station, "Location": location, "Ring": loc["Ring"], "Slot": loc["Slot"], "X": loc["X"], "Y": loc["Y"]})
    return assignments


def physical_link_usage_rule(model, location1, location2):
    z_indices = z_by_physical_link[(location1, location2)]
    return (model.w[location1, location2] == sum(model.z[z_index] for z_index in z_indices))

def crossing_link_rule(model, location1a, location2a, location1b, location2b):
    return (model.w[location1a, location2a] + model.w[location1b, location2b]    <= 1)

def get_used_physical_links(model):
    return [(location1, location2) for location1, location2 in model.PHYSICAL_LINKS if pyo.value(model.w[location1, location2]) > 0.5 ]

