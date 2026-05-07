# Area-Based City Walkability Report
**Location:** Pune, Maharashtra

*Note: This report evaluates the 15-Minute City concept by mapping the physical land area (geographic footprint) covered by each score bracket, computed using DuckDB's `ST_Union_Agg` and `ST_Area` functions.*

## 1. Score Distribution by Land Area
Unlike node-counting, which heavily biases areas with dense road intersections, this metric represents the percentage of total mapped urban land that provides a specific level of walkability.

| Score | Walkability Level | Geographic Footprint (%) |
| :---: | :--- | :--- |
| **6** | True 15-Min City | **2.5%** |
| **5** | Good | **4.4%** |
| **4** | Average | **5.9%** |
| **3** | Below Average | **7.6%** |
| **2** | Poor | **8.1%** |
| **1** | Very Poor | **11.9%** |
| **0** | Car Dependent / No Amenities | **59.5%** |

### Key Observations
While node-based metrics suggested that only 1.3% of the city network achieved a Score 6, evaluating by pure land area reveals that **2.5% of Pune's physical footprint** is a True 15-Minute City. This indicates that highly walkable areas have larger, more spread-out catchment zones relative to their road intersection density.

Conversely, "Car Dependent" (Score 0) drops from 81% (node count) to 59.5% (land area), meaning the areas severely lacking in infrastructure feature very dense and tightly-packed street networks that artificially inflated the previous score.
