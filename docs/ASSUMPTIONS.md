# Assumption register

| Assumption | Default | Treatment |
| --- | --- | --- |
| Balanced MRS weights | 35/20/15/30 | Named profile; user can select another profile or custom weights |
| Peak venue visitors | 95% of listed venue capacity | Transparent planning assumption; not measured attendance |
| Demand event range | 1.5x / 3.0x / 4.5x baseline | Low/base/high scenario, not a confidence interval |
| Combined source markets | Equal allocation to each named city | Partial evidence; no city-specific inference is claimed |
| Shuttle capacity | 50 passengers per bus | Editable in `ScenarioConfig` |
| Shuttle uptake | 70% | Editable scenario assumption |
| Average vehicle occupancy | 2.2 people | Editable scenario assumption |
| Average trip distance | 25 km round trip | Editable scenario assumption |
| Vehicle emissions factor | 0.21 kg CO2e/km | Editable scenario assumption; not a measured fleet inventory |
| Commercial uplift range | 2% / 5% / 10% | Economic-activity scenario, not causal attribution |

Scenario outputs are physically constrained to nonnegative capacity, costs,
vehicle-kilometers, and emissions. Traffic outputs are pressure proxies and do
not measure roadway congestion, queues, reliability, or actual mode choice.

