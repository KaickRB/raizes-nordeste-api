# configura a conexão com o banco SQLite
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# cria a conexão com o arquivo raizes.db, na pasta do projeto
engine = create_engine("sqlite:///./raizes.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


# abre uma sessão com o banco para a requisição e fecha no final
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
