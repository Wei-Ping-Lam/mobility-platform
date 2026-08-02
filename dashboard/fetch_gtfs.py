"""Compatibility entrypoint for the pinned GTFS pipeline."""

from dashboard.pipeline.gtfs.fetch import main

if __name__ == "__main__":
    main()
