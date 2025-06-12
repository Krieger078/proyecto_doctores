#                   Citas Médicas                       #
#       Encargado del proyecto (Scrum Master):          #
#              Oscar Delgadillo Valdés                  #
#                   Integrantes:                        #
#             - Oscar Delgadillo Valdés                 #
#             - Sandra Camila Flores Vargas             #
#             - Daniela Rocio Patiño Martinez           #
#             - Aaron Reyna Gomez                       #
#             - David Arturo Moreno Razo                #
#                                                       #
#                   Descripción:                        #
#   Este archivo controla todas las funciones de la     #
#   aplicación web, incluyendo agregar, editar,         #
#   eliminar y mostrar pacientes, así como gestionar    #
#   citas, estudios médicos, inicio de sesión y         #
#   registro de usuarios.                               #

# Importaciones estándar de Python
import os
from datetime import datetime

# Importaciones de terceros
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify, make_response, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource, reqparse
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from flasgger import Swagger
import ssl
import requests

# Inicialización de la aplicación Flask
app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:P1ng0r1nd05@localhost/proyecto_doctores'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'citasmedicascodad@gmail.com'
app.config['MAIL_PASSWORD'] = 'mufq zzhp ytsa bogh'
app.config['MAIL_DEFAULT_SENDER'] = 'citasmedicascodad@gmail.com'
app.config['MAIL_DEBUG'] = True

# Configuración de SSL
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Configuración de archivos
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB límite

# Inicialización de extensiones
db = SQLAlchemy(app)
mail = Mail(app)
mail.init_app(app)

# Configuración de la API RESTful
api_blueprint = Blueprint('api', __name__, url_prefix='/api')
api = Api(api_blueprint)

# Registra el blueprint de la API
app.register_blueprint(api_blueprint)

# Crear carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ------------------- Utilidades ------------------- #

def allowed_file(filename):
    """Valida si el archivo tiene una extensión permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def login_required(f):
    """Decorador para requerir autenticación en rutas protegidas."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicia sesión para acceder a esta página', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ------------------- Modelos ------------------- #

class User(db.Model):
    """Modelo para doctores."""
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

