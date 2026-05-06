# City Analytics Data Tables

*Note: These values have been computed directly from the local DuckDB spatial database (`accessibility.duckdb`).*

### 1. Overall Metric
| Metric | Value |
| :--- | :--- |
| **Average Walkability Score** | 0.49 (Scale: 0 to 6) |
| **Total Analyzed Nodes** | 57,513 |

---

### 2. Score Distribution
*Percentage of locations falling into each score bracket.*

| Score | Walkability Level | Percentage of City (%) |
| :---: | :--- | :--- |
| **6** | True 15-Min City | 1.3% |
| **5** | Good | 1.7% |
| **4** | Average | 2.4% |
| **3** | Below Average | 2.9% |
| **2** | Poor | 3.6% |
| **1** | Very Poor | 7.0% |
| **0** | Car Dependent / No Amenities | 81.0% |

---

### 3. Amenity Coverage
*Percentage of the city's 15-minute walkable zones that have access to at least one of the following amenities.*

| Amenity Category | City Coverage (%) |
| :--- | :--- |
| Healthcare | 14.0% |
| Park | 8.7% |
| Public Transport | 8.4% |
| School | 7.1% |
| Grocery | 6.9% |
| Pharmacy | 4.0% |
