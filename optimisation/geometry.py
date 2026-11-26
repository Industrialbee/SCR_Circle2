import math

def location_pair_distance(location1, location2):
    #print(location1['X'], location1['Y'], location2['X'],location2['Y'])
    #calc euclidean distance between locations. Actual distance will be mix of arcs and radii (larger)
    return math.hypot(float(location1['X']) - float(location2['X']),float(location1['Y']) - float(location2['Y']))
    

def check_valid_location(location1, location2, maximum_distance, max_ring_difference):
    #exclude where pair is same location 
    if location1["Location"] == location2["Location"]:
        return False            
    #exclude where pair are further than max_ring_difference apart (no. of rings apart) 
    if abs(location1["Ring"] - location2["Ring"]) > max_ring_difference:
        return False
    # exclude where pair are more than maximum_distance apart    
    if location_pair_distance(location1,location2) > maximum_distance:
        return False
    return True

def get_ring_locations(locations):
    ring_locations = {}
    for location in locations:
        ring = location["Ring"]
        if ring not in ring_locations:
            ring_locations[ring] = []
        ring_locations[ring].append((location["Slot"], location["Location"]))
    for ring in ring_locations:
        ring_locations[ring].sort()
    return {ring: [location for slot, location in locations] for ring, locations in ring_locations.items() }

def get_blocking_locations(location1,  location2, location_lookup, ring_locations):
    loc1 = location_lookup[location1]
    loc2 = location_lookup[location2]
    # Version 1: only same-ring blocking
    if loc1["Ring"] != loc2["Ring"]:
        return set()
    ring = loc1["Ring"]
    locations = ring_locations[ring]
    index1 = locations.index(location1)
    index2 = locations.index(location2)
    n = len(locations)
    # Travel clockwise from location1 to location2
    clockwise = []
    i = (index1 + 1) % n
    while i != index2:
        clockwise.append(locations[i])
        i = (i + 1) % n
    # Travel anticlockwise from location1 to location2
    anticlockwise = []
    i = (index1 - 1) % n
    while i != index2:
        anticlockwise.append(locations[i])
        i = (i - 1) % n
    # Use blockers on the shorter arc
    if len(clockwise) < len(anticlockwise):
        return set(clockwise)
    if len(anticlockwise) < len(clockwise):
        return set(anticlockwise)
    # Exact tie: either route is possible, so don't
    # impose a blocking direction yet
    return set()

def orientation(p1, p2, p3):
    #Orientation of three XY points.
    #Returns: > 0 : anticlockwise, < 0 : clockwise, = 0 : collinear
    return ((p2["X"] - p1["X"]) * (p3["Y"] - p1["Y"]) - (p2["Y"] - p1["Y"]) * (p3["X"] - p1["X"]))

def location_links_cross(location1a, location2a, location1b, location2b,location_lookup):
    #Return True if the two straight-line location links cross in their interiors.
    #Links sharing an endpoint are not counted as crossings.
    # Shared endpoint: meeting at a station/location is allowed
    if (location1a in {location1b, location2b} or location2a in {location1b, location2b}):
        return False
    p1 = location_lookup[location1a]
    p2 = location_lookup[location2a]
    p3 = location_lookup[location1b]
    p4 = location_lookup[location2b]

    o1 = orientation(p1, p2, p3)
    o2 = orientation(p1, p2, p4)
    o3 = orientation(p3, p4, p1)
    o4 = orientation(p3, p4, p2)

    # Strict crossing only.
    # Collinear/touching cases are not treated as crossings here.
    return (o1 * o2 < 0 and o3 * o4 < 0)

def physical_link(location1, location2):
    return tuple(sorted((location1, location2)))

def link_spans_ring(location1, location2, target_ring, location_lookup):
    #Cheap filter: does the inter-ring link span the arc’s ring?
    ring1 = location_lookup[location1]["Ring"]
    ring2 = location_lookup[location2]["Ring"]
    return (min(ring1, ring2)<= target_ring<= max(ring1, ring2))

def angle_on_short_arc(theta, theta1, theta2):
    #Keep the shortest-arc angle
    two_pi = 2 * math.pi
    theta = theta % two_pi
    theta1 = theta1 % two_pi
    theta2 = theta2 % two_pi
    anticlockwise = (theta2 - theta1) % two_pi
    clockwise = (theta1 - theta2) % two_pi
    if anticlockwise < clockwise:
        distance = (theta - theta1) % two_pi
        return 0 < distance < anticlockwise
    elif clockwise < anticlockwise:
        distance = (theta1 - theta) % two_pi
        return 0 < distance < clockwise
    # Exactly opposite: routing direction ambiguous
    return False

