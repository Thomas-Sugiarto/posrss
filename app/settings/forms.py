from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional, Length, NumberRange, Email

class TenantInfoForm(FlaskForm):
    name = StringField('Store Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional()])
    submit = SubmitField('Update Store Info')

class PrinterSettingsForm(FlaskForm):
    printer_type = SelectField('Printer Type', choices=[
        ('thermal', 'Thermal Receipt Printer'),
        ('label', 'Label Printer'),
        ('network', 'Network Printer')
    ], default='thermal')
    printer_host = StringField('Printer IP/Host', validators=[Optional()])
    printer_port = IntegerField('Port', default=9100, validators=[Optional(), NumberRange(min=1, max=65535)])
    printer_width = IntegerField('Paper Width', default=42, validators=[NumberRange(min=32, max=80)])
    submit = SubmitField('Save Printer Settings')

class HardwareSettingsForm(FlaskForm):
    barcode_scanner_type = SelectField('Barcode Scanner Type', choices=[
        ('keyboard', 'Keyboard Emulation'),
        ('serial', 'Serial Port'),
        ('bluetooth', 'Bluetooth')
    ], default='keyboard')
    submit = SubmitField('Save Hardware Settings')