from pathlib import Path

import dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from mca_tools.machine_identifier import machine_id

#----- Constants -----------------------------------------------------------------
env_file = Path("config/.env").resolve()
CONFIG_CONSTANTS = dotenv.dotenv_values(env_file)
connection_string = f"postgresql+psycopg://{CONFIG_CONSTANTS['DB_USERNAME']}:{CONFIG_CONSTANTS['DB_PASSWORD']}@localhost:5432/mcamusicdb"
DB_ENGINE = create_engine(connection_string)
SESSION_MANAGER = sessionmaker(bind=DB_ENGINE)
MACHINE_ID = machine_id()



class Base(DeclarativeBase):
    pass
