# Copyright (C) 2026 Open Source Integrators (https://www.opensourceintegrators.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

KN_PO_RE = re.compile(r"^$|^PO[A-Z]{4}[0-9]{9}$")
KN_FILE_RE = re.compile(r"^73[0-9]{14}$")
KN_TRACKING_RE = re.compile(r"^[0-9]{10}-[0-9]{4}$")
KN_BRANCH_RE = re.compile(r"^[0-9]{2}[A-Z0-9]{2,4}$")
KN_TRANSPORT_RE = re.compile(r"^[0-9]{7}$")


class AccountMove(models.Model):
    _inherit = "account.move"

    kn_file_type = fields.Selection(
        selection=[
            ("file", "File Number"),
            ("tracking", "Tracking Number"),
        ],
        string="KN File/Tracking Type",
    )
    kn_file_number_gl = fields.Char(string="KN File Number GL")
    kn_branch_centre = fields.Char(string="KN Branch Centre")
    kn_transport_ref = fields.Char(string="KN Transport Ref")
    kn_flag = fields.Boolean(compute="_compute_kn_flag", store=True)

    @api.depends("partner_id.l10n_mx_edi_addenda")
    def _compute_kn_flag(self):
        for record in self:
            record.kn_flag = (
                record.partner_id.l10n_mx_edi_addenda_name == "Addenda Kuehne Nagel"
            )

    def _l10n_mx_edi_kn_normalize_vals(self, vals):
        """Normalize KN-specific values before create/write."""
        vals = dict(vals)
        if vals.get("kn_branch_centre"):
            vals["kn_branch_centre"] = vals["kn_branch_centre"].strip().upper()
        if vals.get("kn_file_number_gl"):
            vals["kn_file_number_gl"] = vals["kn_file_number_gl"].strip()
        if vals.get("kn_transport_ref"):
            vals["kn_transport_ref"] = vals["kn_transport_ref"].strip()
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._l10n_mx_edi_kn_normalize_vals(vals) for vals in vals_list]
        records = super().create(vals_list)
        kn_records = records.filtered("kn_flag")
        for record in kn_records:
            if record.ref:
                record.ref = record.ref.strip().upper()
        return records

    def write(self, vals):
        vals = self._l10n_mx_edi_kn_normalize_vals(vals)
        res = super().write(vals)
        if "ref" in vals:
            for record in self.filtered("kn_flag"):
                if record.ref:
                    super(AccountMove, record).write(
                        {"ref": record.ref.strip().upper()}
                    )
        return res

    def _post(self, soft=True):
        self._check_kn_addenda_fields()
        return super()._post(soft=soft)

    def _check_kn_addenda_fields(self):
        for record in self:
            if not record.kn_flag or record.move_type not in (
                "out_invoice",
                "out_refund",
            ):
                continue
            ref = (record.ref or "").strip().upper()
            if not KN_PO_RE.match(ref):
                raise ValidationError(
                    _(
                        "Customer Reference (Purchase Order) must be empty or match "
                        "PO + 4 uppercase letters + 9 digits (14 characters)."
                    )
                )
            if not record.kn_file_type:
                raise ValidationError(
                    _("Please select whether File Number or Tracking Number is used.")
                )
            file_val = (record.kn_file_number_gl or "").strip()
            if record.kn_file_type == "file":
                if not KN_FILE_RE.match(file_val):
                    raise ValidationError(
                        _(
                            "File Number must start with 73 followed by 14 digits "
                            "(16 characters, no separators)."
                        )
                    )
            elif not KN_TRACKING_RE.match(file_val):
                raise ValidationError(
                    _(
                        "Tracking Number must be 14 digits with a hyphen between "
                        "digits 10 and 11 (example: 1023950106-1815)."
                    )
                )
            branch = (record.kn_branch_centre or "").strip().upper()
            if not KN_BRANCH_RE.match(branch):
                raise ValidationError(
                    _(
                        "Branch Centre must be 2 digits followed by 2 to 4 "
                        "uppercase letters or digits (no separators)."
                    )
                )
            transport = (record.kn_transport_ref or "").strip()
            if not KN_TRANSPORT_RE.match(transport):
                raise ValidationError(
                    _("Transport Ref must be exactly 7 digits (no separators).")
                )

    @api.constrains(
        "ref",
        "kn_file_type",
        "kn_file_number_gl",
        "kn_branch_centre",
        "kn_transport_ref",
    )
    def _constrain_kn_addenda_format(self):
        """Validate format when KN fields are filled (draft-friendly)."""
        for record in self:
            if not record.kn_flag:
                continue
            ref = (record.ref or "").strip().upper()
            if ref and not KN_PO_RE.match(ref):
                raise ValidationError(
                    _(
                        "Customer Reference (Purchase Order) must be empty or match "
                        "PO + 4 uppercase letters + 9 digits (14 characters)."
                    )
                )
            file_val = (record.kn_file_number_gl or "").strip()
            if (
                file_val
                and record.kn_file_type == "file"
                and not KN_FILE_RE.match(file_val)
            ):
                raise ValidationError(
                    _(
                        "File Number must start with 73 followed by 14 digits "
                        "(16 characters, no separators)."
                    )
                )
            if (
                file_val
                and record.kn_file_type == "tracking"
                and not KN_TRACKING_RE.match(file_val)
            ):
                raise ValidationError(
                    _(
                        "Tracking Number must be 14 digits with a hyphen between "
                        "digits 10 and 11 (example: 1023950106-1815)."
                    )
                )
            branch = (record.kn_branch_centre or "").strip().upper()
            if branch and not KN_BRANCH_RE.match(branch):
                raise ValidationError(
                    _(
                        "Branch Centre must be 2 digits followed by 2 to 4 "
                        "uppercase letters or digits (no separators)."
                    )
                )
            transport = (record.kn_transport_ref or "").strip()
            if transport and not KN_TRANSPORT_RE.match(transport):
                raise ValidationError(
                    _("Transport Ref must be exactly 7 digits (no separators).")
                )
