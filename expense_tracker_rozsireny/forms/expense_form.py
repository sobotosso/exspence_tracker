from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class ExpenseForm(FlaskForm):
    name = StringField('Název', validators=[DataRequired()])
    amount = DecimalField('Částka (Kč)', validators=[DataRequired(), NumberRange(min=0)])
    category = SelectField('Kategorie', coerce=int)
    date = DateField('Datum', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Uložit')