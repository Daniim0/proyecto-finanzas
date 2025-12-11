from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

class Transaccion(Base):
    __tablename__ = 'transacciones'
    
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String, nullable=False)  # 'ingreso' o 'gasto'
    monto = Column(Float, nullable=False)
    categoria = Column(String, nullable=False)
    descripcion = Column(String)
    fecha = Column(DateTime, default=datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))