from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError

@tagged('post_install', '-at_install')
class TestAddUserByJournal(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Admin User with the special bypass group
        cls.group_admin = cls.env.ref('add_user_by_journal.res_groups_admin_journal_access')
        cls.admin_user = cls.env['res.users'].create({
            'name': 'Journal Admin',
            'login': 'journal_admin',
            'email': 'admin@example.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('account.group_account_manager').id, cls.group_admin.id])]
        })

        # Normal User
        cls.normal_user = cls.env['res.users'].create({
            'name': 'Normal User',
            'login': 'normal_user',
            'email': 'user@example.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('account.group_account_invoice').id])]
        })

        # Test Company
        cls.company = cls.env.company

        # Journals
        cls.journal_a = cls.env['account.journal'].create({
            'name': 'Journal A',
            'code': 'JA',
            'type': 'sale',
            'assign_to_ids': [(4, cls.normal_user.id)]
        })
        cls.journal_b = cls.env['account.journal'].create({
            'name': 'Journal B (Public)',
            'code': 'JB',
            'type': 'sale',
            'assign_to_ids': []  # Empty = Public Access (New Logic)
        })

        cls.journal_c = cls.env['account.journal'].create({
            'name': 'Journal C (Restricted)',
            'code': 'JC',
            'type': 'sale',
            'assign_to_ids': [(4, cls.admin_user.id)]  # Assigned only to Admin
        })

        cls.group_test = cls.env['res.groups'].create({'name': 'Test Group'})
        cls.normal_user.group_ids = [(4, cls.group_test.id)]

        cls.journal_d = cls.env['account.journal'].create({
            'name': 'Journal D (Group Access)',
            'code': 'JD',
            'type': 'sale',
            'journal_group_ids': [(4, cls.group_test.id)] # Assigned to Test Group
        })

        cls.journal_bank_restricted = cls.env['account.journal'].create({
            'name': 'Restricted Bank',
            'code': 'BNKR',
            'type': 'bank',
            'assign_to_ids': [(4, cls.admin_user.id)]
        })

        # Partners
        cls.partner_a = cls.env['res.partner'].create({'name': 'Partner A'})

        # Moves
        cls.move_a = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': cls.journal_a.id,
            'partner_id': cls.partner_a.id,
        })
        cls.move_b = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': cls.journal_b.id,
            'partner_id': cls.partner_a.id,
        })

    def test_journal_visibility(self):
        """Test that users can see journals assigned to them, their groups, AND public journals."""
        # Search for journals visible to normal_user
        journals = self.env['account.journal'].with_user(self.normal_user).search([('id', 'in', [self.journal_a.id, self.journal_b.id, self.journal_c.id, self.journal_d.id])])
        
        # Should see Journal A (Assigned)
        self.assertIn(self.journal_a, journals)
        # Should see Journal B (Public)
        self.assertIn(self.journal_b, journals)
        # Should see Journal D (Group Access)
        self.assertIn(self.journal_d, journals)
        
        # Should NOT see Journal C (Restricted to Admin)
        self.assertNotIn(self.journal_c, journals)

    def test_move_visibility(self):
        """Test that users can see moves in accessible journals."""
        # Create move in Public, Restricted, and Group journals
        # Create move in Restricted, and Group journals
        # self.move_b is already created in setUpClass for public journal
        
        move_c = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.journal_c.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2023-01-01',
        })
        # Force compute to ensure security fields are populated before search
        move_c._compute_journal_assign_to_ids() # Critical for tests where triggers might be delayed
        
        move_d = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.journal_d.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2023-01-01',
        })
        move_d._compute_journal_assign_to_ids()

        moves = self.env['account.move'].with_user(self.normal_user).search([('id', 'in', [self.move_a.id, self.move_b.id, move_c.id, move_d.id])])
        
        self.assertIn(self.move_a, moves, "Assigned Journal Move should be visible")
        self.assertIn(self.move_b, moves, "Public Journal Move should be visible")
        self.assertNotIn(move_c, moves, "Restricted Journal Move (Admin only) should NOT be visible")
        self.assertIn(move_d, moves, "Group Assigned Journal Move should be visible")

    def test_admin_bypass(self):
        """Test that admin can see everything."""
        journals = self.env['account.journal'].with_user(self.admin_user).search([('id', 'in', [self.journal_a.id, self.journal_b.id, self.journal_c.id, self.journal_d.id])])
        self.assertIn(self.journal_a, journals)
        self.assertIn(self.journal_b, journals)
        self.assertIn(self.journal_c, journals)
        self.assertIn(self.journal_d, journals)
        
        # Moves
    def test_account_move_compute_logic(self):
        """Verify the optimized compute method for journal_assign_to_ids."""
        self.move_a._compute_journal_assign_to_ids()
        self.assertIn(self.normal_user, self.move_a.journal_assign_to_ids)

        self.move_b._compute_journal_assign_to_ids()
        self.assertFalse(self.move_b.journal_assign_to_ids)

    def test_invoice_with_restricted_payment(self):
        """
        Test that accessing an invoice (Public) that is paid by a Restricted payment
        does not crash or raise AccessError.
        This simulates the user scenario: Invoice in 'Sales' (Allowed), Payment in 'Bank' (Restricted).
        """
        # 1. Create Invoice in Public Journal (Journal B)
        # Need a default account for the line
        default_account = self.journal_b.default_account_id.id or self.env['account.account'].search([('account_type', '=', 'income')], limit=1).id
        if not default_account:
             # Fallback if no default account found
             default_account = self.env['account.account'].create({'name': 'Test Income', 'code': '999999', 'account_type': 'income'}).id

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.journal_b.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2023-01-01',
            'invoice_line_ids': [(0, 0, {'name': 'Line', 'price_unit': 100, 'account_id': default_account})],
        })
        invoice.action_post()
        
        # 2. Create Payment in Restricted Journal (Restricted Bank - Admin Only)
        # We process payment as Admin
        payment_method = self.journal_bank_restricted.inbound_payment_method_line_ids[0]
        payment = self.env['account.payment'].with_user(self.admin_user).create({
            'amount': 100,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'journal_id': self.journal_bank_restricted.id,
            'payment_method_line_id': payment_method.id,
        })
        payment.action_post()
        
        # 3. Reconcile (Link) Invoice and Payment
        # This creates the partial reconciliation
        # Use simple reconciliation if possible or helper
        (invoice.line_ids + payment.move_id.line_ids).filtered(lambda l: l.account_id.account_type == 'asset_receivable').reconcile()

        # 4. Try to Read Invoice as Normal User
        # This mimics opening the form view which triggers 'invoice_payments_widget' computation
        # and potentially reads the linked payment move
        try:
             # Force reading the widget field which triggers the access check on linked moves
             invoice.with_user(self.normal_user).read(['name', 'invoice_payments_widget'])
             
             # Also explicitly check access to the payment move itself
             payment.move_id.with_user(self.normal_user).read(['name'])
             
        except AccessError:
             self.fail("AccessError raised when reading invoice with restricted payment!")

    def test_partner_invoice_smart_button(self):
        """
        Test the 'Invoiced' Smart Button behavior on a Partner.
        It should safely return only the Invoices visible to the user,
        ignoring the restricted ones without raising an Access Error.
        """
        # Simulate clicking the smart button: It acts as a Search for moves linked to the partner
        # We search as Normal User
        partner_moves = self.env['account.move'].with_user(self.normal_user).search([
            ('partner_id', '=', self.partner_a.id),
            ('move_type', '=', 'out_invoice')
        ])

        # Verify visibility
        self.assertIn(self.move_a, partner_moves, "Should see Invoice in Assigned Journal")
        self.assertIn(self.move_b, partner_moves, "Should see Invoice in Public Journal")
        
        # Determine strict visibility of move_d (Group Access)
        # Normal User IS in the group, so they should see it.
        # However, setUpClass creates move_d with journal_d.
        # We need to ensure move_d is definitely created and linked to partner_a.
        # In setUpClass logic:
        # move_c is created in test_move_visibility? No, move_c/d created in test_move_visibility are LOCAL vars.
        # Creating them here to be sure.
        
        move_restricted = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.journal_c.id, # Restricted to Admin
            'partner_id': self.partner_a.id,
            'invoice_date': '2023-01-01',
        })
        move_restricted._compute_journal_assign_to_ids() # Ensure security fields are set
        
        # Re-search
        partner_moves_updated = self.env['account.move'].with_user(self.normal_user).search([
            ('partner_id', '=', self.partner_a.id),
            ('move_type', '=', 'out_invoice')
        ])
        
        self.assertNotIn(move_restricted, partner_moves_updated, "Should NOT see Invoice in Restricted Journal")
        self.assertEqual(len(partner_moves_updated), 2, "Should only see the 2 permitted invoices (Move A and Move B)")

    def test_invoice_paid_by_restricted_misc_entry(self):
        """
        Test that accessing an invoice paid by a Manual Entry (Shift/Misc) in a Restricted Journal
        does NOT crash. This covers 'Exchange Difference' or 'Bank Statement' scenarios
        where no account.payment exists.
        """
        # 1. Invoice
        # Need a default account for the line
        default_account = self.journal_b.default_account_id.id or self.env['account.account'].search([('account_type', '=', 'income')], limit=1).id
        if not default_account:
             # Fallback if no default account found
             default_account = self.env['account.account'].create({'name': 'Test Income', 'code': '999999', 'account_type': 'income'}).id

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.journal_b.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2023-01-01',
            'invoice_line_ids': [(0, 0, {'name': 'Line', 'price_unit': 100, 'account_id': default_account})],
        })
        invoice.action_post()

        # 2. Restricted Manual Entry (Misc/Bank)
        # Ensure Bank Account exists
        bank_account = self.journal_bank_restricted.default_account_id.id
        if not bank_account:
             bank_account = self.env['account.account'].search([('account_type', '=', 'asset_cash')], limit=1).id
        if not bank_account:
             bank_account = self.env['account.account'].create({'name': 'Test Bank', 'code': '101010', 'account_type': 'asset_cash'}).id

        # Create a move directly in restricted bank journal, NO payment object
        misc_move = self.env['account.move'].with_user(self.admin_user).create({
            'move_type': 'entry',
            'journal_id': self.journal_bank_restricted.id,
            'date': '2023-01-02',
            'line_ids': [
                (0, 0, {
                    'name': 'Payment', 
                    'account_id': self.partner_a.property_account_receivable_id.id, 
                    'credit': 100, 
                    'partner_id': self.partner_a.id
                }),
                (0, 0, {
                    'name': 'Bank', 
                    'account_id': bank_account, 
                    'debit': 100
                }),
            ]
        })
        misc_move.action_post()
        misc_move._compute_journal_assign_to_ids() # Ensure security fields are set so it IS restricted
        
        # Verify M2M fields are actually set
        # This debug step ensures we aren't failing due to empty fields making it Public
        # misc_move is created by Admin, but we check values from DB
        self.assertTrue(misc_move.journal_assign_to_ids, "Misc Move should have assigned users (Admin)")
        self.assertNotIn(self.normal_user, misc_move.journal_assign_to_ids, "Normal User should NOT be assigned")
        
        # 3. Reconcile
        (invoice.line_ids + misc_move.line_ids).filtered(lambda l: l.account_id.account_type == 'asset_receivable').reconcile()

        # 4. Attempt Access
        # With the "Interoperability Exception for Commercial Data (AR/AP)", this should NO LONGER fail.
        # The user needs to see the payment/credit to apply it or validat the invoice state.
        try:
             invoice.with_user(self.normal_user).read(['name', 'invoice_payments_widget'])
        except AccessError:
             self.fail("Standard Interoperability: Should read invoice paid by restricted MISC entry if it affects AR/AP!")

    def test_invoice_with_outstanding_restricted_credit(self):
        """
        Test that accessing an invoice with an OUTSTANDING (unreconciled) credit 
        from a Restricted Manual Entry does NOT crash.
        The 'invoice_outstanding_credits_debits_widget' tries to fetch these.
        """
        # 1. Invoice (Open, Unpaid)
        # Need a default account for the line
        default_account = self.journal_b.default_account_id.id or self.env['account.account'].search([('account_type', '=', 'income')], limit=1).id
        if not default_account:
             # Fallback if no default account found
             default_account = self.env['account.account'].create({'name': 'Test Income', 'code': '999999', 'account_type': 'income'}).id

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.journal_b.id, # Public
            'partner_id': self.partner_a.id,
            'invoice_date': '2023-01-01',
            'invoice_line_ids': [(0, 0, {'name': 'Line', 'price_unit': 100, 'account_id': default_account})],
        })
        invoice.action_post()

        # 2. Restricted Manual Credit (Misc/Bank) - UNRECONCILED
        # This creates a 'potencial' credit for the partner.
        bank_account = self.journal_bank_restricted.default_account_id.id
        misc_credit = self.env['account.move'].with_user(self.admin_user).create({
            'move_type': 'entry',
            'journal_id': self.journal_bank_restricted.id, # Restricted
            'date': '2023-01-01',
            'line_ids': [
                (0, 0, {
                    'name': 'Customer Prepayment', 
                    'account_id': self.partner_a.property_account_receivable_id.id, 
                    'credit': 50, # Partial credit
                    'partner_id': self.partner_a.id
                }),
                (0, 0, {
                    'name': 'Bank', 
                    'account_id': bank_account, 
                    'debit': 50
                }),
            ]
        })
        misc_credit.action_post()
        misc_credit._compute_journal_assign_to_ids() # Ensure restricted

        # 3. Attempt Access as Normal User
        try:
             # Just reading the field should trigger the widget computation
             invoice.with_user(self.normal_user).read(['invoice_outstanding_credits_debits_widget'])
        except AccessError:
             self.fail("AccessError raised for outstanding restricted credit! It should be visible as AR/AP.")

    def test_restricted_invoice_is_hidden(self):
        """
        Test that an INVOICE in a Restricted Journal remains HIDDEN even if it touches AR/AP.
        The Interoperability Exception should ONLY apply to 'entry' (Payments/Misc), NOT 'out_invoice'.
        """
        # 1. Create Restricted Invoice
        default_account = self.journal_c.default_account_id.id or self.env['account.account'].search([('account_type', '=', 'income')], limit=1).id
        if not default_account:
            default_account = self.env['account.account'].create({'name': 'Test Income C', 'code': '888888', 'account_type': 'income'}).id

        restricted_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.journal_c.id, # Restricted to Admin
            'partner_id': self.partner_a.id,
            'invoice_date': '2023-01-01',
            # This creates a receivable line automatically
            'invoice_line_ids': [(0, 0, {'name': 'Line', 'price_unit': 100, 'account_id': default_account})],
        })
        restricted_invoice.action_post()
        restricted_invoice._compute_journal_assign_to_ids()
        
        # 2. Search as Normal User
        search_res = self.env['account.move'].with_user(self.normal_user).search([('id', '=', restricted_invoice.id)])
        
        # 3. Assert HIDDEN
        # If the AR/AP rule is too broad, this will fail (it will be found)
        self.assertFalse(search_res, "Restricted Invoice should be HIDDEN, but it was found (Leaked by AR/AP rule?)")

    def test_journal_items_visibility(self):
        """
        Test that Journal Items (account.move.line) respect the same security rules as Moves.
        A user should NOT be able to see lines of a restricted move.
        If they do, accessing 'move_id' (e.g. in list view) triggers AccessError.
        """
        # 1. Restricted Move (already created as move_d in setUpClass? No, local var. Let's create one)
        # We can use move_restricted from previous tests or create new.
        default_account = self.journal_c.default_account_id.id or self.env['account.account'].search([('account_type', '=', 'income')], limit=1).id
        if not default_account:
            default_account = self.env['account.account'].create({'name': 'Test Income JIV', 'code': '777777', 'account_type': 'income'}).id

        restricted_move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal_c.id, # Restricted
            'date': '2023-01-01',
            'line_ids': [
                (0, 0, {'name': 'Debit', 'account_id': default_account, 'debit': 100}),
                (0, 0, {'name': 'Credit', 'account_id': default_account, 'credit': 100}),
            ]
        })
        restricted_move.action_post()
        restricted_move._compute_journal_assign_to_ids()
        
        # 2. Search Lines as Normal User
        # We specifically search for lines of this move to see if they are visible
        lines = self.env['account.move.line'].with_user(self.normal_user).search([('move_id', '=', restricted_move.id)])
        
        # 3. Assert HIDDEN
        # Currently this will FAIL (lines are visible), causing the AccessError the user sees later in UI
        self.assertFalse(lines, "Journal Items of restricted move should be HIDDEN")

    def test_misc_entry_without_ar_ap_is_hidden(self):
        """
        Test that a 'Pure' Miscellaneous entry (e.g. Asset vs Expense) that does NOT
        touch AR/AP accounts remains HIDDEN in a restricted journal.
        This verifies that the Interoperability Whitelist isn't too broad.
        """
        # 1. Create Pure Internal Move (No Partner, No AR/AP)
        # We need accounts that are NOT asset_receivable or liability_payable.
        # 'income' and 'expense' types are safe.
        default_income = self.journal_b.default_account_id.id or self.env['account.account'].search([('account_type', '=', 'income')], limit=1).id
        if not default_income:
            default_income = self.env['account.account'].create({'name': 'Test Income', 'code': '999901', 'account_type': 'income'}).id
            
        default_expense = self.env['account.account'].search([('account_type', '=', 'expense')], limit=1).id
        if not default_expense:
             default_expense = self.env['account.account'].create({'name': 'Test Expense', 'code': '666601', 'account_type': 'expense'}).id

        internal_move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal_c.id, # Restricted to Admin
            'date': '2023-01-05',
            'line_ids': [
                (0, 0, {'name': 'Expense', 'account_id': default_expense, 'debit': 100}),
                (0, 0, {'name': 'Income', 'account_id': default_income, 'credit': 100}),
            ]
        })
        internal_move.action_post()
        internal_move._compute_journal_assign_to_ids() # Ensure security

        # 2. Search as Normal User
        search_res = self.env['account.move'].with_user(self.normal_user).search([('id', '=', internal_move.id)])

        # 3. Assert HIDDEN
        self.assertFalse(search_res, "Pure Internal Misc Entry should be HIDDEN")

    def test_group_restricted_interoperability(self):
        """
        Test that Interoperability Exceptions (e.g. Payments) work even for journals
        restricted by 'Allowed Groups' (journal_group_ids), not just 'Assigned Users'.
        """
        # 1. Setup: Create Secret Group and Journal
        group_secret = self.env['res.groups'].create({'name': 'Secret Group'})
        journal_secret = self.env['account.journal'].create({
            'name': 'Secret Journal (Group)',
            'code': 'JSG',
            'type': 'bank',
            'journal_group_ids': [(4, group_secret.id)]
        })
        
        # 2. Create Whitelisted Entry (Payment) in Secret Journal
        # User is NOT in group_secret
        payment_move = self.env['account.move'].with_user(self.admin_user).create({
            'move_type': 'entry',
            'journal_id': journal_secret.id,
            'date': '2023-01-06',
            'line_ids': [
                (0, 0, {'name': 'Payment', 'account_id': self.partner_a.property_account_receivable_id.id, 'credit': 100}),
                (0, 0, {'name': 'Bank', 'account_id': journal_secret.default_account_id.id, 'debit': 100}),
            ]
        })
        # Mock payment linkage (since we used manual entry for speed, but structurally matches payment)
        # To truly test 'payment_ids' rule, we need an account.payment or manually set payment_ids?
        # Account.payment is easier to verify 'payment_ids' field.
        # Let's create a real payment.
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'amount': 100,
            'journal_id': journal_secret.id,
        })
        payment.action_post()
        payment_move = payment.move_id
        payment_move._compute_journal_assign_to_ids()
        
        # 3. Verify Normal User CAN see it (Whitelist works)
        # Normal user is NOT in 'Secret Group', so normally hidden.
        # But 'payment_ids' is set, so should be visible.
        visible_move = self.env['account.move'].with_user(self.normal_user).search([('id', '=', payment_move.id)])
        self.assertTrue(visible_move, "Should see Payment Move in Group-Restricted Journal due to Whitelist")
        
        # 4. Verify Non-Whitelisted Entry is HIDDEN
        secret_move = self.env['account.move'].with_user(self.admin_user).create({
            'move_type': 'entry',
            'journal_id': journal_secret.id,
            'date': '2023-01-06',
            'line_ids': [
                (0, 0, {'name': 'Secret Exp', 'account_id': journal_secret.default_account_id.id, 'debit': 100}),
                (0, 0, {'name': 'Secret Bank', 'account_id': journal_secret.default_account_id.id, 'credit': 100}),
            ]
        })
        secret_move.action_post()
        secret_move._compute_journal_assign_to_ids()
        
        hidden_move = self.env['account.move'].with_user(self.normal_user).search([('id', '=', secret_move.id)])
        self.assertFalse(hidden_move, "Should NOT see pure internal move in Group-Restricted Journal")

    def test_combined_user_and_group_access(self):
        """
        Test that a Journal works correctly when BOTH 'assign_to_ids' AND 'journal_group_ids' are set.
        The logic should be additive (Union): Access if Assigned OR in Group.
        """
        # 1. Setup users
        user_assigned = self.normal_user # Will be explicitly assigned
        
        group_special = self.env['res.groups'].create({'name': 'Special Group'})
        user_in_group = self.env['res.users'].create({
            'name': 'Group User',
            'login': 'group_user',
            'email': 'group_user@test.com',
            'group_ids': [(6, 0, [self.env.ref('account.group_account_user').id, group_special.id])]
        })
        
        user_outsider = self.env['res.users'].create({
            'name': 'Outsider',
            'login': 'outsider',
            'email': 'outsider@test.com',
            'group_ids': [(6, 0, [self.env.ref('account.group_account_user').id])]
        })



        # 2. Setup Combined Journal
        default_account = self.env['account.account'].create({'name': 'Combo Account', 'code': '123456', 'account_type': 'asset_current'}).id
        journal_combo = self.env['account.journal'].create({
            'name': 'Combined Access Journal',
            'code': 'CMB',
            'type': 'general',
            'default_account_id': default_account,
            'assign_to_ids': [(4, user_assigned.id)],      # Explicitly assigned user
            'journal_group_ids': [(4, group_special.id)]   # Allowed Group
        })

        # 3. Create Move
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal_combo.id,
            'date': '2023-01-01',
            'line_ids': [
                (0, 0, {'name': 'Debit', 'account_id': journal_combo.default_account_id.id, 'debit': 100}),
                (0, 0, {'name': 'Credit', 'account_id': journal_combo.default_account_id.id, 'credit': 100}),
            ]
        })
        move.action_post()
        move._compute_journal_assign_to_ids()

        # 4. Assertions
        
        # A. User Assigned -> Should See
        self.assertTrue(self.env['account.move'].with_user(user_assigned).search([('id', '=', move.id)]), 
                        "User explicitly assigned should see the move (OR logic)")

        # B. User in Group -> Should See
        self.assertTrue(self.env['account.move'].with_user(user_in_group).search([('id', '=', move.id)]), 
                        "User in Allowed Group should see the move (OR logic)")

        # C. Outsider -> Should NOT See
        self.assertFalse(self.env['account.move'].with_user(user_outsider).search([('id', '=', move.id)]), 
                         "Outsider (neither assigned nor in group) should be BLOCKED")
