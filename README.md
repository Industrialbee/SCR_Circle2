# SCR_Circle2
An experimental Python project to create a schematic map of the **Stepford County Railway (SCR)** network using **mixed-integer linear programming (MILP)**.

The aim is to separate **network layout optimisation** from **visualisation**. Rather than allowing the plotting code to decide how stations and lines should be arranged, the project will use an optimisation model to choose station locations on a set of predefined concentric rings.

## Current approach

The initial version will:

- generate a set of potential station locations on concentric circular rings
- keep potential locations approximately equally spaced along each ring
- assign stations to those locations using **Pyomo**
- solve the optimisation model using **HiGHS**
- initially test the approach using a single SCR operator
- later extend the model to include multiple operators and explicit track routing

The eventual objective is to produce a clean circuit-style schematic in which station placement and routing are determined by explicit constraints and optimisation criteria rather than ad-hoc plotting rules.

## Project status

Early development.

Current work:
- potential station location generator
- initial station-location MILP formulation

Planned later stages:
- adjacency and track-length objectives
- ring and spacing constraints
- multi-operator layouts
- track routing
- Matplotlib visualisation
- Alternative shapes (currently circle only, but could extend to ellipses etc.)