class Patient(db.Model):
    """Modelo para pacientes."""
    __tablename__ = 'pacientes'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctores.id'), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    telefono = db.Column(db.String(20), nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=True)
    genero = db.Column(db.String(20), nullable=True)
    peso = db.Column(db.Float, nullable=True)
    altura = db.Column(db.Float, nullable=True)
    condiciones_medicas = db.Column(db.Text, nullable=True)
    notas = db.Column(db.Text, nullable=True)
    especialidad = db.Column(db.String(100), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<Patient {self.nombre}>'

class Appointment(db.Model):
    """Modelo para citas médicas."""
    __tablename__ = 'citas'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctores.id'), nullable=False)
    fecha_cita = db.Column(db.DateTime, nullable=False)
    motivo = db.Column(db.Text, nullable=True)
    estado = db.Column(db.String(50), default='Programada', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref='appointments')
    doctor = db.relationship('User', backref='appointments')

    def __repr__(self):
        return f'<Appointment {self.id} for {self.patient.nombre}>'

class MedicalStudy(db.Model):
    """Modelo para estudios médicos."""
    __tablename__ = 'estudios_medicos'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctores.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    patient = db.relationship('Patient', backref='studies')
    doctor = db.relationship('User', backref='uploaded_studies')

# -------------------- API RESTful -------------------- #

# Parser para los datos de las citas
appointment_parser = reqparse.RequestParser()
appointment_parser.add_argument('patient_id', type=int, required=True, help='ID del paciente es requerido')
appointment_parser.add_argument('fecha_cita', type=str, required=True, help='Fecha y hora de la cita es requerida')
appointment_parser.add_argument('motivo', type=str, required=False)
appointment_parser.add_argument('estado', type=str, required=False)

class AppointmentListResource(Resource):
    @login_required
    def get(self):
        """
        Obtener todas las citas del doctor logueado
        ---
        tags:
          - Citas
        security:
          - sessionAuth: []
        responses:
          200:
            description: Lista de citas del doctor logueado
            schema:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  patient_id:
                    type: integer
                  patient_name:
                    type: string
                  fecha_cita:
                    type: string
                    format: date-time
                  motivo:
                    type: string
                  estado:
                    type: string
                  created_at:
                    type: string
                    format: date-time
        """
        appointments = Appointment.query.filter_by(doctor_id=session['user_id']).all()
        return jsonify([{
            'id': app.id,
            'patient_id': app.patient_id,
            'patient_name': app.patient.nombre,
            'fecha_cita': app.fecha_cita.isoformat(),
            'motivo': app.motivo,
            'estado': app.estado,
            'created_at': app.created_at.isoformat()
        } for app in appointments])

    @login_required
    def post(self):
        """
        Crear una nueva cita
        ---
        tags:
          - Citas
        security:
          - sessionAuth: []
        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              required:
                - patient_id
                - fecha_cita
              properties:
                patient_id:
                  type: integer
                fecha_cita:
                  type: string
                  format: date-time
                motivo:
                  type: string
                estado:
                  type: string
        responses:
          201:
            description: Cita creada exitosamente
            schema:
              type: object
              properties:
                message:
                  type: string
                appointment:
                  type: object
                  properties:
                    id:
                      type: integer
                    patient_id:
                      type: integer
                    fecha_cita:
                      type: string
                      format: date-time
                    motivo:
                      type: string
                    estado:
                      type: string
          400:
            description: Datos inválidos
        """
        
        """Crear una nueva cita"""
        args = appointment_parser.parse_args()
        
        try:
            fecha_cita_obj = datetime.strptime(args['fecha_cita'], '%Y-%m-%dT%H:%M')
            if fecha_cita_obj < datetime.now():
                return {'message': 'La fecha de la cita no puede ser en el pasado'}, 400
        except ValueError:
            return {'message': 'Formato de fecha y hora incorrecto. Usa YYYY-MM-DDTHH:MM'}, 400

        # Verificar que el paciente pertenece al doctor
        patient = Patient.query.filter_by(id=args['patient_id'], doctor_id=session['user_id']).first()
        if not patient:
            return {'message': 'Paciente no encontrado o no pertenece a este doctor'}, 404

        new_appointment = Appointment(
            patient_id=args['patient_id'],
            doctor_id=session['user_id'],
            fecha_cita=fecha_cita_obj,
            motivo=args.get('motivo'),
            estado=args.get('estado', 'Programada')
        )

        try:
            db.session.add(new_appointment)
            db.session.commit()
            
            # Enviar correo de confirmación
            try:
                msg = Message(
                    subject='Confirmación de Cita Médica',
                    recipients=[patient.email],
                    html=f"""
                    <h1>Confirmación de Cita Médica</h1>
                    <p>Estimado(a) {patient.nombre},</p>
                    <p>Se ha programado una cita médica con el Dr(a). {new_appointment.doctor.nombrecompleto}.</p>
                    <p><strong>Detalles de la cita:</strong></p>
                    <ul>
                        <li>Fecha y hora: {fecha_cita_obj.strftime('%d/%m/%Y %H:%M')}</li>
                        <li>Motivo: {args.get('motivo', 'No especificado')}</li>
                        <li>Especialidad: {new_appointment.doctor.especialidad}</li>
                    </ul>
                    <p>Por favor, asegúrese de llegar a tiempo.</p>
                    """
                )
                mail.send(msg)
            except Exception as email_error:
                print(f"Error al enviar el correo: {email_error}")

            return {
                'message': 'Cita creada exitosamente',
                'appointment': {
                    'id': new_appointment.id,
                    'patient_id': new_appointment.patient_id,
                    'fecha_cita': new_appointment.fecha_cita.isoformat(),
                    'motivo': new_appointment.motivo,
                    'estado': new_appointment.estado
                }
            }, 201
        except Exception as e:
            db.session.rollback()
            return {'message': 'Error al crear la cita', 'error': str(e)}, 500

class AppointmentResource(Resource):
    @login_required
    def get(self, appointment_id):
        """
        Obtener una cita específica
        ---
        tags:
          - Citas
        security:
          - sessionAuth: []
        parameters:
          - in: path
            name: appointment_id
            type: integer
            required: true
            description: ID de la cita
        responses:
          200:
            description: Cita encontrada
            schema:
              type: object
              properties:
                id:
                  type: integer
                patient_id:
                  type: integer
                patient_name:
                  type: string
                fecha_cita:
                  type: string
                  format: date-time
                motivo:
                  type: string
                estado:
                  type: string
                created_at:
                  type: string
                  format: date-time
          404:
            description: Cita no encontrada
        """
        appointment = Appointment.query.filter_by(id=appointment_id, doctor_id=session['user_id']).first()
        if not appointment:
            return {'message': 'Cita no encontrada'}, 404

        return jsonify({
            'id': appointment.id,
            'patient_id': appointment.patient_id,
            'patient_name': appointment.patient.nombre,
            'fecha_cita': appointment.fecha_cita.isoformat(),
            'motivo': appointment.motivo,
            'estado': appointment.estado,
            'created_at': appointment.created_at.isoformat()
        })

    @login_required
    def put(self, appointment_id):
        """
        Actualizar una cita existente
        ---
        tags:
          - Citas
        security:
          - sessionAuth: []
        parameters:
          - in: path
            name: appointment_id
            type: integer
            required: true
            description: ID de la cita
          - in: body
            name: body
            required: true
            schema:
              type: object
              required:
                - patient_id
                - fecha_cita
              properties:
                patient_id:
                  type: integer
                fecha_cita:
                  type: string
                  format: date-time
                motivo:
                  type: string
                estado:
                  type: string
        responses:
          200:
            description: Cita actualizada exitosamente
            schema:
              type: object
              properties:
                message:
                  type: string
                appointment:
                  type: object
                  properties:
                    id:
                      type: integer
                    patient_id:
                      type: integer
                    fecha_cita:
                      type: string
                      format: date-time
                    motivo:
                      type: string
                    estado:
                      type: string
          400:
            description: Datos inválidos o cita no editable
          404:
            description: Cita no encontrada
        """

        """Actualizar una cita existente"""
        appointment = Appointment.query.filter_by(id=appointment_id, doctor_id=session['user_id']).first()
        if not appointment:
            return {'message': 'Cita no encontrada'}, 404
            
        if appointment.estado != 'Programada':
            return {'message': 'Solo se pueden editar citas programadas'}, 400
            
        args = appointment_parser.parse_args()
        
        try:
            fecha_cita_obj = datetime.strptime(args['fecha_cita'], '%Y-%m-%dT%H:%M')
            if fecha_cita_obj < datetime.now():
                return {'message': 'La fecha de la cita no puede ser en el pasado'}, 400
        except ValueError:
            return {'message': 'Formato de fecha y hora incorrecto. Usa YYYY-MM-DDTHH:MM'}, 400

        # Verificar que el paciente pertenece al doctor
        patient = Patient.query.filter_by(id=args['patient_id'], doctor_id=session['user_id']).first()
        if not patient:
            return {'message': 'Paciente no encontrado o no pertenece a este doctor'}, 404

        appointment.patient_id = args['patient_id']
        appointment.fecha_cita = fecha_cita_obj
        appointment.motivo = args.get('motivo', appointment.motivo)
        
        try:
            db.session.commit()
            
            # Enviar correo de notificación
            try:
                msg = Message(
                    subject='Actualización de Cita Médica',
                    recipients=[patient.email],
                    html=f"""
                    <h1>Actualización de Cita Médica</h1>
                    <p>Estimado(a) {patient.nombre},</p>
                    <p>Su cita con el Dr(a). {appointment.doctor.nombrecompleto} ha sido actualizada.</p>
                    <p><strong>Nuevos detalles:</strong></p>
                    <ul>
                        <li>Fecha y hora: {fecha_cita_obj.strftime('%d/%m/%Y %H:%M')}</li>
                        <li>Motivo: {args.get('motivo', 'No especificado')}</li>
                    </ul>
                    """
                )
                mail.send(msg)
            except Exception as email_error:
                print(f"Error al enviar el correo: {email_error}")
            
            return {
                'message': 'Cita actualizada exitosamente',
                'appointment': {
                    'id': appointment.id,
                    'patient_id': appointment.patient_id,
                    'fecha_cita': appointment.fecha_cita.isoformat(),
                    'motivo': appointment.motivo,
                    'estado': appointment.estado
                }
            }
        except Exception as e:
            db.session.rollback()
            return {'message': 'Error al actualizar la cita', 'error': str(e)}, 500

    @login_required
    def delete(self, appointment_id):
        """
        Cancelar una cita
        ---
        tags:
          - Citas
        security:
          - sessionAuth: []
        parameters:
          - in: path
            name: appointment_id
            type: integer
            required: true
            description: ID de la cita
        responses:
          200:
            description: Cita cancelada exitosamente
            schema:
              type: object
              properties:
                message:
                  type: string
        """
        
        """Cancelar una cita"""
        appointment = Appointment.query.filter_by(id=appointment_id, doctor_id=session['user_id']).first()
        if not appointment:
            return {'message': 'Cita no encontrada'}, 404
            
        if appointment.estado == 'Cancelada':
            return {'message': 'La cita ya está cancelada'}, 400
            
        try:
            appointment.estado = 'Cancelada'
            db.session.commit()
            
            # Enviar correo de notificación
            try:
                msg = Message(
                    subject='Cancelación de Cita Médica',
                    recipients=[appointment.patient.email],
                    html=f"""
                    <h1>Cancelación de Cita Médica</h1>
                    <p>Estimado(a) {appointment.patient.nombre},</p>
                    <p>Su cita con el Dr(a). {appointment.doctor.nombrecompleto} ha sido cancelada.</p>
                    <p><strong>Detalles de la cita cancelada:</strong></p>
                    <ul>
                        <li>Fecha y hora: {appointment.fecha_cita.strftime('%d/%m/%Y %H:%M')}</li>
                        <li>Motivo: {appointment.motivo or 'No especificado'}</li>
                    </ul>
                    """
                )
                mail.send(msg)
            except Exception as email_error:
                print(f"Error al enviar el correo: {email_error}")
            
            return {'message': 'Cita cancelada exitosamente'}
        except Exception as e:
            db.session.rollback()
            return {'message': 'Error al cancelar la cita', 'error': str(e)}, 500

# Añadir los recursos a la API
api.add_resource(AppointmentListResource, '/citas')
api.add_resource(AppointmentResource, '/citas/<int:appointment_id>')

# ------------------- Configuración de Swagger ------------------- #

# Configuración básica de Swagger (colocar después de crear la app Flask)
app.config['SWAGGER'] = {
    'title': 'API de Citas Médicas',
    'uiversion': 3,
    'description': 'Documentación de la API para el sistema de gestión de citas médicas',
    'termsOfService': '',
    'specs_route': '/apidocs/'
}

# Configuración extendida del template Swagger
app.config['SWAGGER']['template'] = {
    'swagger': '2.0',
    'info': {
        'title': 'API de Citas Médicas',
        'description': 'API para el sistema de gestión de citas médicas',
        'version': '1.0',
        'contact': {
            'email': 'citasmedicascodad@gmail.com'
        }
    },
    'components': {
        'schemas': {
            'Appointment': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'patient_id': {'type': 'integer'},
                    'patient_name': {'type': 'string'},
                    'fecha_cita': {'type': 'string', 'format': 'date-time'},
                    'motivo': {'type': 'string'},
                    'estado': {'type': 'string'},
                    'created_at': {'type': 'string', 'format': 'date-time'}
                }
            },
            'NewAppointment': {
                'type': 'object',
                'required': ['patient_id', 'fecha_cita'],
                'properties': {
                    'patient_id': {'type': 'integer'},
                    'fecha_cita': {'type': 'string', 'format': 'date-time'},
                    'motivo': {'type': 'string'},
                    'estado': {'type': 'string'}
                }
            },
            'AppointmentResponse': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'appointment': {
                        '$ref': '#/components/schemas/Appointment'
                    }
                }
            }
        },
        'securitySchemes': {
            'sessionAuth': {
                'type': 'apiKey',
                'in': 'cookie',
                'name': 'session'
            }
        }
    },
    'security': [{'sessionAuth': []}]
}

