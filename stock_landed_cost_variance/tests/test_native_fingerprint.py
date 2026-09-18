import hashlib
import inspect

from odoo.tests import TransactionCase, tagged

from odoo.addons.sale_stock.models.account_move import AccountMoveLine as SaleStockLine
from odoo.addons.stock_account.models.product import ProductProduct as StockAccountProduct
from odoo.addons.stock_account.models.stock_lot import StockLot as StockAccountLot
from odoo.addons.stock_account.models.stock_move import StockMove as StockAccountMove

# The engine does not compute a cost of its own: it reproduces these native methods statement by statement
# (design v4, D3 and D5), because Odoo's own functions cannot be called per exit -- they filter by date and
# confuse movements sharing a second (measured). A fingerprint of each one turns an update of Odoo into a
# failed build instead of a wrong valuation discovered months later.
#
# Each method carries the set of versions ALREADY REVIEWED. A version is only added after reading the new
# native source, checking the mirror still reproduces it and re-running the measured scenarios; the date
# and the reason are written next to it. An unknown hash fails the build, which is the whole point.
#
# Bootstrap: put 'BOOTSTRAP' in a set and the test prints the current hash.
REVIEWED = {
    "ProductProduct._run_average_batch": (StockAccountProduct._run_average_batch, {
        # Odoo 19.0 snapshot / Docker image, 2026-09
        "6b6e4409eb02ccedec101882d8e915c6a22a87fffc4010d393ac4bb815e43d2b",
        # Odoo.SH build 2026-09-18: dropship leaves the average engine and the loop keeps its state per
        # move instead of per product. The replay already excluded dropship, and the accumulation (entry
        # on positive stock, reset on negative, exit at the average) is unchanged. Reviewed line by line.
        "c703848bc5699c1f208db259c33622c9a490b99dbe604eede83c17274708d4d2",
    }),
    "ProductProduct._run_fifo": (StockAccountProduct._run_fifo, {
        "d41b8e3e4992aeeb8d9233dbee31bd9489a5c23f2228cd9880e9f78901a2447e",
    }),
    "ProductProduct._run_fifo_get_stack": (StockAccountProduct._run_fifo_get_stack, {
        "a8146f915dcae9ee6b900681648be8f21623ae8a23b512fdb3cf6082412f2a5a",
    }),
    "ProductProduct._update_standard_price": (StockAccountProduct._update_standard_price, {
        "65b71eac7182a5fe5d83f9f9d7a8e68beeaf73e3a7da00493dc61a3159d0a4cb",
    }),
    "StockMove._set_value": (StockAccountMove._set_value, {
        "ab6221d8c6b1af60bcdcadebaa312620edba171df6e722f489c715159d918142",
        # Odoo.SH build 2026-09-18: dropship leaves the incoming branch and a correction with no previous
        # quantity now falls through instead of returning. The engine calls this method (it does not copy
        # it) and only mirrors the lot rule -- an exit line at lot.standard_price -- which is untouched.
        "1347466e2a06b5d13181cc35c2704e15430c60f2b9b877e937a33439d295d8a2",
    }),
    "StockMove._get_valued_qty": (StockAccountMove._get_valued_qty, {
        "e181dfdb02a4fe7fb3bfef5063c50761dba53d7dbaf04bfb547b98d456595d88",
    }),
    "StockLot._update_standard_price": (StockAccountLot._update_standard_price, {
        "49d4c462c79c2d09d91168012b20861e7baac262b8cc921d05d96978d67d54b4",
    }),
    "StockLot._compute_value": (StockAccountLot._compute_value, {
        "833d87d1fb73d683f25396551d5653735dc751102e120689d6d5d56fbfb2d14a",
        # Odoo.SH build 2026-09-18: same source, different file layout around it.
        "fec8afaffbe4d95f117ca2ed28c84c032755bbbb89d31c4be12c5bc1e1d93332",
    }),
    "AccountMoveLine._get_posted_cogs_value (sale_stock)": (SaleStockLine._get_posted_cogs_value, {
        "322b31e43234f4037f8e44fa9583680bc83d428ab547939d860026961718bc40",
        # Odoo.SH build 2026-09-18: credit notes now count in the cost of sales already posted, and a new
        # helper feeds a refund from its original invoice. Our extension adds its adjustments on top of
        # whatever the native formula returns, and the credit note reversal (D6) is measured on top of
        # this: test_e3 and test_f pass on both builds.
        "b8f1dc1855cd63b77ba1e72890dcd3a9603c1736f99831efac20433f7dd4e2b4",
    }),
    "AccountMoveLine._get_cogs_qty (sale_stock)": (SaleStockLine._get_cogs_qty, {
        "07e4b3f09811d92af25c965d0cea8f60bdb27bf361baf642fef8e075800ceb50",
        # Odoo.SH build 2026-09-18: credit notes also count in the quantity. Our own count of units whose
        # cost of sales is posted already subtracts refunds (sale_order_line._variance_costed_qty).
        "2dc203837d2c856c0c5b33c3276ecef068d176178bd78a106840b437dcdb1e54",
    }),
}

DRIFT = ("Odoo changed %s, which this module reproduces. Read the new native source, check the mirror still "
         "reproduces it, re-run the measured scenarios and only then add the hash to REVIEWED. Current: %s")


@tagged("post_install", "-at_install")
class TestNativeFingerprint(TransactionCase):
    """Guard against Odoo changing the code the engine reproduces.

    Odoo.SH runs a newer build than any local snapshot, and clients sit on different ones, so a method has
    several reviewed versions. What is never allowed is an unreviewed one: the parity tests check the
    replay against the values Odoo actually stores, but only for the scenarios they cover, and this is
    what makes someone read the diff.
    """

    def test_the_native_methods_this_module_mirrors_have_not_changed(self):
        drifted, bootstrap = [], []
        for name, (method, reviewed) in REVIEWED.items():
            actual = hashlib.sha256(inspect.getsource(method).encode()).hexdigest()
            if "BOOTSTRAP" in reviewed:
                bootstrap.append(f'    "{name}": ..., "{actual}"')
            elif actual not in reviewed:
                drifted.append(DRIFT % (name, actual))
        if bootstrap:
            self.fail("FINGERPRINTS TO RECORD:\n" + "\n".join(bootstrap))
        self.assertFalse(drifted, "\n\n".join(drifted))
