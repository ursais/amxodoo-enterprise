from odoo import fields, models


class HrPayrollIsr(models.Model):
    _name = "hr.payroll.isr"
    _description = "Payroll ISR Table"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    code = fields.Char(required=True)
    name = fields.Char(required=True, translate=True)
    date = fields.Date(string="Effective after", required=True)
    active = fields.Boolean(default=True)
    type_table = fields.Selection(
        [
            ("d", "Daily"),
            ("w", "Weekly"),
            ("t", "Every 10 days"),
            ("b", "Biweekly"),
            ("m", "Monthly"),
            ("a", "Annually"),
        ],
        string="Type",
    )
    line_ids = fields.One2many("hr.payroll.isr.line", "line_id", string="Periods Lines")

    _sql_constraints = [
        (
            "unique_type_table_date",
            "UNIQUE(type_table, date)",
            "A record with this type and date already exists.",
        )
    ]
