from app import app, config
from peewee import (
    Model,
    PostgresqlDatabase,
    TextField,
    SmallIntegerField,
    CharField,
    ForeignKeyField,
    SQL,
)
from marshmallow import Schema, fields, validate, validates_schema, ValidationError
from datetime import date

db = PostgresqlDatabase(
    config.get("Database", "name"),
    user=config.get("Database", "user"),
    password=config.get("Database", "password"),
)


class BirthdaysSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(max=255))
    day = fields.Integer(required=True)
    month = fields.Integer(required=True)
    year = fields.Integer()
    note = fields.String()

    @validates_schema
    def valid_date(self, data, **kwargs):
        try:
            year = data["year"]
        except KeyError:
            year = date.today().year - 1
        if (data["month"] == 2) and (data["day"] == 29):
            raise ValidationError("29th of February is forbidden. Choose 28.02 or 1.03")
        try:
            birthday = date(year, data["month"], data["day"])
        except ValueError:
            raise ValidationError("Non-existent date")
        if date.today() < birthday:
            raise ValidationError("Future dates are forbidden")
        #    print(exception.__class__.__name__)


birthdays_schema = BirthdaysSchema()


class BaseModel(Model):
    class Meta:
        database = db


class Users(BaseModel):
    telegram_id = CharField(primary_key=True, unique=True)  # col_creator
    language = CharField(
        default="en"
    )  # col_language. #one lang - en, automatic translation later.


class Birthdays(BaseModel):
    name = CharField()  # col_name
    day = SmallIntegerField()  # col_day
    month = SmallIntegerField()  # col_month
    year = SmallIntegerField(null=True)  # col_year
    note = TextField(null=True)  # col_note
    creator = ForeignKeyField(Users, backref="birthdays")  # col_creator

    class Meta:
        constraints = [SQL("UNIQUE (name, creator_id)")]


with app.app_context():
    # db.drop_tables([Birthdays, Users])
    db.create_tables([Birthdays, Users])

# Users.create(telegram_id=651472384)

# Birthdays.create(
#     name="Nazar",
#     day=13,
#     month=11,
#     year=2003,
#     creator=Users.get(Users.telegram_id == 651472384),
# )

# User.create(telegram_id=4321, col_language="en")

# Birthdays.create(
#     name="Nazar",
#     day=15,
#     month=3,
#     year=2002,
#     creator=User.get(User.telegram_id == 4321),
# )
