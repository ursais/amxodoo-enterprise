from odoo import fields, models


class HrPayrollTableES(models.Model):
    _name = "hr.payroll.es"
    _description = "Payroll Employment Subsidy Table"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    code = fields.Char(required=True)
    name = fields.Char(required=True)
    date = fields.Date(string="Effective after", required=True)
    active = fields.Boolean(default=True)
    type_table = fields.Selection(
        [
            ("d", "Daily"),
            ("w", "Weekly"),
            ("d", "Decenial"),
            ("b", "Biweekly"),
            ("m", "Monthly"),
            ("a", "Yearly"),
        ],
        string="Type",
        help="""* """,
    )
    line_ids = fields.One2many("hr.payroll.es.line", "line_id", string="Periods Lines")

    _sql_constraints = [
        (
            "unique_type_table_date",
            "UNIQUE(type_table, date)",
            "A record with this type and date already exists.",
        )
    ]
