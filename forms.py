# forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class LoginForm(FlaskForm):
    """
    Formulario para inicio de sesión
    """
    username = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=32)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Ingresar')


class NuevoUsuarioForm(FlaskForm):
    """
    Formulario para que el admin cree nuevos usuarios
    """
    username = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=32)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    role = SelectField(
        'Rol',
        choices=[
            ('usuario', 'Usuario'),
            ('medico', 'Médico'),
            ('admin', 'Administrador')
        ],
        validators=[DataRequired()]
    )
    
    # Campos adicionales para el rol 'medico'
    # (puedes mostrarlos/ocultarlos con JS en la plantilla nuevo_usuario.html)
    run_profesional = StringField('RUN Profesional', validators=[Optional(), Length(max=12)])
    nombre_profesional = StringField('Nombre Profesional', validators=[Optional(), Length(max=50)])
    primer_apellido_profesional = StringField('Primer Apellido Profesional', validators=[Optional(), Length(max=50)])
    segundo_apellido_profesional = StringField('Segundo Apellido Profesional', validators=[Optional(), Length(max=50)])
    tipo_profesional = StringField('Tipo Profesional', validators=[Optional(), Length(max=50)])
    
    submit = SubmitField('Crear Usuario')


class SolicitudForm(FlaskForm):
    """
    Formulario para:
    - Que el médico cree solicitudes de recetas
    - O el usuario envíe recetas directamente a Mirth
      (dependiendo de cómo quieras reutilizarlo).
    """
    # Campos básicos
    rut_paciente = StringField('RUT Paciente', validators=[DataRequired(), Length(max=12)])
    nombre_paciente = StringField('Nombres y Apellidos', validators=[DataRequired(), Length(max=100)])
    diagnostico = StringField('Diagnóstico', validators=[DataRequired(), Length(max=255)])

    # Campos adicionales (opcional)
    run_profesional = StringField('RUN Profesional', validators=[Optional(), Length(max=12)])
    nombre_profesional = StringField('Nombre Profesional', validators=[Optional(), Length(max=50)])
    tipo_profesional = StringField('Tipo Profesional', validators=[Optional(), Length(max=50)])
    
    # Botón de enviar
    submit = SubmitField('Enviar Solicitud')
# forms.py

from flask_wtf import FlaskForm
from wtforms import (
    StringField, 
    DateField,
    SelectField,
    IntegerField,
    HiddenField,
    SubmitField
)
from wtforms.validators import DataRequired, Optional, Length

class RecetaForm(FlaskForm):
    """
    Formulario para gestionar la creación/edición de una Receta.
    Incluye campos típicos que has usado en tu template y tu app.py.
    Ajusta los validadores y choices según tu lógica.
    """

    # Token CSRF para protección
    csrf_token = HiddenField()

    # Datos del Paciente
    rut = StringField('RUT Paciente', validators=[DataRequired(), Length(max=12)])
    nombre = StringField('Nombres y Apellidos', validators=[DataRequired(), Length(max=100)])
    fecha_nacimiento = DateField('Fecha de Nacimiento', validators=[Optional()])
    sexo = SelectField(
        'Sexo',
        choices=[('', 'Seleccionar'), ('M', 'Masculino'), ('F', 'Femenino')],
        validators=[Optional()]
    )
    edad = IntegerField('Edad', validators=[Optional()])

    # Servicio y Cama
    servicio = SelectField(
        'Servicio',
        choices=[
            ('', 'Seleccione un servicio'),
            ('1', 'MEDICINA 1'),
            ('2', 'MEDICINA 2'),
            ('3', 'MEDICINA 3'),
            ('4', 'GERIATRIA'),
            ('5', 'GINECOLOGIA - ARO'),
            ('6', 'PUERPERIO'),
            ('7', 'CIRUGIA 1'),
            ('8', 'CIRUGIA 2'),
            ('9', 'MQI5TO PISO'),
            ('10', 'PEDIATRIA AGUDO'),
            ('11', 'PEDIATRIA BASICO'),
            ('12', 'MQI2DO PISO'),
            ('13', 'HOSPITALIZACION DOMICILIARIA'),
            ('14', 'NEONATOLOGIA'),
            ('15', 'SAIP'),
            ('16', 'UPC INFANTIL'),
            ('17', 'UPC ADULTO'),
            ('18', 'MQI3ER PISO'),
            ('19', 'HOSPITAL DE DIA - SALUD MENTAL'),
            ('20', 'URGENCIA PEDIATRICA'),
            ('21', 'URGENCIA MATERNIDAD'),
            ('22', 'CMA'),
            ('23', 'URGENCIA ADULTO'),
        ],
        validators=[Optional()]
    )
    cama = StringField('Cama', validators=[Optional(), Length(max=20)])

    # Datos del Profesional
    run_profesional = StringField('RUN Profesional', validators=[Optional(), Length(max=12)])
    nombre_profesional = StringField('Nombre Profesional', validators=[Optional(), Length(max=50)])
    primer_apellido_profesional = StringField('Primer Apellido Profesional', validators=[Optional(), Length(max=80)])
    segundo_apellido_profesional = StringField('Segundo Apellido Profesional', validators=[Optional(), Length(max=80)])
    tipo_profesional = StringField('Tipo Profesional', validators=[Optional(), Length(max=50)])

    # Diagnóstico
    diagnostico = StringField('Diagnóstico', validators=[DataRequired(), Length(max=255)])

    # Botón de envío (opcional, si quieres usarlo en tu plantilla)
    submit = SubmitField('Enviar Receta')
