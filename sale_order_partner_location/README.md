# Sale Order Partner Location

## Overview

This module enhances Odoo's Sales functionality by capturing geolocation coordinates when creating or confirming sales orders. It enables sales teams to track where deals are being closed, update customer locations on-site, and maintain accurate geographic data for sales analytics and territory management.

## Features

- **Device GPS Integration**: Capture real-time coordinates from the user's device when creating/confirming sales orders.
- **Partner Location Update**: Update customer coordinates directly from the sales order form.
- **Auto-Capture on Confirmation**: Automatically capture location when confirming a sales order (configurable per team).
- **Google Maps Integration**: View captured locations directly on Google Maps.
- **Team-Level Configuration**: Enable/disable auto-capture functionality per Sales Team.
- **Manual Location Capture**: Button to manually capture location at any time during the sales process.

## Configuration

### Sales Team Setup

1. Navigate to **Sales > Configuration > Sales Teams**.
2. Select or create a Sales Team.
3. Enable the **"Auto-capture Location on Confirm"** checkbox to automatically capture location when confirming orders.

### Usage Permissions

No special permissions required beyond standard sales user access.

## Usage

### Manual Location Capture

1. Open a Sales Order (Quotation or confirmed).
2. Click the **"Update Partner Location"** button in the order form.
3. Allow browser location access when prompted.
4. The partner's latitude and longitude will be updated with your current device coordinates.

### Automatic Location Capture

1. Create a Sales Order with a team that has auto-capture enabled.
2. Confirm the order.
3. The system automatically captures and stores the current device location.
4. Location is linked to both the partner and the sale order.

### View Location on Map

1. Open a Sales Order with captured location data.
2. Click the **"View on Google Maps"** button.
3. The location opens in a new browser tab showing the exact coordinates.

## Use Cases

- **Field Sales**: Sales representatives can capture exact meeting locations when closing deals on-site.
- **Territory Management**: Track where sales are happening geographically for territory optimization.
- **Customer Visits**: Record precise customer locations during site visits for better service planning.
- **Sales Analytics**: Analyze sales performance by geographic region with accurate location data.
- **Delivery Planning**: Accurate customer coordinates improve delivery route optimization.

## Technical Details

### Dependencies

- `base`
- `sale`
- `sale_management`
- `partner_current_location`

### Models Extended

- `crm.team`: Added `auto_capture_location` boolean field.
- `sale.order`: Added location capture logic and Google Maps integration.
- `res.partner`: Uses existing geolocation fields from `partner_current_location` module.

### JavaScript Components

- `sale_location_action.js`: Implements browser geolocation API integration for sales orders.

### Workflow

1. User clicks "Update Partner Location" or confirms order with auto-capture enabled.
2. JavaScript requests device location via browser geolocation API.
3. Coordinates are sent to backend and stored on partner record.
4. Location data is available for reporting and mapping.

## Credits

### Authors

- Ganemo

### Maintainer

This module is maintained by Ganemo.

For support and more information, please visit [https://www.ganemo.co](https://www.ganemo.co)
