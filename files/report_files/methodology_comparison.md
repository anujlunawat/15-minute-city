# Analytical Approaches to Urban Walkability

When auditing a city against the 15-Minute City framework, the methodology used to calculate percentages drastically alters the narrative. 

## 1. Node-Based vs. Area-Based Evaluation

| Feature | Node-Based Analysis (Current Default) | Area-Based Analysis (ST_Union) |
| :--- | :--- | :--- |
| **How it works** | Counts the number of street intersections (`nodes`) belonging to a score bracket. | Merges all isochrone polygons belonging to a score and calculates the total square meters/degrees. |
| **Bias** | Heavily biased toward areas with dense, complex road networks. A tiny neighborhood with 1,000 tiny alleys will dominate the statistics. | Better represents physical land, but isochrones spanning different scores overlap, leading to slight double-counting at the boundaries. |
| **Best used for** | Understanding the "network scale" and routing efficiency. | Understanding the actual geographic footprint of infrastructure. |

---

## 2. Better Approaches for Urban Planning

To generate truly actionable insights for city planners, neither pure node-counting nor raw area aggregation is perfect. Here are the gold-standard approaches you could implement in the future:

### A. Population-Weighted Accessibility (The Gold Standard)
**The Concept:** Instead of asking "What percentage of the *land* is a 15-minute city?", ask **"What percentage of the *population* lives in a 15-minute city?"**
**How to build it:** 
1. Ingest Census Block shapefiles containing population counts.
2. Use DuckDB to intersect your Score 6 isochrones with the census blocks.
3. Calculate the population inside the overlaps. 
**Why it's better:** An industrial zone covering 20% of the city land area (Score 0) will heavily drag down area-based scores, even though nobody lives there. Population-weighting ignores empty land.

### B. Equal-Area Grid Aggregation (e.g., Uber H3 Hexagons)
**The Concept:** The city is divided into uniform hexagons (like a honeycomb) of equal size. Each hexagon gets a walkability score based on the isochrones falling inside it.
**How to build it:** 
1. Generate an H3 grid over Pune.
2. Assign each hex cell the maximum or average score of the nodes within it.
**Why it's better:** It eliminates all biases. It doesn't matter if the road network is dense or sparse; every hexagon is exactly the same size, resulting in perfectly uniform and statistically sound city coverage percentages.

### C. Pedestrian Infrastructure (Street Length)
**The Concept:** Rather than nodes or polygon areas, calculate the total linear kilometers of walkable roads.
**How to build it:** 
1. Join the score data back to the actual OpenStreetMap LineStrings (road segments).
2. Sum `ST_Length(geom)`.
**Why it's better:** "500 kilometers of Pune's streets are highly walkable" is a very tangible metric for a transportation department focusing on sidewalk maintenance and street lighting.

### D. Qualitative Amenity Weighting
**The Concept:** Right now, a tiny corner convenience store carries the same weight as a massive supermarket. A small patch of grass is equal to a 50-acre central park.
**How to build it:** 
1. Pull the `building_area` or `capacity` tags from OSM data.
2. Scale the node score based on the *quality/size* of the amenities reachable within 15 minutes, not just their binary presence.
