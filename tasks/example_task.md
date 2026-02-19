# Task: USGS Earthquake Feed Parser & Analyzer

Build a Python CLI tool that fetches, parses, and analyzes real earthquake data from the USGS API.

## Data Source
- URL: `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson`
- Format: GeoJSON (FeatureCollection with nested properties)
- This is live data — results will vary on each run

## Features Required
1. Fetch the monthly earthquake feed and parse it into clean, structured data
2. Display a summary table: total events, magnitude range, date range, geographic spread
3. Filter events by: minimum magnitude, date range, geographic region (bounding box), event type
4. Show a "Top 10 strongest quakes this month" table with: time (local + UTC), location, magnitude, depth, felt reports, tsunami alert status
5. Generate magnitude distribution stats: count by magnitude bracket (0-1, 1-2, 2-3, etc.)
6. Export filtered results to CSV with clean column headers
7. Display a text-based geographic summary grouping events by region/country

## Technical Requirements
- Use `httpx` for async HTTP fetching
- Use Click for the CLI framework
- Use Rich for terminal output (tables, panels, progress bars during fetch)
- Use Pydantic models for the parsed earthquake data
- Handle ALL edge cases in the real data (this is the core challenge — see below)

## Known Data Quirks (the agent must discover and handle these)
The USGS feed has many non-obvious data issues. The agent should discover these
through careful data exploration and handle them robustly. Do NOT assume the data
is clean or consistent. Parse defensively.

Some things to watch out for:
- Not all numeric fields are always present or always numeric
- Geographic coordinates may not be in the format you expect
- Timestamps may not be in the units you expect
- The `type` field may contain surprises beyond just "earthquake"
- The `place` field format is inconsistent
- Some magnitude and depth values may seem physically impossible but are valid

## Example Usage
    quake-analyzer fetch                          # Fetch and display summary
    quake-analyzer top --count 10                 # Top 10 strongest
    quake-analyzer filter --min-mag 4.0           # Filter by magnitude
    quake-analyzer filter --type "quarry blast"   # Filter by event type
    quake-analyzer stats                          # Magnitude distribution
    quake-analyzer export --output quakes.csv     # Export to CSV
    quake-analyzer regions                        # Geographic summary

## Quality Bar
- The tool should handle network errors, malformed data, and missing fields gracefully
- Rich tables should be well-formatted with proper alignment and color coding
- Magnitude color coding: 5+ red, 3-5 yellow, below 3 green
- Timestamps must display correctly in human-readable format
- Include at least 3 tests using pytest (test parsing, filtering, edge cases)
- The parser must not crash on ANY valid USGS feed data
