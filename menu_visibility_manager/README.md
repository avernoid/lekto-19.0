# Menu Visibility Manager

**Hide specific menu items for selected users.**

This module empowers administrators to fine-tune menu access rights with ease. You can hide specific menus for individual users or exclude users from specific menus directly from the menu configuration. This bi-directional synchronization ensures easy management and robust security, allowing you to declutter the interface for users and restrict access to sensitive areas without complex group configurations.

## Features

*   **Hide Menus per User**: Select specific menus to hide directly from the User form.
*   **Exclude Users per Menu**: Select specific users to exclude directly from the Menu form.
*   **Bi-directional Synchronization**: Changes in the User form are automatically reflected in the Menu form, and vice versa.
*   **Auto-Cleanup**: If a user loses "Internal User" status, their hidden menu settings are automatically cleared to prevent data inconsistency.
*   **Superuser Protection**: Administrators and Superusers always retain full access, preventing accidental lockouts.

## Installation

1.  Install the module normally from the Odoo Apps menu.
2.  No external dependencies are required.

## Configuration

You can configure visibility in two ways:

### Method 1: From the User Form
1.  Go to **Settings > Users & Companies > Users**.
2.  Open the user you want to restrict.
3.  Navigate to the **Hidden Menus** tab.
4.  Add the menu items you want to hide for this user.

### Method 2: From the Menu Form
1.  Go to **Settings > Technical > User Interface > Menu Items**.
2.  Open the menu item you want to restrict.
3.  Navigate to the **Excluded Users** tab.
4.  Add the users you want to exclude from this menu.

**Note**: Changes are automatically synchronized between both views.

## Usage

Once configured, the effect is immediate:
*   The restricted user will no longer see the hidden menus upon their next page refresh or login.
*   If you remove the restriction (from either the User or Menu form), the menu will become visible again immediately.

## Known Issues / Roadmap

*   This module hides menus from the UI but does not strictly enforce access control rules (ACLs) on the underlying models. It is intended for UI decluttering and basic access restriction, not as a replacement for strict Record Rules or Access Rights.

## Bug Tracker

Bugs are tracked on GitHub Issues. In case of trouble, please check there if your issue has already been reported.

## Credits

### Authors

*   Ganemo

### Maintainers

This module is maintained by Ganemo.

For more information, please visit https://www.ganemo.co
