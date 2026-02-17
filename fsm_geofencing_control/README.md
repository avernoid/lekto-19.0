# FSM Geofencing Control

Control technician location when starting and stopping Field Service Management timers in Odoo 19.

## Features

- **Distance Validation on Start**: Prevent technicians from starting timers when too far from customer location
- **Distance Validation on Stop**: Prevent technicians from stopping timers when too far from customer location
- **Lost Reason Integration**: Require lost reason when stopping timer without a confirmed sale order
- **Auto Mark Done**: Automatically mark tasks as done when logging time
- **Location Tracking**: Track last known technician location on tasks
- **Seamless Integration**: Works with Odoo's native geolocation features

## Requirements

- Odoo 19.0
- `industry_fsm` module
- `fsm_sale_lost_reason` module
- `base_geolocalize` module

## Installation

1. Copy the module to your Odoo addons directory
2. Update the apps list: `Settings > Apps > Update Apps List`
3. Search for "FSM Geofencing Control"
4. Click Install

## Configuration

### Project Settings

Navigate to **Field Service > Configuration > Projects** and select your FSM project:

1. **Geolocation**: Enable to track technician location (required for geofencing)
2. **Control Distance on Start**: Enable to validate distance when starting timer
3. **Control Distance on Stop**: Enable to validate distance when stopping timer
4. **Allowed Distance (km)**: Set maximum allowed distance from customer (default: 1.0 km)
5. **Auto Mark Done**: Enable to automatically mark tasks as done when logging time
6. **Use Lost Reason**: Enable to require lost reason when no sale order is confirmed

### Customer Settings

Ensure customers have valid geolocation:

1. Navigate to **Contacts** and select a customer
2. Set complete address (street, city, country)
3. Click **Geo Localize** button to get coordinates
4. Verify latitude and longitude are not 0

## Usage

### Starting Timer

1. Open an FSM task
2. Click **Start** button
3. Browser will request location permission
4. If distance control is enabled:
   - System validates distance from customer
   - If within allowed distance: timer starts
   - If outside allowed distance: error message shows actual distance

### Stopping Timer

1. Click **Stop** button on running timer
2. Wizard opens with time details
3. If distance control is enabled:
   - System validates distance from customer
4. If lost reason is required and no confirmed sale:
   - Select a lost reason from dropdown
5. Click **Log Time**
6. If auto-mark done is enabled:
   - Task automatically moves to "Done" state

## Error Messages

### Distance Validation Errors

**"Cannot start timer: You are too far from the customer location"**
- Your distance exceeds the allowed distance
- Move closer to customer location
- Check allowed distance setting in project

**"Cannot start/stop timer: Customer does not have a valid geolocation"**
- Customer address is not geolocated
- Set customer address and click "Geo Localize"

**"Cannot start/stop timer: Unable to get your current location"**
- Browser location services are disabled
- Enable location services in browser settings
- Grant location permission when prompted

### Lost Reason Errors

**"Lost Reason is required when stopping timer without a confirmed sale order"**
- No confirmed sale order exists for this task
- Select a lost reason from the dropdown
- Or create a confirmed sale order first

## Technical Details

### Distance Calculation

Uses the Haversine formula to calculate great-circle distances between GPS coordinates:

```python
distance = calculate_distance(lat1, lon1, lat2, lon2)  # Returns km
```

Accuracy: ~0.5% for distances up to 500km

### Location Storage

Last known coordinates are stored in task fields:
- `last_latitude`: Last recorded latitude
- `last_longitude`: Last recorded longitude

These fields are updated on both Start and Stop actions when geolocation is captured.

### Validation Flow

**Start Timer:**
1. JavaScript captures geolocation
2. Sends to server in context
3. Python validates distance
4. Raises UserError if validation fails
5. Stores coordinates in task
6. Continues normal timer flow

**Stop Timer:**
1. JavaScript captures geolocation
2. Wizard validates distance
3. Wizard validates lost reason requirement
4. Saves timesheet
5. Auto-marks task as done (if enabled)

## Troubleshooting

### Location Permission Issues

**Problem**: Browser doesn't request location permission

**Solution**:
- Check browser location settings
- Ensure site is served over HTTPS
- Clear browser cache and reload

### Distance Always Fails

**Problem**: Distance validation always fails even when close

**Solution**:
- Verify customer geolocation is correct
- Check allowed distance setting (may be too small)
- Test with larger allowed distance (e.g., 5 km)
- Verify GPS accuracy on device

### Lost Reason Not Showing

**Problem**: Lost reason field doesn't appear in wizard

**Solution**:
- Enable "Use Lost Reason" in project settings
- Ensure no confirmed sale order exists on task
- Check module `fsm_sale_lost_reason` is installed

## Development

### Running Tests

```bash
# Run all tests
python odoo-bin -c odoo.conf -u fsm_geofencing_control --test-enable --stop-after-init

# Run specific test file
python odoo-bin -c odoo.conf -u fsm_geofencing_control --test-enable --stop-after-init --test-tags /test_geofencing_distance
```

### Debug Mode

Enable developer mode to see debug fields:
1. Settings > Activate Developer Mode
2. Open FSM task
3. Navigate to "Geofencing Debug" tab
4. View `last_latitude` and `last_longitude` values

## Support

For issues, questions, or feature requests:
- **Website**: https://www.ganemo.co
- **Author**: Ganemo

## License

OPL-1 (Odoo Proprietary License v1.0)

## Credits

**Author**: Ganemo  
**Maintainer**: Ganemo
