from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:P1ng0r1nd05@localhost/proyecto_doctores'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo del Doctor
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

# Modelo del Paciente (con campo "activo")
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
    activo = db.Column(db.Boolean, default=True, nullable=False)  # Nuevo campo

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

        # Validación de 7 u 8 dígitos para la cédula profesional
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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    return render_template('dashboard.html')

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

        fecha_obj = None
        if fecha_nacimiento:
            try:
                from datetime import datetime
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

        # Obtenemos la información del doctor que está logueado
        doctor = User.query.get(session['user_id'])

        # Al crear el paciente, asignamos la especialidad del doctor
        new_patient = Patient(
            doctor_id=session['user_id'],
            nombre=nombre,
            fecha_nacimiento=fecha_obj,
            genero=genero,
            peso=peso,
            altura=altura,
            condiciones_medicas=condiciones_medicas,
            notas=notas,
            especialidad=doctor.especialidad  # Asignamos la especialidad del doctor
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


# Mostrar solo pacientes activos
@app.route('/ver_pacientes')
def ver_pacientes():
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    patients = Patient.query.filter_by(doctor_id=session['user_id'], activo=True).all()
    return render_template('ver_pacientes.html', patients=patients)

# Lista de pacientes para eliminar (sólo activos)
@app.route('/eliminar_paciente')
def lista_eliminar_pacientes():
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    patients = Patient.query.filter_by(doctor_id=session['user_id'], activo=True).all()
    return render_template('eliminar_paciente.html', patients=patients)

# "Eliminar" paciente: cambiar estado a inactivo
@app.route('/eliminar_paciente/<int:patient_id>', methods=['POST'])
def eliminar_paciente(patient_id):
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    patient = Patient.query.filter_by(id=patient_id, doctor_id=session['user_id'], activo=True).first()
    if not patient:
        flash('Paciente no encontrado o ya inactivo', 'error')
        return redirect(url_for('lista_eliminar_pacientes'))
    try:
        patient.activo = False  # Marcar paciente como inactivo
        db.session.commit()
        flash('Paciente marcado como inactivo', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al actualizar el estado del paciente', 'error')
        print(e)
    return redirect(url_for('lista_eliminar_pacientes'))

@app.route('/detalle_paciente/<int:patient_id>')
def detalle_paciente(patient_id):
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    patient = Patient.query.filter_by(id=patient_id, doctor_id=session['user_id']).first()
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('ver_pacientes'))
    return render_template('detalle_paciente.html', patient=patient)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('index'))

@app.route('/editar_paciente/<int:patient_id>', methods=['GET', 'POST'])
def editar_paciente(patient_id):
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    
    patient = Patient.query.filter_by(id=patient_id, doctor_id=session['user_id']).first()
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('ver_pacientes'))
    
    if request.method == 'POST':
        try:
            patient.nombre = request.form['nombre']
            
            # Procesar fecha de nacimiento
            fecha_nacimiento = request.form.get('fecha_nacimiento')
            patient.fecha_nacimiento = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date() if fecha_nacimiento else None
            
            patient.genero = request.form.get('genero')
            
            # Procesar peso y altura
            peso = request.form.get('peso')
            patient.peso = float(peso) if peso else None
            
            altura = request.form.get('altura')
            patient.altura = float(altura) if altura else None
            
            patient.condiciones_medicas = request.form.get('condiciones_medicas')
            patient.notas = request.form.get('notas')
            
            db.session.commit()
            flash('Paciente actualizado correctamente', 'success')
            return redirect(url_for('detalle_paciente', patient_id=patient.id))
            
        except ValueError as e:
            db.session.rollback()
            flash('Error en los datos proporcionados: ' + str(e), 'error')
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar el paciente', 'error')
            print(e)
    
    return render_template('editar_paciente.html', patient=patient)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Asegúrate de migrar o actualizar la BD si ya existe
    app.run(debug=True)