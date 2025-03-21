from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Acceso a mi SQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:P1ng0r1nd05@localhost/proyecto_doctores'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Clase Doctor
class User(db.Model):
    __tablename__ = 'doctores'
    id = db.Column(db.Integer, primary_key=True)
    nombrecompleto = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    telefono = db.Column(db.String(20), nullable=False)
    edad = db.Column(db.Integer, nullable=False)
    sexo = db.Column(db.String(20), nullable=False)
    licencia = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(300), nullable=False)
    especialidad = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<User {self.nombrecompleto}>'

# Clase Paciente
class Patient(db.Model):
    __tablename__ = 'pacientes'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctores.id'), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=True)
    genero = db.Column(db.String(20), nullable=True)
    peso = db.Column(db.Float, nullable=True)
    altura = db.Column(db.Float, nullable=True)
    condiciones_medicas = db.Column(db.Text, nullable=True)
    notas = db.Column(db.Text, nullable=True)
    especialidad = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<Patient {self.nombre}>'

# Rutas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password_input = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password_input):
            flash('Inicio de sesión exitoso', 'success')
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            flash('Correo o contraseña incorrectos', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombrecompleto = request.form['nombrecompleto']
        email = request.form['email']
        telefono = request.form['telefono']
        edad = request.form['edad']
        sexo = request.form['sexo']
        licencia_prof = request.form['licencia']
        especialidad = request.form['especialidad']
        password_input = request.form['password']

        # Validación 7 u 8 digitos cedula profesional
        if not licencia_prof.isdigit() or not (7 <= len(licencia_prof) <= 8):
            flash('La cédula profesional debe contener 7 u 8 dígitos.', 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password_input)

        new_user = User(
            nombrecompleto=nombrecompleto,
            email=email,
            telefono=telefono,
            edad=edad,
            sexo=sexo,
            licencia=licencia_prof,
            especialidad=especialidad,
            password=hashed_password
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Error al registrar el usuario. Inténtalo de nuevo.', 'error')
            print(e)
    return render_template('register.html')


# Dashboard del doctor
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# Rutas para la gestión de pacientes

# Agregar paciente
@app.route('/agregar_paciente', methods=['GET', 'POST'])
def agregar_paciente():
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        nombre = request.form['nombre']
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        genero = request.form['genero']
        peso = request.form.get('peso')
        altura = request.form.get('altura')
        condiciones_medicas = request.form.get('condiciones_medicas')
        notas = request.form.get('notas')

        from datetime import datetime
        fecha_obj = None
        if fecha_nacimiento:
            try:
                fecha_obj = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
            except ValueError:
                flash('Formato de fecha incorrecto. Usa AAAA-MM-DD.', 'error')
                return redirect(url_for('agregar_paciente'))

        try:
            peso = float(peso) if peso else None
            altura = float(altura) if altura else None
        except ValueError:
            flash('El peso y la altura deben ser números.', 'error')
            return redirect(url_for('agregar_paciente'))

        new_patient = Patient(
            doctor_id=session['user_id'],
            nombre=nombre,
            fecha_nacimiento=fecha_obj,
            genero=genero,
            peso=peso,
            altura=altura,
            condiciones_medicas=condiciones_medicas,
            notas=notas
        )
        try:
            db.session.add(new_patient)
            db.session.commit()
            flash('Paciente agregado exitosamente', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Error al agregar paciente', 'error')
            print(e)
    return render_template('agregar_paciente.html')

# Ver pacientes
@app.route('/ver_pacientes')
def ver_pacientes():
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    patients = Patient.query.filter_by(doctor_id=session['user_id']).all()
    return render_template('ver_pacientes.html', patients=patients)

# Eliminar pacientes (lista)
@app.route('/eliminar_pacientes')
def eliminar_pacientes():
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    patients = Patient.query.filter_by(doctor_id=session['user_id']).all()
    return render_template('eliminar_pacientes.html', patients=patients)

# Borrar paciente
@app.route('/eliminar_paciente/<int:patient_id>', methods=['POST'])
def eliminar_paciente(patient_id):
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    patient = Patient.query.filter_by(id=patient_id, doctor_id=session['user_id']).first()
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('eliminar_pacientes'))
    try:
        db.session.delete(patient)
        db.session.commit()
        flash('Paciente eliminado', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar paciente', 'error')
    return redirect(url_for('eliminar_pacientes'))

# Cerrar sesión
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
