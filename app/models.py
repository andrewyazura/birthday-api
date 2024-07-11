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
from marshmallow import (
    Schema,
    fields,
    validate,
    validates_schema,
    ValidationError,
)
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
            raise ValidationError("29th of February is not a valid date", field="date")
        try:
            birthday = date(year, data["month"], data["day"])
        except ValueError:
            raise ValidationError("Invalid date", field="date",)
        if date.today() < birthday:
            raise ValidationError("Future dates are forbidden", field="date")


birthdays_schema = BirthdaysSchema()


class BaseModel(Model):
    class Meta:
        database = db


class Users(BaseModel):
    telegram_id = CharField(primary_key=True, unique=True)
    language = CharField(default="en")

    # col_language. #one lang - en, automatic translation later.


class Birthdays(BaseModel):
    name = CharField()
    day = SmallIntegerField()
    month = SmallIntegerField()
    year = SmallIntegerField(null=True)
    note = TextField(null=True)
    creator = ForeignKeyField(Users, backref="birthdays")

    class Meta:
        constraints = [SQL("UNIQUE (name, creator_id)")]


with app.app_context():
    # db.drop_tables([Birthdays, Users])
    db.create_tables([Birthdays, Users])
