# **L10n Country Filter**

<img src="static/description/banner.png" width="100%" alt="Banner">

A technical utility module for Odoo Localization development. It provides a standardized mechanism to dynamically hide XML fields and groups in views based on the company's current country configuration.

This module is essential for multi-company/multi-country environments where using a single form view for diverse regions (e.g., Peru and USA) results in cluttered interfaces full of irrelevant fields.

## Features

-   **Dynamic Hiding**: Automatically hides fields that do not belong to the active company's country.
-   **View Support**: Handles `invisible="1"` for Form/Kanban views and `column_invisible="True"` for Tree/List views (Odoo 19+).
-   **Multi-Company Cache**: Ensures view caching is segmented by company, preventing UI pollution when switching contexts.

## Usage (For Developers)

This module adds the `_tags_invisible_per_country` method to all models (via `Base`). You can use it in your model's `_get_view` method to clean up the interface.

 **Example Implementation:**

```python
```python
class ResPartner(models.Model):
    _inherit = ['res.partner', 'l10n.country.filter.mixin'] # Inherit Mixin for Cache

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)

        # Define fields to hide if Country is NOT Peru
        arch, view = self._tags_invisible_per_country(
            arch, view, view_type,
            tags=[
                'l10n_pe_vat_code', 
                ('group', 'l10n_pe_group_extended')
            ],
            countries=[self.env.ref('base.pe')]
        )
        return arch, view
```

### Important: The Mixin
You **MUST** inherit `l10n.country.filter.mixin` in your model. This mixin handles the **View Cache Segmentation** by Company. Without it, field visibility changes won't update correctly when switching companies.

### Critical Considerations
-   **Server-Side RAM Usage**: This module optimizes memory on the **Odoo Server** (not the client browser). By using the Mixin, you prevent the server from storing redundant view caches for every company, which is critical for performance in multi-company environments. (cache poisoning).

### Arguments:
-   **arch**: The XML architecture.
-   **view**: The view object.
-   **view_type**: Type of view ('form', 'tree', 'list', etc.).
-   **tags**: List of field names (strings) or (tag, name) tuples (e.g., `('group', 'name')`).
-   **countries**: List of `res.country` records where these fields SHOULD be visible.

## Installation

This module is a technical dependency. Installing it alone does not change the UI unless other modules utilize its API.

## Credits

**Author**: [Ganemo](https://www.ganemo.com)
