from datetime import datetime, timedelta

import requests
import re
import logging
from odoo.exceptions import UserError
from odoo import fields, _, models
from pytz import timezone, UTC
from collections import defaultdict

from ..utils.credentials_manager import encrypt_credential, decrypt_credential

_logger = logging.getLogger(__name__)


class MobilvendorAPIHandler:
    def __init__(self, company, env):
        self.base_url = company.mobilvendor_api_url
        self.mobilvendor_api_session_id = company.mobilvendor_api_session_id
        self.mobilvendor_api_password = company.mobilvendor_api_password
        self.mobilvendor_api_context = company.mobilvendor_api_context
        self.mobilvendor_api_username = company.mobilvendor_api_username
        self.mobilvendor_api_conciliate_credit_notes = company.mobilvendor_api_conciliate_credit_notes
        self.company = company
        self.mobilvendor_sync_days = company.mobilvendor_api_days_sync if company.mobilvendor_api_days_sync and company.mobilvendor_api_days_sync > 0 else 3
        self.env = env

    def _get_decrypted_password(self):
        """Retrieve the decrypted password for API usage."""
        if self.mobilvendor_api_password:
            return decrypt_credential(self.mobilvendor_api_password)
        return ''

    def _get_decrypted_session_id(self):
        """Retrieve the decrypted password for API usage."""
        if self.mobilvendor_api_session_id:
            return decrypt_credential(self.mobilvendor_api_session_id)
        return ''

    def _store_session_id(self, session_id):
        """Store the session ID securely."""
        encrypted_session_id = encrypt_credential(session_id)
        self.company.write({'mobilvendor_api_session_id': encrypted_session_id})
        self.mobilvendor_api_session_id = encrypted_session_id

    def _parse_request(self, schema="", records=[], action="put", webservice=False, process_status="", status=""):
        """
        Splits the records into batches and sends them to the API to avoid payload limits.

        This method iterates through the provided records list, creates chunks of a defined size,
        and calls the `_send_post_request` method for each batch.

        :param schema: The API schema name (e.g., 'products', 'customers').
        :param records: List of dictionaries containing the data to synchronize.
        :param action: The specific API action to perform (default is 'put').
        :param webservice: Boolean flag to indicate if a webservice endpoint is used.
        :param process_status: internal process status flag for the API.
        :param status: Status value to be sent in the request.
        """
        # Define the batch size limit to prevent server timeouts
        chunk_size = 200
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            _logger.debug(f"Sending {schema} chunk {i // chunk_size + 1} with {len(chunk)} items.")

            # Verify that the sending method exists in the current context
            if hasattr(self, '_send_post_request'):
                try:
                    # Transmit the current chunk to the API
                    self._send_post_request(schema=schema, records=chunk, action=action, webservice=webservice,
                                            process_status=process_status, status=status)
                except Exception as e:
                    _logger.error(f"Error sending chunk {i // chunk_size + 1}: {str(e)}")
                    raise e  # Propagate exception to stop the synchronization process
            else:
                _logger.error(f"'_send_post_request' method not found in {self.__class__.__name__}.")
                break  # Stop loop if dependency method is missing

    def _send_post_request(self, schema="", records=[], retry=True, action="put", webservice=False,
                           process_status="", status=""):
        """
        Sends a POST request to the Mobilvendor API with the provided data payload.

        This method handles credential verification, payload construction, and automatic
        re-authentication if the session has expired during the request.

        :param schema: The entity schema name (e.g., 'products').
        :param records: List of data dictionaries to be sent.
        :param retry: Boolean flag to allow one retry attempt on authentication failure.
        :param action: The API action to perform (default: 'put').
        :param webservice: Optional specific webservice endpoint.
        :param process_status: Optional process status flag.
        :param status: Optional status value.
        """
        # Verify that necessary credentials exist before initiating the request
        if not self.mobilvendor_api_session_id:
            if not self.mobilvendor_api_username:
                raise UserError(f"Invalid username for Mobilvendor API")
            if not self.mobilvendor_api_password:
                raise UserError(f"Invalid password for Mobilvendor API")
            if not self.mobilvendor_api_context:
                raise UserError(f"Invalid context for Mobilvendor API")

            # Attempt automatic login if session ID is missing but credentials are present
            self._mobilvendor_login()

        url = self.base_url
        payload = {
            "session_id": self._get_decrypted_session_id(),
            "action": action
        }

        if schema:
            payload["schema"] = schema

        if records:
            payload["records"] = records

        if webservice:
            payload["webservice"] = webservice

        if process_status:
            payload["process_status"] = process_status

        if status:
            payload["status"] = status

        try:
            # Execute the HTTP POST request
            response = requests.post(url, json=payload)

            # Validate the HTTP status code
            if response.status_code == 200:
                # Request was successful (HTTP 200)
                response_data = response.json()  # Get the JSON response

                if "error" in response_data:
                    error_msg = response_data.get("error")
                    if ("session_id" in error_msg or "Not authorized" in error_msg) and retry:
                        # Handle session expiration: Re-authenticate and retry the request once
                        _logger.debug(f"Invalid session id, trying to login again")
                        self._mobilvendor_login()
                        self._send_post_request(schema=schema, records=records, retry=False, action=action,
                                                webservice=webservice, process_status=process_status, status=status)
                    else:
                        raise UserError(f"Post {schema} unsuccessful, {error_msg}")

            else:
                # Handle non-200 HTTP status codes
                raise UserError(f"Error: {response.status_code} - {response.text}")
            _logger.debug(records)

        except requests.exceptions.RequestException as e:
            # Catch network-related exceptions (e.g., connection timeout)
            raise UserError(f"Post {schema} Request failed: {e}")

    def _send_get_request(self, action="", schema="", filter={}, page=0, retry=True):
        """
        Sends a request to retrieve data from the Mobilvendor API.

        Although semantically a GET operation, this method uses an HTTP POST request
        as required by the specific API architecture. It handles payload construction,
        pagination, and automatic re-authentication if the session expires.

        :param action: The specific API action to execute (e.g., 'getProducts').
        :param schema: The data entity schema to retrieve.
        :param filter: Dictionary containing query filters.
        :param page: Pagination index (default 0).
        :param retry: Boolean flag to allow one recursive retry on authentication failure.
        :return: Dictionary containing the parsed JSON response.
        """
        # Verify that necessary credentials exist before initiating the request
        if not self.mobilvendor_api_session_id:
            if not self.mobilvendor_api_username:
                raise UserError(f"Invalid username for Mobilvendor API")
            if not self.mobilvendor_api_password:
                raise UserError(f"Invalid password for Mobilvendor API")
            if not self.mobilvendor_api_context:
                raise UserError(f"Invalid context for Mobilvendor API")

            # Attempt automatic login if credentials exist but session is missing
            self._mobilvendor_login()

        response_data = {}

        payload = {
            "session_id": self._get_decrypted_session_id()
        }

        if action:
            payload["action"] = action

        if schema:
            payload["schema"] = schema

        if filter:
            payload["filter"] = filter

        if page > 0:
            payload["page"] = page

        try:
            # Execute the API request using POST method (API convention for retrieval)
            response = requests.post(self.base_url, json=payload)

            # Validate HTTP status
            if response.status_code == 200:
                # HTTP 200 OK
                response_data = response.json()  # Get the JSON response

                if "error" in response_data:
                    error_msg = response_data.get("error")
                    if ("session_id" in error_msg or "Not authorized" in error_msg) and retry:
                        # Handle session expiration: Re-authenticate and retry the request once recursively
                        _logger.debug(f"Invalid session id, trying to login again")
                        self._mobilvendor_login()
                        return self._send_get_request(action=action, schema=schema, filter=filter, page=page,
                                                      retry=False)
                    else:
                        raise UserError(f"GET {action} unsuccessful, {error_msg}")

            else:
                # Handle non-200 HTTP status codes
                raise UserError(f"Error: {response.status_code} - {response.text}")
            _logger.debug(filter)

        except requests.exceptions.RequestException as e:
            # Catch network-related exceptions (e.g., connection timeout)
            raise UserError(f"GET {action} Request failed: {e}")

        return response_data

    def _mobilvendor_login(self):
        """
        Authenticates with the Mobilvendor API to establish a session.

        This method sends the configured credentials (username, decrypted password, context)
        to the API login endpoint. Upon success, it extracts and stores the 'session_id'
        required for subsequent requests.
        """
        _logger.info("##################### login ##############################")
        # Construct the authentication payload using stored credentials
        payload = {
            "action": "login",
            "login": self.mobilvendor_api_username,
            "password": self._get_decrypted_password(),
            "context": self.mobilvendor_api_context
        }

        try:
            # Execute the authentication POST request
            response = requests.post(self.base_url, json=payload)

            # Validate HTTP status code
            if response.status_code == 200:
                # Request successful
                response_data = response.json()  # Parse JSON response

                # Check for logical errors returned by the API
                if "error" in response_data:
                    error_msg = response_data.get("error")
                    raise UserError(f"Login unsuccessful, {error_msg}")

                # Retrieve the session token
                session_id = response_data.get("session_id")

                if not session_id:
                    raise UserError("Login successful, but no session_id found in response.")
                else:
                    # Persist the session ID (usually encrypts it)
                    self._store_session_id(session_id)

            else:
                # Handle non-200 HTTP responses
                response_text = str(response.text) if not isinstance(response.text, str) else response.text
                raise UserError(f"Error: {response.status_code} - {response_text}")

        except requests.exceptions.RequestException as e:
            # Handle network or connection errors
            raise UserError(f"Login Request failed: {e}")

    def _mobilvendor_inventory_types(self):
        """
        Synchronizes the inventory types (locations/branches) definition to Mobilvendor.

        Currently, this method defines a single inventory type corresponding to the
        main company, using a hardcoded code '1'.
        """
        _logger.info("##################### inventory types ##############################")
        # Construct the payload defining the main company as the default inventory type
        records = [
            {
                "code": "1",
                "description": self.company.name
            }
        ]
        # Transmit the records to the API under the 'inv_types' schema
        self._parse_request("inv_types", records)

    def _mobilvendor_categories(self):
        """
        Synchronizes product categories from Odoo to Mobilvendor.

        This method retrieves all product categories configured in Odoo, formats them
        into the specific dictionary structure required by the API (code/description),
        and sends them using the batch processing method.
        """
        _logger.info("##################### categories ##############################")
        records = []

        # Retrieve all product categories from the system
        categories = self.env['product.category'].search([])
        for category in categories:
            # Map Odoo category data to API format
            records.append({
                'code': str(category.id),
                'description': category.name,
            })

        # Send the formatted records to the 'categories' schema endpoint
        self._parse_request("categories", records)

    def _mobilvendor_units(self):
        """
        Synchronizes Units of Measure (UoM) from Odoo to Mobilvendor.

        This method retrieves all defined units of measure, formats them according
        to the API requirements (truncating the description to 10 characters),
        and pushes the data to the external system.
        """
        _logger.info("##################### units ##############################")
        records = []
        # Retrieve all Unit of Measure records from Odoo
        uoms = self.env['uom.uom'].search([])
        for uom in uoms:
            # Map Odoo UoM to API format; description is truncated to 10 chars
            records.append({
                'code': str(uom.id),
                'description': uom.name[:10],
            })

        # Transmit the records to the 'units' schema endpoint
        self._parse_request("units", records)

    def _mobilvendor_articles(self, product_tmpl_ids=None):
        """
        Synchronizes product articles (templates) from Odoo to Mobilvendor.

        This method filters for active, saleable, and consumable products. It maps
        product data including tax configuration (VAT/IVA status), categories,
        and article types (service vs standard) to the API schema.
        Accepts an optional product_tmpl_ids recordset to sync specific products.
        """
        _logger.info("##################### articles ##############################")
        records = []

        domain = [
            ('sale_ok', '=', True),
            ('active', '=', True),
            ('type', '=', 'consu')  # 'consu' maps to Consumable products
        ]
        if product_tmpl_ids:
            domain.append(('id', 'in', product_tmpl_ids.ids))

        # Retrieve product templates
        product_templates_to_send = self.env['product.template'].sudo().search(domain)

        for product in product_templates_to_send:
            # Filter for active sales taxes associated with the product
            taxes = product.taxes_id.filtered(lambda tax: tax.type_tax_use == 'sales' and tax.active)

            # Handle products with no specific tax configuration
            if not taxes:
                records.append({
                    'code': str(product.id),
                    'description': product.name,
                    'has_iva0': 1,  # Default to zero-rated tax
                    'has_iva': 0,  # No VAT
                    'category_code': str(product.categ_id.id),
                    'inv_type_code': '1',
                    'type': "5" if product.type == 'service' else "0"
                })

            # Handle products with defined taxes
            for tax in taxes:
                records.append({
                    'code': str(product.id),
                    'description': product.name,
                    'has_iva0': 1 if tax.amount == 0 else 0,  # Set flag based on tax amount
                    'has_iva': 0 if tax.amount == 0 else 1,  # Set flag based on tax amount
                    'category_code': str(product.categ_id.id),
                    'inv_type_code': '1',
                    'type': "5" if product.type == 'service' else "0"
                })

        # Transmit the formatted records to the 'articles' schema endpoint
        self._parse_request("articles", records)

    def _mobilvendor_price_list(self, pricelist_ids=None):
        """
        Synchronizes product price lists from Odoo to Mobilvendor.

        This method retrieves active price lists, formats their descriptions
        by escaping special characters (quotes) to prevent payload parsing errors,
        and sends the definitions to the API.
        Accepts an optional pricelist_ids recordset for specific syncing.
        """
        _logger.info("##################### price list ##############################")
        records = []

        domain = [('active', '=', True)]
        if pricelist_ids:
            domain.append(('id', 'in', pricelist_ids.ids))

        # Retrieve active price lists
        price_lists = self.env['product.pricelist'].sudo().search(domain)
        for price_list in price_lists:
            records.append({
                'code': str(price_list.id),
                # Escape quotes in the description to ensure safe data transmission
                'description': price_list.name.replace('"', '\"').replace("'", "\'"),
            })

        # Transmit the formatted records to the 'price_lists' schema endpoint
        self._parse_request("price_lists", records)

    def _mobilvendor_article_prices(self, pricelist_ids=None, product_tmpl_ids=None):
        """
        Synchronizes product prices per pricelist from Odoo to Mobilvendor.

        This method iterates through saleable consumable products, retrieves their
        specific pricelist items, and maps the fixed prices to the API schema.
        It uses a fixed historical date to ensure consistency in the external system.
        Allows filtering by specific pricelists and/or specific products.
        """
        _logger.info("##################### article prices ##############################")
        records = []

        domain = [
            ('sale_ok', '=', True),
            ('active', '=', True),
            ('type', '=', 'consu')
        ]
        if product_tmpl_ids:
            domain.append(('id', 'in', product_tmpl_ids.ids))

        # Retrieve product templates
        product_templates = self.env['product.template'].sudo().search(domain)

        # Use a fixed historical date to prevent Mobilvendor from creating duplicate
        # price list entries based on varying dates.
        formatted_date_fixed = '2020-01-01'

        for product in product_templates:
            pricelist_domain = [('product_tmpl_id', '=', product.id)]
            if pricelist_ids:
                pricelist_domain.append(('pricelist_id', 'in', pricelist_ids.ids))

            # Get all price list items associated with the current product template
            pricelist_items = self.env['product.pricelist.item'].sudo().search(pricelist_domain)

            # Iterate through each pricelist item to extract price details
            for pricelist_item in pricelist_items:
                pricelist = pricelist_item.pricelist_id
                records.append({
                    'article_code': str(product.id),  # Product template ID
                    'price_list_code': str(pricelist.id),  # Pricelist ID
                    'value': pricelist_item.fixed_price,  # Fixed price from pricelist item
                    # Specific logic for Unit of Measure code mapping
                    'unit_code': 'UNI' if product.uom_id.id == 1 else str(product.uom_id.id),
                    'valid_from': formatted_date_fixed
                })

        # Transmit the formatted records to the 'article_prices' schema endpoint
        self._parse_request("article_prices", records)

    def _mobilvendor_article_units(self, product_tmpl_ids=None):
        """
        Synchronizes the relationship between articles and units of measure.

        This method retrieves active product variants to associate them with their
        corresponding Units of Measure (UoM) and barcodes.
        Accepts optional product_tmpl_ids recordset.
        """
        _logger.info("##################### article units ##############################")
        records = []
        domain = [
            ('product_tmpl_id.sale_ok', '=', True),
            ('product_tmpl_id.active', '=', True),
            ('product_tmpl_id.type', '=', 'consu'),
            ('active', '=', True),
        ]
        if product_tmpl_ids:
            domain.append(('product_tmpl_id', 'in', product_tmpl_ids.ids))
        
        # Retrieve active product variants
        products = self.env['product.product'].sudo().search(domain)

        for product in products:
            records.append({
                'article_code': str(product.product_tmpl_id.id),  # Product template ID
                # Map UoM ID: If ID is 1, use 'UNI' as required by external system, else use ID string
                'unit_code': 'UNI',
                # 'unit_code': str(product.product_tmpl_id.uom_id.id),
                'barcode': product.barcode if product.barcode else "",  # Barcode from product.product variant
            })

        # Transmit the formatted records to the 'article_units' schema endpoint
        self._parse_request("article_units", records)

    def _mobilvendor_storages_special_condition(self):
        """
        Synchronizes only stock locations where the 'mobilvendor_sync' parameter is set to True.

        Instead of inferring locations from Operation Types, this method explicitly
        looks for physical internal locations flagged for synchronization.
        """
        _logger.debug("### Synchronizing Mobilvendor locations (Flagged by 'mobilvendor_sync') ###")
        records = []

        # 1. Search directly in stock.location
        domain = [
            ('mobilvendor_sync', '=', True),
            ('active', '=', True),
            ('company_id', '=', self.company.id),
        ]

        locations = self.env['stock.location'].search(domain)

        for location in locations:
            records.append({
                'code': str(location.id),
                'description': location.display_name,
            })

        self._parse_request("storages", records)

    def _mobilvendor_storages(self):
        """
        Synchronizes only locations configured for Outgoing shipments (Output/Delivery).

        This method searches for 'outgoing' Operation Types (Picking Types) defined
        for the company and extracts their default source locations. This ensures
        that only locations actually used for dispatching goods are sent to the API.
        """
        _logger.info("##################### storages (Output Only) ##############################")
        records = []

        # 1. Search for Operation Types defined as OUTGOING (code = 'outgoing')
        # This automatically filters for warehouses/locations specifically used for dispatching.
        picking_types = self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('company_id', '=', self.company.id),
            ('active', '=', True)
        ])

        # 2. Extract the default source locations from those operation types
        # Using 'mapped' creates an implicit set to avoid duplicates
        # (in case multiple output types point to the same location).
        output_locations = picking_types.mapped('default_location_src_id')

        for location in output_locations:
            # Safety Check: Ensure the location is an active internal location
            if location.usage == 'internal' and location.active:
                # NOTE: Using 'location.id' ensures we send the specific location
                # where stock resides (e.g., WH/Stock), rather than the parent View.
                # 'display_name' provides the full path (e.g., "Warehouse A / Stock").

                records.append({
                    'code': str(location.id),
                    'description': location.location_id.display_name,
                })

        self._parse_request("storages", records)

    def _mobilvendor_business_types(self):
        """
        Synchronizes partner industries (business types) from Odoo to Mobilvendor.

        This method retrieves all configured partner industries in Odoo and maps
        them to the 'business_types' schema expected by the API.
        """
        _logger.info("##################### business types ##############################")
        records = []

        # Retrieve all partner industries defined in the system
        industries = self.env['res.partner.industry'].search([])

        for industry in industries:
            # Map industry data to API format
            records.append({
                'code': industry.id,
                'description': industry.name,
            })

        # Transmit the formatted records to the 'business_types' schema endpoint
        self._parse_request("business_types", records)

    def _mobilvendor_customer_group(self):
        """
        Synchronizes customer groups (tags) from Odoo to Mobilvendor.

        This method retrieves all partner categories (res.partner.category) defined
        in Odoo and maps them to the 'customer_groups' schema expected by the API.
        """
        _logger.info("##################### customer group ##############################")
        records = []

        # Retrieve all partner categories (customer tags)
        customer_groups = self.env['res.partner.category'].search([])

        for customer_group in customer_groups:
            # Map category data to API format
            records.append({
                'code': customer_group.id,
                'description': customer_group.name,
            })

        # Transmit the formatted records to the 'customer_groups' schema endpoint
        self._parse_request("customer_groups", records)

    def _mobilvendor_banks(self):
        """
        Synchronizes bank definitions from Odoo to Mobilvendor.

        This method retrieves all bank records (res.bank) configured in Odoo,
        formats them with their ID and name, and sends them to the API
        under the 'banks' schema.
        """
        _logger.info("##################### banks ##############################")
        records = []
        # Retrieve all bank records from the system
        banks = self.env['res.bank'].search([])
        for bank in banks:
            # Map bank data to API format
            records.append({
                'code': str(bank.id),
                'description': bank.name,
            })
        # Transmit the formatted records to the 'banks' schema endpoint
        self._parse_request("banks", records)

    def _mobilvendor_payment_terms(self):
        """
        Synchronizes payment terms from Odoo to Mobilvendor.

        This method retrieves all payment terms (account.payment.term) configured in Odoo
        and maps them to the 'payment_methods' schema expected by the API.
        """
        _logger.info("##################### payment terms ##############################")
        records = []

        # Retrieve all payment terms; additional domain filters can be applied here if needed
        payment_terms = self.env['account.payment.term'].search([])

        for term in payment_terms:
            records.append({
                'code': term.id,  # Use the Odoo ID as the unique code
                'description': term.name,  # Map the term name to the description
            })

        # Transmit the formatted records to the 'payment_methods' schema endpoint
        self._parse_request("payment_methods", records)

    def _mobilvendor_payment_methods(self):
        """
        Synchronizes payment method types from Odoo to Mobilvendor.

        This method retrieves all defined account payment methods (e.g., Manual, Checks,
        Electronic) and maps them to the 'payment_methods_2' schema expected by the API.
        """
        _logger.info("##################### payment methods ##############################")
        records = []
        # Retrieve all payment methods configured in the accounting system
        # Note: This retrieves methods for both inbound (customer) and outbound (supplier) flows
        payment_methods = self.env['account.payment.method'].search([])
        for method in payment_methods:
            records.append({
                'code': method.id,
                'description': method.name,
            })

        # Transmit the formatted records to the 'payment_methods_2' schema endpoint
        self._parse_request("payment_methods_2", records)

    def _mobilvendor_inventory_special_condition(self):
        """
        Synchronizes inventory stock levels from Odoo to Mobilvendor.

        This method ensures ALL product-location combinations are sent,
        even if stock is 0, to maintain accurate inventory sync.
        """
        _logger.info("##################### inventory (Mobilvendor Sync Flag) ##############################")

        # 1. Get all locations flagged for sync
        synced_locations = self.env['stock.location'].search([
            ('mobilvendor_sync', '=', True),
            ('active', '=', True)
        ])

        # 2. Get all saleable products
        saleable_products = self.env['product.template'].search([
            ('sale_ok', '=', True),
            ('active', '=', True)
        ])

        # 3. Initialize dictionary with ALL combinations at 0
        inventory_summary = {}
        for product in saleable_products:
            for location in synced_locations:
                key = (product.id, location.id)
                inventory_summary[key] = 0  # Start all at 0

        # 4. Now update with ACTUAL stock quantities
        domain = [
            ('location_id.mobilvendor_sync', '=', True),
            ('location_id.active', '=', True),
            ('product_id.product_tmpl_id.sale_ok', '=', True),
            ('quantity', '>', 0),  # Only get records with actual stock
        ]

        stock_quants = self.env['stock.quant'].search(domain)

        # 5. Update the summary with real quantities
        for quant in stock_quants:
            location_id = quant.location_id.id
            product_tmpl_id = quant.product_id.product_tmpl_id.id
            key = (product_tmpl_id, location_id)

            # This will overwrite the 0 with the actual quantity
            if key in inventory_summary:
                inventory_summary[key] += quant.quantity

        # 6. Format records for API
        records = []
        for (product_tmpl_id, location_id), total_quantity in inventory_summary.items():
            records.append({
                'article_code': str(product_tmpl_id),
                'storage_code': str(location_id),
                'stock': str(total_quantity),
                'reserved': "0"
            })

        _logger.info(f"INVENTORY SYNC: Sending {len(records)} records to Mobilvendor")

        # 7. Send to API
        self._parse_request("inventory", records)

    def _mobilvendor_inventory(self):
        """
        Synchronizes inventory stock levels from Odoo to Mobilvendor.

        This method aggregates stock quantities from 'stock.quant' records, grouping them
        by product and the parent storage location. The aggregated totals are then
        sent to the 'inventory' schema endpoint.
        """
        _logger.info("##################### inventory ##############################")
        records = []

        # Retrieve stock quants for active, internal locations and saleable products
        stock_quants = self.env['stock.quant'].search([
            ('location_id.active', '=', True),  # Filter for active locations
            # ('location_id.company_id', '=', self.company.id),  # Optional: Filter by company
            ('location_id.usage', '=', 'internal'),  # Filter for internal locations only
            # ('product_id.product_tmpl_id.company_id', '=', self.company.id),
            ('product_id.product_tmpl_id.sale_ok', '=', True)  # Filter for saleable products
        ])

        inventory_summary = {}

        # Iterate through stock quants to aggregate quantities
        for quant in stock_quants:
            # Identify the location (quant.location_id)
            root_location = quant.location_id
            product_id = quant.product_id.product_tmpl_id.id

            # Generate a unique grouping key based on Product ID and the Parent Location ID
            # This groups specific sub-locations/bins under their main warehouse/storage
            key = (product_id, root_location.id)

            # Initialize the accumulator for this key if not present
            if key not in inventory_summary:
                inventory_summary[key] = 0

            # Add the quant's quantity to the total for this product/location pair
            inventory_summary[key] += quant.quantity

        # Format the aggregated data for the API payload
        for (product_id, root_location_id), total_quantity in inventory_summary.items():
            records.append({
                'article_code': str(product_id),  # Product Template ID
                'storage_code': str(root_location_id),  # Parent Stock Location ID
                'stock': str(total_quantity),  # Total aggregated quantity
                'reserved': "0"  # Reserved quantity (currently hardcoded to 0)
            })

        # Transmit the formatted records to the 'inventory' schema endpoint
        self._parse_request("inventory", records)

    def _process_invoice_headers(self, headers):
        """
        Transforms the list of invoice headers into a dictionary keyed by invoice code.

        This helper optimizes the synchronization process by converting a list of headers
        into a hash map (dictionary), enabling efficient O(1) lookups of invoice data
        using the Mobilvendor invoice code as the key.

        :param headers: List of dictionaries containing invoice header data from the API.
        :return: Dictionary mapping {invoice_code: header_data_dict}.
        """
        header_obj = {}
        for header in headers:
            # Extract the unique identifier for the invoice
            header_code = header.get("code")

            # Validate that the mandatory identifier is present to avoid data integrity issues
            if not header_code:
                raise UserError(f"Invalid Header for invoice: {header}")

            # Index the header data by its code
            header_obj[header_code] = header
        return header_obj

    def _process_invoice_details(self, details):
        """
        Groups a flat list of invoice line items by their parent invoice code.

        This method processes the raw 'details' list from the API and organizes them
        into a dictionary where the key is the 'invoice_code' and the value is a list
        of line items belonging to that invoice. This facilitates processing headers
        and their corresponding lines together.

        :param details: List of dictionaries representing invoice lines (products).
        :return: Dictionary mapping {invoice_code: [list_of_line_items]}.
        """
        details_obj = {}
        for line_item in details:
            # Extract the parent invoice identifier
            header_code = line_item.get("invoice_code")

            # Validate data integrity: Orphaned lines without a parent code are invalid
            if not header_code:
                raise UserError(f"Invalid Product for invoice: {line_item}")

            # Group line items under their respective invoice code
            if header_code not in details_obj:
                details_obj[header_code] = [line_item]
            else:
                details_obj[header_code].append(line_item)
        return details_obj

    def _mobilvendor_create_payment_method(self):
        """
        Retrieves or creates the specific Payment Method for Mobilvendor.

        This method ensures that an 'inbound' payment method with the code 'mobilvendor'
        exists in the system. This is required to correctly categorize and process
        payments synchronized from the external API.

        :return: The 'account.payment.method' record for Mobilvendor.
        """
        # Search for the payment method by its unique code to check existence
        mobilvendor_payment_method = self.env['account.payment.method'].sudo().search([('code', '=', 'mobilvendor')],
                                                                                      limit=1)

        # If the method does not exist, initialize a new record
        if not mobilvendor_payment_method:
            # Create the payment method configuration in the system
            mobilvendor_payment_method = self.env['account.payment.method'].sudo().create({
                'name': 'Mobilvendor',
                'payment_type': 'inbound',  # Defined for customer payments (inbound flow)
                'code': 'mobilvendor',  # Unique identifier code
            })

        return mobilvendor_payment_method

    def _mobilvendor_create_payments_journal(self, route_id=False):
        """
        Retrieves or creates the Account Journal used for Mobilvendor payments.

        Updated Priority Logic:
        1. Check Payment Journal defined on the specific Route (if route_id provided).
        2. Check Payment Journal configured in Company settings.
        3. Fallback to standard logic: Search for 'MOB-P' or create it.

        :param route_id: Optional ID of the mobilvendor.route to check for a specific journal.
        :return: The 'account.journal' record to be used for payments.
        """
        company = self.company
        if not company:
            # Fallback if 'self.company' is not available
            company = getattr(self, 'company_id', self.env.company)

        # --- PRIORITY 1: Route-specific Journal ---
        if route_id:
            route = self.env['mobilvendor.route'].sudo().browse(route_id)
            if route.exists() and route.payment_journal_id:
                # _logger.debug(f"Using Route Payment Journal: {route.payment_journal_id.name}")
                return route.payment_journal_id

        # --- PRIORITY 2: Company Configuration ---
        if company.mobilvendor_payment_journal_id:
            _logger.debug(
                f"Using pre-configured payment journal: {company.mobilvendor_payment_journal_id.name} "
                f"(ID: {company.mobilvendor_payment_journal_id.id})"
            )
            return company.mobilvendor_payment_journal_id

        # --- PRIORITY 3: Fallback (MOB-P) ---
        _logger.debug("Payment journal not configured. Searching/Creating 'MOB-P'...")

        company_id = company.id
        journal = self.env['account.journal'].sudo().search([
            ('code', '=', 'MOB-P'),
            ('company_id', '=', company_id)
        ], limit=1)

        # Create if it doesn't exist
        if not journal:
            journal_sequence_store = f'2{company_id}{company_id}'
            search_index = f'001-{journal_sequence_store} Mobilvendor Payments'

            _logger.debug(
                f"CREATING PAYMENT JOURNAL: {company_id}, search index: {search_index}, "
                f"sequence store: {journal_sequence_store}")

            # Create a custom sequence for this journal to avoid gaps
            check_sequence_vals = {
                'name': 'MOB Payment: Payment numbering sequence',
                'implementation': 'no_gap',
                'prefix': 'MOB-P',
                'padding': 5,
                'number_increment': 1,
                'company_id': company_id,
            }
            check_sequence = self.env['ir.sequence'].create(check_sequence_vals)

            journal_vals = {
                'name': search_index,
                'type': 'cash',
                'code': 'MOB-P',
                'company_id': company_id,
                'sequence': 10,
                'color': 0,
                'invoice_reference_type': 'invoice',
                'invoice_reference_model': 'odoo',
                'bank_statements_source': 'undefined',
                'refund_sequence': True,
                'payment_sequence': False,
                'show_on_dashboard': True,
                'check_sequence_id': check_sequence.id
            }

            journal = self.env['account.journal'].sudo().create(journal_vals)

            # Ensure the custom payment method exists
            payment_method = self._mobilvendor_create_payment_method()

            # Bind the Mobilvendor payment method to this journal
            self.env['account.payment.method.line'].sudo().create({
                'journal_id': journal.id,
                'payment_method_id': payment_method.id,
                'payment_type': 'inbound',  # For customer receipts
                'name': 'Mobilvendor',
                'payment_account_id': journal.default_account_id.id
            })

            # Fix: Ensure 'Manual' payment methods also use the journal's default account
            payment_method_lines_manual = self.env['account.payment.method.line'].search([
                ('journal_id', '=', journal.id),
                ('name', '=', 'Manual')
            ])

            if journal.id and payment_method_lines_manual:
                for payment_method_line_m in payment_method_lines_manual:
                    payment_method_line_m.payment_account_id = journal.default_account_id.id

        return journal

    def _mobilvendor_create_invoice_journal(self, route_id=False):
        """
        Retrieves or creates the Account Journal used for Mobilvendor invoices.

        Priority Logic:
        1. Check Journal defined on the specific Mobilvendor Route (if route_id provided).
        2. Check Journal configured in Company settings.
        3. Fallback to standard logic: Search for 'MOBD' or create it.

        :param route_id: Optional ID of the mobilvendor.route to check for a specific journal.
        :return: The 'account.journal' record to be used for invoices.
        """
        # Resolve company context safely
        company = self.company
        if not company:
            # Fallback if 'self.company' is not available
            company = getattr(self, 'company_id', self.env.company)

        # --- PRIORITY 1: Route-specific Journal ---
        if route_id:
            route = self.env['mobilvendor.route'].sudo().browse(route_id)
            if route.exists() and route.invoice_journal_id:
                _logger.debug(f"Using Route-specific Invoice Journal: {route.invoice_journal_id.name} for Route {route.name}")
                return route.invoice_journal_id

        # --- PRIORITY 2: Company Configuration ---
        if company.mobilvendor_invoice_journal_id:
            _logger.debug(
                f"Using pre-configured invoice journal: {company.mobilvendor_invoice_journal_id.name} "
                f"(ID: {company.mobilvendor_invoice_journal_id.id})"
            )
            return company.mobilvendor_invoice_journal_id

        # --- PRIORITY 3: Fallback (MOBD) ---
        _logger.debug("Invoice journal not configured. Searching for 'MOBD' or creating a new one...")

        company_id = company.id

        # Search logic for existing journal by code
        journal = self.env['account.journal'].sudo().search([
            ('code', '=', 'MOBD'),
            ('company_id', '=', company_id)
        ], limit=1)

        # Create if it doesn't exist
        if not journal:
            journal_sequence_store = f'12{company_id}'
            search_index = f'001-{journal_sequence_store} Mobilvendor'

            _logger.debug(
                f"CREATING JOURNAL: {company_id}, name: {search_index}, sequence store: {journal_sequence_store}")

            journal_vals = {
                'name': search_index,
                'type': 'sale',
                'code': 'MOBD',
                'company_id': company_id,
                'sequence': 10,
                'color': 0,
                'invoice_reference_type': 'invoice',
                'invoice_reference_model': 'odoo',
                'bank_statements_source': 'undefined',
                'refund_sequence': True,
                'payment_sequence': False,
                'show_on_dashboard': True,
                'default_account_id': 38,
            }

            journal = self.env['account.journal'].sudo().create(journal_vals)
            _logger.debug(f"Journal MOBD created with ID: {journal.id}")

        return journal

    def _format_line_items_sale_order(self, api_line_items, create=True, company_id=1):
        """
        Formats raw line items from the API into Odoo Sale Order Line tuples.

        This method maps product codes to Odoo IDs, applies company-specific taxes,
        and structures the data using Odoo's (0, 0, values) command for creating
        One2many records.

        :param api_line_items: List of dictionaries containing item data.
        :param create: Boolean flag to trigger creation logic.
        :param company_id: ID of the company to filter taxes.
        :return: List of tuples compatible with the 'order_line' field.
        """
        line_items = []
        if create:
            for item in api_line_items:
                # Parse numeric fields from the API payload
                try:
                    article_code_int = int(item['article_code'])
                except ValueError:
                    continue

                # Locate the specific product variant and template
                product_id = self.env['product.product'].search([('product_tmpl_id', '=', article_code_int)],
                                                                limit=1).id
                product_template = self.env['product.template'].search([('id', '=', article_code_int)], limit=1)

                # --- PARSING VALUES & DISCOUNT CALCULATION ---
                quantity = float(item.get('quantity', 0.0))
                price_unit = float(item.get('price', 0.0))

                # Get raw values
                discount_amount_api = float(item.get('discount', 0.0))
                discount_percent_api = float(item.get('discount_p', 0.0))

                final_odoo_discount = 0.0

                # Calculate Percentage
                if discount_percent_api > 0:
                    final_odoo_discount = discount_percent_api
                elif discount_amount_api > 0 and price_unit > 0 and quantity > 0:
                    total_base = price_unit * quantity
                    final_odoo_discount = (discount_amount_api / total_base) * 100

                # Retrieve product taxes filtered by the specific company context
                product_taxes = product_template.taxes_id.filtered(lambda tax: tax.company_id.id == company_id)
                # Format taxes using Odoo's Many2many command (6, 0, [ids])
                tax_ids = [(6, 0, product_taxes.ids)] if product_taxes else []

                if not product_id:
                    _logger.debug(f"PRODUCT CODE: {article_code_int}, Company ID: {company_id}")
                    # Abort processing if a product cannot be mapped
                    return []

                # Construct the Odoo command tuple (0, 0, values) to create a new order line
                line_items.append((0, 0, {
                    'product_id': product_id,
                    'product_uom_qty': quantity,  # Quantity field specific to Sale Orders
                    'price_unit': price_unit,
                    'discount': final_odoo_discount,  # Calculated Percentage
                    'tax_id': tax_ids,  # Link applicable taxes
                    'name': product_template.name or 'Description not provided',
                    # Use product name as default description
                }))

        return line_items

    def _format_line_items_invoice(self, api_line_items, create=True, journal=None, res_partner=None, company_id=1):
        """
        Formats raw line items from the API into Odoo Invoice Line tuples.

        This method maps product codes to Odoo IDs, applies company-specific taxes,
        and structures the data using Odoo's (0, 0, values) command for creating
        One2many records within an Account Move (Invoice).

        :param api_line_items: List of dictionaries containing item data.
        :param create: Boolean flag to trigger creation logic.
        :param journal: The account journal record (required).
        :param res_partner: The partner record (unused in current logic but kept for signature compatibility).
        :param company_id: ID of the company to filter taxes.
        :return: List of tuples compatible with the 'invoice_line_ids' field.
        """
        _logger.info(
            f"MAIN METHOD _format_line_items_invoice - journal: {journal} - company_id: {company_id}")
        line_items = []
        if create:
            # A journal is mandatory for invoice line creation validation
            if not journal:
                _logger.info(
                    f"NO JOURNAL for LINE ITEMS")
                return line_items

            for item in api_line_items:
                # Retrieve or map the necessary fields from the payload

                try:
                    article_code_int = int(item['article_code'])
                except ValueError:
                    _logger.info(
                        f"NO VALID ARTICLE CODE")
                    continue

                # Locate product variant and template based on the external code
                product_id = self.env['product.product'].search([('product_tmpl_id', '=', article_code_int)],
                                                                limit=1).id
                product_template = self.env['product.template'].search([('id', '=', article_code_int)],
                                                                       limit=1)

                # --- PARSING VALUES & DISCOUNT CALCULATION ---
                quantity = float(item.get('quantity', 0.0))
                price_unit = float(item.get('price', 0.0))

                # Get raw values from API
                discount_amount_api = float(item.get('discount', 0.0))  # e.g., 441.00
                discount_percent_api = float(item.get('discount_p', 0.0))  # e.g., 0.00

                final_odoo_discount = 0.0

                # Logic: Odoo needs Percentage.
                # 1. If API gives percentage, use it.
                if discount_percent_api > 0:
                    final_odoo_discount = discount_percent_api
                # 2. If API gives Amount but 0%, calculate the percentage manually.
                elif discount_amount_api > 0 and price_unit > 0 and quantity > 0:
                    total_base = price_unit * quantity
                    # Formula: (Discount Amount / Total Base) * 100
                    final_odoo_discount = (discount_amount_api / total_base) * 100

                # Filter taxes specifically for the target company
                product_taxes = product_template.taxes_id.filtered(lambda tax: tax.company_id.id == company_id)
                # Format taxes using Odoo's Many2many command (6, 0, [ids])
                tax_ids = [(6, 0, product_taxes.ids)] if product_taxes else []

                # Strict validation: Abort if no valid taxes are found for the product in this company
                if not tax_ids:
                    _logger.info(f"PRODUCT CODE: {article_code_int}, Company ID: {company_id}")
                    return []

                # Append the line item in the format required by Odoo for Account Move Lines
                line_items.append((0, 0, {
                    # 'partner_id': res_partner.id,
                    'product_id': product_id,
                    'product_uom_id': product_template.uom_id.id,
                    'quantity': quantity,  # 'quantity' field is used in Account Move Lines (unlike Sale Orders)
                    'price_unit': price_unit,
                    'discount': final_odoo_discount,  # Calculated Percentage
                    'tax_ids': tax_ids,
                    # 'journal_id': journal.id
                }))

        return line_items

    def _mobilvendor_update_inventory_storages(self, line_items, partner_id, transfer_type, dispatch_date=None,
                                               reverse_invoice=False, reversed_invoice_name=None, route_id=False):
        """
        Creates and validates stock pickings based on API line item data.

        This method processes a list of line items, determines the origin
        and destination locations, and identifies the correct picking type (Operation Type).
        It uses a robust logic based on the Warehouse and Operation Code (incoming/outgoing/internal),
        with a fallback to barcode matching.

        It groups items by route to optimize transaction count.

        :param line_items: List of line item dictionaries from the API.
        :param partner_id: The Odoo Partner ID to link to the picking.
        :param transfer_type: String ("INVOICE", "TRANSFER", "NC") to determine logic.
        :param dispatch_date: Optional datetime object to set as the done date.
        :param reverse_invoice: Boolean, True if this is a return (NC).
        :param reversed_invoice_name: Optional string (parent invoice name) for returns.
        :return: True on completion.
        """
        # This dictionary will group all stock.move values by their intended picking.
        # Key = (origin_location_id, destination_location_id, picking_type_id)
        # Value = list of 'stock.move' value dictionaries
        picking_groups = {}

        # Cache for warehouses to reduce DB calls inside the loop
        warehouse_cache = {}

        for item in line_items:
            invoice_code = item.get('invoice_code', 'Unknown')
            origin_location_name = item.get('org_storage_description', 'Unknown')

            # --- 1. Product Resolution ---
            try:
                product_template_id = int(item.get('article_code'))
                product = self.env['product.product'].search([('product_tmpl_id', '=', product_template_id)], limit=1)
                if not product:
                    _logger.debug(f"Product with template ID {product_template_id} not found.")
                    continue
            except (TypeError, ValueError):
                _logger.debug(f"Invalid product template id {item.get('article_code')}")
                continue

            try:
                quantity = int(float(item.get('quantity')))
                if quantity == 0:
                    continue
            except (TypeError, ValueError):
                _logger.debug(f"Invalid quantity to transfer for {item}")
                continue

            # --- 2. Odoo 18 Compatibility: Check Product Type ---
            # Use 'detailed_type' instead of 'type' or 'l10n_ec_type'
            if product.product_tmpl_id.type == 'service':
                continue

            # --- 3. Determine Origin and Destination Locations ---
            try:
                origin_location_id = int(item.get('org_storage_code'))
                origin_location = self.env['stock.location'].search([('id', '=', origin_location_id)], limit=1)
                if not origin_location:
                    _logger.debug(f"Origin stock location with ID {origin_location_id} does not exist for {item}")
                    continue
            except (TypeError, ValueError):
                # Fallback for returns: If origin storage is missing, assume it's from the Customer
                if reverse_invoice:
                    origin_location = self.env.ref('stock.stock_location_customers')
                    origin_location_id = origin_location.id
                else:
                    _logger.debug(f"Invalid origin storage code for {item}")
                    continue

            try:
                destination_location_id = int(item.get('dest_storage_code'))
                destiny_location = self.env['stock.location'].search([('id', '=', destination_location_id)], limit=1)
                if not destiny_location:
                    _logger.debug(f"Destiny stock location with ID {destination_location_id} does not exist for {item}")
                    continue
            except (TypeError, ValueError):
                # Fallback for sales: If destination is missing, assume it's going to the Customer
                if not reverse_invoice:
                    destiny_location = self.env.ref('stock.stock_location_customers')
                    destination_location_id = destiny_location.id
                else:
                    _logger.debug(f"Invalid origin and destination NC from MV {invoice_code}")
                    continue

            # --- 4. Determine Picking Type (Operation Type) ---
            picking_type = None

            # A. Determine the relevant Warehouse
            # For Sales/Transfers, we look at the Origin Warehouse.
            # For Returns (NC), we look at the Destination Warehouse (where goods are entering).
            warehouse = origin_location.warehouse_id
            if transfer_type not in ["INVOICE", "TRANSFER"]:  # It is a Return (NC)
                warehouse = destiny_location.warehouse_id

            # If the specific location doesn't have a warehouse set, try the company default
            if not warehouse:
                warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company.id)], limit=1)

            # B. Search for the Picking Type by Warehouse & Code
            if warehouse:
                if transfer_type == "INVOICE":
                    # Outgoing: Delivery Orders
                    picking_type = self.env['stock.picking.type'].search([
                        ('warehouse_id', '=', warehouse.id),
                        ('code', '=', 'outgoing')
                    ], limit=1)
                elif transfer_type == "TRANSFER":
                    # Internal: Internal Transfers
                    picking_type = self.env['stock.picking.type'].search([
                        ('warehouse_id', '=', warehouse.id),
                        ('code', '=', 'internal')
                    ], limit=1)
                else:  # NC (Credit Note)
                    # Incoming: Receipts (Returns)
                    picking_type = self.env['stock.picking.type'].search([
                        ('warehouse_id', '=', warehouse.id),
                        ('code', '=', 'incoming')
                    ], limit=1)

            # C. Fallback: Legacy Barcode Logic (if warehouse logic fails)
            if not picking_type:
                _logger.warning(f"Standard picking type logic failed for {transfer_type}, trying barcode fallback.")

                barcode_suffix = ""
                if transfer_type == "INVOICE":
                    barcode_suffix = "OUT"
                elif transfer_type == "TRANSFER":
                    barcode_suffix = "INT"
                else:
                    barcode_suffix = "-RETURNS"

                # Clean name to avoid spaces affecting barcode construction
                clean_name = origin_location.name.upper().strip()
                custom_barcode = f"{clean_name}{barcode_suffix}"

                picking_type = self.env['stock.picking.type'].search([
                    ('company_id', '=', self.company.id),
                    ('barcode', '=', custom_barcode),
                ], limit=1)

            if not picking_type:
                _logger.error(
                    f"CRITICAL: Could not find picking type for {transfer_type} (Wh: {warehouse.name if warehouse else 'None'}). Location: {origin_location.name}")
                continue

            # --- 5. Prepare the 'stock.move' values dictionary ---
            # NOTE: We don't set mobilvendor_route_id here because it is a RELATED field
            # to the picking. It will be set automatically when the picking is created.
            move_vals = {
                'name': f'MV: {product.product_tmpl_id.name}' if not reverse_invoice else f'Return: {product.product_tmpl_id.name} ({reversed_invoice_name})',
                'product_id': product.id,
                'product_uom_qty': quantity,
                'product_uom': product.product_tmpl_id.uom_id.id,
                'location_id': origin_location_id,
                'location_dest_id': destination_location_id,
                'state': 'draft',
                'company_id': self.company.id,
                'partner_id': partner_id,
                'picking_type_id': picking_type.id,
                'warehouse_id': warehouse.id if warehouse else origin_location.warehouse_id.id,
                'procure_method': 'make_to_stock',
                'description_picking': product.product_tmpl_id.name,
                'mobilvendor_id': invoice_code
            }

            # --- 6. Group the move values ---
            group_key = (origin_location_id, destination_location_id, picking_type.id)
            if group_key not in picking_groups:
                picking_groups[group_key] = []

            # Add the move values as an Odoo create-command tuple
            picking_groups[group_key].append((0, 0, move_vals))

        # --- 7. Process Groups: Create and Validate Pickings ---
        current_datetime = datetime.now()

        for (origin_id, dest_id, picking_type_id), move_lines_vals in picking_groups.items():
            try:
                # Create the 'stock.picking' AND its 'stock.move' lines simultaneously
                stock_picking = self.env['stock.picking'].create({
                    'location_id': origin_id,
                    'location_dest_id': dest_id,
                    'picking_type_id': picking_type_id,
                    'origin': f'Invoice {invoice_code}' if not reverse_invoice else f"Return of {reversed_invoice_name}",
                    'partner_id': partner_id,
                    'company_id': self.company.id,
                    'move_type': 'direct',
                    'state': 'assigned',  # Start as 'assigned' for Odoo 18+
                    'scheduled_date': dispatch_date or current_datetime,
                    'date': dispatch_date or current_datetime,
                    'mobilvendor_route_id': route_id,
                    # Key Odoo 18+ pattern: Create the move lines using this field
                    'move_ids_without_package': move_lines_vals
                })

                # Confirm and assign the picking
                stock_picking.action_confirm()
                stock_picking.action_assign()

                # Set 'quantity_done' to match 'product_uom_qty' for immediate validation
                for move in stock_picking.move_ids:
                    move.quantity = move.product_uom_qty

                # Validate the picking (this executes the stock move)
                stock_picking.button_validate()

                if dispatch_date:
                    stock_picking.sudo().write({
                        'date_done': dispatch_date
                    })

                # If a specific dispatch date was provided, force it as the 'date_done'
                # Note: In Odoo 18, date_done is often readonly, sudo might be needed

                # ======================================================================
                # FIX: Force exact dates on the picking and its stock moves
                # ======================================================================
                # target_date = dispatch_date or current_datetime

                # 1. Update Picking (Header): Scheduled, Creation, and Effective dates
                # stock_picking.sudo().write({
                #     'scheduled_date': target_date,
                #     'date': target_date,
                #     'date_done': target_date
                # })
                #
                # # 2. Update move lines (Critical for Kardex/Inventory Valuation)
                # if stock_picking.move_ids:
                #     stock_picking.move_ids.sudo().write({'date': target_date})
                #
                # # Odoo 18 uses move_line_ids for actual physical stock moves
                # if stock_picking.move_line_ids:
                #     stock_picking.move_line_ids.sudo().write({'date': target_date})
                # # ======================================================================

                _logger.info(f"Inventory moved for {invoice_code}: Picking {stock_picking.name}")

            except Exception as e:
                # IMPORTANT: Raise the exception so the SAVEPOINT in the parent method catches it.
                # Do NOT rollback the cursor here (self.env.cr.rollback()), as that kills the whole batch.
                error_msg = f"Failed to create/validate picking (Org: {origin_id}, Dst: {dest_id}). Error: {str(e)}"
                _logger.error(error_msg)
                raise UserError(error_msg)

        return True

    def _get_safe_employee_id(self, incoming_id):
        """
        Validates that the numeric ID received from Mobilvendor actually exists in Odoo.
        Returns the ID if valid, otherwise returns False.
        """
        if not incoming_id:
            return False

        try:
            # Safely cast to integer
            emp_id = int(incoming_id)

            # .exists() checks if the record is effectively present in the database
            if self.env['hr.employee'].browse(emp_id).exists():
                return emp_id
            else:
                _logger.warning(f"Employee ID {emp_id} sent by Mobilvendor does NOT exist in Odoo.")
                return False
        except ValueError:
            _logger.error(f"Invalid (non-numeric) employee ID received: {incoming_id}")
            return False

    def _mobilvendor_get_invoices(self, inv_type="1,3,6"):
        """
        Main controller method for synchronizing invoices from Mobilvendor.

        This method ("The Boss") manages the pagination and transaction handling.
        It iterates through API pages, calling a "worker" method for each page.
        Each page is processed in a separate, safe database transaction to ensure
        that large data volumes do not cause timeouts or data corruption.
        """
        _logger.info("##################### get invoices (Controller) ##############################")

        # Get the current datetime
        current_datetime = datetime.now()
        # Calculate the start date for the sync based on configuration
        previous_day = current_datetime - timedelta(days=self.mobilvendor_sync_days)
        previous_day_format = previous_day.strftime('%Y-%m-%d')

        current_page = 1
        has_more_pages = True

        # Loop as long as the API reports more pages
        while has_more_pages:
            _logger.info(f"Starting invoice page processing: {current_page}")

            try:
                # --- CRITICAL: Safe Transaction Handling ---
                # Create a new cursor to isolate this page
                with self.env.registry.cursor() as new_cr:

                    # 1. Create a new environment (Environment) with that cursor
                    new_env = self.env(cr=new_cr)

                    # 2. Get the company in this NEW environment
                    # (This is vital so that writes are done in the new_cr context)
                    company_in_new_env = new_env['res.company'].browse(self.company.id)

                    # 3. Instantiate the Handler class again, "injecting"
                    # the new environment and the company linked to that environment.
                    # Using self.__class__ is safer than hardcoding the class name.
                    handler_new_env = self.__class__(company_in_new_env, new_env)

                    # 4. Call the worker using this new "safe" instance
                    has_more_pages = handler_new_env._process_invoices_page(
                        page=current_page,
                        inv_type=inv_type,
                        previous_day_format=previous_day_format
                    )

                # If the 'with' block ends successfully, Odoo automatically commits new_cr.
                # This commits all invoices that succeeded within their individual savepoints.
                _logger.info(f"Page {current_page} processed and committed successfully.")

            except Exception as e:
                # If the 'with' block fails, Odoo automatically rolls back new_cr.
                # This catches errors that happen outside of the per-invoice try/except logic.
                _logger.error(f"Error processing page {current_page}. Transaction rolled back. Error: {e}")
                has_more_pages = False

            current_page += 1

        _logger.info("Invoice synchronization complete.")

    def _process_invoices_page(self, page, inv_type, previous_day_format):
        """
        Worker method that processes a single page of invoice/order data from the API.

        This method is designed to be executed within a specific database transaction.
        It implements Batch Caching strategies to avoid N+1 queries for Routes and Journals.

        :param page: The specific page number to retrieve from the API.
        :param inv_type: String of comma-separated document types to filter.
        :param previous_day_format: The start date for the synchronization filter.
        :return: Boolean indicating if there are more pages to process.
        """
        _logger.info(f"##################### processing invoices page {page} (Worker) #################")

        filter_invoice = {
            "process_status": "0,1",
            "type": inv_type,
            "status": "2,3,10",
            "page": page,
            "start_date": previous_day_format
        }

        _logger.info(f"Getting invoices page {page}")

        # Get Odoo timezone
        user_tz = self.env.user.tz or self.env.company.partner_id.tz or 'UTC'
        local_tz = timezone(user_tz)

        # Fetch data from API
        invoices_response = self._send_get_request(action="getInvoices", filter=filter_invoice)
        number_of_pages = invoices_response.get("pages", 1)

        if "headers" not in invoices_response or "details" not in invoices_response:
            _logger.error(f"Invalid response for Get Invoices on page {page}")
            raise UserError(f"Invalid API response for Get Invoices on page {page}")

        invoice_headers = self._process_invoice_headers(invoices_response.get("headers"))
        invoice_line_items = self._process_invoice_details(invoices_response.get("details"))

        # ==============================================================================
        # 1. PRE-FETCH: DEFAULT JOURNAL (Optimization)
        # ==============================================================================
        default_journal_record = self._mobilvendor_create_invoice_journal(route_id=False)
        default_journal_id = default_journal_record.id

        # ==============================================================================
        # 2. BATCH CACHE: ROUTES & ROUTE-SPECIFIC JOURNALS (Optimization)
        # ==============================================================================
        route_codes_in_batch = set()
        for header_val in invoice_headers.values():
            r_data = header_val.get("user_route", {})
            if r_data and r_data.get("code"):
                route_codes_in_batch.add(r_data.get("code"))

        routes_cache = {}  # Map: { 'MV_CODE': ODOO_ROUTE_ID }
        route_journals_map = {}  # Map: { ODOO_ROUTE_ID: ODOO_JOURNAL_ID }

        if route_codes_in_batch:
            found_routes = self.env['mobilvendor.route'].sudo().search([
                ('mobilvendor_id', 'in', list(route_codes_in_batch))
            ])
            for r in found_routes:
                routes_cache[r.mobilvendor_id] = r.id
                if r.invoice_journal_id:
                    route_journals_map[r.id] = r.invoice_journal_id.id

        _logger.info(f"Routes cached: {len(routes_cache)}. Route-Journals found: {len(route_journals_map)}")

        # ==============================================================================
        # 3. PROCESS LOOP (With SafePoint)
        # ==============================================================================

        for key, value in invoice_headers.items():
            external_mobilvendor_id = key

            # --- ATOMICITY START: Each invoice is processed in isolation ---
            try:
                with self.env.cr.savepoint():

                    try:
                        order_invoice_type = int(value.get('type'))
                    except (TypeError, ValueError):
                        order_invoice_type = 1

                    # Determine Odoo Model
                    model_name = 'account.move'
                    if order_invoice_type == 2:
                        model_name = 'sale.order'
                    elif order_invoice_type == 3:
                        model_name = 'stock.move'

                    # Search for existing record (Idempotency)
                    existing_record = self.env[model_name].search(
                        [('mobilvendor_id', '=', external_mobilvendor_id)], limit=1)

                    # --- A. ROUTE RESOLUTION ---
                    route_data = value.get("user_route", {})
                    if not isinstance(route_data, dict):
                        route_data = {}

                    route_mv_code = route_data.get("code")
                    route_description = route_data.get("description", "N/A")

                    # Fast Lookup from Cache (O(1))
                    route_id_odoo = routes_cache.get(route_mv_code)

                    # --- B. JOURNAL RESOLUTION ---
                    target_journal_id = default_journal_id
                    if route_id_odoo and route_id_odoo in route_journals_map:
                        target_journal_id = route_journals_map[route_id_odoo]

                    if existing_record:
                        if value.get('status') == '3' and hasattr(existing_record, 'state') and existing_record.state != 'cancel':
                            _logger.info(f"{model_name} {external_mobilvendor_id} annulled in Mobilvendor. Canceling in Odoo...")
                            if model_name == 'account.move':
                                self._mobilvendor_cancel_invoice(existing_record, external_mobilvendor_id)
                            elif model_name == 'sale.order':
                                existing_record.action_cancel()
                        else:
                            _logger.info(f"{model_name} {external_mobilvendor_id} already synced.")
                        continue

                    _logger.info(
                        f"Processing {external_mobilvendor_id} - Route ID: {route_id_odoo} - Journal ID: {target_journal_id}")

                    # --- PARTNER RESOLUTION ---
                    partner_code = value.get('customer_code')
                    res_partner = self.env['res.partner'].sudo().search([
                        ('mobilvendor_id', '=', partner_code),
                        ('vat', '!=', False)
                    ], limit=1)

                    if not res_partner:
                        try:
                            res_partner = self.env['res.partner'].sudo().search([
                                ('id', '=', int(partner_code)),
                                ('vat', '!=', False)
                            ], limit=1)
                        except (TypeError, ValueError):
                            _logger.error(f"INVALID ID FOR RES PARTNER: {partner_code}")
                            pass

                    # --- ADDRESS RESOLUTION ---
                    partner_addr_code = value.get('customer_address_code')
                    res_partner_addr = self.env['res.partner'].sudo().search([
                        ('address_mobilvendor_id', '=', partner_addr_code),
                        ('vat', '!=', False)
                    ], limit=1)

                    if not res_partner_addr:
                        try:
                            res_partner_addr = self.env['res.partner'].sudo().search([
                                ('id', '=', int(partner_addr_code)),
                                ('vat', '!=', False)
                            ], limit=1)
                        except (TypeError, ValueError):
                            _logger.error(f"NO RES PARTNER ADDR FOR INVOICE: {external_mobilvendor_id}")
                            pass

                    if not res_partner and order_invoice_type != 3:
                        _logger.error(f"INVALID RES PARTNER FOR: {external_mobilvendor_id}")
                        continue  # Missing Partner for Sales/Invoices

                    # --- USER RESOLUTION ---
                    user_id = 3  # Default fallback
                    user_code = value.get('user_code')
                    res_partner_record = self.env['res.partner'].search([('name', '=', user_code)], limit=1)
                    if res_partner_record:
                        user_record = self.env['res.users'].with_context(active_test=False).search(
                            [('partner_id', '=', res_partner_record.id)], limit=1)
                        if user_record:
                            user_id = user_record.id

                    # Date Parsing
                    if value.get("create_date"):
                        utc_dt = datetime.fromtimestamp(int(value.get("create_date")), tz=UTC)
                        local_dt = utc_dt.astimezone(local_tz)
                        date_create_obj = local_dt.date()
                    else:
                        date_create_obj = None

                    if value.get("dispatch_date"):
                        utc_dt = datetime.fromtimestamp(int(value.get("dispatch_date")), tz=UTC)
                        local_dt = utc_dt.astimezone(local_tz)
                        dispatch_date_obj = local_dt.date()
                    else:
                        dispatch_date_obj = None

                    invoice_reference_code = value.get('code', '')
                    company_id = self.company.id
                    currency_id = res_partner.currency_id.id if res_partner else self.company.currency_id.id

                    # ---------------------------------------------------------
                    # TYPE 1 (INVOICE) OR 6 (CREDIT NOTE)
                    # ---------------------------------------------------------
                    if order_invoice_type == 1 or order_invoice_type == 6:
                        parent_invoice_obj = None
                        parent_invoice_number = None

                        # Credit Note Logic
                        if order_invoice_type == 6:
                            parent_invoice_mv = value.get('parent')
                            if parent_invoice_mv:
                                parent_invoice_number = parent_invoice_mv.get('code')

                            if parent_invoice_number:
                                parent_invoice_obj = self.env['account.move'].search(
                                    [('mobilvendor_id', '=', parent_invoice_number)], limit=1)

                            if not parent_invoice_obj:
                                _logger.error(
                                    f"Parent Invoice {parent_invoice_number} not found for NC {external_mobilvendor_id}")
                                continue

                        # Format Lines
                        journal_obj = self.env['account.journal'].browse(target_journal_id)

                        formatted_line_items = self._format_line_items_invoice(
                            invoice_line_items.get(external_mobilvendor_id, []),
                            journal=journal_obj,
                            res_partner=res_partner,
                            company_id=company_id
                        )

                        if not formatted_line_items:
                            _logger.info(f"NO FORMATTED LINE ITEMS: {external_mobilvendor_id}")
                            continue

                        try:
                            status_mb = int(value.get('status'))
                        except (TypeError, ValueError):
                            status_mb = 2

                        partner_id_reference = res_partner_addr.id if res_partner_addr else res_partner.id
                        incoming_seller_id = value.get('user_code')

                        # Prepare Invoice Values
                        invoice_vals = {
                            'partner_id': res_partner.id,
                            'name': f'{invoice_reference_code}',
                            'commercial_partner_id': res_partner.id,
                            'partner_shipping_id': partner_id_reference,
                            'move_type': 'out_refund' if parent_invoice_obj else 'out_invoice',
                            'mobilvendor_id': external_mobilvendor_id,
                            'date': date_create_obj,
                            'invoice_date': date_create_obj,
                            'invoice_line_ids': formatted_line_items,
                            'sequence_prefix': f'Fact 001-10{company_id}-',
                            'payment_reference': f'{invoice_reference_code}',
                            'invoice_partner_display_name': value.get('customer_name', ''),
                            'team_id': 1,
                            'company_id': company_id,
                            'currency_id': currency_id,
                            'invoice_user_id': user_id,
                            'access_token': value.get('auth_code'),
                            'reversed_entry_id': parent_invoice_obj.id if parent_invoice_obj else None,
                            'journal_id': target_journal_id,
                            'mobilvendor_route_id': route_id_odoo,
                            'mobilvendor_route_definition': route_description,
                            'mobilvendor_vendor_id': self._get_safe_employee_id(incoming_seller_id)
                        }

                        # Create Record
                        invoice = self.env['account.move'].sudo().create(invoice_vals)

                        if status_mb == 3:
                            invoice.button_cancel()
                            continue  # Canceled status: Skip post and inventory update

                        if status_mb != 0:
                            invoice.action_post()
                            if parent_invoice_obj and self.mobilvendor_api_conciliate_credit_notes:
                                invoice_lines = parent_invoice_obj.line_ids.filtered(
                                    lambda l: l.account_id.reconcile and not l.tax_line_id)
                                credit_note_lines = invoice.line_ids.filtered(
                                    lambda l: l.account_id.reconcile and not l.tax_line_id)
                                if invoice_lines and credit_note_lines:
                                    (invoice_lines + credit_note_lines).reconcile()

                        # Trigger Inventory Update
                        # If this raises an Exception, it will be caught by the except block below
                        # and the savepoint will rollback ONLY this invoice.
                        self._mobilvendor_update_inventory_storages(
                            invoice_line_items.get(external_mobilvendor_id, []),
                            res_partner.id,
                            "INVOICE" if order_invoice_type == 1 else "NC",
                            dispatch_date=dispatch_date_obj,
                            reverse_invoice=order_invoice_type == 6,
                            reversed_invoice_name=parent_invoice_number,
                            route_id=route_id_odoo
                        )

                    # ---------------------------------------------------------
                    # TYPE 2 (SALE ORDER)
                    # ---------------------------------------------------------
                    elif order_invoice_type == 2:
                        if value.get('payment_method_description', '') == "Pago inmediato":
                            continue

                        formatted_line_items = self._format_line_items_sale_order(
                            invoice_line_items.get(external_mobilvendor_id, []),
                            company_id=company_id)

                        if not formatted_line_items:
                            continue

                        try:
                            pricelist_id = int(value.get('price_list_code'))
                        except (TypeError, ValueError):
                            pricelist_id = 1

                        try:
                            status_mb = int(value.get('status'))
                        except (TypeError, ValueError):
                            status_mb = 2

                        warehouse = None
                        try:
                            stock_location_id = int(value.get('org_storage_code'))
                            stock_location = self.env['stock.location'].search([('id', '=', stock_location_id)],
                                                                               limit=1)
                            warehouse = stock_location.warehouse_id if stock_location else None
                        except (TypeError, ValueError):
                            pass

                        sale_order_vals = {
                            'partner_id': res_partner.id,
                            'partner_invoice_id': res_partner.id,
                            'partner_shipping_id': res_partner.id,
                            'date_order': date_create_obj,
                            'team_id': 1,
                            'currency_id': 2,
                            'company_id': company_id,
                            'pricelist_id': pricelist_id,
                            'user_id': user_id,
                            'order_line': formatted_line_items,
                            'mobilvendor_id': external_mobilvendor_id,
                        }
                        if warehouse:
                            sale_order_vals['warehouse_id'] = warehouse.id

                        sale_order = self.env['sale.order'].sudo().create(sale_order_vals)

                        if status_mb != 0:
                            try:
                                if warehouse and warehouse.id == 1:
                                    sale_order.action_confirm()
                            except Exception as e:
                                _logger.error(f"Error during order confirmation: {e}")

                    # ---------------------------------------------------------
                    # TYPE 3 (INTERNAL TRANSFER)
                    # ---------------------------------------------------------
                    elif order_invoice_type == 3:
                        partner_id = res_partner.id if res_partner else None
                        self._mobilvendor_update_inventory_storages(
                            invoice_line_items.get(external_mobilvendor_id, []),
                            partner_id,
                            "TRANSFER",
                            dispatch_date=dispatch_date_obj,
                            route_id=route_id_odoo
                        )

            except Exception as e:
                # --- ATOMICITY HANDLER ---
                # If ANY error occurs inside the savepoint (Invoice creation, Posting, or Inventory Stock Picking),
                # Odoo automatically rolls back changes for THIS iteration only.
                _logger.error(f"FAILED PROCESSING INVOICE {external_mobilvendor_id}: {str(e)}")
                # Continue loop to process the next invoice
                continue

        return number_of_pages > page

    def _mobilvendor_cancel_invoice(self, invoice, external_mobilvendor_id):
        """
        Cancels an invoice in Odoo and rolls back any associated inventory movements.
        """
        # 1. Unreconcile and Cancel Invoice
        if invoice.state != 'cancel':
            # Unreconcile payments if any
            if invoice.payment_state in ('paid', 'in_payment', 'partial'):
                invoice.lines.remove_move_reconcile()
            invoice.button_cancel()

        # 2. Reverse Inventory
        moves = self.env['stock.move'].sudo().search([('mobilvendor_id', '=', external_mobilvendor_id)])
        pickings = moves.mapped('picking_id').filtered(lambda p: p.state == 'done')
        
        for picking in pickings:
            # Check if it already has a return in progress or done
            existing_return = self.env['stock.picking'].sudo().search([
                ('origin', 'ilike', picking.name),
                ('state', 'not in', ['cancel'])
            ], limit=1)
            
            if existing_return:
                continue
                
            try:
                # In Odoo 18, product_return_moves inside stock.return.picking is a computed field.
                # When we create the wizard with the picking_id, it is automatically computed.
                # action_create_returns_all() calculates the max quantities and safely returns the new picking.
                return_wizard = self.env['stock.return.picking'].with_context(
                    active_ids=picking.ids, active_id=picking.id).create({
                        'picking_id': picking.id
                })
                
                new_picking_res = return_wizard.action_create_returns_all()
                
                if isinstance(new_picking_res, dict):
                    new_picking_id = new_picking_res.get('res_id')
                elif isinstance(new_picking_res, tuple):
                    new_picking_id = new_picking_res[0]
                elif hasattr(new_picking_res, 'id'):
                    new_picking_id = new_picking_res.id
                else:
                    new_picking_id = new_picking_res
                    
                if new_picking_id:
                    new_return_picking = self.env['stock.picking'].sudo().browse(new_picking_id)
                    new_return_picking.action_confirm()
                    new_return_picking.action_assign()
                    
                    for move in new_return_picking.move_ids:
                        move.quantity = move.product_uom_qty
                        if hasattr(move, 'picked'):
                            move.picked = True
                        
                    res = new_return_picking.button_validate()
                    if isinstance(res, dict) and res.get('res_model'):
                        wizard = self.env[res['res_model']].with_context(res.get('context', {})).create({})
                        if hasattr(wizard, 'process'):
                            wizard.process()
                    _logger.info(f"Successfully reversed inventory picking {picking.name} for annulled invoice {external_mobilvendor_id}")
            except Exception as e:
                _logger.error(f"Error trying to reverse inventory for picking {picking.name}: {e}")

    def _get_identification_type_id(self, name_ilike):
        """
        Helper method to retrieve the ID of a specific identification type using the ORM.

        This method performs a case-insensitive search for an active identification type
        matching the provided name pattern. It provides a safer abstraction layer compared
        to executing raw SQL queries.

        :param name_ilike: The name pattern to search for (e.g., 'RUC', 'Cedula').
        :return: The database ID (int) of the found record, or None if not found.
        """
        # Search for an active identification type matching the name pattern (case-insensitive)
        identification_type = self.env['l10n_latam.identification.type'].search([
            ('name', 'ilike', name_ilike),
            ('active', '=', True)
        ], limit=1)

        # Return the ID if the record exists, otherwise return None
        return identification_type.id if identification_type else None

    def _create_new_customer(self, customer_data={}, is_contact=True):
        """
        Creates a new customer or address record in Odoo based on Mobilvendor data.

        This method handles the mapping of identification types (RUC, Cedula, Passport)
        specific to the localization, formats the identification numbers, and sets up
        initial contact details, payment terms, and customer categories.

        :param customer_data: Dictionary containing raw customer data from the API.
        :param is_contact: Boolean indicating if this is a main contact (True) or a delivery address (False).
        :return: The created 'res.partner' record.
        """
        # Prevent creation of inactive or empty customer records to maintain database hygiene
        if not customer_data.get("active"):
            return

        if not customer_data:
            return

        identity_type_id = None
        identification_number = None
        identification_mobilvendor = customer_data.get("identification")

        identity_type = customer_data.get("identity_type")

        # --- Identification Type Mapping and Formatting ---
        # Logic to map API identity keys (C, R, D) to Odoo L10n Latam types.
        # Includes formatting to ensure fixed-length requirements (padding/slicing).
        if identity_type == "C":
            identity_type_id = self._get_identification_type_id('%Cédula%')
            if identity_type_id and identification_mobilvendor:
                # FIX: Removed [:10] slicing to respect Nicaragua's 14-char ID
                identification_number = str(identification_mobilvendor).strip()
            elif identity_type_id:
                identification_number = "0000000000"

        elif identity_type == "R":
            identity_type_id = self._get_identification_type_id('%RUC%')
            if identity_type_id and identification_mobilvendor:
                # FIX: Removed [:13] slicing to respect Nicaragua's 14-char RUC
                identification_number = str(identification_mobilvendor).strip()
            elif identity_type_id:
                identification_number = "0000000000000"

        elif identity_type == "D":
            identity_type_id = self._get_identification_type_id('%Passport%')
            if identity_type_id and identification_mobilvendor:
                # FIX: Removed [:10] slicing
                identification_number = str(identification_mobilvendor).strip()
            elif identity_type_id:
                identification_number = "0000000000"

        # Default to Nicaragua (base.ni) if the reference exists
        country_id = self.env.ref('base.ni', raise_if_not_found=False)

        # Map API fields to Odoo res.partner fields
        partner_vals = {
            'name': customer_data.get("name", "NO-NAME"),
            'commercial_company_name': customer_data.get("commercial_company_name"),
            'mobilvendor_id': str(customer_data.get("code")) if customer_data.get("code") else None,
            'company_id': self.company.id,
            'country_id': country_id.id if country_id else False,
            'lang': 'es_ES',
            'tz': 'America/Managua',
            'type': 'contact' if is_contact else 'delivery',
            'l10n_latam_identification_type_id': identity_type_id,
            'phone': customer_data.get("phone"),
            'street': customer_data.get("street"),
            'street2': customer_data.get("street2"),
            'zip': customer_data.get("zip"),
            'email': customer_data.get("email"),
            'partner_latitude': customer_data.get("partner_latitude"),
            'partner_longitude': customer_data.get("partner_longitude"),
            'contact_address_complete': customer_data.get("contact_address_complete"),
            'vat': identification_number,
            'address_mobilvendor_id': str(customer_data.get("address_mobilvendor_id")) if customer_data.get(
                "address_mobilvendor_id") else None,
            'parent_id': customer_data.get("parent_id")
        }

        if is_contact:
            payment_method_code = customer_data.get("payment_method_code")
            price_list_code = customer_data.get("price_list_code")
            default_receivable = self.company.partner_id.property_account_receivable_id

            if default_receivable:
                partner_vals['property_account_receivable_id'] = default_receivable.id

            if payment_method_code:
                try:
                    # Assign the Payment Term ID based on the code provided
                    partner_vals['property_payment_term_id'] = int(payment_method_code)
                except (ValueError, TypeError):
                    _logger.warning(f"Invalid payment_method_code: {payment_method_code}")

            # Uncomment if the pricelist module logic is required
            # if price_list_code:
            #     try:
            #         # Assign the Pricelist ID
            #         partner_vals['property_product_pricelist'] = int(price_list_code)
            #     except (ValueError, TypeError):
            #         _logger.warning(f"Invalid price_list_code: {price_list_code}")

        _logger.debug(f"Creating res.partner with vals: {partner_vals}")

        # Create the partner record with elevated privileges
        new_partner = self.env['res.partner'].sudo().create(partner_vals)

        # --- Assign Customer Groups/Tags ---
        if is_contact and customer_data.get("customer_group_code"):
            try:
                customer_group_code_int = int(customer_data.get("customer_group_code"))
                # Check if the category exists in the database
                if self.env['res.partner.category'].search_count([('id', '=', customer_group_code_int)]) > 0:
                    if customer_group_code_int not in new_partner.category_id.ids:
                        # Use Odoo's M2M command (4, id) to link the partner to the category
                        new_partner.sudo().write({
                            'category_id': [(4, customer_group_code_int)]
                        })
                else:
                    _logger.warning(f"Customer category ID {customer_group_code_int} not found.")
            except (ValueError, TypeError):
                _logger.warning(f"Invalid customer_group_code: {customer_data.get('customer_group_code')}")

        return new_partner

    def _process_customer_addresses_object(self, all_customer_addresses=None, page=1):
        """
        Retrieves and processes customer address data from the API across multiple pages.

        This recursive method fetches address records, parses them into a standardized
        dictionary format, and accumulates them into the 'all_customer_addresses' mapping.

        :param all_customer_addresses: Dictionary accumulator for address data (keyed by address code).
        :param page: Current page number for API pagination.
        :return: Dictionary containing all processed address records.
        """
        if all_customer_addresses is None:
            all_customer_addresses = {}

        # Execute the API request for the specific page
        customer_response = self._send_get_request(action="get", schema="customer_addresses", page=page)

        if "records" not in customer_response:
            raise UserError(f"Invalid response for Get Routes")

        number_of_pages = customer_response.get("pages", 1)

        for record in customer_response.get("records", []):
            # Extract the necessary IDs directly
            api_addr_id = record.get("code")  # e.g., 'PRINCIPAL'
            api_parent_id = record.get("customer_code")  # e.g., 'CLMR000001'

            if not api_addr_id or not api_parent_id:
                continue

            # FIX: Use composite key to prevent overwriting identical addresses like 'PRINCIPAL'
            composite_key = (str(api_parent_id), str(api_addr_id))

            # Parse geolocation data
            lat_float = float(record.get("lat")) if record.get("lat") else None
            lon_float = float(record.get("lon")) if record.get("lon") else None

            # Map API fields to internal dictionary structure
            all_customer_addresses[composite_key] = {
                'commercial_company_name': record.get("description"),
                'phone': record.get("phone"),
                'street': record.get("street1"),
                'street2': record.get("street2"),
                'zip': record.get("zipcode"),
                'email': record.get("email"),
                'partner_latitude': lat_float,
                'partner_longitude': lon_float,
                'contact_address_complete': record.get("reference"),
                'address_mobilvendor_id': api_addr_id,
                'parent_id': api_parent_id,
                'active': record.get("status", "0") == "1"
                # Add as many fields as needed
            }

        # Handle pagination recursively if more pages exist
        if number_of_pages > page:
            return self._process_customer_addresses_object(page=page + 1, all_customer_addresses=all_customer_addresses)

        return all_customer_addresses

    def _mobilvendor_update_customer(self, odoo_customer, mobilvendor_customer, customer_key):
        """
        Compares Odoo partner data (from a query) with Mobilvendor data (from API)
        and updates the Odoo record if discrepancies are found.

        :param odoo_customer: dict of Odoo partner data (from a custom query).
        :param mobilvendor_customer: dict of Mobilvendor customer data (from API).
        :param customer_key: The primary identifier (code/ID) for the customer.
        """
        # --- Data Extraction ---
        # Extract fields from both Mobilvendor (API) and Odoo (query) dictionaries

        # Pricelist and Payment Method handling
        price_list_code_mb = int(mobilvendor_customer.get("price_list_code")) if mobilvendor_customer.get(
            "price_list_code") else None
        price_list_code_odoo = odoo_customer.get("price_list_code")

        payment_method_code_mb = int(mobilvendor_customer.get("payment_method_code")) if mobilvendor_customer.get(
            "payment_method_code") else None
        payment_method_code_odoo = odoo_customer.get("payment_method_code")

        # Basic fields
        name_mb = mobilvendor_customer.get("name")
        name_odoo = odoo_customer.get("customer_name")

        commercial_company_name_mb = mobilvendor_customer.get("company_name")
        commercial_company_name_odoo = odoo_customer.get("company_name")

        # Status / Active
        is_active_mb = mobilvendor_customer.get("status") == "1"
        is_active_odoo = odoo_customer.get("active")

        # Identification Data (Raw)
        identity_type_mb = mobilvendor_customer.get("identity_type")
        identity_number_mb_raw = mobilvendor_customer.get("identity_")  # Raw value from API
        identity_number_odoo = odoo_customer.get("identity_")

        customer_mobilvendor_odoo_id = odoo_customer.get("mobilvendor_id")

        # --- Data Normalization (Pre-Calculation) ---
        # We normalize the API ID number based on type.
        identification_number_mb = None

        if identity_type_mb == "C":
            if identity_number_mb_raw:
                # identification_number_mb = identity_number_mb_raw.ljust(10, '0')[:10]
                identification_number_mb = identity_number_mb_raw.strip()
            else:
                identification_number_mb = "0000000000"
        elif identity_type_mb == "R":
            if identity_number_mb_raw:
                # identification_number_mb = identity_number_mb_raw.ljust(13, '0')[:13]
                identification_number_mb = identity_number_mb_raw.strip()
            else:
                identification_number_mb = "0000000000000"
        elif identity_type_mb == "D":
            if identity_number_mb_raw:
                identification_number_mb = identity_number_mb_raw.strip()
            else:
                identification_number_mb = "0000000000"
        else:
            # FALLBACK: If type is unknown or empty, use the raw number stripped.
            # This fixes issues where API sends valid numbers but invalid types.
            if identity_number_mb_raw:
                identification_number_mb = identity_number_mb_raw.strip()
            else:
                identification_number_mb = None

        # --- Robust Comparison Logic ---
        # Convert to string and strip to ensure " 123" equals "123" and prevent False != "" errors
        vat_api_clean = str(identification_number_mb).strip() if identification_number_mb else ""
        vat_odoo_clean = str(identity_number_odoo).strip() if identity_number_odoo else ""

        # Check if VAT has effectively changed
        vat_has_changed = (vat_api_clean != vat_odoo_clean) and (vat_api_clean != "")

        # Check if valid company_id from existing customer
        valid_company = odoo_customer.get('company_id')

        # --- Main Comparison Check ---
        # Proceed only if differences are detected or if mobilvendor_id is missing.
        if (
                price_list_code_mb != price_list_code_odoo or
                is_active_mb != is_active_odoo or
                payment_method_code_mb != payment_method_code_odoo or
                name_mb != name_odoo or
                commercial_company_name_mb != commercial_company_name_odoo or
                vat_has_changed or
                not customer_mobilvendor_odoo_id
        ):

            partner = None
            if customer_key:
                # 1. Search by mobilvendor_id string
                partner = self.env['res.partner'].sudo().search([
                    ('mobilvendor_id', '=', customer_key)
                ], limit=1)

                # 2. Fallback: Search by ID int
                if not partner:
                    try:
                        customer_key_int = int(customer_key)
                        partner = self.env['res.partner'].sudo().search([
                            ('id', '=', customer_key_int)
                        ], limit=1)
                    except (TypeError, ValueError):
                        pass

            if partner:
                _logger.debug(f"Partner match found: {partner.id} for external key {customer_key}")

                # --- Build Update Payload ---
                vals = {
                    'mobilvendor_id': str(customer_key)
                }

                if not valid_company:
                    vals['company_id'] = self.company.id

                # Add fields only if they changed
                if is_active_mb != is_active_odoo:
                    vals['active'] = is_active_mb

                if name_mb != name_odoo:
                    vals['name'] = name_mb

                if commercial_company_name_mb != commercial_company_name_odoo:
                    vals['commercial_company_name'] = commercial_company_name_mb

                # VAT Update Logic:
                # Update ONLY the number ('vat'). Do NOT update the document type ID.
                if vat_has_changed:
                    vals['vat'] = vat_api_clean
                    _logger.info(
                        f"Customer {customer_key}: VAT changed from '{vat_odoo_clean}' to '{vat_api_clean}'. Updating VAT only.")

                # Payment Term Logic
                if payment_method_code_mb != payment_method_code_odoo:
                    try:
                        vals['property_payment_term_id'] = int(payment_method_code_mb)
                    except (TypeError, ValueError):
                        _logger.debug(f"Invalid payment term ID: {payment_method_code_mb}")

                # Pricelist Logic (Uncomment if needed)
                # if price_list_code_mb != price_list_code_odoo:
                #     try:
                #         vals['property_product_pricelist'] = int(price_list_code_mb)
                #     except (TypeError, ValueError):
                #         pass

                # --- Execute Write Operation ---
                if len(vals) > 1:  # If there are changes other than just 'mobilvendor_id'
                    _logger.debug(f"Updating partner {partner.id} with vals: {vals}")
                    partner.sudo().write(vals)
                else:
                    _logger.debug(f"No significant changes detected for partner {partner.id}")

    def _mobilvendor_update_customer_address(self, odoo_customer, mobilvendor_customer, api_addr_id):
        """
        Updates an existing customer address record in Odoo if changes are detected from Mobilvendor.

        This method compares specific address fields (phone, street, coordinates, zip)
        between the current Odoo record and the incoming API data. If discrepancies exist,
        it updates the Odoo record, prioritizing non-empty values from Mobilvendor.

        :param odoo_customer: Dictionary containing current Odoo address data.
        :param mobilvendor_customer: Dictionary containing new address data from the API.
        :param api_addr_id: The specific address ID from API (e.g., 'PRINCIPAL').
        """
        # Extract fields from both sources for comparison
        address_mobilvendor_id_mb = mobilvendor_customer.get("address_mobilvendor_id")
        address_mobilvendor_id_odoo = odoo_customer.get("address_mobilvendor_id")

        phone_mb = mobilvendor_customer.get("phone")
        phone_odoo = odoo_customer.get("phone")

        street_mb = mobilvendor_customer.get("street")
        street_odoo = odoo_customer.get("street1")

        street2_mb = mobilvendor_customer.get("street2")
        street2_odoo = odoo_customer.get("street2")

        zip_mb = mobilvendor_customer.get("zip")
        zip_odoo = odoo_customer.get("zipcode")

        partner_latitude_mb = mobilvendor_customer.get("partner_latitude")
        partner_latitude_odoo = odoo_customer.get("lat")

        partner_longitude_mb = mobilvendor_customer.get("partner_longitude")
        partner_longitude_odoo = odoo_customer.get("lon")

        # Check if any field values differ between the systems
        if (
                address_mobilvendor_id_mb != address_mobilvendor_id_odoo or
                phone_mb != phone_odoo or
                partner_longitude_mb != partner_longitude_odoo or
                street_mb != street_odoo or
                street2_mb != street2_odoo or
                zip_mb != zip_odoo or
                partner_latitude_mb != partner_latitude_odoo
        ):
            # FIX: Use the exact database ID already stored in memory to prevent
            # overwriting other addresses with generic names like 'PRINCIPAL'
            odoo_partner_id = odoo_customer.get('code')

            if odoo_partner_id:
                partner = self.env['res.partner'].sudo().browse(odoo_partner_id)

                if partner.exists():
                    # Prepare the update dictionary
                    # Logic: Use Mobilvendor value if present; otherwise, retain existing Odoo value
                    vals = {
                        'phone': phone_mb if phone_mb else phone_odoo,
                        'address_mobilvendor_id': str(api_addr_id),
                        'partner_latitude': partner_latitude_mb if partner_latitude_mb not in [None, 0,
                                                                                               0.0] else partner_latitude_odoo,
                        'partner_longitude': partner_longitude_mb if partner_longitude_mb not in [None, 0,
                                                                                                  0.0] else partner_longitude_odoo,
                        'zip': zip_mb if zip_mb else zip_odoo,
                        'street': street_mb if street_mb else street_odoo,
                        'street2': street2_mb if street2_mb else street2_odoo
                    }

                    # Apply changes to the exact database record
                    try:
                        partner.sudo().with_context(
                            tracking_disable=True,
                            mail_create_nosubscribe=True,
                            mail_notrack=True
                        ).write(vals)
                    except Exception as e:
                        _logger.error(f"Error updating customer address {api_addr_id}: {e}")
            else:
                _logger.warning(f"Could not update address {api_addr_id}: Odoo Database ID not found in memory.")

    def _mobilvendor_get_routes(self, page=1):
        """
        Synchronizes sales routes from Mobilvendor to Odoo.

        This method fetches routes from the API. It performs an UPSERT operation:
        - If the route exists (matched by mobilvendor_id), it updates the name and status.
        - If it does not exist, it creates a new route record.

        Manual configuration fields (Journals, Warehouse, Agency) are NOT touched during update.

        :param page: Current page number for API pagination.
        """
        _logger.info("##################### get routes ##############################")

        filter_route_type = {
            "type": "0"
        }

        route_response = self._send_get_request(action="get", schema="routes", page=page, filter=filter_route_type)

        if "records" not in route_response:
            raise UserError(f"Invalid response for Get Routes")

        number_of_pages = route_response.get("pages", 1)
        api_records = route_response.get("records", [])

        # Optimization: Pre-load existing routes into a dictionary to avoid N+1 queries.
        # Structure: { 'MV_CODE': record_object }
        _logger.debug("Odoo ORM: Loading existing routes into cache...")
        existing_routes = self.env['mobilvendor.route'].search([('mobilvendor_id', '!=', False)])
        routes_map = {r.mobilvendor_id: r for r in existing_routes}

        for record in api_records:
            mv_code = record.get('code')
            description = record.get('description')
            status = record.get('status')  # '1' = Active, '0' = Inactive/Deleted

            # Validation: Ensure essential data exists
            if not mv_code:
                _logger.warning(f"Skipping route record without code: {record}")
                continue

            # Prepare values for Odoo
            is_active = True if status == '1' else False

            vals = {
                'name': description or 'NO-NAME',
                'active': is_active
            }

            # Scenario 1: Update existing route
            if mv_code in routes_map:
                route = routes_map[mv_code]

                # Check if update is actually needed to save resources
                if route.name != vals['name'] or route.active != vals['active']:
                    route.write(vals)
                    _logger.info(f"Route Updated: {mv_code} - {description}")

            # Scenario 2: Create new route
            else:
                # Add the ID to the creation dictionary
                create_vals = vals.copy()
                create_vals['mobilvendor_id'] = mv_code

                # Note: We do NOT set journals or warehouses here.
                # Those are manual configurations in Odoo.
                self.env['mobilvendor.route'].sudo().create(create_vals)
                _logger.info(f"Route Created: {mv_code} - {description}")

        # Commit transaction after processing the batch
        self.env.cr.commit()

        # Recursive call to fetch the next page if available
        if number_of_pages > page:
            self._mobilvendor_get_routes(page=page + 1)

    def _mobilvendor_get_route_details(self, page=1, route_map=None, partner_address_map=None):
        """
        Synchronizes route details (itineraries) from Mobilvendor to Odoo.
        Optimized with Batch Search to avoid N+1 queries.
        """
        _logger.info(f"##################### Get Route Details - Page {page} ##############################")

        response = self._send_get_request(action="get", schema="route_details", page=page)

        if "records" not in response:
            raise UserError(f"Invalid response for Get Route Details")

        number_of_pages = response.get("pages", 1)
        api_records = response.get("records", [])

        # ---------------------------------------------------------
        # 1. GLOBAL CACHES (Built once and passed recursively)
        # ---------------------------------------------------------

        # A. Route Cache
        if route_map is None:
            _logger.debug("Odoo ORM: Building Route Cache...")
            routes = self.env['mobilvendor.route'].sudo().search([('mobilvendor_id', '!=', False)])
            route_map = {r.mobilvendor_id: r.id for r in routes}

        # B. Partner Cache
        if partner_address_map is None:
            _logger.debug("Odoo ORM: Building Partner Address Cache...")
            domain = [('address_mobilvendor_id', '!=', False), ('parent_id', '!=', False)]
            partners = self.env['res.partner'].sudo().search(domain)
            partner_address_map = {}
            for p in partners:
                parent_code = p.parent_id.mobilvendor_id
                addr_code = p.address_mobilvendor_id
                if parent_code and addr_code:
                    key = (str(parent_code), str(addr_code))
                    partner_address_map[key] = p.id

        # ---------------------------------------------------------
        # 2. BATCH CACHE (Built for the current API page only)
        #    Optimization: Fetch all existing lines for this batch in 1 query
        # ---------------------------------------------------------

        # Extract all IDs from the current API page
        batch_mv_ids = [rec.get('code') for rec in api_records if rec.get('code')]

        # Search in Odoo using 'IN' operator
        # active_test=False is CRITICAL to find archived records too
        existing_lines = self.env['mobilvendor.route.line'].sudo().with_context(active_test=False).search([
            ('mobilvendor_id', 'in', batch_mv_ids)
        ])

        # Map: { '688fff...': record_object }
        lines_map = {line.mobilvendor_id: line for line in existing_lines}

        # ---------------------------------------------------------
        # 3. PROCESS RECORDS (Loop)
        # ---------------------------------------------------------
        for record in api_records:
            try:
                mv_line_id = record.get('code')
                route_code = record.get('route_code')
                customer_code = record.get('customer_code')
                addr_code = record.get('customer_address_code')
                status = record.get('status')

                if not mv_line_id or not route_code:
                    continue

                # 3.1 Resolve IDs from Global Cache
                route_id = route_map.get(route_code)
                if not route_id:
                    _logger.warning(f"Route not found for code {route_code}. Skipping line.")
                    continue

                partner_key = (str(customer_code), str(addr_code))
                partner_address_id = partner_address_map.get(partner_key)

                if not partner_address_id:
                    # _logger.debug(f"Address not found for key {partner_key}. Skipping visit.")
                    continue

                # 3.2 Prepare Values
                is_active = True if status == '1' else False

                vals = {
                    'route_id': route_id,
                    'partner_address_id': partner_address_id,
                    'mobilvendor_id': mv_line_id,
                    'day': str(record.get('day')),
                    'week': int(record.get('week', 1)),
                    'sequence': int(record.get('sequence', 0)),
                    'active': is_active
                }

                # 3.3 UPSERT using Batch Cache (Dictionary Lookup = O(1))
                existing_line = lines_map.get(mv_line_id)

                if existing_line:
                    # Optional Optimization: Only write if values changed
                    if existing_line.active != is_active or existing_line.day != vals[
                        'day'] or existing_line.sequence != vals['sequence']:
                        existing_line.sudo().write(vals)
                else:
                    self.env['mobilvendor.route.line'].sudo().create(vals)

            except Exception as e:
                _logger.error(f"Error processing route detail {record.get('code')}: {str(e)}")
                continue

        # 4. Commit transaction
        self.env.cr.commit()

        # 5. Recursive call
        if number_of_pages > page:
            self._mobilvendor_get_route_details(page=page + 1, route_map=route_map,
                                                partner_address_map=partner_address_map)

    def _mobilvendor_get_customers(self, page=1, odoo_customer_records={}, customer_addrs={}, api_filter=None):
        """
        Synchronizes customer data from Mobilvendor to Odoo.

        This method fetches customers from the API page by page. It uses an efficient
        caching mechanism (`odoo_customer_records`) to minimize database reads by
        loading existing Odoo partners into memory on the first page load. It then
        iterates through the API data to either create new partners or update existing ones.

        :param page: Current page number for API pagination.
        :param odoo_customer_records: Cache dictionary of existing Odoo customers {mobilvendor_id: data}.
        :param customer_addrs: Cache dictionary for customer addresses (currently unused in this block but passed recursively).
        """
        _logger.info("##################### get customers ##############################")

        customer_response = self._send_get_request(action="get", schema="customers", page=page, filter=api_filter or {})

        if "records" not in customer_response:
            raise UserError(f"Invalid response for Get Customers")

        number_of_pages = customer_response.get("pages", 1)

        batch_size = 25  # Set batch size

        # Initialize the Odoo customer cache only on the first page or if empty
        if not odoo_customer_records:

            _logger.debug("Odoo ORM: Searching for existing clients with mobilvendor_id...")

            # 1. Execute ORM search to find existing synchronized partners (excluding contacts/children)
            odoo_partners = self.env['res.partner'].sudo().search([
                ('mobilvendor_id', '!=', False),
                ('mobilvendor_id', '!=', ''),
                ('parent_id', '=', False),
                # ('active', '=', True), # Logic for activation/inactivation to be considered
                # ('company_id', '=', self.company.id)
            ])

            _logger.debug(f"Odoo ORM: Found {len(odoo_partners)} clients.")

            customer_odoo_dict = {}

            # 2. Iterate results and build the comparison dictionary
            for partner in odoo_partners:
                # Normalize identification type names for comparison
                identity_type_name = partner.l10n_latam_identification_type_id.name or ''
                identity_type = 'C'  # Default value (Cedula)
                if 'RUC' in identity_type_name.upper():
                    identity_type = 'R'
                elif 'CÉDULA' in identity_type_name.upper():
                    identity_type = 'C'
                elif 'PASSPORT' in identity_type_name.upper():
                    identity_type = 'D'

                # Retrieve the first category ID as the group code
                customer_group_code = partner.category_id[0].id if partner.category_id else None

                # 3. Create 'result_dict' mapping Odoo fields to API-compatible keys for later comparison
                result_dict = {
                    'code': partner.id,  # Internal Odoo ID
                    'customer_name': partner.name,
                    'price_list_code': partner.property_product_pricelist.id,
                    'payment_method_code': partner.property_payment_term_id.id,
                    'customer_group_code': customer_group_code,
                    'company_name': partner.commercial_company_name,
                    'comment': partner.company_id.name,
                    'mobilvendor_id': partner.mobilvendor_id,
                    'id_identification_type': partner.l10n_latam_identification_type_id.id,
                    'identity_type': identity_type,
                    'identity_': partner.vat,
                    'active': partner.active,
                    'company_id': partner.company_id
                }

                # 4. Use mobilvendor_id as the dictionary key for O(1) lookup
                try:
                    mobilvendor_id_code = int(result_dict['mobilvendor_id'])
                except (TypeError, ValueError):
                    mobilvendor_id_code = result_dict['mobilvendor_id']

                # Overwrite 'code' with the external ID for the comparison logic in the loop
                result_dict['code'] = mobilvendor_id_code
                customer_odoo_dict[mobilvendor_id_code] = result_dict

        else:
            # Reuse the cache passed from the previous recursion
            customer_odoo_dict = odoo_customer_records

        total_customers = customer_response.get("records", [])
        total_customers_len = len(total_customers)

        # Process API records in batches
        for start in range(0, total_customers_len, batch_size):
            try:
                batch_customers = total_customers[start:start + batch_size]
                for record in batch_customers:
                    is_int_code = False
                    try:
                        customer_key = int(record.get("code"))  # Convert if it's a valid integer string
                        is_int_code = True
                    except (TypeError, ValueError):
                        customer_key = record.get("code")  # Handle invalid or None values

                    # We want to know if the client already exists in Odoo with a valid ID but doesn't
                    # have the mobilvendor_id defined
                    if is_int_code and customer_key not in customer_odoo_dict:
                        # we search directly in the res partner table
                        existing_partner_by_id = self.env['res.partner'].browse(customer_key)

                        if existing_partner_by_id.exists():
                            _logger.info(f"Match Found! Linking Odoo ID {customer_key} to Mobilvendor ID.")

                            existing_partner_by_id.sudo().write({
                                'mobilvendor_id': str(customer_key)
                            })

                            identity_type_name = existing_partner_by_id.l10n_latam_identification_type_id.name or ''
                            identity_type = 'C'
                            if 'RUC' in identity_type_name.upper():
                                identity_type = 'R'
                            elif 'CÉDULA' in identity_type_name.upper():
                                identity_type = 'C'
                            elif 'PASSPORT' in identity_type_name.upper():
                                identity_type = 'D'

                            result_dict = {
                                'code': existing_partner_by_id.id,
                                'customer_name': existing_partner_by_id.name,
                                'price_list_code': existing_partner_by_id.property_product_pricelist.id,
                                'payment_method_code': existing_partner_by_id.property_payment_term_id.id,
                                'customer_group_code': existing_partner_by_id.category_id[
                                    0].id if existing_partner_by_id.category_id else None,
                                'company_name': existing_partner_by_id.commercial_company_name,
                                'comment': existing_partner_by_id.company_id.name,
                                'mobilvendor_id': str(customer_key),
                                'id_identification_type': existing_partner_by_id.l10n_latam_identification_type_id.id,
                                'identity_type': identity_type,
                                'identity_': existing_partner_by_id.vat,
                                'active': existing_partner_by_id.active,
                                'company_id': existing_partner_by_id.company_id
                            }

                            customer_odoo_dict[customer_key] = result_dict

                    if customer_key:
                        if customer_key not in customer_odoo_dict and record.get("status") == '1':
                            customer_data = {
                                "price_list_code": record.get("price_list_code", ""),
                                "payment_method_code": record.get("payment_method_code", ""),
                                "customer_group_code": record.get("customer_group_code", ""),
                                "user_code": record.get("user_code", ""),
                                "routes": record.get("routes", ""),
                                "name": record.get("name", "NO-NAME"),
                                "code": customer_key,
                                "identity_type": record.get("identity_type"),
                                "commercial_company_name": record.get("company_name"),
                                "identification": record.get("identity_"),
                                "active": True if record.get("status", "0") else False
                            }

                            self._create_new_customer(customer_data=customer_data)

                        # Scenario 2: Customer exists in Odoo -> Check for updates
                        elif customer_key in customer_odoo_dict:
                            self._mobilvendor_update_customer(customer_odoo_dict.get(customer_key), record,
                                                              str(customer_key))
                # Commit transaction after processing each batch to save progress
                self.env.cr.commit()
            except Exception as e:
                _logger.error("Failed to update customers batch starting from ID %s: %s", batch_customers[0], e)
                # Rollback to undo changes made within the current batch if error occurs
                self.env.cr.rollback()

        # Recursive call to fetch the next page if available
        if number_of_pages > page:
            self._mobilvendor_get_customers(page=page + 1, odoo_customer_records=customer_odoo_dict,
                                            customer_addrs=customer_addrs, api_filter=api_filter)

    def _mobilvendor_get_customers_addrs(self):
        """
        Synchronizes customer addresses (delivery/shipping) from Mobilvendor to Odoo.

        Logic Update:
        This method uses a Composite Key (Parent External ID + Address ID) to identify
        records. This is necessary because 'address_mobilvendor_id' is unique per
        customer, but not globally unique across all customers.
        """
        _logger.info("##################### get customers addrs ##############################")

        # Fetch address data from the API
        customer_addrs = self._process_customer_addresses_object()

        # 1. Define search domain to find existing Mobilvendor addresses in Odoo
        domain = [
            ('address_mobilvendor_id', '!=', False),  # Must have an external ID
            ('address_mobilvendor_id', '!=', ''),
            ('parent_id', '!=', False),  # Must be a child record (address/contact)
            ('active', '=', True),
        ]

        # 2. Execute ORM search
        partner_addresses = self.env['res.partner'].sudo().search(domain)

        customer_odoo_dict = {}

        # 3. Iterate through Odoo results to build a cache dictionary for comparison
        for partner in partner_addresses:
            # Extract the first email if multiple are present
            first_email = ''
            if partner.email:
                emails = re.split(r'[,;\s]+', partner.email.strip())
                if emails:
                    first_email = emails[0]

            # Vital: We need the Parent's External ID to create the unique composite key.
            # If the parent partner in Odoo doesn't have 'mobilvendor_id' set, we skip it.
            parent_mb_id = partner.parent_id.mobilvendor_id
            if not parent_mb_id:
                continue

            # 4. Map Odoo fields to a standardized dictionary
            result_dict = {
                'code': partner.id,
                'customer_code': partner.parent_id.id,
                'description': (partner.name or '')[:25],
                'phone': partner.phone_sanitized,
                'street1': partner.street,
                'street2': partner.street2,
                'zipcode': partner.zip,
                'email': first_email,
                'lat': partner.partner_latitude,
                'lon': partner.partner_longitude,
                'reference': (partner.contact_address_complete or '')[:75],
                'address_mobilvendor_id': partner.address_mobilvendor_id,
                'parent_mobilvendor_id': parent_mb_id
            }

            # ### CHANGE 1: Create Composite Key (Parent External ID + Address External ID) ###
            # Convert to string to ensure type consistency (avoiding int vs str mismatches)
            key_parent = str(parent_mb_id)
            key_address = str(partner.address_mobilvendor_id)

            # The key is now a unique TUPLE
            composite_key = (key_parent, key_address)

            customer_odoo_dict[composite_key] = result_dict

        # Loop through API addresses to create or update records
        for api_composite_key, value in customer_addrs.items():

            # ### CHANGE 2: Construct the composite key from API data ###
            api_parent_id = value.get('parent_id')  # The Customer ID in Mobilvendor
            api_addr_id = value.get('address_mobilvendor_id')  # The Address ID (e.g., 'PRINCIPAL')

            # Validate existence of IDs
            if not api_parent_id or not api_addr_id:
                _logger.warning(f"Skipping record due to missing IDs: {value}")
                continue

            # Create the tuple structure to compare against Odoo dictionary
            api_composite_key = (str(api_parent_id), str(api_addr_id))

            # Case 1: The combination (Customer + Address) does not exist in Odoo -> Create
            if api_composite_key not in customer_odoo_dict:
                try:
                    addr_id_int = int(api_addr_id)
                    existing_addr_by_id = self.env['res.partner'].browse(addr_id_int)

                    if existing_addr_by_id.exists() and not existing_addr_by_id.address_mobilvendor_id:
                        # Validate existing user with a valid Mobilvendor id (this field must be set inside the get customer method)
                        parent_mb_id = existing_addr_by_id.parent_id.mobilvendor_id
                        if not parent_mb_id:
                            continue

                        existing_addr_by_id.sudo().write({
                            'address_mobilvendor_id': str(api_addr_id),
                            'mobilvendor_id': str(parent_mb_id)
                        })

                        first_email = ''
                        if existing_addr_by_id.email:
                            emails = re.split(r'[,;\s]+', existing_addr_by_id.email.strip())
                            if emails:
                                first_email = emails[0]

                        result_dict = {
                            'code': existing_addr_by_id.id,
                            'customer_code': existing_addr_by_id.parent_id.id,
                            'description': (existing_addr_by_id.name or '')[:25],
                            'phone': existing_addr_by_id.phone_sanitized,
                            'street1': existing_addr_by_id.street,
                            'street2': existing_addr_by_id.street2,
                            'zipcode': existing_addr_by_id.zip,
                            'email': first_email,
                            'lat': existing_addr_by_id.partner_latitude,
                            'lon': existing_addr_by_id.partner_longitude,
                            'reference': (existing_addr_by_id.contact_address_complete or '')[:75],
                            'address_mobilvendor_id': existing_addr_by_id.address_mobilvendor_id,
                            'parent_mobilvendor_id': parent_mb_id
                        }

                        # Call update method (passing the specific address ID from API)
                        self._mobilvendor_update_customer_address(result_dict, value, api_addr_id)

                except (TypeError, ValueError):

                    # Resolve the Parent Partner (Customer) Record
                    if isinstance(api_parent_id, int):
                        # Search by Odoo Database ID (if API sends Odoo IDs)
                        partner_record = self.env['res.partner'].search([('id', '=', api_parent_id)], limit=1)
                    else:
                        # Search by Mobilvendor External ID (Most common scenario)
                        partner_record = self.env['res.partner'].search([('mobilvendor_id', '=', api_parent_id)], limit=1)

                    if partner_record:
                        customer_data = {
                            "name": value.get("commercial_company_name", "NO-NAME"),
                            "parent_id": partner_record.id,
                            "address_mobilvendor_id": value.get("address_mobilvendor_id"),
                            "phone": value.get("phone"),
                            "street": value.get("street"),
                            "street2": value.get("street2"),
                            "zip": value.get("zip"),
                            "email": value.get("email"),
                            "partner_latitude": value.get("partner_latitude"),
                            "partner_longitude": value.get("partner_longitude"),
                            "contact_address_complete": value.get("contact_address_complete"),
                            "code": value.get("parent_id"),
                            "active": value.get("active")
                        }

                        # Create the address record (is_contact=False ensures it's treated as an address)
                        self._create_new_customer(customer_data=customer_data, is_contact=False)
                    else:
                        _logger.warning(f"Parent partner with ID {api_parent_id} not found. Cannot create address.")

            # Case 2: Address exists in Odoo -> Update if necessary
            else:

                # Retrieve existing data using the composite key
                existing_data = customer_odoo_dict.get(api_composite_key)

                # Call update method (passing the specific address ID from API)
                self._mobilvendor_update_customer_address(existing_data, value, api_addr_id)

    def _mobilvendor_get_payments(self, page=1, date=None):
        """
        Main controller method for synchronizing payments from Mobilvendor.

        This method manages the pagination loop and ensures database transaction safety.
        It iterates through API pages, processing each one in a separate, isolated
        database cursor. This "batch commit" strategy prevents memory overloads and
        ensures that a failure in one page does not roll back valid data from previous pages.

        :param page: The starting page number for the API request (default 1).
        :param date: Optional datetime object to filter payments by date. Defaults to today.
        """
        current_page = 1
        has_more_pages = True

        # Determine the date filter: use the provided date or default to today
        if date is None:
            date_obj = fields.Date.today()
        else:
            date_obj = date
        date_str = date_obj.strftime('%Y-%m-%d')

        _logger.info("Starting batch payment synchronization...")

        while has_more_pages:
            _logger.info(f"Starting processing of payment page: {current_page}")

            try:
                # --- CRITICAL: Safe Transaction Handling ---
                # Create an independent cursor
                with self.env.registry.cursor() as new_cr:

                    # 1. Create the new environment (env)
                    new_env = self.env(cr=new_cr)

                    # 2. Get the company record in this NEW environment
                    # This is necessary so that any write linked to the company uses new_cr
                    company_in_new_env = new_env['res.company'].browse(self.company.id)

                    # 3. Re-instantiate the current class (MobilvendorAPIHandler)
                    # Use self.__class__ to refer to the same class regardless of its name
                    handler_new_env = self.__class__(company_in_new_env, new_env)

                    # 4. Call the worker using this new "safe" instance
                    has_more_pages = handler_new_env._process_payments_page(
                        page=current_page,
                        date_obj=date_obj,
                        date_str=date_str
                    )

                # If the 'with' block ends successfully, Odoo automatically commits new_cr.
                _logger.info(f"Page {current_page} processed and committed successfully.")

            except Exception as e:
                # If an error occurs, Odoo rolls back new_cr.
                _logger.error(f"Error processing page {current_page}. "
                              f"The transaction for this page has been rolled back. Error: {e}")
                has_more_pages = False  # Stop the loop

            current_page += 1

        _logger.info("Payment synchronization completed.")

    def _process_payments_page(self, page, date_obj, date_str):
        """
        Process a page of payments from the Mobilvendor API.

        CORRECTED VERSION that:
        1. Correctly groups payments by payment_code (One payment -> Multiple Invoices)
        2. EXTRACTS RETENTIONS from 'retentions' array to get the valid invoice list
        3. EXTRACTS NORMAL PAYMENTS from 'payments' array
        4. Uses the Many2many field mobilvendor_invoice_ids
        5. Automatically posts and reconciles ALL payments.

        It implements Batch Optimization to map Routes to Payment Journals efficiently.
        For Odoo 18: Supports payments linked to multiple invoices using reconciled_invoice_ids.

        :param page: The page number to retrieve from the API.
        :param date_obj: The datetime object for the date filter.
        :param date_str: The string formatted date used in the API filter and new records.
        :return: Boolean indicating if there are more pages (True) or if this is the last page (False).
        """
        filter_payments = {
            "date": date_str
        }

        # Fetch page data from API
        payments_response = self._send_get_request(
            action="getBalanceDebit",
            filter=filter_payments,
            page=page
        )

        if "records" not in payments_response or "payments" not in payments_response:
            raise UserError(f"Invalid API response for Get Payments on page {page}")

        # ==========================================================================
        # 1. BATCH OPTIMIZATION: PAYMENT JOURNALS & METHODS CACHE
        # ==========================================================================
        default_journal_record = self._mobilvendor_create_payments_journal(route_id=False)
        default_journal_id = default_journal_record.id

        payment_method = self._mobilvendor_create_payment_method()

        # Search for Check Payment Method (Inbound)
        check_payment_method = self.env['account.payment.method'].sudo().search([
            ('payment_type', '=', 'inbound'),
            '|', ('name', 'ilike', 'cheq'), ('code', 'ilike', 'check')
        ], limit=1)

        if not check_payment_method:
            check_payment_method = self.env['account.payment.method'].sudo().search([
                ('payment_type', '=', 'inbound'),
                ('code', 'in', ['batch_payment', 'manual'])
            ], limit=1)

        routes_with_journal = self.env['mobilvendor.route'].sudo().search([
            ('payment_journal_id', '!=', False)
        ])
        route_journal_map = {r.id: r.payment_journal_id.id for r in routes_with_journal}

        # ==============================================================================
        # 2. DATA ORGANIZATION (HEADERS, PAYMENTS, AND RETENTIONS)
        # ==============================================================================
        records_config_map = {}
        record_id_to_code = {}
        bank_codes_needed = set()

        for record in payments_response.get('records', []):
            record_code = record.get('code', '')
            record_id = str(record.get('id', ''))
            if record_code:
                bank_code = record.get('bank_code')
                records_config_map[record_code] = {
                    'type': str(record.get('type', '0')),
                    'bank_code': bank_code,
                    'number': record.get('number', ''),
                    'doc': record.get('doc', ''),
                    'status': str(record.get('status', '1')),
                }
                record_id_to_code[record_id] = record_code
                if bank_code:
                    bank_codes_needed.add(bank_code)

        bank_journal_map = {}
        if bank_codes_needed:
            bank_journals = self.env['account.journal'].sudo().search([
                ('code', 'in', list(bank_codes_needed)),
                ('type', 'in', ['bank', 'cash']),
            ])
            bank_journal_map = {j.code: j.id for j in bank_journals}

        # Group Standard Payments
        payments_grouped = defaultdict(list)
        for payment in payments_response.get('payments', []):
            p_code = payment.get('payment_code', '')
            if p_code:
                payments_grouped[p_code].append(payment)

        # Group Retentions linking balance_debit_payment_id with the record code
        retentions_grouped = defaultdict(list)
        for ret in payments_response.get('retentions', []):
            bd_id = str(ret.get('balance_debit_payment_id', ''))
            p_code = record_id_to_code.get(bd_id)
            if p_code:
                retentions_grouped[p_code].append(ret)

        # ==============================================================================
        # 3. TRANSACTION PROCESSING (GROUPED LOGIC)
        # ==============================================================================
        for payment_code, record_config in records_config_map.items():
            record_type = record_config.get('type', '0')
            bank_code = record_config.get('bank_code')

            # Ignore Credit Notes
            if record_type in ['4', '6']:
                continue

            # Array Selection based on type
            if record_type == '3':
                payment_items = retentions_grouped.get(payment_code, [])
            else:
                payment_items = payments_grouped.get(payment_code, [])

            if not payment_items:
                continue

            # Idempotency and Status check
            status_mb = record_config.get('status', '1')
            
            existing_payment = self.env['account.payment'].search([
                ('mobilvendor_id', '=', payment_code)
            ], limit=1)

            if existing_payment:
                if status_mb == '0' and existing_payment.state != 'cancel':
                    _logger.info(f"Payment {payment_code} annulled in Mobilvendor. Canceling in Odoo...")
                    existing_payment.action_cancel()
                else:
                    _logger.info(f"Payment {payment_code} already exists. Skipping.")
                continue

            invoices_to_pay = self.env['account.move']
            total_payment_amount = 0.0
            currency = None
            partner_id = None
            route_id_from_invoice = False

            # Map to store specific amounts per invoice for proper reconciliation
            reconciliation_amounts = {}

            for item in payment_items:
                inv_code = item.get('invoice_code', '')
                
                domain = [
                    ('mobilvendor_id', '=', inv_code),
                    ('move_type', '=', 'out_invoice')
                ]
                if status_mb != '0':
                    domain.append(('state', '=', 'posted'))
                    
                invoice = self.env['account.move'].search(domain, limit=1)

                if not invoice:
                    continue
                if status_mb != '0' and self.check_reconcile_invoice_payments(invoice):
                    continue

                try:
                    # Sum to total and store the specific amount intended for this invoice
                    line_amount = float(item.get('payment', 0))
                    if line_amount > 0:
                        total_payment_amount += line_amount
                        reconciliation_amounts[invoice.id] = line_amount
                        invoices_to_pay |= invoice
                except (TypeError, ValueError):
                    _logger.warning(f"Invalid payment amount for invoice {inv_code}, skipping.")

                if not currency:
                    curr_code = item.get('currency_code')
                    currency = self.env['res.currency'].search([('name', '=', curr_code)],
                                                               limit=1) if curr_code else invoice.currency_id

                if not partner_id:
                    partner_id = invoice.partner_id.id

                if not route_id_from_invoice and invoice.mobilvendor_route_id:
                    route_id_from_invoice = invoice.mobilvendor_route_id.id

            if not invoices_to_pay or total_payment_amount <= 0:
                continue

            # --- Journal Resolution ---
            if record_type == '1':  # CASH
                target_journal_id = route_journal_map.get(route_id_from_invoice, default_journal_id)
            elif record_type == '3':  # RETENTIONS
                ret_bank_journal = self.env['account.journal'].sudo().search([('code', '=', 'BNK13')], limit=1)
                target_journal_id = ret_bank_journal.id if ret_bank_journal else route_journal_map.get(
                    route_id_from_invoice, default_journal_id)
            else:  # BANKS / CHECKS
                target_journal_id = bank_journal_map.get(bank_code, route_journal_map.get(route_id_from_invoice,
                                                                                          default_journal_id))

            # Memo and Method Preparation
            invoice_names = ", ".join(invoices_to_pay.mapped('name'))
            memo_text = f"{payment_code} - Ref: {invoice_names}"
            current_method_id = check_payment_method.id if record_type == '2' else payment_method.id

            if record_type == '2':
                # Dynamic Check Method Linking to Journal
                existing_line = self.env['account.payment.method.line'].sudo().search([
                    ('journal_id', '=', target_journal_id),
                    ('payment_method_id', '=', current_method_id),
                    ('payment_type', '=', 'inbound')
                ], limit=1)
                if not existing_line:
                    self.env['account.payment.method.line'].sudo().create({
                        'journal_id': target_journal_id,
                        'payment_method_id': current_method_id,
                        'name': 'Cheque',
                        'payment_type': 'inbound'
                    })
                check_num = record_config.get('number') or record_config.get('doc')
                if check_num:
                    memo_text += f" - Cheque Nro: {check_num}"

            # CREATE GROUPED PAYMENT INJECTING BREAKDOWN IN CONTEXT
            payment_vals = {
                'date': date_str,
                'memo': memo_text,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': partner_id,
                'amount': total_payment_amount,
                'currency_id': currency.id,
                'payment_method_id': current_method_id,
                'journal_id': target_journal_id,
                'mobilvendor_id': payment_code,
                'mobilvendor_route_id': route_id_from_invoice,
                'mobilvendor_invoice_ids': [(6, 0, invoices_to_pay.ids)],
            }

            try:
                new_payment = self.env['account.payment'].with_context(
                    mv_reconciliation_breakdown=reconciliation_amounts
                ).create(payment_vals)
                
                if status_mb == '0':
                    new_payment.action_cancel()
                    _logger.info(f"GROUPED Payment {payment_code} created as CANCELED directly.")
                    continue
                    
                new_payment.with_context(
                    mv_reconciliation_breakdown=reconciliation_amounts
                ).action_post()
                _logger.info(f"GROUPED Payment {payment_code} created successfully.")

                # ================================================================
                # RETENTION LINES: Populate the "Retenciones" tab on each invoice
                # Only for retention payments (type 3)
                # NOTE: Commented out — out of scope for current release.
                # ================================================================
                # if record_type == '3':
                #     for item in payment_items:
                #         try:
                #             inv_code = item.get('invoice_code', '')
                #             retention_code = item.get('retention_code', '')
                #
                #             if not inv_code or not retention_code:
                #                 continue
                #
                #             invoice = self.env['account.move'].search([
                #                 ('mobilvendor_id', '=', inv_code),
                #                 ('move_type', '=', 'out_invoice'),
                #                 ('state', '=', 'posted')
                #             ], limit=1)
                #
                #             if not invoice:
                #                 _logger.warning(f"Invoice {inv_code} not found for retention line.")
                #                 continue
                #
                #             # Search by code field; fallback to id if code doesn't exist
                #             retention = self.env['res.partner.retention'].sudo().search([
                #                 ('code', '=', retention_code)
                #             ], limit=1)
                #
                #             if not retention:
                #                 try:
                #                     retention = self.env['res.partner.retention'].sudo().browse(
                #                         int(retention_code)
                #                     )
                #                     if not retention.exists():
                #                         retention = None
                #                 except (TypeError, ValueError):
                #                     retention = None
                #
                #             if not retention:
                #                 _logger.warning(
                #                     f"Retention type '{retention_code}' not found in res.partner.retention."
                #                 )
                #                 continue
                #
                #             # Idempotency: skip if line already exists for this invoice + retention
                #             existing_line = self.env['account.move.retention.line'].sudo().search([
                #                 ('move_id', '=', invoice.id),
                #                 ('retention_id', '=', retention.id),
                #             ], limit=1)
                #
                #             if existing_line:
                #                 if not existing_line.paid:
                #                     existing_line.sudo().write({'paid': True})
                #                 continue
                #
                #             self.env['account.move.retention.line'].sudo().create({
                #                 'move_id': invoice.id,
                #                 'retention_id': retention.id,
                #                 'paid': True,
                #             })
                #             _logger.info(
                #                 f"Retention line created for invoice {inv_code}, code {retention_code}"
                #             )
                #
                #         except Exception as e_ret:
                #             _logger.error(
                #                 f"Error creating retention line for invoice {inv_code}: {e_ret}"
                #             )

            except Exception as e:
                _logger.error(f"Error creating/posting payment {payment_code}: {e}")

        return payments_response.get("pages", 1) > page

    def mobilvendor_send_balance_debit(self, records=[]):
        """
        Sends customer balance and debit information to Mobilvendor.

        This method acts as a wrapper to push financial status updates (balance,
        debit, credit limits) for customers to the API using the 'balance_debit' schema.
        It utilizes the generic request parser to handle batching and transmission.

        :param records: List of dictionaries containing balance data.
        """
        # Delegate the batch processing and transmission to the generic request parser
        self._parse_request("balance_debit", records)

    def _mobilvendor_sync_payment_by_days(self, number_of_days=1):
        """
        Synchronizes payments for a specified range of past days.

        This utility method iterates backwards from the current date, triggering
        the payment synchronization process for each individual day within the
        defined range. This is useful for historical data recovery or ensuring
        recent payments are up to date.

        :param number_of_days: Integer representing how many days back to sync (default is 1).
        """
        day_index = 0
        today = datetime.today()

        # Iterate through the specified number of days
        while day_index < number_of_days:
            # Calculate the specific date to sync (Today - Index)
            payment_date = today - timedelta(days=day_index)

            # Trigger the payment sync logic for that specific date
            self._mobilvendor_get_payments(date=payment_date)

            day_index += 1

    def check_reconcile_invoice_payments(self, invoice):
        """
        Checks if the provided invoice is fully reconciled.

        This method inspects the lines of the given invoice (account.move) to determine
        if they are associated with a full reconciliation record. This is typically
        used to skip processing of invoices that are already fully paid or settled.

        :param invoice: The 'account.move' record to check.
        :return: Boolean (True if reconciled, False otherwise).
        """
        # Check if any of the invoice lines have a 'full_reconcile_id' set
        invoice_reconciled = invoice.line_ids.filtered(lambda l: l.full_reconcile_id).exists()
        return invoice_reconciled

    def _mobilvendor_fix_invoices(self):
        """
        Corrects partner assignment on invoices generated via Mobilvendor.

        This utility method identifies invoices where the 'Customer' field was linked
        directly to a delivery address (child contact) rather than the parent company.
        It updates the invoice to set the parent company as the main 'partner_id'
        while preserving the specific contact as the 'partner_shipping_id'.
        """
        # Retrieve the specific journal used for Mobilvendor transactions
        journal = self._mobilvendor_create_invoice_journal()

        # Search for invoices in this journal where the assigned partner is a child record
        # (has a parent_id) and a shipping address is defined.
        account_move_records = self.env['account.move'].search([
            ('journal_id', '=', journal.id),
            ('partner_id.parent_id', '!=', None),
            ('partner_shipping_id', '!=', None)
        ])

        for invoice in account_move_records:
            # Identify the correct address and parent company
            invoice_addr = invoice.partner_shipping_id
            invoice_partner = invoice.partner_id.parent_id

            # Reassign: Parent becomes the Invoice Customer, Child remains Shipping Address
            invoice.write({
                'partner_id': invoice_partner.id,
                'commercial_partner_id': invoice_partner.id,
                'partner_shipping_id': invoice_addr.id
            })

    def _mobilvendor_get_cancelled_invoices(self, page=1):
        """
        Main controller for synchronizing cancelled invoices from Mobilvendor.

        This method manages the pagination loop and executes the processing of each
        page within a separate, isolated database transaction. This ensures that
        complex cancellation operations (invoice, payments, stock reversals) are
        atomic per page and do not cause database locks or partial corruption.

        :param page: The starting page number for the API request.
        """
        _logger.info("##################### get cancelled invoices (Controller) ##############################")

        # Calculate the start date for the sync (45 days lookback window)
        current_datetime = datetime.now()
        mv_start_date = current_datetime - timedelta(days=45)
        mv_day_format = mv_start_date.strftime('%Y-%m-%d')

        current_page = 1
        has_more_pages = True

        while has_more_pages:
            _logger.info(f"Starting processing of cancelled invoices page: {current_page}")

            try:
                # --- CRITICAL: Safe Transaction Handling ---
                # Create a new, independent database cursor for this page.
                with self.env.registry.cursor() as new_cr:

                    # Create a new environment bound to the isolated cursor
                    new_env = self.env(cr=new_cr)

                    # Re-instantiate 'self' in the new environment
                    self_in_new_env = new_env[self._name].browse(self.ids)

                    # Call the worker method to process the specific page
                    has_more_pages = self_in_new_env._process_cancelled_invoices_page(
                        page=current_page,
                        start_date=mv_day_format
                    )

                # Automatic commit occurs here if no exceptions are raised
                _logger.info(f"Page {current_page} of cancelled invoices processed successfully.")

            except Exception as e:
                # Automatic rollback occurs here on error
                _logger.error(
                    f"Error processing cancelled invoices page {current_page}. Transaction rolled back. Error: {e}")
                has_more_pages = False  # Stop processing to prevent infinite loops

            current_page += 1

        _logger.info("Cancelled invoices synchronization complete.")

    def _mobilvendor_get_user_routes(self, page=1):
        """
        Synchronizes the assignment of Users (Employees) to Routes from Mobilvendor.

        This method updates the intermediate table `mobilvendor.route.employee`.

        Employee Lookup Logic:
        1. First, try to find by `mobilvendor_code`.
        2. If not found and the code is numeric, try to find by Odoo Database ID.
           - If found by ID, update the employee's `mobilvendor_code` for future syncs.

        Assignment Logic:
        - Creates the link between Employee and Route even if the status is inactive (for history).
        - Updates the 'active' status if the link already exists.

        :param page: Current page number for API pagination.
        """
        _logger.info(f"##################### Get User Routes (Page {page}) ##############################")

        # 1. Fetch data from API
        response = self._send_get_request(action="get", schema="users_in_routes", page=page)

        if "records" not in response:
            raise UserError(f"Invalid response for Get User Routes")

        number_of_pages = response.get("pages", 1)
        api_records = response.get("records", [])

        # ==============================================================================
        # 2. BATCH CACHE: ROUTES
        # ==============================================================================
        # Pre-load routes referenced in this batch to avoid N+1 queries.
        route_codes = set(rec.get('route_code') for rec in api_records if rec.get('route_code'))

        routes_map = {}
        if route_codes:
            found_routes = self.env['mobilvendor.route'].sudo().search([
                ('mobilvendor_id', 'in', list(route_codes))
            ])
            routes_map = {r.mobilvendor_id: r.id for r in found_routes}

        # ==============================================================================
        # 3. PROCESS RECORDS
        # ==============================================================================

        for record in api_records:
            user_code_str = str(record.get('user_code', ''))
            route_code_str = record.get('route_code')
            status = record.get('status')

            if not user_code_str or not route_code_str:
                continue

            # --- A. EMPLOYEE RESOLUTION ---
            employee = None

            # Priority 1: Search by Mobilvendor Code
            employee = self.env['hr.employee'].sudo().search([
                ('mobilvendor_code', '=', user_code_str)
            ], limit=1)

            # Priority 2: Fallback to Odoo Database ID if not found by MV Code
            if not employee and user_code_str.isdigit():
                try:
                    user_id = int(user_code_str)
                    employee_by_id = self.env['hr.employee'].sudo().browse(user_id)

                    if employee_by_id.exists():
                        employee = employee_by_id

                        # Update the code to fix the link for future runs
                        if employee.mobilvendor_code != user_code_str:
                            employee.sudo().write({'mobilvendor_code': user_code_str})
                            _logger.debug(f"Updated MV Code for Employee {employee.name}: {user_code_str}")
                except Exception:
                    pass

            if not employee:
                _logger.warning(f"Employee not found for code: {user_code_str}. Skipping assignment.")
                continue

            # --- B. ROUTE RESOLUTION ---
            route_id = routes_map.get(route_code_str)

            if not route_id:
                _logger.warning(f"Route not found in Odoo: {route_code_str}. Skipping assignment.")
                continue

            # --- C. UPDATE INTERMEDIATE TABLE (UPSERT) ---

            # Map API status '1'/'0' to Boolean
            is_active = True if status == '1' else False

            # Search for existing assignment (including archived/inactive ones)
            assignment = self.env['mobilvendor.route.employee'].sudo().with_context(active_test=False).search([
                ('employee_id', '=', employee.id),
                ('route_id', '=', route_id)
            ], limit=1)

            if assignment:
                # Update status if it changed
                if assignment.active != is_active:
                    assignment.sudo().write({'active': is_active})
                    _logger.info(f"Updated Assignment: {employee.name} -> {route_code_str} (Active: {is_active})")
            else:
                # Create new assignment (ALWAYS create, even if inactive, to keep history)
                self.env['mobilvendor.route.employee'].sudo().create({
                    'employee_id': employee.id,
                    'route_id': route_id,
                    'active': is_active
                })
                _logger.info(f"Created Assignment: {employee.name} -> {route_code_str} (Active: {is_active})")

        # 4. Commit transaction
        self.env.cr.commit()

        # 5. Recursive call
        if number_of_pages > page:
            self._mobilvendor_get_user_routes(page=page + 1)

    def _process_cancelled_invoices_page(self, page, start_date):
        """
        Worker method to process a single page of cancelled invoices.

        This method fetches data from the API and performs the necessary cleanup in Odoo:
        1. Unreconciles payments.
        2. Cancels associated payments.
        3. Cancels the invoice.
        4. Reverses stock movements (creates return pickings).

        :param page: Page number to fetch.
        :param start_date: String formatted date filter.
        :return: Boolean indicating if more pages exist.
        """
        filter_invoice = {
            "process_status": "0,1",
            "type": "1",
            "status": "3",  # Status '3' indicates Cancelled in Mobilvendor
            "page": page,
            "start_date": start_date
        }

        invoices_response = self._send_get_request(action="getInvoices", filter=filter_invoice)

        if "headers" not in invoices_response or "details" not in invoices_response:
            raise UserError(f"Invalid API response for Get Cancelled Invoices on page {page}")

        invoice_headers = self._process_invoice_headers(invoices_response.get("headers"))
        # Note: line items are processed but not explicitly used in the cancellation logic below,
        # as we rely on existing Odoo records.
        # invoice_line_items = self._process_invoice_details(invoices_response.get("details"))

        for key, value in invoice_headers.items():
            external_mobilvendor_id = key

            # Double-check status (API filter should handle this, but good for safety)
            if value.get('status') != '3':
                continue

            try:
                order_invoice_type = int(value.get('type'))
            except (TypeError, ValueError):
                order_invoice_type = 1

            # Only process standard invoices (Type 1)
            if order_invoice_type != 1:
                continue

            # Find the existing Odoo invoice
            existing_invoice_order = self.env['account.move'].search(
                [('mobilvendor_id', '=', external_mobilvendor_id)], limit=1)

            if not existing_invoice_order:
                continue

            if existing_invoice_order.state == 'cancel':
                _logger.debug(f"Skipping invoice {existing_invoice_order.mobilvendor_id} as it is already cancelled.")
                continue

            # --- Step 1: Unreconcile Payments ---
            # Detach payments from the invoice to allow cancellation
            for payment in existing_invoice_order.payment_ids:
                try:
                    reconciled_invoice_line = existing_invoice_order.line_ids.filtered(
                        lambda x: x.account_id.account_type in ('asset_receivable')
                    )
                    reconciled_payment_line = payment.move_id.line_ids.filtered(
                        lambda x: x.account_id.account_type in ('asset_receivable')
                    )

                    all_reconciled_lines = reconciled_invoice_line + reconciled_payment_line
                    if all_reconciled_lines:
                        all_reconciled_lines.remove_move_reconcile()
                except Exception as e:
                    _logger.error(f"Error unreconciling payment for invoice {external_mobilvendor_id}: {str(e)}")

            # --- Step 2: Cancel Payments ---
            for payment in existing_invoice_order.payment_ids:
                try:
                    if payment.state == 'posted':
                        payment.action_draft()
                    payment.action_cancel()
                except Exception as e:
                    _logger.error(f"Error canceling payment for invoice {external_mobilvendor_id}: {str(e)}")

            # --- Step 3: Cancel Invoice ---
            try:
                if existing_invoice_order.state == 'posted':
                    existing_invoice_order.button_cancel()
            except Exception as e:
                _logger.error(f"Error canceling invoice {external_mobilvendor_id}: {str(e)}")

            # --- Step 4: Reverse Stock Movements ---
            # Identify related stock moves and create return pickings
            related_stock_moves = self.env['stock.move'].search([('mobilvendor_id', '=', external_mobilvendor_id)])
            for move in related_stock_moves:
                try:
                    if move.state == 'done':
                        picking = move.picking_id
                        if not picking.move_ids:
                            continue

                        if picking.state != 'cancel':
                            # Initialize the Return Picking Wizard
                            ReturnPicking = self.env['stock.return.picking']
                            return_wizard = ReturnPicking.create({
                                'picking_id': picking.id,
                            })

                            # Trigger onchange to populate default return lines
                            return_wizard._onchange_picking_id()

                            # Generate the return picking
                            return_moves = return_wizard.create_returns()

                            # Retrieve the created return picking
                            return_picking_id = return_moves.get('res_id')
                            return_picking = self.env['stock.picking'].browse(return_picking_id)

                            # Confirm the return (triggers stock moves)
                            return_picking.action_confirm()

                            # Auto-fill quantities to validate immediately
                            for return_move in return_picking.move_ids:
                                return_move.quantity_done = abs(return_move.product_uom_qty)

                            # Validate the return picking
                            return_picking.button_validate()

                            # Force state consistency if validation didn't complete as expected
                            for return_move in return_picking.move_ids:
                                if return_move.state not in ('done', 'cancel'):
                                    return_move.write({'state': 'done'})

                            if return_picking.state != 'done':
                                return_picking.write({'state': 'done'})

                except Exception as e:
                    _logger.error(
                        f"Error processing stock move reversal for invoice {external_mobilvendor_id}: {str(e)}")

        number_of_pages = invoices_response.get("pages", 1)
        return number_of_pages > page

    def _notify_success(self, message="Sync"):
        """
        Constructs and returns a client action to display a success notification in the UI.

        This method utilizes Odoo's 'display_notification' client tag to show a
        non-sticky (temporary) toast message to the user, confirming that the
        requested operation completed successfully.

        :param message: A string indicating the specific operation name (default "Sync").
        :return: A dictionary definition for the 'ir.actions.client' action.
        """
        # Return the specific action dictionary required by the web client to show a notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Success"),
                'message': _(f"{message} completado satisfactoriamente!"),
                'sticky': False,
            },
        }

    def sync_inventory(self):
        """
        Orchestrates the synchronization of all inventory-related master data to Mobilvendor.

        This method triggers a sequence of outgoing (POST) requests to update
        Mobilvendor with the latest configuration from Odoo, including:
        - Inventory Types and Storages
        - Product Categories and Units of Measure
        - Product Articles (Templates/Variants)
        - Price Lists and Prices
        - Current Stock Levels

        Note: Inventory management is unidirectional (Odoo -> Mobilvendor).
        """

        # ############### POST #################
        # Execute sequential synchronization of master data entities
        self._mobilvendor_inventory_types()
        self._mobilvendor_categories()
        self._mobilvendor_units()
        self._mobilvendor_articles()
        self._mobilvendor_price_list()
        self._mobilvendor_article_prices()
        self._mobilvendor_article_units()
        self._mobilvendor_storages_special_condition()
        self._mobilvendor_inventory_special_condition()

        return self._notify_success(message="Sincronización de Inventario")

    def sync_customers_users(self):
        """
        Orchestrates the synchronization of customer data and addresses from Mobilvendor.

        This method sequentially triggers the retrieval of:
        1. Main customer records (Partners).
        2. Customer addresses/contacts (Child Partners).
        """
        # ############### GET ##################
        # Trigger the import of main customer records
        self._mobilvendor_get_customers()
        # Trigger the import of delivery addresses associated with customers
        self._mobilvendor_get_customers_addrs()

        # Sync routes as part of the client information
        self._mobilvendor_get_routes()
        self._mobilvendor_get_route_details()

        # ############### GET USER IN ROUTES #################
        self._mobilvendor_get_user_routes()

        return self._notify_success(message="Sincronización de Clientes y Rutas")

    def sync_price_list_products(self):
        """
        Manually triggers the synchronization of Price Lists and Product Prices.

        This method executes the sequence to update both the Price List definitions
        (headers) and the specific product prices in Mobilvendor.
        It concludes by displaying a success notification to the user.
        """
        self._mobilvendor_price_list()
        self._mobilvendor_article_prices()

        return self._notify_success(message="Lista de precios y precios de productos actualizados")

    def sync_invoice_and_payments_partners(self):
        """
        Triggers the update of partner and shipping information on existing invoices.

        This method serves as an entry point to run specific fix scripts (like
        `_mobilvendor_fix_invoices`) to correct data consistency issues between
        partners and invoices. Currently, the logic is commented out, returning
        only a notification.
        """
        # Execute the invoice correction logic (currently disabled)
        # self._mobilvendor_fix_invoices()

        return self._notify_success(message="Actualizar Información de Cliente y Envío en Facturas")

    def sync_cancel_invoice_and_payments(self):
        """
        Triggers the synchronization process for cancelled invoices and payments.

        This method is intended to fetch cancelled status updates from Mobilvendor
        and reflect them in Odoo (cancelling invoices, payments, and reversing inventory).
        Currently, the execution logic is commented out for safety or testing purposes.
        """
        # Execute the cancellation synchronization logic (currently disabled)
        # self._mobilvendor_get_cancelled_invoices()
        return self._notify_success(message="Actualizar Facturas e inventarios cancelados en MV")

    def sync_fast_invoices_payments(self):
        """
        Orchestrates a rapid synchronization of essential transaction data.

        This method executes a dependency-ordered sync sequence to ensure data integrity:
        1. Customers (to ensure invoices can be linked to partners).
        2. Customer Addresses (to link shipping/billing details).
        3. Invoices (financial documents).

        Note: Payment synchronization and specific Credit Note passes are currently
        disabled/commented out in this routine.
        """
        # Sync dependencies first to avoid 'Partner not found' errors during invoice creation
        self.sync_customers_users()

        # Sync invoices using the default transaction types
        self._mobilvendor_get_invoices()
        self._mobilvendor_sync_payment_by_days(number_of_days=self.mobilvendor_sync_days + 1)  # Day count start at 0
        # self._mobilvendor_get_invoices(inv_type="6")

        return self._notify_success(message="Sincronización de Facturas, NC y Pagos")

    def sync_all(self):
        """
        Executes the complete bidirectional synchronization process between Odoo and Mobilvendor.

        This master method runs all synchronization sub-routines in a specific dependency order
        to ensure data integrity:
        1. Inbound (GET): Customers and Addresses (prerequisites for transactions).
        2. Inbound (GET): Invoices, Payments, and Credit Notes (transactional data).
        3. Outbound (POST): Master data (Products, Prices) and Inventory levels.

        :return: A client action dictionary to display a success notification.
        """
        # ################### GET CUSTOMERS #####################
        self.sync_customers_users()

        # ############# GET INVOICES AND PAYMENTS ##############
        # Retrieve standard invoices and internal transfers
        self._mobilvendor_get_invoices()
        # Sync payments based on the configured day range (offset + 1 to include start day)
        self._mobilvendor_sync_payment_by_days(number_of_days=self.mobilvendor_sync_days + 1)
        # Retrieve Credit Notes (Type 6) specifically
        # self._mobilvendor_get_invoices(inv_type="6")

        # ################### POST INVENTORY ####################
        # Push master data configuration and current stock levels to Mobilvendor
        self.sync_inventory()

        return self._notify_success(message="Sincronización total")
