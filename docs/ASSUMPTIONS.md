# Assumption register

Values in the current implementation remain current until the contract-0.3
models integrate. Release values must come from versioned factor artifacts; no
documentation value may silently become a model default.

| Assumption family | Current behavior | Contract-0.3 release requirement |
| --- | --- | --- |
| Match attendance | Generic venue-capacity/event multipliers | Per-match low/base/high editable range; never observed attendance |
| Arrival/departure profile | Generic event uplift | Hourly profile anchored to local kickoff and reconciled to attendance |
| Commercial baseline | 2022–2024 Rice activity with 2023/2024 holdouts | Retain comparator results and planning-scenario language unless both pass |
| Transit capacity | Legacy values are unavailable in strict mode | Mode-capacity low/base/high × event-valid departures; not ridership |
| Walking distance | Venue-centered straight-line context | Pinned network distance plus detour ratio and tag coverage |
| Shuttle/additional service | Generic bus capacity and uptake | Vehicle capacity, utilization, VMT, emissions, and cost ranges |
| Park-and-ride | Generic spaces and displaced trips | Preserve upstream drive VMT; count only venue-area displacement |
| Bike/micromobility | Generic station capacity | Distance-limited, demand-capped uptake and explicit operating assumptions |
| Pedestrian/cooling | Cost can change without a modeled benefit | Must change heat/walking outcome or remain absent from release controls |
| Arrival spreading | Not separately modeled | Shift peak demand to shoulders; no direct emissions credit |
| Vehicle emissions | Editable generic factor | Pinned EPA low/base/high registry with units and year |
| Operating/capital cost | Generic model constants | Pinned FTA NTD/Capital Cost Database and FHWA/PBIC ranges with cost year |
| Combined Rice markets | Equal allocation | Remain partial; sensitivity or better city evidence required for stronger claim |
| MRS | Headline supplied-data lens can exclude transit | Secondary index with rank sensitivity; transportation profiles require transit |

All assumptions are scenarios unless their evidence status says otherwise.
Planning cost ranges are not bids, and national factors are not local inventories.
