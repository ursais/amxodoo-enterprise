# Copyright (C) 2023 Open Source Integrators
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    audi_business_unit = fields.Char(string="Business Unit")
    audi_applicant_email = fields.Char(string="Applicant email")
    audi_flag = fields.Boolean(compute="_compute_audi_flag", store=True)
    audi_tax_code = fields.Char(string="Tax Code")
    audi_fiscal_document_type = fields.Char(string="Fiscal Document Type")
    audi_document_type = fields.Char(string="Document Type")

    @api.depends(
        "commercial_partner_id.l10n_mx_edi_addenda_ids",
        "l10n_mx_edi_addenda_ids",
    )
    def _compute_audi_flag(self):
        """Show the Audi tab from the parent company addenda.

        Invoicing settings, including addendas, are stored on the commercial
        partner. An invoice for a contact must still open the tab. A leftover
        record with the same name as the module addenda counts too.
        """
        addenda = self.env.ref(
            "l10n_mx_edi_addenda_audi.l10n_mx_edi_addenda_audi",
            raise_if_not_found=False,
        )
        official = addenda or self.env["l10n_mx_edi.addenda"]
        if addenda:
            official |= self.env["l10n_mx_edi.addenda"].search(
                [("name", "=", addenda.name)]
            )
        for record in self:
            selected = (
                record.l10n_mx_edi_addenda_ids
                | record.commercial_partner_id.l10n_mx_edi_addenda_ids
            )
            record.audi_flag = bool(official & selected)
