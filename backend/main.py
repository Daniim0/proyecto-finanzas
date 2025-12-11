from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from models import Base, Usuario, Transaccion
from datetime import datetime
import hashlib
import os

app = FastAPI()

# Configurar base de datos
engine = create_engine('sqlite:///../finanzas.db')
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crear directorios si no existen
os.makedirs("static/css", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Configurar archivos estáticos y templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Función para obtener sesión de BD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Funciones de ayuda
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Ruta principal - Redirige al login o dashboard según sesión
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Login - Página
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Login - Procesar formulario
@app.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db)
):
    try:
        hashed_password = hash_password(password)
        usuario = db.query(Usuario).filter(
            Usuario.email == email, 
            Usuario.password == hashed_password
        ).first()
        
        if usuario:
            response = RedirectResponse(url="/dashboard", status_code=303)
            response.set_cookie(key="user_id", value=str(usuario.id))
            return response
        
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Email o contraseña incorrectos"
        })
    except Exception as e:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Error: {str(e)}"
        })

# Registro - Página
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Registro - Procesar formulario
@app.post("/register")
async def register(
    request: Request,
    nombre: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db)
):
    try:
        # Verificar si el usuario ya existe
        existing_user = db.query(Usuario).filter(Usuario.email == email).first()
        if existing_user:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "El email ya está registrado"
            })
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            nombre=nombre,
            email=email,
            password=hash_password(password)
        )
        
        db.add(nuevo_usuario)
        db.commit()
        
        # Iniciar sesión automáticamente
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="user_id", value=str(nuevo_usuario.id))
        return response
        
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": f"Error al registrar: {str(e)}"
        })

# Dashboard - Página principal
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db=Depends(get_db)
):
    try:
        user_id = request.cookies.get("user_id")
        
        if not user_id:
            return RedirectResponse(url="/login")
        
        # Obtener usuario
        usuario = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not usuario:
            response = RedirectResponse(url="/login")
            response.delete_cookie("user_id")
            return response
        
        # Obtener transacciones del usuario
        transacciones = db.query(Transaccion).filter(
            Transaccion.usuario_id == int(user_id)
        ).order_by(desc(Transaccion.fecha)).all()
        
        # Calcular totales
        total_ingresos = 0.0
        total_gastos = 0.0
        
        for trans in transacciones:
            if trans.tipo == 'ingreso':
                total_ingresos += trans.monto
            elif trans.tipo == 'gasto':
                total_gastos += trans.monto
        
        balance = total_ingresos - total_gastos
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "usuario": usuario,
            "transacciones": transacciones,
            "total_ingresos": total_ingresos,
            "total_gastos": total_gastos,
            "balance": balance,
            "num_transacciones": len(transacciones)
        })
        
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })

# Crear nueva transacción
@app.post("/transaccion")
async def crear_transaccion(
    request: Request,
    tipo: str = Form(...),
    monto: float = Form(...),
    categoria: str = Form(...),
    descripcion: str = Form(None),
    db=Depends(get_db)
):
    try:
        user_id = request.cookies.get("user_id")
        
        if not user_id:
            return RedirectResponse(url="/login")
        
        # Validar monto positivo
        if monto <= 0:
            return RedirectResponse(url="/dashboard", status_code=303)
        
        nueva_transaccion = Transaccion(
            tipo=tipo,
            monto=monto,
            categoria=categoria,
            descripcion=descripcion,
            usuario_id=int(user_id),
            fecha=datetime.now()
        )
        
        db.add(nueva_transaccion)
        db.commit()
        
        return RedirectResponse(url="/dashboard", status_code=303)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url="/dashboard", status_code=303)

# Eliminar transacción
@app.post("/transaccion/{trans_id}/eliminar")
async def eliminar_transaccion(
    request: Request,
    trans_id: int,
    db=Depends(get_db)
):
    try:
        user_id = request.cookies.get("user_id")
        
        if not user_id:
            return RedirectResponse(url="/login")
        
        # Buscar la transacción (solo del usuario actual)
        transaccion = db.query(Transaccion).filter(
            Transaccion.id == trans_id,
            Transaccion.usuario_id == int(user_id)
        ).first()
        
        if transaccion:
            db.delete(transaccion)
            db.commit()
        
        return RedirectResponse(url="/dashboard", status_code=303)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url="/dashboard", status_code=303)

# Editar transacción
@app.post("/transaccion/{trans_id}/editar")
async def editar_transaccion(
    request: Request,
    trans_id: int,
    tipo: str = Form(...),
    monto: float = Form(...),
    categoria: str = Form(...),
    descripcion: str = Form(None),
    db=Depends(get_db)
):
    try:
        user_id = request.cookies.get("user_id")
        
        if not user_id:
            return RedirectResponse(url="/login")
        
        # Validar monto positivo
        if monto <= 0:
            return RedirectResponse(url="/dashboard", status_code=303)
        
        # Buscar la transacción (solo del usuario actual)
        transaccion = db.query(Transaccion).filter(
            Transaccion.id == trans_id,
            Transaccion.usuario_id == int(user_id)
        ).first()
        
        if transaccion:
            # Actualizar los campos
            transaccion.tipo = tipo
            transaccion.monto = monto
            transaccion.categoria = categoria
            transaccion.descripcion = descripcion
            transaccion.fecha = datetime.now()  # Actualizar fecha de modificación
            
            db.commit()
        
        return RedirectResponse(url="/dashboard", status_code=303)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url="/dashboard", status_code=303)

# Logout
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("user_id")
    return response

# Página de error
@app.get("/error")
async def error_page(request: Request, error: str = ""):
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error": error
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)