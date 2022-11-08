from odoo import models, _
from odoo.exceptions import ValidationError

class inheritModel(models.Model):

    def write(self, vals):
        vals = super().write(vals)
        self.validate_required_field()
        return vals

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

    def validate_change_state(self, vals):
        # change state Draft / None -> Submit -> Cancel 
        # Change state Cancel -> Draft
        state_before = {
            "submit": ['', 'draft'],
            "cancel": ['submit']
        }

        if vals.get('state'):
            new_state = vals.get('state')
            name_cur_state = [s[1] for s in self.list_state if s[0] == self.state] or [""]
            for i in state_before:
                if new_state == i and self.state not in state_before[i]:
                    raise ValidationError(_("Current state must be %s when update state into %s, state document %s is %s" % (
                        "(" + ", ".join(state_before[i]) +")",
                        new_state,
                        self.name,
                        name_cur_state[0]
                    )))

    def validate_change_value_in_restrict_field(self, vals):
        readonly_status = False
        for i in vals:
            if i in self.readonly_fields:
                readonly_status = True

        if self.state in ['submit', 'cancel'] and readonly_status:
            name_cur_state = [s[1] for s in self.list_state if s[0] == self.state] or [""]
            raise ValidationError(_("You Cannot Edit %s as it is in %s State" % (self.name, name_cur_state[0])))
