from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/agregar_paciente')
def agregar_paciente():
    return render_template('agregar_paciente.html')

@app.route('/ver_pacientes')
def ver_pacientes():
    return render_template('ver_pacientes.html')

@app.route('/eliminar_pacientes')
def eliminar_pacientes():
    return render_template('eliminar_pacientes.html')

if __name__ == '__main__':
    app.run(debug=True)
