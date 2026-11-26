import math
import json
import numpy as np
from scipy.special import ellipe


ring_shapes=["Circle","Ellipse", "Rounded_Rectangle", "Pentagram"]

def radian_circle_arc(radius, arclength):
    return arclength/radius
    

def length_circle_perimeter(radius):
	return 2*math.pi*radius

def length_ellipse_perimeter(axisa, axisb):
    """
    Calculates the exact perimeter of an ellipse.
    axisa: semi-major axis
    axisb: semi-minor axis
    """
    # Ensure 'a' is the semi-major axis
    if b > a:
        a, b = b, a
        
    # Calculate eccentricity squared: e^2 = 1 - (b^2 / a^2)
    ecc_squared = 1 - (b**2 / a**2)
    
    # Formula: 4 * a * E(e^2)
    return 4 * a * ellipe(ecc_squared)

def length_pentagram_perimeter(radius: float):
    # A regular pentagram's edge subtends a 144° (4pi/5 rad) angle at the center,
    # leading to a half-angle of 72° for the right triangle components.
    side_length = 2 * radius * math.sin(math.radians(72))
    perimeter = 5 * side_length
    return perimeter

def calculate_ellipse_coordinates(xc, yc, axisa, axisb, num_points=100):
    # t ranges from 0 to 2*pi (360 degrees in radians)
    t = np.linspace(0, 2 * np.pi, num_points)
    
    x = xc + axisa * np.cos(t)
    y = yc + axisb * np.sin(t)
    
    # Return as an array of (x, y) coordinates
    return np.column_stack((x, y))

def calculate_circle_coordinates(xc, yc, radius, num_points=100):
    # t ranges from 0 to 2*pi (360 degrees in radians)
    t = np.linspace(0, 2 * np.pi, num_points)
    
    x = xc + radius * np.cos(t)
    y = yc + radius* np.sin(t)
    
    # Return as an array of (x, y) coordinates
    return np.column_stack((x, y))

def calculate_pentagram_coordinates():
    #To be developed
    return
    
# Example usage:
#coordinates = calculate_ellipse_coordinates(xc=0, yc=0, axisa=5, axisb=3, num_points=10)
#print("Ellipse Coordinates:" coordinates)	

#coordinates = calculate_circle_coordinates(xc=0, yc=0, radius=5, num_points=10)
#print("Circle Coordinates:" coordinates)	

#perimeter=ellipse_perimeter_exact(axisa=5, axisb=3)
#print("Ellipse Perimeter:", perimeter)

#perimeter= length_circle_perimeter(radius=5)
#print("Circle Perimeter:", perimeter)
 
#perimeter= length_pentagram_perimeter(radius=5)
#print(f"Pentagram Perimeter: {perimeter:.4f}")


def Calc_Total_Perimeter(ring_shape, max_rings, interval_space, parametera, parameterb):
    #ring_shape - from ring_shapes list
    #max_rings - no. of concentric shapes
    #interval_space - space between concentric shapes
    #parametera/parameterb - parameters relating to the particular shape    
    Total_Perimeter=0
    for i in range[1,max_rings+1]:
        if ring_shape=="Circle":
            radius=interval_space*(i-1)+parametera        
            Total_Perimeter=Total_Perimeter+length_circle_perimeter(radius)        
        elif ring_shape=="Ellipse":
            axisa=interval_space*(i-1)+parametera
            axisb=interval_space*(i-1)+parameterb        
            Total_Perimeter=Total_Perimeter+ length_ellipse_perimeter(axisa,axisb)
    return Total_Perimeter

def calc_no_stations_in_ring(perimeter, intrastationdistance):
    return max(1, round(perimeter / intrastationdistance))
    
def calc_station_positions_in_ring(radius, ringno, ringstations):
    stationlist = []
    #Stagger rings - if even add offset to angle, if even - no offset
    offsetalpha = 0.5 if ringno % 2 == 0 else 0.0    
     
    for s in range(ringstations):        
        theta=2*math.pi*(s+offsetalpha)/ringstations
        #convert polar to x,y co-ordinates
        x=radius*math.cos(theta)
        y=radius*math.sin(theta)        
        station_details={"Location": f"R{ringno:04d}_S{s:05d}", "Ring": ringno, "Slot": s, "Theta": theta,  "Radius": radius, "ArcSpacing": 2 * math.pi * radius / ringstations, "X":x, "Y":y}
        stationlist.append(station_details)
    return stationlist
    
def output_dict_to_json(fpath, fname, stationlist):
    with open(fpath+fname, "w") as f:
        json.dump(stationlist, f)
        
#No. of rings
 #Space between rings
circle_radius=20;
ellipse_axisa=15
ellipse_axisb=25
Minimum_no_stations=200 #no. of potential station locations across all shapes
intra_station_distance=10 #how far apart on a ring the potential station locations should be
inter_ring_distance = 10 #how far apart the rings (whatever shape) should be

#Redo - make increasingly big rings until exceed minimum_no_stations
potential_stations=0
rings=0
stationslots=[]
ring_shape=ring_shapes[0]
fname="potential_station_locations.json"
stationslots=[]

while potential_stations<Minimum_no_stations:
    rings=rings+1    
    #print("rings: ", rings)
    if ring_shape=="Circle":
        radius=circle_radius+(rings-1)*inter_ring_distance
        perimeter=length_circle_perimeter(radius)
        #calc no. of stations in a ring 
        nstations=calc_no_stations_in_ring(perimeter, intra_station_distance)
        #update no. of potential stations (slots)
        potential_stations=potential_stations+nstations
        #calc actual station positions
        stat=calc_station_positions_in_ring(radius, rings, nstations)
        #print("station positions:", stat)         
        stationslots.extend(stat)
    #print("station rings: ", len(stationslots))
    
#Create metadata + stationslots
stationdata={ "Shape": ring_shape, "TargetSpacing": intra_station_distance, "InterRingDistance": inter_ring_distance, "NoRings": rings, "NoStations":len(stationslots), "Locations": stationslots}    
output_dict_to_json("",fname,stationdata)

#
# 
#for i in range(0,len(stationslots)):
#    print("station rings: ", i+1)
#    print("station slots: ", stationslots[i])

#TP=Calc_Total_Perimeter(ring_shape=ring_shapes[1],max_rings=5,interval_space =10,parametera=circle_radius); 
#Distance_between_stations=TP/Minimum_no_stations
