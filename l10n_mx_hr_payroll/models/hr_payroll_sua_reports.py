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
    afilacion_file = fields.Binary("Afiliación txt file")
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

        for sua in self:
            # Determine file name based on report type and movement type
            if sua.report_type == "alta":
                file_name = "aseg.txt"
            elif sua.report_type == "movt" and sua.movt_type == "02":
                file_name = "baja.txt"
            else:
                file_name = "movimiento.txt"
            
            for line in self.line_ids:
                contract = line.contract_id
                employee = line.name

                # Get employer register (11 chars)
                employer_register = str(employee.employer_register.name if employee.employer_register else "")
                registro_patronal = employer_register[:11].ljust(11)

                # NSS (11 chars)
                ssnid = str(employee.ssnid or "")
                if len(ssnid) == 10:
                    nss = "0" + ssnid
                elif len(ssnid) == 11:
                    nss = ssnid
                else:
                    nss = ssnid.zfill(11)
                nss_padded = nss[:11].ljust(11)

                # Check if this is a Baja (deregistration) process
                if sua.report_type == "movt" and sua.movt_type == "02":
                    # Baja format (49 characters total)
                    # 1-11: Registro Patronal (11 chars)
                    # 12-22: NSS (11 chars)
                    # 23-24: Causa de baja (2 chars) - hardcoded as "20"
                    # 25-26: Día baja (2 chars)
                    # 27-28: Mes baja (2 chars)
                    # 29-32: Año baja (4 chars)
                    # 33-40: Espacios vacíos (8 chars)
                    # 41-49: Ceros fijos (9 chars)
                    
                    # Causa de baja - hardcoded as "20"
                    causa_baja = "02"

                    # Get date components from line.date
                    if line.date:
                        baja_date = line.date
                    else:
                        baja_date = fields.Date.context_today(self)
                    
                    day = str(baja_date.day).zfill(2)
                    month = str(baja_date.month).zfill(2)
                    year = str(baja_date.year)[-4:]  # Get last 4 digits of year

                    # Espacios vacíos (8 chars)
                    espacios_vacios = " " * 8

                    # Ceros fijos (9 chars)
                    ceros_fijos = "000000000"

                    record = (
                        registro_patronal +        # 1-11: Registro Patronal
                        nss_padded +               # 12-22: NSS
                        causa_baja +               # 23-24: Causa de baja
                        day +                      # 25-26: Día baja
                        month +                    # 27-28: Mes baja
                        year +                     # 29-32: Año baja
                        espacios_vacios +          # 33-40: Espacios vacíos
                        ceros_fijos                # 41-49: Ceros fijos
                    )
                else:
                    # Alta format (164 characters total)
                    # Get contract date components
                    reg_date = contract.date_start
                    day = str(reg_date.day).zfill(2)
                    month = str(reg_date.month).zfill(2)
                    year = str(reg_date.year)
                    
                    # Get employee name components
                    lastname = str(employee.lastname or "").upper()
                    second_lastname = str(employee.second_lastname or "").upper()
                    firstname = str(employee.firstname or "").upper()
                    
                    # Get RFC (13 chars) from employee's VAT
                    rfc = str(employee.address_home_id.vat or "").upper()
                    rfc_padded = (rfc + " " * 13)[:13]
                    
                    # Get CURP (18 chars) from employee
                    curp = str(employee.address_home_id.curp or "").upper()
                    curp_padded = (curp + " " * 18)[:18]
                    
                    # Nombre completo con $ separador, pad a 50 caracteres
                    # Formato: Apellido P. $ Apellido M. $ Nombres
                    nombre_completo = f"{lastname}${second_lastname}${firstname}"
                    nombre_completo_padded = (nombre_completo + " " * 50)[:50]
                    
                    # Tipo trabajador: from contract_type
                    # Mapping contract_type to worker type (1=Perm, 2=Eventual, 3=Ev.Constr.)
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
                    # New mapping: 0=Fijo, 1=Variable, 2=Mixto
                    salary_type = contract.salary_type or "01"
                    if salary_type == "01":
                        tipo_salario = "0"  # Fixed -> 0 (Fijo)
                    elif salary_type == "03":
                        tipo_salario = "1"  # Variable -> 1 (Variable)
                    else:
                        tipo_salario = "2"  # Mixte -> 2 (Mixto)
                    
                    # Salario diario integrado (SDI)
                    sdi = contract.sdi or 0.0
                    sdi_entero = int(sdi)
                    sdi_decimal = int(round((sdi - sdi_entero) * 100))
                    
                    # Format salary: entero (5 digits) + decimales (2 digits)
                    salario_entero = str(sdi_entero).zfill(5)[-5:]  # RIGHT("00000"& INT(sal), 5)
                    salario_decimales = str(sdi_decimal).zfill(2)[-2:]  # RIGHT(FIXED(sal,2), 2)
                    
                    # Clave/Ocupación: employee_number (17 chars)
                    employee_number = str(employee.employee_number or "")
                    clave_ocupacion = (employee_number + " " * 17)[:17]
                    
                    # Tipo salario code (8 chars)
                    tipo_salario_code = tipo_salario * 7
                    
                    record = (
                        employer_register[:11].ljust(11) +           # 1-11: Registro Patronal
                        nss +                                        # 12-22: NSS
                        rfc_padded +                                 # 23-35: RFCC
                        curp_padded +                                # 36-53: CURP
                        nombre_completo_padded +                     # 54-103: Nombre completo
                        tipo_trabajador +                            # 104: Tipo trabajador
                        tipo_jornada +                               # 105: Tipo jornada
                        day +                                        # 106-107: Día
                        month +                                      # 108-109: Mes
                        year +                                       # 110-113: Año
                        salario_entero +                             # 114-118: Salario entero
                        salario_decimales +                          # 119-120: Salario decimales
                        clave_ocupacion +                            # 121-137: Clave/Ocupación
                        " " * 10 +                                   # 138-147: Espacios vacíos
                        day +                                        # 148-149: Día repetido
                        month +                                      # 150-151: Mes repetido
                        year +                                       # 152-155: Año repetido
                        " " +                                        # 156: Espacio separador
                        tipo_salario_code                            # 157-164: Tipo salario
                    )

                data += record + "\n"

        self.txt_file = base64.b64encode(data.encode("cp1252"))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/hr.payroll.sua.reports/"
            + "%s/txt_file/%s?download=true" % (self.id, file_name),
            "target": "self",
        }

    def afilacion_txt(self):
        """Generate Afiliación TXT file for IMSS registration"""
        lines = ""
        for sua in self:
            for line in self.line_ids:
                contract = line.contract_id
                employee = line.name

                # Get employer register (11 chars)
                employer_register = str(employee.employer_register.name if employee.employer_register else "")
                registro_patronal = employer_register[:11].ljust(11)

                # NSS (11 chars)
                ssnid = str(employee.ssnid or "")
                if len(ssnid) == 10:
                    nss = "0" + ssnid
                elif len(ssnid) == 11:
                    nss = ssnid
                else:
                    nss = ssnid.zfill(11)
                nss_padded = nss[:11].ljust(11)

                # CP - Código Postal from employee address (5 chars)
                zip_code = str(employee.address_home_id.zip or "")
                cp = zip_code[:5].zfill(5)

                # Birth date components from CURP (positions 0-5: YYMMDD)
                curp = str(employee.address_home_id.curp or "").upper()
                if curp and len(curp) >= 6:
                    # Extract YYMMDD from CURP
                    ano_nacimiento = curp[4:6]  # Last 2 digits of year
                    mes_nacimiento = curp[6:8]  # Month
                    dia_nacimiento = curp[8:10]  # Day
                else:
                    # Default values if CURP is not available
                    dia_nacimiento = "01"
                    mes_nacimiento = "01"
                    ano_nacimiento = "00"

                # State code from CURP (positions 10-11, characters 11-12 in 1-based)
                # Mapping CURP state codes to numeric keys (1-33)
                curp_state_code = curp[11:13] if curp and len(curp) >= 13 else ""
                
                # State code mapping table (CURP code -> numeric key)
                state_code_mapping = {
                    "AS": 1,   # Aguascalientes
                    "BC": 2,   # Baja California
                    "BS": 3,   # Baja California Sur
                    "CC": 4,   # Campeche
                    "CS": 5,   # Chiapas
                    "CH": 6,   # Chihuahua
                    "DF": 7,   # Ciudad de México
                    "CL": 8,   # Coahuila
                    "CM": 9,   # Colima
                    "DG": 10,  # Durango
                    "GT": 11,  # Guanajuato
                    "GR": 12,  # Guerrero
                    "HG": 13,  # Hidalgo
                    "JC": 14,  # Jalisco
                    "MC": 15,  # Estado de México
                    "MN": 16,  # Michoacán
                    "MS": 17,  # Morelos
                    "NT": 18,  # Nayarit
                    "NL": 19,  # Nuevo León
                    "OC": 20,  # Oaxaca
                    "PL": 21,  # Puebla
                    "QT": 22,  # Querétaro
                    "QR": 23,  # Quintana Roo
                    "SP": 24,  # San Luis Potosí
                    "SL": 25,  # Sinaloa
                    "SR": 26,  # Sonora
                    "TC": 27,  # Tabasco
                    "TS": 28,  # Tamaulipas
                    "TL": 29,  # Tlaxcala
                    "VZ": 30,  # Veracruz
                    "YN": 31,  # Yucatán
                    "ZS": 32,  # Zacatecas
                    "NE": 33,  # Nacido en el Extranjero
                }
                
                # Get numeric state key from CURP code
                state_key = state_code_mapping.get(curp_state_code, 0)
                
                # State code (2 chars) - use the numeric key padded to 2 digits
                state_code_padded = str(state_key).zfill(2) if state_key > 0 else "00"

                # State name (25 chars, right aligned) - mapping numeric key to state name
                # Using ANSI/CP1252 compatible format in UPPERCASE
                state_name_mapping = {
                    1: "AGUASCALIENTES",
                    2: "BAJA CALIFORNIA",
                    3: "BAJA CALIFORNIA SUR",
                    4: "CAMPECHE",
                    5: "CHIAPAS",
                    6: "CHIHUAHUA",
                    7: "CIUDAD DE MEXICO",
                    8: "COAHUILA",
                    9: "COLIMA",
                    10: "DURANGO",
                    11: "GUANAJUATO",
                    12: "GUERRERO",
                    13: "HIDALGO",
                    14: "JALISCO",
                    15: "ESTADO DE MEXICO",
                    16: "MICHOACAN",
                    17: "MORELOS",
                    18: "NAYARIT",
                    19: "NUEVO LEON",
                    20: "OAXACA",
                    21: "PUEBLA",
                    22: "QUERETARO",
                    23: "QUINTANA ROO",
                    24: "SAN LUIS POTOSI",
                    25: "SINALOA",
                    26: "SONORA",
                    27: "TABASCO",
                    28: "TAMAULIPAS",
                    29: "TLAXCALA",
                    30: "VERACRUZ",
                    31: "YUCATAN",
                    32: "ZACATECAS",
                    33: "NACIDO EN EL EXTRANJERO",
                }
                
                state_name = state_name_mapping.get(state_key, "")
                state_name_padded = state_name[-25:].rjust(25)

                # UMF - Unidad Médica Familiar (3 chars)
                umf = str(employee.umf or "001")
                umf_padded = umf[:3].zfill(3)

                # Clave/Ocupación - employee_number (12 chars)
                employee_number = str(employee.employee_number or "")
                clave_ocupacion = employee_number[:12].ljust(12)

                # Sexo (1 char) from CURP position 11 (index 10)
                # CURP position 11: H = hombre, M = mujer
                # Mapping: H -> M, M -> F
                if curp and len(curp) >= 11:
                    curp_gender = curp[10]  # Position 11 in 1-based indexing
                    if curp_gender == "H":
                        sexo = "M"  # Hombre -> M
                    elif curp_gender == "M":
                        sexo = "F"  # Mujer -> F
                    else:
                        sexo = " "
                else:
                    sexo = " "

                # Tipo jornada (1 char) - from contract.journal_type
                journal_type = contract.journal_type or "00"
                if journal_type == "00":
                    tipo_jornada = "0"
                elif journal_type in ["01", "02", "03", "04", "05"]:
                    tipo_jornada = journal_type[-1]
                elif journal_type == "06":
                    tipo_jornada = "6"
                else:
                    tipo_jornada = "0"

                # Espacio (1 char)
                espacio = " "

                # Build the record (80 characters total)
                # Position mapping:
                # 1-11: Registro Patronal (11 chars)
                # 12-22: NSS (11 chars)
                # 23-27: CP (5 chars)
                # 28-29: Día nacimiento (2 chars)
                # 30-31: Mes nacimiento (2 chars)
                # 32-35: Año nacimiento (4 chars)
                # 36-60: Nombre estado (25 chars, right aligned)
                # 61-62: Clave estado (2 chars)
                # 63-65: UMF (3 chars)
                # 66-77: Clave/Ocupación (12 chars)
                # 78: Sexo (1 char)
                # 79: Tipo jornada (1 char)
                # 80: Espacio (1 char)

                record = (
                    registro_patronal +                    # 1-11: Registro Patronal
                    nss_padded +                           # 12-22: NSS
                    cp +                                   # 23-27: CP
                    dia_nacimiento +                       # 28-29: Día nacimiento
                    mes_nacimiento +                       # 30-31: Mes nacimiento
                    ano_nacimiento +                       # 32-35: Año nacimiento
                    state_name_padded +                    # 36-60: Nombre estado
                    state_code_padded +                    # 61-62: Clave estado
                    umf_padded +                           # 63-65: UMF
                    clave_ocupacion +                      # 66-77: Clave/Ocupación
                    sexo +                                 # 78: Sexo
                    tipo_jornada +                         # 79: Tipo jornada
                    espacio                                # 80: Espacio
                )

                lines += record + "\n"

            # Encode to CP1252 and then Base64
            encoded_bytes = lines.encode("cp1252")
            base64_encoded = base64.b64encode(encoded_bytes)
            
            self.afilacion_file = base64_encoded
            
            return {
                "type": "ir.actions.act_url",
                "url": "/web/content/hr.payroll.sua.reports/%s/afilacion_file?download=true&filename=afiliacion.txt" % (self.id),
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
