from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, DecimalField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, Optional
from .database.models.user import User  # Assuming User model is here


class RequestResetForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Request Password Reset")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError(
                "There is no account with that email. You must register first."
            )


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=4, message="Password must be at least 4 characters long."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Reset Password")


class FundForm(FlaskForm):
    # Remove the amount field, it will be calculated
    fund_type = SelectField('Fund Type', validators=[DataRequired()])
    
    sales = DecimalField('Sales', validators=[
        DataRequired(message='Sales amount is required'),
        NumberRange(min=0, message='Sales must be positive or zero')
    ], default=0.0)
    
    payout = DecimalField('Payout', validators=[
        DataRequired(message='Payout amount is required'),
        NumberRange(min=0, message='Payout must be positive or zero')
    ], default=0.0)
    
    remarks = TextAreaField('Remarks (Optional)', validators=[Optional()])
    
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        from .routes.admin_routes import FUND_TYPES
        super(FundForm, self).__init__(*args, **kwargs)
        self.fund_type.choices = [(k, v) for k, v in FUND_TYPES.items()]
