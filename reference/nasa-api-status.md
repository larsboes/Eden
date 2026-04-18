# NASA API Status (tested 2026-03-18)

API Key: `YOUR_NASA_API_KEY`

## Working

### InSight Mars Weather
- **Endpoint**: `https://api.nasa.gov/insight_weather/?api_key=KEY&feedtype=json&ver=1.0`
- **Status**: Live but data frozen at Sol 675-681 (Oct 2020). InSight mission ended Dec 2022.
- **Data**: Temperature (avg -62°C, range -97 to -16°C), pressure (~750 Pa), wind (avg 7-8 m/s, max 27 m/s), wind direction, season
- **Also available without key**: `https://mars.nasa.gov/rss/api/?feed=weather&category=insight_temperature&feedtype=json&ver=1.0`

### DONKI — Magnetopause Crossings (Mars)
- **Endpoint**: `https://api.nasa.gov/DONKI/MPC?startDate=2026-01-01&endDate=2026-03-18&api_key=KEY`
- **Status**: Live — 3 events in 2026 so far, linked to CME events
- **Data**: Event time, instruments, linked CME activity IDs

### DONKI — Coronal Mass Ejections
- **Endpoint**: `https://api.nasa.gov/DONKI/CME?startDate=2026-03-01&endDate=2026-03-18&api_key=KEY`
- **Status**: Live — multiple events with analysis data
- **Data**: Start time, source location, speed, half-angle, type

### NASA Image & Video Library (no key needed)
- **Endpoint**: `https://images-api.nasa.gov/search?q=mars&media_type=image`
- **Status**: Live — 26,371 Mars images
- **Data**: Image metadata, thumbnails, center, NASA ID, descriptions

### JPL SSD Close Approaches (no key needed)
- **Endpoint**: `https://ssd-api.jpl.nasa.gov/cad.api?body=Mars&date-min=2025-01-01&date-max=2027-01-01`
- **Status**: Live — 96 asteroid close approaches to Mars
- **Data**: Object name, date, distance (au), velocity

### APOD
- **Endpoint**: `https://api.nasa.gov/planetary/apod?api_key=KEY`
- **Status**: Live — Mars content appears randomly
- **Data**: Daily astronomy image with explanation. Use `count=N` for bulk random pulls.

### Techport
- **Endpoint**: `https://api.nasa.gov/techport/api/projects/search?api_key=KEY&titleSearch=mars`
- **Status**: Live — NASA R&D projects related to Mars

### EPIC (Earth imagery, not Mars-specific)
- **Endpoint**: `https://api.nasa.gov/EPIC/api/natural?api_key=KEY`
- **Status**: Live

## Dead / Not Working

### Mars Rover Photos
- **Endpoint**: `https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos?sol=1000&api_key=KEY`
- **Status**: 404 "No such app" — backend Heroku app appears decommissioned
- **All formats tested**: `/rovers`, `/rovers/curiosity/photos`, `/rovers/perseverance/latest_photos`, `/manifests/Curiosity`
- **Heroku fallback also dead**: `mars-photos.herokuapp.com`
- **Both DEMO_KEY and personal key return 404**

### NASA POWER
- **Endpoint**: `https://api.nasa.gov/POWER/` — not tested in depth

### Mars Trek WMS
- **Endpoint**: `https://api.nasa.gov/mars-wmts/catalog?api_key=KEY`
- **Status**: 404
