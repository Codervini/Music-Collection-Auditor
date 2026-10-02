from schema.base import DB_ENGINE, Base
from schema.lookup import *
from schema.models import *

# print(Base.metadata.tables)
Base.metadata.drop_all(DB_ENGINE)
Base.metadata.create_all(DB_ENGINE)
