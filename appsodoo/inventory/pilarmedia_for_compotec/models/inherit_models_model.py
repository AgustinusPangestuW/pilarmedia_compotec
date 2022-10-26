from odoo import models, _
from odoo.exceptions import ValidationError

class inheritModel(models.Model):
    def validate_required_field(self):
        """
        validation field with required=True must be filled
        """
        fields = self.fields_get()
        required_fields = [field for field in fields if 'required' in fields[field] and fields[field]['required']]
        for fieldname in required_fields:
            if not fieldname in self or fieldname in self and not self[fieldname]:
                raise ValidationError(_("value for field %s(%s) is required." % (
                    fields[fieldname].get('string'),
                    fieldname
                )))

    def write(self, vals):
        vals = super().write(vals)
        self.validate_required_field()
        return vals