# ------------------- Rutas de autenticación ------------------- #

@app.route('/')
def index():
    """Página principal."""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Iniciar sesión."""
    if request.method == 'POST':
        email = request.form['email']
        password_input = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password_input):
            flash('Inicio de sesión exitoso', 'success')
            session['user_id'] = user.id
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Correo o contraseña incorrectos', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registrar un nuevo doctor."""
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

        # Verificar si el correo ya está registrado
        if User.query.filter_by(email=email).first():
            flash('Este correo electrónico ya está registrado.', 'error')
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
            
            # Enviar correo electrónico de confirmación
            try:
                msg = Message(
                    subject='Registro Exitoso - Sistema de Citas Médicas',
                    recipients=[email],
                    html=f"""
                    <h1>¡Bienvenido(a) al Sistema de Citas Médicas!</h1>
                    <p>Estimado(a) Dr(a). {nombrecompleto},</p>
                    <p>Su registro en nuestro sistema ha sido exitoso.</p>
                    <p><strong>Datos de su cuenta:</strong></p>
                    <ul>
                        <li>Nombre: {nombrecompleto}</li>
                        <li>Especialidad: {especialidad}</li>
                        <li>Correo electrónico: {email}</li>
                    </ul>
                    <p>Ahora puede iniciar sesión en nuestro sistema y comenzar a gestionar sus pacientes.</p>
                    <p>Si no realizó este registro, por favor ignore este mensaje.</p>
                    <br>
                    <p>Atentamente,</p>
                    <p>El equipo de Sistema de Citas Médicas</p>
                    """
                )
                mail.send(msg)
                flash('Registro exitoso. Se ha enviado un correo de confirmación.', 'success')
            except Exception as email_error:
                print(f"Error al enviar el correo: {email_error}")
                flash('Registro exitoso, pero no se pudo enviar el correo de confirmación.', 'warning')
            
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Error al registrar el usuario. Inténtalo de nuevo.', 'error')
            print(e)
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Cerrar sesión."""
    session.pop('user_id', None)
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('index'))

# ------------------- Rutas del dashboard ------------------- #

@app.route('/dashboard')
@login_required
def dashboard():
    """Panel principal del doctor."""
    return render_template('dashboard.html')

# ------------------- Rutas de pacientes ------------------- #

@app.route('/agregar_paciente', methods=['GET', 'POST'])
@login_required
def agregar_paciente():
    """Agregar un nuevo paciente."""
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        telefono = request.form['telefono']
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        genero = request.form['genero']
        peso = request.form.get('peso')
        altura = request.form.get('altura')
        condiciones_medicas = request.form.get('condiciones_medicas')
        notas = request.form.get('notas')

        # Validar formato de teléfono (10 dígitos)
        if not telefono.isdigit() or len(telefono) != 10:
            flash('El número de teléfono debe contener 10 dígitos.', 'error')
            return redirect(url_for('agregar_paciente'))

        # Verificar si el correo ya está registrado
        if Patient.query.filter_by(email=email).first():
            flash('Este correo electrónico ya está registrado.', 'error')
            return redirect(url_for('agregar_paciente'))

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

        # Obtenemos la información del doctor que está logueado
        doctor = User.query.get(session['user_id'])

        # Creamos el paciente
        new_patient = Patient(
            doctor_id=session['user_id'],
            nombre=nombre,
            email=email,
            telefono=telefono,
            fecha_nacimiento=fecha_obj,
            genero=genero,
            peso=peso,
            altura=altura,
            condiciones_medicas=condiciones_medicas,
            notas=notas,
            especialidad=doctor.especialidad
        )

        try:
            db.session.add(new_patient)
            db.session.commit()

            # Enviar correo de confirmación al paciente
            try:
                msg = Message(
                    subject='Bienvenido al Sistema de Citas Médicas',
                    recipients=[email],
                    html=f"""
                    <h1>¡Bienvenido(a) al Sistema de Citas Médicas!</h1>
                    <p>Estimado(a) {nombre},</p>
                    <p>Ha sido registrado exitosamente en nuestro sistema por el Dr(a). {doctor.nombrecompleto}.</p>
                    <p><strong>Datos registrados:</strong></p>
                    <ul>
                        <li>Nombre: {nombre}</li>
                        <li>Correo electrónico: {email}</li>
                        <li>Teléfono: {telefono}</li>
                    </ul>
                    <p>Recibirá notificaciones sobre sus citas médicas en este correo.</p>
                    <p>Si no reconoce este registro, por favor contáctenos.</p>
                    <br>
                    <p>Atentamente,</p>
                    <p>El equipo de Sistema de Citas Médicas</p>
                    """
                )
                mail.send(msg)
                flash('Paciente agregado exitosamente. Se ha enviado un correo de confirmación.', 'success')
            except Exception as email_error:
                print(f"Error al enviar el correo: {email_error}")
                flash('Paciente agregado, pero no se pudo enviar el correo de confirmación.', 'warning')

            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Error al agregar paciente', 'error')
            print(e)
    return render_template('agregar_paciente.html')

@app.route('/ver_pacientes')
@login_required
def ver_pacientes():
    """Mostrar lista de pacientes activos."""
    patients = Patient.query.filter_by(doctor_id=session['user_id'], activo=True).all()
    return render_template('ver_pacientes.html', patients=patients)

@app.route('/detalle_paciente/<int:patient_id>')
@login_required
def detalle_paciente(patient_id):
    """Mostrar detalles de un paciente."""
    patient = Patient.query.filter_by(id=patient_id, doctor_id=session['user_id']).first()
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('ver_pacientes'))
    return render_template('detalle_paciente.html', patient=patient)

@app.route('/editar_paciente/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def editar_paciente(patient_id):
    """Editar información de un paciente."""
    patient = Patient.query.filter_by(id=patient_id, doctor_id=session['user_id']).first()
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('ver_pacientes'))
    
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            email = request.form['email']
            telefono = request.form['telefono']

            # Validar formato de teléfono
            if not telefono.isdigit() or len(telefono) != 10:
                flash('El número de teléfono debe contener 10 dígitos.', 'error')
                return redirect(url_for('editar_paciente', patient_id=patient_id))

            # Verificar si el correo ya está registrado por otro paciente
            existing_patient = Patient.query.filter_by(email=email).first()
            if existing_patient and existing_patient.id != patient.id:
                flash('Este correo electrónico ya está registrado.', 'error')
                return redirect(url_for('editar_paciente', patient_id=patient_id))

            patient.nombre = nombre
            patient.email = email
            patient.telefono = telefono
            
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

@app.route('/eliminar_paciente')
@login_required
def lista_eliminar_pacientes():
    """Mostrar lista de pacientes activos para eliminar."""
    patients = Patient.query.filter_by(doctor_id=session['user_id'], activo=True).all()
    return render_template('eliminar_paciente.html', patients=patients)

@app.route('/eliminar_paciente/<int:patient_id>', methods=['POST'])
@login_required
def eliminar_paciente(patient_id):
    """Marcar un paciente como inactivo."""
    patient = Patient.query.filter_by(id=patient_id, doctor_id=session['user_id'], activo=True).first()
    if not patient:
        flash('Paciente no encontrado o ya inactivo', 'error')
        return redirect(url_for('lista_eliminar_pacientes'))
    try:
        patient.activo = False
        db.session.commit()
        flash('Paciente marcado como inactivo', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al actualizar el estado del paciente', 'error')
        print(e)
    return redirect(url_for('lista_eliminar_pacientes'))

# ------------------- Rutas de citas ------------------- #

@app.route('/agregar_cita/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def agregar_cita(patient_id):
    """Mostrar formulario para programar una nueva cita (frontend)"""
    patient = Patient.query.filter_by(id=patient_id, doctor_id=session['user_id']).first()
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('ver_pacientes'))
    
    if request.method == 'POST':
        # Enviar datos a la API
        response = requests.post(
            f'http://{request.host}/api/citas',
            json={
                'patient_id': patient_id,
                'fecha_cita': request.form['fecha_cita'],
                'motivo': request.form.get('motivo')
            },
            cookies=request.cookies
        )
        
        data = response.json()
        if response.status_code == 201:
            flash('Cita programada exitosamente', 'success')
            return redirect(url_for('ver_citas', patient_id=patient_id))
        else:
            flash(data.get('message', 'Error al programar la cita'), 'error')
    
    return render_template('agregar_cita.html', patient=patient)

@app.route('/ver_citas/<int:patient_id>')
@login_required
def ver_citas(patient_id):
    """Mostrar lista de citas de un paciente (frontend)"""
    patient = Patient.query.filter_by(id=patient_id, doctor_id=session['user_id']).first()
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('ver_pacientes'))
    
    # Obtener citas desde la API
    response = requests.get(
        f'http://{request.host}/api/citas',
        cookies=request.cookies
    )
    
    if response.status_code == 200:
        all_appointments = response.json()
        # Filtrar las citas del paciente específico
        patient_appointments = [app for app in all_appointments if app['patient_id'] == patient_id]
    else:
        patient_appointments = []
        flash('Error al obtener las citas', 'error')
    
    return render_template('ver_citas.html', patient=patient, appointments=patient_appointments)

@app.route('/editar_cita/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def editar_cita(appointment_id):
    """Mostrar formulario para editar una cita (frontend)"""
    # Obtener la cita desde la API
    response = requests.get(
        f'http://{request.host}/api/citas/{appointment_id}',
        cookies=request.cookies
    )
    
    if response.status_code != 200:
        flash('Cita no encontrada', 'error')
        return redirect(url_for('ver_pacientes'))
    
    appointment_data = response.json()
    patient = Patient.query.get(appointment_data['patient_id'])
    
    if request.method == 'POST':
        # Actualizar la cita mediante la API
        response = requests.put(
            f'http://{request.host}/api/citas/{appointment_id}',
            json={
                'patient_id': appointment_data['patient_id'],
                'fecha_cita': request.form['fecha_cita'],
                'motivo': request.form.get('motivo')
            },
            cookies=request.cookies
        )
        
        data = response.json()
        if response.status_code == 200:
            flash('Cita actualizada exitosamente', 'success')
            return redirect(url_for('ver_citas', patient_id=appointment_data['patient_id']))
        else:
            flash(data.get('message', 'Error al actualizar la cita'), 'error')
    
    # Convertir los datos de la API a un objeto Appointment para el template
    class MockAppointment:
        def __init__(self, data):
            self.id = data['id']
            self.patient_id = data['patient_id']
            self.fecha_cita = datetime.strptime(data['fecha_cita'], '%Y-%m-%dT%H:%M:%S')
            self.motivo = data['motivo']
            self.estado = data['estado']
            self.patient = patient
            self.doctor = User.query.get(session['user_id'])
    
    appointment = MockAppointment(appointment_data)
    return render_template('editar_cita.html', appointment=appointment, patient=patient)

@app.route('/cancelar_cita/<int:appointment_id>', methods=['POST'])
@login_required
def cancelar_cita(appointment_id):
    """Cancelar una cita (frontend)"""
    # Obtener la cita primero para redirigir al paciente correcto
    response = requests.get(
        f'http://{request.host}/api/citas/{appointment_id}',
        cookies=request.cookies
    )
    
    if response.status_code != 200:
        flash('Cita no encontrada', 'error')
        return redirect(url_for('ver_pacientes'))
    
    appointment_data = response.json()
    
    # Cancelar la cita mediante la API
    response = requests.delete(
        f'http://{request.host}/api/citas/{appointment_id}',
        cookies=request.cookies
    )
    
    if response.status_code == 200:
        flash('Cita cancelada exitosamente', 'success')
    else:
        flash(response.json().get('message', 'Error al cancelar la cita'), 'error')
    
    return redirect(url_for('ver_citas', patient_id=appointment_data['patient_id']))

# ------------------- Rutas de estudios médicos ------------------- #

@app.route('/subir_estudio/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def subir_estudio(patient_id):
    """Subir un estudio médico para un paciente."""
    patient = Patient.query.filter_by(id=patient_id, doctor_id=session['user_id']).first()
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('ver_pacientes'))
    
    if request.method == 'POST':
        # Verificar si se envió el archivo
        if 'file' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        description = request.form.get('description', '')
        
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            try:
                file.save(filepath)
                file_size = os.path.getsize(filepath)
                
                new_study = MedicalStudy(
                    patient_id=patient_id,
                    doctor_id=session['user_id'],
                    filename=unique_filename,
                    original_filename=filename,
                    file_type=filename.rsplit('.', 1)[1].lower(),
                    file_size=file_size,
                    description=description
                )
                
                db.session.add(new_study)
                db.session.commit()
                flash('Estudio subido correctamente', 'success')
                return redirect(url_for('ver_estudios', patient_id=patient_id))
            
            except Exception as e:
                db.session.rollback()
                flash('Error al subir el archivo', 'error')
                print(e)
        
        else:
            flash('Tipo de archivo no permitido', 'error')
    
    return render_template('subir_estudio.html', patient=patient)

@app.route('/ver_estudios/<int:patient_id>')
@login_required
def ver_estudios(patient_id):
    """Mostrar lista de estudios médicos de un paciente."""
    patient = Patient.query.filter_by(id=patient_id, doctor_id=session['user_id']).first()
    if not patient:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('ver_pacientes'))
    
    studies = MedicalStudy.query.filter_by(patient_id=patient_id).order_by(MedicalStudy.upload_date.desc()).all()
    return render_template('ver_estudios.html', patient=patient, studies=studies)

@app.route('/descargar_estudio/<int:study_id>')
@login_required
def descargar_estudio(study_id):
    """Descargar un estudio médico."""
    study = MedicalStudy.query.filter_by(id=study_id, doctor_id=session['user_id']).first()
    if not study:
        flash('Estudio no encontrado', 'error')
        return redirect(url_for('ver_pacientes'))
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], study.filename)
    return send_file(filepath, as_attachment=True, download_name=study.original_filename)

@app.route('/eliminar_estudio/<int:study_id>', methods=['POST'])
@login_required
def eliminar_estudio(study_id):
    """Eliminar un estudio médico."""
    study = MedicalStudy.query.filter_by(id=study_id, doctor_id=session['user_id']).first()
    if not study:
        flash('Estudio no encontrado', 'error')
        return redirect(url_for('ver_pacientes'))
    
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], study.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        
        db.session.delete(study)
        db.session.commit()
        flash('Estudio eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar el estudio', 'error')
        print(e)
    
    return redirect(url_for('ver_estudios', patient_id=study.patient_id))

# ------------------- Ejecución de la aplicación ------------------- #

# Inicialización de Swagger
swagger = Swagger(app)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)