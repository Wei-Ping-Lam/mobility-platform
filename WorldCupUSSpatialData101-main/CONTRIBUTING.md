# Contributing

Thanks for helping keep this catalog useful.

## What to Add

- Official government, transit-agency, university, or regional-planning data portals.
- Dataset pages with stable URLs, clear licensing, and downloadable files or services.
- Notes about useful themes: transit, safety, public health, environment, housing, accessibility, infrastructure, imagery, parcels, boundaries, and emergency planning.

## What to Avoid

- Scraped copies of public portals when the source can be linked directly.
- Personal data, sensitive operational details, or restricted security information.
- Links that require private credentials unless the access requirement is clearly noted.

## Source Entry Format

For `data/sources.csv`, include:

- `host_city`: one of the 11 host-city names, or `National`.
- `source_name`: the public name of the portal or source.
- `scale`: municipal, county, regional, state, transit, national, or global.
- `theme`: short topic tags.
- `url`: stable source URL.
- `notes`: one sentence about why the source is useful.

Before submitting a change, check that the link opens in a normal browser and record the access date in your pull request description.
