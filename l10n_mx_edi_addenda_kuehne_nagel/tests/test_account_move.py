# Copyright (C) 2026 Gray Matter Logic (https://www.graymatterlogic.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from lxml import etree

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestKnAddenda(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.addenda = cls.env.ref(
            "l10n_mx_edi_addenda_kuehne_nagel.l10n_mx_edi_addenda_kuehne_nagel"
        )
        cls.partner_kn = cls.env["res.partner"].create(
            {
                "name": "Kuehne Nagel Test",
                "company_type": "company",
                "l10n_mx_edi_addenda": cls.addenda.id,
            }
        )
        cls.partner_other = cls.env["res.partner"].create(
            {
                "name": "Other Customer",
                "company_type": "company",
            }
        )

    def _create_invoice(self, partner, **extra):
        invoice = self.init_invoice(
            "out_invoice",
            partner=partner,
            products=self.product_a,
        )
        if extra:
            invoice.write(extra)
        return invoice

    def test_kn_flag_on_partner_with_addenda(self):
        invoice = self._create_invoice(self.partner_kn)
        self.assertTrue(invoice.kn_flag)
        self.assertEqual(
            self.partner_kn.l10n_mx_edi_addenda_name, "Addenda Kuehne Nagel"
        )

    def test_kn_flag_false_for_other_partner(self):
        invoice = self._create_invoice(self.partner_other)
        self.assertFalse(invoice.kn_flag)

    def test_normalize_branch_centre_uppercase(self):
        invoice = self._create_invoice(
            self.partner_kn,
            kn_file_type="file",
            kn_file_number_gl="7310880180505405",
            kn_branch_centre="10dwt",
            kn_transport_ref="2886541",
        )
        self.assertEqual(invoice.kn_branch_centre, "10DWT")

    def test_normalize_ref_uppercase_for_kn(self):
        invoice = self._create_invoice(
            self.partner_kn,
            ref="poabcd123456789",
            kn_file_type="file",
            kn_file_number_gl="7310880180505405",
            kn_branch_centre="10DWT",
            kn_transport_ref="2886541",
        )
        self.assertEqual(invoice.ref, "POABCD123456789")

    def test_invalid_purchase_order_format(self):
        invoice = self._create_invoice(self.partner_kn)
        with self.assertRaises(ValidationError):
            invoice.write({"ref": "INVALID-PO"})

    def test_invalid_file_number_format(self):
        invoice = self._create_invoice(self.partner_kn)
        with self.assertRaises(ValidationError):
            invoice.write(
                {
                    "kn_file_type": "file",
                    "kn_file_number_gl": "12345",
                }
            )

    def test_invalid_tracking_number_format(self):
        invoice = self._create_invoice(self.partner_kn)
        with self.assertRaises(ValidationError):
            invoice.write(
                {
                    "kn_file_type": "tracking",
                    "kn_file_number_gl": "10239501061815",
                }
            )

    def test_valid_tracking_number(self):
        invoice = self._create_invoice(
            self.partner_kn,
            kn_file_type="tracking",
            kn_file_number_gl="1023950106-1815",
            kn_branch_centre="10WP",
            kn_transport_ref="2886541",
        )
        self.assertEqual(invoice.kn_file_number_gl, "1023950106-1815")

    def test_invalid_branch_centre(self):
        invoice = self._create_invoice(self.partner_kn)
        with self.assertRaises(ValidationError):
            invoice.write({"kn_branch_centre": "AB"})

    def test_invalid_transport_ref(self):
        invoice = self._create_invoice(self.partner_kn)
        with self.assertRaises(ValidationError):
            invoice.write({"kn_transport_ref": "123"})

    def test_check_required_fields_on_post_helper(self):
        invoice = self._create_invoice(self.partner_kn)
        with self.assertRaises(ValidationError):
            invoice._check_kn_addenda_fields()

    def test_check_passes_with_complete_file_data(self):
        invoice = self._create_invoice(
            self.partner_kn,
            kn_file_type="file",
            kn_file_number_gl="7310880180505405",
            kn_branch_centre="10DWT",
            kn_transport_ref="2886541",
        )
        invoice._check_kn_addenda_fields()

    def test_check_passes_with_empty_purchase_order(self):
        invoice = self._create_invoice(
            self.partner_kn,
            ref=False,
            kn_file_type="file",
            kn_file_number_gl="7310880180505405",
            kn_branch_centre="10DWT",
            kn_transport_ref="2886541",
        )
        invoice._check_kn_addenda_fields()

    def test_other_partner_skips_kn_checks(self):
        invoice = self._create_invoice(self.partner_other, ref="anything")
        invoice._check_kn_addenda_fields()

    def test_qweb_addenda_xml_structure(self):
        invoice = self._create_invoice(
            self.partner_kn,
            ref=False,
            kn_file_type="file",
            kn_file_number_gl="7310880180505405",
            kn_branch_centre="10DWT",
            kn_transport_ref="2886541",
        )
        xml = self.env["ir.qweb"]._render(
            self.addenda.id,
            {"record": invoice},
        )
        root = etree.fromstring(xml)
        self.assertTrue(root.tag.endswith("KNRECEPCION"))
        ns = {"kn": "http://www.w3.org/2001/XMLSchema"}
        facturas = root.find(".//kn:FacturasKN", namespaces=ns)
        self.assertIsNotNone(facturas)
        self.assertEqual(
            facturas.findtext("kn:FileNumber_GL", namespaces=ns),
            "7310880180505405",
        )
        self.assertEqual(
            facturas.findtext("kn:Branch_Centre", namespaces=ns),
            "10DWT",
        )
        self.assertEqual(
            facturas.findtext("kn:TransportRef", namespaces=ns),
            "2886541",
        )
        po = facturas.find("kn:Purchase_Order", namespaces=ns)
        self.assertIsNotNone(po)
        self.assertFalse((po.text or "").strip())

    def test_qweb_addenda_with_purchase_order(self):
        invoice = self._create_invoice(
            self.partner_kn,
            ref="POABCD123456789",
            kn_file_type="tracking",
            kn_file_number_gl="1023950106-1815",
            kn_branch_centre="99NFP",
            kn_transport_ref="1234567",
        )
        xml = self.env["ir.qweb"]._render(
            self.addenda.id,
            {"record": invoice},
        )
        root = etree.fromstring(xml)
        ns = {"kn": "http://www.w3.org/2001/XMLSchema"}
        self.assertEqual(
            root.findtext(".//kn:Purchase_Order", namespaces=ns),
            "POABCD123456789",
        )
        self.assertEqual(
            root.findtext(".//kn:FileNumber_GL", namespaces=ns),
            "1023950106-1815",
        )
