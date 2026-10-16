# Copyright (C) 2023 Open Source Integrators
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    audi_supplier_email = fields.Char(string="Supplier Email")
    audi_supplier_number = fields.Char(string="Supplier Number")
    audi_addenda_selected = fields.Boolean(
        compute="_compute_audi_addenda_selected",
    )

    @api.depends(
        "l10n_mx_edi_addenda_ids",
        "commercial_partner_id.l10n_mx_edi_addenda_ids",
    )
    def _compute_audi_addenda_selected(self):
        addenda = self.env.ref(
            "l10n_mx_edi_addenda_audi.l10n_mx_edi_addenda_audi",
            raise_if_not_found=False,
        )
        official = addenda or self.env["l10n_mx_edi.addenda"]
        if addenda:
            official |= self.env["l10n_mx_edi.addenda"].search(
                [("name", "=", addenda.name)]
            )
        for partner in self:
            selected = partner.commercial_partner_id.l10n_mx_edi_addenda_ids
            partner.audi_addenda_selected = bool(official & selected)
