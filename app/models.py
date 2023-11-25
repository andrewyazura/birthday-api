from app import app
from peewee import (
    Model,
    PostgresqlDatabase,
    TextField,
    SmallIntegerField,
    CharField,
    ForeignKeyField,
)

db = PostgresqlDatabase("postgres", user="postgres", password="postgres")


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    telegram_id = CharField(unique=True)  # col_creator
    language = CharField(
        default="en"
    )  # col_language. #one lang - en, automatic translation later.


class Birthdays(BaseModel):
    name = CharField()  # col_name
    day = SmallIntegerField()  # col_day
    month = SmallIntegerField()  # col_month
    year = SmallIntegerField(null=True)  # col_year
    note = TextField(null=True)  # col_note
    creator = ForeignKeyField(User, backref="birthdays")  # col_creator


with app.app_context():
    # db.drop_tables([Birthdays, User])
    db.create_tables([Birthdays, User])

# User.create(telegram_id=1234)

# Birthdays.create(
#     name="Oleh",
#     day=12,
#     month=4,
#     year=2003,
#     creator=User.get(User.telegram_id == 1234),
# )

# User.create(telegram_id=4321, col_language="en")

# Birthdays.create(
#     name="Nazar",
#     day=15,
#     month=3,
#     year=2002,
#     creator=User.get(User.telegram_id == 4321),
# )
