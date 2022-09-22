from email.policy import default
from odoo import models, fields, api

class Job(models.Model):
    _name = 'job'

    name = fields.Char(string='Nama Pengerjaan', required=True)
    active = fields.Boolean(string='Active', default="1")
    description = fields.Text(string='Description')