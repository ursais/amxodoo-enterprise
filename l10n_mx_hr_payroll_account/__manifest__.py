{
    "name": "Payroll Account for Mexico",
    "icon": "/l10n_mx/static/description/icon.png",
    "website": "https://github.com/amxodoo/enterprise",
    "summary": "Mexican Localization for Payroll Accounts",
    "author": "Open Source Integrators, " "Odoo Mexican Association (AMOdoo)",
    "category": "Human Resources/Payroll",
    "version": "16.0.1.0.0",
    "depends": [
        # Odoo
        "hr_payroll_account",
        # Other
        "l10n_mx_hr_payroll",
    ],
    "data": [
        "data/account.account.csv",
        "data/hr.salary.rule.csv",
    ],
    "demo": [],
    "installable": True,
    "application": False,
    "post_init_hook": "_set_account_in_rules",
    "license": "LGPL-3",
    "assets": {},
}
