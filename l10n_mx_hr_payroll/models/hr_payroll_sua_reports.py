import base64
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class HrPayrollSUAReports(models.Model):
    _name = "hr.payroll.sua.reports"
    _description = "Payroll SUA Reports"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char()
    date_start = fields.Date()
    date_end = fields.Date()
    report_type = fields.Selection(
        [
            ("alta", "SUA Registration"),
            ("movt", "SUA Movements"),
        ]
    )
    movt_type = fields.Selection(
        [
            ("02", "Deregistration"),
            ("07", "Salary Modification"),
            ("08", "Reinstatement"),
            ("11", "Absenteeism"),
            ("12", "Incapacity"),
        ],
        default="02",
        string="Movement Type",
    )
    line_ids = fields.One2many(
        "hr.payroll.sua.reports.line", "line_id", string="Payment Lines"
    )
    notes = fields.Html()
    movs_count = fields.Integer(compute="_compute_movs_count")
    txt_file = fields.Binary("txt file")
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("calculated", "Calculated"),
            ("done", "Done"),
            ("cancel", "Cancel"),
        ],
        default="draft",
    )

    def _compute_movs_count(self):
        for movs in self:
            movs.movs_count = len(movs.line_ids)

    def action_open_payroll_movs_sua(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payroll.sua.reports.line",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [["id", "in", self.line_ids.ids]],
            "name": "Payroll Movements of SUA",
        }

    @api.onchange("report_type", "date_start", "date_end", "name", "movt_type")
    def _onchange_name(self):
        for sua in self:
            if sua.report_type == "alta":
                sua.name = "SUA Report - Registration "
            elif sua.report_type == "movt":
                sua.name = "SUA Report - Movements "
            elif sua.report_type == "movt" and sua.movt_type == "08":
                sua.name = "SUA Report - Reinstatement"
            else:
                sua.name = ""

    def sua_done(self):
        for sua in self:
            sua.state = "done"
            sua.message_post(body=_("Payroll SUA Report has been Calculated"))
            return True

    def sua_cancel(self):
        for sua in self:
            sua.state = "cancel"
            sua.message_post(body=_("Payroll SUA Report has been Cancelled"))
            return True

    def sua_calculate(self):
        for sua in self:
            sua.state = "calculated"
            date_start = sua.date_start
            date_end = sua.date_end

            if sua.report_type == "alta":
                sua.name = "SUA Report- Registration "
                contract_ids = self.env["hr.contract"].search(
                    [
                        "&",
                        "&",
                        ("date_start", ">=", date_start),
                        ("date_start", "<=", date_end),
                        ("state", "=", "open"),
                        ("company_id", "=", sua.company_id.id),
                    ]
                )
                sua.line_ids.unlink()
                for contract_id in contract_ids:
                    line = self.env["hr.payroll.sua.reports.line"].create(
                        {
                            "line_id": sua.id,
                            "date": fields.Date.context_today(self),
                            "name": contract_id.employee_id.id,
                            "contract_id": contract_id.id,
                            "ssnid": contract_id.employee_id.ssnid,
                            "company_id": sua.company_id.id,
                        }
                    )
            elif sua.report_type == "movt":
                self.movements(sua)
            else:
                sua.name = "SUA Report - without specifying the type of movement"

            sua.message_post(body=_("Payroll SUA Report has been Calculated"))
            return True

    def movements(self, sua):
        if sua.movt_type == "02":
            sua.name = "SUA Report - Deregistration "
            contract_ids = self.env["hr.contract"].search(
                [
                    "&",
                    ("date_end", ">=", sua.date_start),
                    ("date_end", "<=", sua.date_end),
                    ("state", "=", "cancel"),
                ]
            )
            self.line_ids.unlink()
            for contract_id in contract_ids:
                self.env["hr.payroll.sua.reports.line"].create(
                    {
                        "line_id": self.id,
                        "date": fields.Date.context_today(self),
                        "name": contract_id.employee_id.id,
                        "contract_id": contract_id.id,
                        "ssnid": contract_id.employee_id.ssnid,
                        "company_id": sua.company_id.id,
                    }
                )
        if self.movt_type == "07":
            sua.name = "SUA Report - Salary Modification"
            sua.line_ids.unlink()
            salary_history_ids = self.env["hr.contract.salary_history"].search(
                [
                    "&",
                    "&",
                    ("state", "=", "applied"),
                    ("date_applied", ">=", sua.date_start),
                    ("date_applied", "<=", sua.date_end),
                ]
            )
            sua.line_ids.unlink()
            for salary_id in salary_history_ids:
                self.env["hr.payroll.sua.reports.line"].create(
                    {
                        "line_id": sua.id,
                        "date": salary_id.date_applied,
                        "name": salary_id.employee_id.id,
                        "contract_id": salary_id.contract_id.id,
                        "ssnid": salary_id.employee_id.ssnid,
                        "company_id": sua.company_id.id,
                    }
                )
        if sua.movt_type == "08":
            sua.name = "SUA Report- Reinstatement"
            contract_ids = self.env["hr.contract"].search(
                [
                    "&",
                    "&",
                    ("date_start", ">=", sua.date_start),
                    ("date_start", "<=", sua.date_end),
                    ("state", "=", "open"),
                    ("company_id", "=", sua.company_id.id),
                ]
            )
            contract_olders_ids = self.env["hr.contract"].search(
                [
                    ("state", "in", ["cancel", "close"]),
                    ("company_id", "=", sua.company_id.id),
                ]
            )
            sua.line_ids.unlink()
            if contract_ids and contract_olders_ids:
                for contract_id in contract_ids:
                    self.env["hr.payroll.sua.reports.line"].create(
                        {
                            "line_id": sua.id,
                            "date": fields.Date.context_today(self),
                            "name": contract_id.employee_id.id,
                            "contract_id": contract_id.id,
                            "ssnid": contract_id.employee_id.ssnid,
                            "company_id": sua.company_id.id,
                        }
                    )
        if sua.movt_type == "11":
            sua.name = "SUA Report - Absenteeism"
            timeoff_ids = self.env["hr.leave"].search(
                [
                    "&",
                    "&",
                    ("state", "=", "validate"),
                    ("request_date_from", ">=", sua.date_start),
                    ("request_date_to", "<=", sua.date_end),
                ]
            )
            sua.line_ids.unlink()
            if timeoff_ids:
                for timeoff_id in timeoff_ids:
                    if (
                        timeoff_id.holiday_status_id.time_type == "leave"
                        and not timeoff_id.holiday_status_id.disabilities_type
                    ):
                        self.env["hr.payroll.sua.reports.line"].create(
                            {
                                "line_id": sua.id,
                                "date": timeoff_id.request_date_from,
                                "name": timeoff_id.employee_id.id,
                                "contract_id": False,
                                "timeoff_id": timeoff_id.id,
                                "ssnid": timeoff_id.employee_id.ssnid,
                                "company_id": sua.company_id.id,
                            }
                        )
        if sua.movt_type == "12":
            sua.name = "SUA Report - Incapacity"
            timeoff_ids = self.env["hr.leave"].search(
                [
                    "&",
                    "&",
                    ("state", "=", "validate"),
                    ("request_date_from", ">=", sua.date_start),
                    ("request_date_to", "<=", sua.date_end),
                ]
            )
            sua.line_ids.unlink()
            if timeoff_ids:
                for timeoff_id in timeoff_ids:
                    if (
                        timeoff_id.holiday_status_id.time_type == "leave"
                        and timeoff_id.holiday_status_id.disabilities_type
                    ):
                        self.env["hr.payroll.sua.reports.line"].create(
                            {
                                "line_id": sua.id,
                                "date": timeoff_id.request_date_from,
                                "name": timeoff_id.employee_id.id,
                                "contract_id": False,
                                "timeoff_id": timeoff_id.id,
                                "ssnid": timeoff_id.employee_id.ssnid,
                                "company_id": sua.company_id.id,
                            }
                        )

    def sua_back_to_draft(self):
        for sua in self:
            sua.state = "draft"
            sua.message_post(body=_("Payroll SUA Report has been draft"))
            return True

    def sua_txt(self):
        data = ""
        lines = ""

        for sua in self:
            if sua.report_type == "alta":
                for line in self.line_ids:
                    contract = line.contract_id
                    employee = line.name
                    
                    # Get contract date components
                    reg_date = contract.date_start
                    day = str(reg_date.day).zfill(2)
                    month = str(reg_date.month).zfill(2)
                    year = str(reg_date.year)
                    
                    # Get employee name components
                    lastname = str(employee.lastname or "").upper()
                    second_lastname = str(employee.second_lastname or "").upper()
                    firstname = str(employee.firstname or "").upper()
                    
                    # Nombre fragmento 1: LEFT(col & espacios, 13) - lastname
                    fragmento_1 = (lastname + " " * 13)[:13]
                    
                    # Nombre fragmento 2: LEFT(col & espacios, 18) - second_lastname
                    fragmento_2 = (second_lastname + " " * 18)[:18]
                    
                    # Nombre completo con $ separador, pad a 50 caracteres
                    nombre_completo = f"{lastname}${second_lastname}${firstname}"
                    nombre_completo_padded = (nombre_completo + " " * 50)[:50]
                    
                    # Tipo trabajador: from contract_type
                    # Mapping contract_type to worker type (1=Permanente, 2=Eventual, 3=Ev. Construcción)
                    contract_type = contract.contract_type or "01"
                    if contract_type in ["01", "03"]:  # Indefinite, Specific period
                        tipo_trabajador = "1"
                    elif contract_type in ["02", "04", "05", "06", "07", "08"]:
                        tipo_trabajador = "2"
                    else:
                        tipo_trabajador = "1"  # Default to permanente
                    
                    # Tipo jornada: from journal_type
                    # 0=Completa, 1-5=días trabajados, 6=menos de 1 día
                    journal_type = contract.journal_type or "00"
                    if journal_type == "00":
                        tipo_jornada = "0"
                    elif journal_type in ["01", "02", "03", "04", "05"]:
                        tipo_jornada = journal_type[-1]  # Get last digit: 1, 2, 3, 4, 5
                    elif journal_type == "06":
                        tipo_jornada = "6"
                    else:
                        tipo_jornada = "0"
                    
                    # Tipo salario: from salary_type
                    # 01=Fixed, 02=Mixte, 03=Variable -> mapped to SUA codes
                    salary_type = contract.salary_type or "01"
                    # Map to SUA salary type codes (need to verify exact mapping)
                    if salary_type == "01":
                        tipo_salario = "0"  # Fixed -> 0
                    elif salary_type == "02":
                        tipo_salario = "1"  # Mixte -> 1
                    else:
                        tipo_salario = "2"  # Variable -> 2
                    
                    # Salario diario integrado (SDI)
                    sdi = contract.sdi or 0.0
                    sdi_entero = int(sdi)
                    sdi_decimal = int(round((sdi - sdi_entero) * 100))
                    
                    # Format salary: entero (5 digits) + decimales (2 digits)
                    salario_entero = str(sdi_entero).zfill(5)[-5:]  # RIGHT("00000"& INT(sal), 5)
                    salario_decimales = str(sdi_decimal).zfill(2)[-2:]  # RIGHT(FIXED(sal,2), 2)
                    
                    # NSS: If 10 digits -> "0"&NSS, if 11 -> NSS as is
                    ssnid = str(employee.ssnid or "")
                    if len(ssnid) == 10:
                        nss = "0" + ssnid
                    elif len(ssnid) == 11:
                        nss = ssnid
                    else:
                        nss = ssnid.zfill(11)
                    
                    # Worker name (17 chars) - repeat full name padded
                    nombre_trabajador_17c = (lastname + second_lastname + firstname + " " * 17)[:17]
                    
                    # Get employer register
                    employer_register = employee.employer_register.name if employee.employer_register else ""
                    
                    # Tipo salario code (8 chars)
                    tipo_salario_code = tipo_salario + " " * 7
                    
                    # Build the record according to new format (164 characters total)
                    # Position mapping:
                    # 1-11: Registro Patronal (11 chars)
                    # 12-22: NSS (11 chars)
                    # 23-35: Nombre fragmento 1 (13 chars)
                    # 36-53: Nombre fragmento 2 (18 chars)
                    # 54-103: Datos compuestos con $ separador (50 chars)
                    # 104-104: Tipo trabajador (1 char)
                    # 105-105: Tipo jornada (1 char)
                    # 106-107: Día de alta (2 chars)
                    # 108-109: Mes de alta (2 chars)
                    # 110-113: Año de alta (4 chars)
                    # 114-118: Salario entero (5 chars)
                    # 119-120: Salario decimales (2 chars)
                    # 121-137: Nombre trabajador (17 chars)
                    # 138-147: Espacios vacíos (10 chars)
                    # 148-149: Día de alta repetido (2 chars)
                    # 150-151: Mes de alta repetido (2 chars)
                    # 152-155: Año de alta repetido (4 chars)
                    # 156-156: Espacio separador (1 char)
                    # 157-164: Tipo salario (8 chars)
                    
                    record = (
                        employer_register[:11].ljust(11) +           # 1-11: Registro Patronal
                        nss +                                        # 12-22: NSS
                        fragmento_1 +                                # 23-35: Nombre fragmento 1
                        fragmento_2 +                                # 36-53: Nombre fragmento 2
                        nombre_completo_padded +                     # 54-103: Datos compuestos
                        tipo_trabajador +                            # 104: Tipo trabajador
                        tipo_jornada +                               # 105: Tipo jornada
                        day +                                        # 106-107: Día
                        month +                                      # 108-109: Mes
                        year +                                       # 110-113: Año
                        salario_entero +                             # 114-118: Salario entero
                        salario_decimales +                          # 119-120: Salario decimales
                        nombre_trabajador_17c +                      # 121-137: Nombre trabajador
                        " " * 10 +                                   # 138-147: Espacios vacíos
                        day +                                        # 148-149: Día repetido
                        month +                                      # 150-151: Mes repetido
                        year +                                       # 152-155: Año repetido
                        " " +                                        # 156: Espacio separador
                        tipo_salario_code                            # 157-164: Tipo salario
                    )
                    
                    lines += record + "\n"

                self.txt_file = base64.b64encode(lines.encode("cp1252"))
                return {
                    "type": "ir.actions.act_url",
                    "url": "/web/content/hr.payroll.sua.reports/"
                    + "%s/txt_file/%s?download=true" % (self.id, "aseg.txt"),
                    "target": "self",
                }
            elif sua.report_type == "movt":
                if sua.movt_type == "02":
                    for line in self.line_ids:
                        data = [""] * 7
                        data[0] = line.name.employer_register.name
                        data[1] = line.name.ssnid.zfill(11)
                        data[2] = "02"
                        data[3] = (
                            str(line.contract_id.date_end)[-2:]
                            + str(line.contract_id.date_end)[5:7]
                            + str(line.contract_id.date_end)[:4]
                        )
                        data[4] = " " * 8
                        data[5] = " " * 2
                        data[6] = " " * 7

                        lines += "".join(str(d) for d in data) + "\n"

                    self.txt_file = base64.b64encode(lines.encode("cp1252"))
                    return {
                        "type": "ir.actions.act_url",
                        "url": "/web/content/hr.payroll.sua.reports/"
                        + "%s/txt_file/%s?download=true" % (self.id, "movt.txt"),
                        "target": "self",
                    }
                if sua.movt_type == "07":
                    for line in self.line_ids:
                        date = sorted(
                            line.name.contract_id.salary_history_ids,
                            key=lambda x: x.date_applied,
                            reverse=True,
                        )[0]
                        data = [""] * 7
                        data[0] = line.name.employer_register.name
                        data[1] = line.name.ssnid.zfill(11)
                        data[2] = "07"
                        data[3] = (
                            str(date.date_applied)[-2:]
                            + str(date.date_applied)[5:7]
                            + str(date.date_applied)[:4]
                        )
                        data[4] = " " * 8
                        data[5] = " " * 2
                        data[6] = (
                            format(line.name.contract_id.sdi, ".2f")
                            .replace(".", "")
                            .zfill(7)
                        )

                        lines += "".join(str(d) for d in data) + "\n"

                    self.txt_file = base64.b64encode(lines.encode("cp1252"))
                    return {
                        "type": "ir.actions.act_url",
                        "url": "/web/content/hr.payroll.sua.reports/"
                        + "%s/txt_file/%s?download=true" % (self.id, "movt.txt"),
                        "target": "self",
                    }
                if sua.movt_type == "08":
                    for line in self.line_ids:
                        data = [""] * 7
                        data = [""] * 7
                        data[0] = line.name.employer_register.name
                        data[1] = line.name.ssnid.zfill(11)
                        data[2] = "08"
                        data[3] = (
                            str(line.contract_id.date_start.strftime("%d"))
                            + str(line.contract_id.date_start.strftime("%m"))
                            + str(line.contract_id.date_start.strftime("%Y"))
                        )
                        data[4] = " " * 8
                        data[5] = " " * 2
                        data[6] = (
                            format(line.name.contract_id.sdi, ".2f")
                            .replace(".", "")
                            .zfill(7)
                        )

                        lines += "".join(str(d) for d in data) + "\n"

                    self.txt_file = base64.b64encode(lines.encode("cp1252"))
                    return {
                        "type": "ir.actions.act_url",
                        "url": "/web/content/hr.payroll.sua.reports/"
                        + "%s/txt_file/%s?download=true" % (self.id, "movt.txt"),
                        "target": "self",
                    }
                if sua.movt_type in ["11", "12"]:
                    _logger.info("SUA to TXT -->>  11 o 12")
                    for line in self.line_ids:
                        employer_register = line.name.employer_register.name
                        ssnid = line.name.ssnid

                        data = [""] * 7
                        data[0] = employer_register
                        data[1] = ssnid.zfill(11)
                        data[2] = sua.movt_type
                        data[3] = line.date.strftime("%d%m%Y")
                        if isinstance(line.timeoff_id.disability_folio, str):
                            data[4] = line.timeoff_id.disability_folio[:8]
                        else:
                            data[4] = " " * 8
                        data[5] = str(
                            int(line.timeoff_id.number_of_days_display)
                        ).zfill(2)
                        data[6] = " " * 7

                        lines += "".join(str(d) for d in data) + "\n"

                    self.txt_file = base64.b64encode(lines.encode("cp1252"))
                    return {
                        "type": "ir.actions.act_url",
                        "url": "/web/content/hr.payroll.sua.reports/"
                        + "%s/txt_file/%s?download=true" % (self.id, "movt.txt"),
                        "target": "self",
                    }


class HrPayrollSUAReportsLine(models.Model):
    _name = "hr.payroll.sua.reports.line"
    _description = "Payroll SUA Reports Line"

    line_id = fields.Many2one(
        "hr.payroll.sua.reports", required=True, ondelete="cascade"
    )
    name = fields.Many2one("hr.employee")
    date = fields.Date()
    contract_id = fields.Many2one("hr.contract")
    ssnid = fields.Char(string="NSS")
    amount = fields.Float()
    timeoff_id = fields.Many2one("hr.leave")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("paid", "Paid"),
            ("cancel", "Cancel"),
        ],
        default="draft",
    )
    company_id = fields.Many2one("res.company")
