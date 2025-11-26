# Partner Current Location

## Overview

This module allows users to capture partner (contact) geolocation coordinates directly from the device's GPS/location instead of relying on address geocoding. This is particularly useful for field service teams who need accurate coordinates when visiting clients on-site.

## Features

- **Device GPS Integration**: Capture real-time coordinates from the user's device.
- **One-Click Location Update**: Simple button interface to update partner coordinates.
- **Accurate Positioning**: Get precise latitude/longitude without address-based approximations.
- **Browser-Based**: Works directly in the web interface using browser geolocation API.

## Configuration

No special configuration is required. The module extends the standard Partner form view.

## Usage

1. Navigate to **Contacts** and open a partner record.
2. Click the **"Get Current Location"** button (visible in the partner form).
3. Allow browser location access when prompted.
4. The partner's latitude and longitude fields will be automatically updated with your current device coordinates.

## Use Cases

- **Field Service**: Technicians can update client coordinates while on-site.
- **Sales Visits**: Sales representatives can mark exact visit locations.
- **Delivery Services**: Drivers can record precise delivery addresses.
- **Event Management**: Capture exact event venue coordinates.

## Technical Details

### Dependencies

- `base`
- `contacts`
- `base_geolocalize`
- `web`

### Models Extended

- `res.partner`: No new fields added; uses existing `partner_latitude` and `partner_longitude` from `base_geolocalize`.

### JavaScript Components

- `partner_location_action.js`: Implements browser geolocation API integration and coordinate update logic.

## Credits

### Authors

- Ganemo

### Maintainer

This module is maintained by Ganemo.

For support and more information, please visit [https://www.ganemo.co](https://www.ganemo.co)