def same_ring_inter_ring_cross(same_location1, same_location2, inter_location1, inter_location2, location_lookup):
    same1 = location_lookup[same_location1]
    same2 = location_lookup[same_location2]
    # Must genuinely be a same-ring link
    if same1["Ring"] != same2["Ring"]:
        return False
    # Shared endpoint is allowed
    if (same_location1 in {inter_location1, inter_location2} or same_location2 in {inter_location1, inter_location2}):
        return False
    target_ring = same1["Ring"]
    # Cheap filter first
    if not link_spans_ring(inter_location1, inter_location2, target_ring, location_lookup):
        return False
    target_radius = same1["Radius"]
    intersection_angles = (segment_ring_intersection_angles(inter_location1, inter_location2, target_radius, location_lookup))
    for theta in intersection_angles:
        if angle_on_short_arc(theta, same1["Theta"], same2["Theta"]):
            return True
    return False

def physical_links_cross(link_a, link_b, location_lookup):
    a1, a2 = link_a
    b1, b2 = link_b
    # Shared endpoint is allowed
    if (a1 in {b1, b2} or a2 in {b1, b2}):
        return False
    ring_a1 = location_lookup[a1]["Ring"]
    ring_a2 = location_lookup[a2]["Ring"]
    ring_b1 = location_lookup[b1]["Ring"]
    ring_b2 = location_lookup[b2]["Ring"]
    a_same_ring = (ring_a1 == ring_a2)
    b_same_ring = (ring_b1 == ring_b2)
    # Both inter-ring:
    # use existing straight-line crossing test
    if not a_same_ring and not b_same_ring:
        return location_links_cross(a1, a2, b1, b2, location_lookup)
    # A same-ring, B inter-ring
    if a_same_ring and not b_same_ring:
        return same_ring_inter_ring_cross(a1, a2, b1, b2, location_lookup)
    # B same-ring, A inter-ring
    if b_same_ring and not a_same_ring:
        return same_ring_inter_ring_cross(b1, b2, a1, a2, location_lookup)
    # Both same-ring:
    # existing blocker logic handles these
    return False

def segment_ring_intersection_angles(location1, location2, target_radius, location_lookup):
    #if the inter-ring link (loc1-loc2) spans the target ring, then the crossing position is where the segment reaches that ring radius.
    p1 = location_lookup[location1]
    p2 = location_lookup[location2]
    x1 = p1["X"]
    y1 = p1["Y"]
    dx = p2["X"] - x1
    dy = p2["Y"] - y1
    a = dx * dx + dy * dy
    b = 2 * (x1 * dx + y1 * dy)
    c = (x1 * x1 + y1 * y1 - target_radius **2)
    discriminant = b * b - 4 * a * c
    if discriminant <= 0:
        return []
    root = math.sqrt(discriminant)
    angles = []
    for t in ((-b - root) / (2 * a), (-b + root) / (2 * a)):
        if 0 < t < 1:
            x = x1 + t * dx
            y = y1 + t * dy
            theta = math.atan2(y, x)
            if theta < 0:
                theta += 2 * math.pi
            angles.append(theta)
    return angles

def canonical_crossing(link_a, link_b):
    return tuple(sorted((tuple(sorted(link_a)), tuple(sorted(link_b)))))

def get_reference_locations(potential_locations):
    #for each ring, find the location with the smallest theta (closest to the horizontal axis)
    by_ring = {}
    for location in potential_locations:
        ring = location["Ring"]
        theta_distance = min(location["Theta"],  2 * math.pi - location["Theta"] )
        if (ring not in by_ring  or theta_distance < by_ring[ring][0] ):
            by_ring[ring] = (theta_distance, location["Location"] )
    return [by_ring[ring][1] for ring in sorted(by_ring)]


############
#def location_pair_distance(location1, location2):
#def check_valid_location(location1, location2, maximum_distance, max_ring_difference):
#def get_ring_locations(locations):
#def get_blocking_locations(location1,  location2, location_lookup, ring_locations):
#def orientation(p1, p2, p3):
#def location_links_cross(location1a, location2a, location1b, location2b,location_lookup):
#def physical_link(location1, location2):
#def link_spans_ring(location1, location2, target_ring, location_lookup):
#def angle_on_short_arc(theta, theta1, theta2):
#def same_ring_inter_ring_cross(same_location1, same_location2, inter_location1, inter_location2, location_lookup):
#def physical_links_cross(link_a, link_b, location_lookup):
#def segment_ring_intersection_angles(location1, location2, target_radius, location_lookup):
#canonical def_crossing(link_a, link_b):

#UNIT TESTING
def test_angle_on_short_arc():
    assert angle_on_short_arc(0.5, 0.0, 1.0)
    assert not angle_on_short_arc(2.0, 0.0, 1.0)

def test_angle_wraparound():
    assert angle_on_short_arc(0.0, 6.0, 0.3)

def geo_unit_tests():
    test_angle_on_short_arc
    test_angle_wraparound
    
    
