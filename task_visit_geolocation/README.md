# Task Visit Geolocation

## Overview

This module allows Field Service technicians to register their visits with geolocation verification. It ensures that the technician is physically present at the customer's location before they can mark a task as done.

## Features

- **Geolocation Verification**: Captures the technician's current GPS coordinates when clicking "Registrar visita".
- **Distance Validation**: Calculates the distance between the technician and the customer's registered address.
- **Configurable Radius**: Allows setting a maximum allowed distance (in meters) per project.
- **Lost Reason Integration**: Seamlessly integrates with `fsm_sale_lost_reason` to require a lost reason if the task is completed without a sale.

## Configuration

1. Navigate to **Field Service > Configuration > Projects**.
2. Select a project.
3. Enable **Registrar visita con Geolocalización**.
4. Set the **Distancia máxima permitida (m)** (default is 100m).

## Usage

1. Open a Field Service task assigned to a customer with a valid address (and geolocation).
2. Click the **Registrar visita** button.
3. The system will request browser geolocation permissions.
4. If the technician is within the allowed range:
    - The visit is registered in the chatter with coordinates and distance.
    - If `fsm_sale_lost_reason` is enabled and applicable, a wizard will prompt for a lost reason.
    - Otherwise, the task is marked as **Done**.
5. If the technician is too far, an error message is displayed, and the task remains open.

## Technical Details

### Dependencies

- `base`
- `project`
- `fsm_sale_lost_reason`
- `web`

### Models Extended

- `project.project`: Added `register_geo_visit` and `max_distance_m` fields.
- `project.task`: Added `last_latitude`, `last_longitude`, and `register_geo_visit` fields.

## Credits

### Authors

- Ganemo

### Maintainer

This module is maintained by Ganemo.

For support and more information, please visit [https://www.ganemo.co](https://www.ganemo.co)
