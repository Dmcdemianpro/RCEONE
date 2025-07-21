function completarDatosPaciente() {
  let rut = $("#rut").val();
  if (!rut) return;

  $.get("/obtener_datos_paciente", { rut: rut }, function (data) {
    if (data && !data.error) {
      $("#nombre").val(`${data.nombres} ${data.apell1} ${data.apell2}`);
      $("#fecha_nacimiento").val(data.fechaNacimiento);

      // Convertimos género a M o F de forma segura
      const genero = data.genero?.toString().trim().toUpperCase();
      if (genero === "M" || genero === "1") {
        $("#sexo").val("M");
      } else if (genero === "F" || genero === "2") {
        $("#sexo").val("F");
      } else {
        $("#sexo").val(""); // valor indefinido si no coincide
      }

      calcularEdad(data.fechaNacimiento);
    } else {
      alert("No se encontraron datos del paciente.");
    }
  });
}

// Función para calcular la edad
function calcularEdad(fechaNacimiento) {
  const hoy = new Date();
  const nacimiento = new Date(fechaNacimiento);
  let edad = hoy.getFullYear() - nacimiento.getFullYear();
  const mes = hoy.getMonth() - nacimiento.getMonth();
  if (mes < 0 || (mes === 0 && hoy.getDate() < nacimiento.getDate())) {
      edad--;
  }
  $("#edad").val(edad);
}

$(document).ready(function() {
  // Inicializar el autocompletado para el campo de diagnóstico
$("#diagnostico").autocomplete({
    source: function(request, response) {
        $.ajax({
            url: "/buscar_diagnostico",
            data: { q: request.term },
            success: function(data) {
                response($.map(data, function(item) {
                    return {
                        label: item.id + ' - ' + item.descripcion,
                        value: item.id + ' - ' + item.descripcion
                    };
                }));
            }
        });
    },
    minLength: 1,
    select: function(event, ui) {
        $("#diagnostico").val(ui.item.value);
    }
});

// Función para completar datos del paciente al salir del campo RUT
$("#rut").on('blur', function() {
    completarDatosPaciente();
});


// Función para aplicar autocompletado a los campos de medicamentos
function applyAutocomplete(selector) {
    $(selector).autocomplete({
        source: function(request, response) {
            var matches = [];
            var substrRegex = new RegExp(request.term, 'i');
            $.each(window.farmacos || [], function(i, farmaco) {
                if (substrRegex.test(farmaco.name)) {
                    matches.push({
                        label: farmaco.name,
                        value: farmaco.name,
                        codigo: farmaco.id
                    });
                }
            });
            response(matches);
        },
        minLength: 1,
        select: function(event, ui) {
            var medicamentoInput = $(this);
            var codigoInput = medicamentoInput.siblings('input[name="codigo_medicamento[]"]');
            codigoInput.val(ui.item.codigo);
        }
    });

    // Evento blur para manejar entrada manual
    $(selector).on('blur', function() {
        var medicamentoInput = $(this);
        var valorIngresado = medicamentoInput.val();
        var codigoInput = medicamentoInput.siblings('input[name="codigo_medicamento[]"]');

        var medicamento = window.farmacos.find(function(farmaco) {
            return farmaco.name.toLowerCase() === valorIngresado.toLowerCase();
        });

        if (medicamento) {
            codigoInput.val(medicamento.id);
        } else {
            codigoInput.val('');
            alert('Por favor, seleccione un medicamento válido de la lista de sugerencias.');
        }
    });
}

// Aplicar autocompletado a los campos existentes
applyAutocomplete('input[name="medicamento[]"]');

// Aplicar autocompletado a nuevas filas
$('#addRowBtn').click(function() {
    var rowCount = $('#medicamentos-list tr').length + 1;
    var newRow = `
        <tr>
            <td>${rowCount}</td>
            <td>
                <input type="text" name="medicamento[]" placeholder="Buscar medicamento..." class="form-control">
                <input type="hidden" name="codigo_medicamento[]" value="">
            </td>
            <td><input type="number" name="dosis_por_toma[]" placeholder="Dosis por toma..." class="form-control" step="any"></td>
            <td>
                <select name="unidad_dosis[]" class="form-control">
                    <option value="">Seleccione</option>
                    <option value="mg">MG</option>
                    <option value="g">G</option>
                    <option value="ml">ML</option>
                    <option value="comprimidos">Comprimidos</option>
                    <!-- Más opciones -->
                </select>
            </td>
            <td>
                <select name="posologia[]" class="form-control">
                    <option value="">Seleccione</option>
                    <option value="1 cada 8 horas">1 cada 8 horas</option>
                    <option value="1 cada 12 horas">1 cada 12 horas</option>
                    <option value="1 cada 6 horas">1 cada 6 horas</option>
                    <option value="2 veces al día">2 veces al día</option>
                    <option value="1 cada 24 horas">1 cada 24 horas</option>
                    <option value="1 cada 4 horas">1 cada 4 horas</option>
                    <option value="1 antes de cada comida">1 antes de cada comida</option>
                    <option value="1 después de cada comida">1 después de cada comida</option>
                    <option value="1 al acostarse">1 al acostarse</option>
                    <option value="Aplicar 1 vez al día">Aplicar 1 vez al día</option>
                    <!-- Más opciones -->
                </select>
            </td>
            <td><input type="number" name="duracion[]" placeholder="Duración..." class="form-control"></td>
            <td>
                <select name="via[]" class="form-control">
                    <option value="">Seleccione</option>
                    <option value="ORAL">ORAL</option>
                    <option value="SUBLINGUAL">SUBLINGUAL</option>
                    <option value="TOPICA">TÓPICA</option>
                    <option value="SUBCUTANEA">SUBCUTÁNEA</option>
                    <option value="INTRAMUSCULAR">INTRAMUSCULAR</option>
                    <option value="INTRATECAL, EPIDURAL">INTRATECAL, EPIDURAL</option>
                    <option value="INTRARTICULAR">INTRARTICULAR</option>
                    <option value="INTRAVENOSA">INTRAVENOSA</option>
                    <!-- Más opciones -->
                </select>
            </td>
            <td><input type="text" name="observacion[]" placeholder="Observaciones..." class="form-control"></td>
        </tr>
    `;
    $('#medicamentos-list').append(newRow);
    applyAutocomplete('input[name="medicamento[]"]'); // Reaplicar autocompletar a la nueva fila
});

// Manejar el envío del formulario con validación
$('form').on('submit', function(event) {
    event.preventDefault(); // Evitar que el formulario haga un envío tradicional

    // Verificar que todos los códigos de medicamentos están presentes
    var codigosValidos = true;
    $('input[name="codigo_medicamento[]"]').each(function() {
        if ($(this).val() === '') {
            codigosValidos = false;
            alert('Por favor, seleccione un medicamento válido de la lista de sugerencias.');
            return false; // Salir del each
        }
    });

    if (!codigosValidos) {
        return; // Detener el envío del formulario
    }

    // Aquí, en lugar de enviar la receta directamente, mostramos el modal con los detalles
    mostrarDetallesReceta();
});

// Función para mostrar el modal con los detalles de la receta
function mostrarDetallesReceta() {
    // Recopilar los datos del formulario
    var formData = $('form').serializeArray();

    // Procesar los datos para estructurarlos y mostrarlos
    var recetaData = procesarDatosReceta(formData);

    // Generar el HTML para mostrar los detalles
    var detallesHTML = generarHTMLReceta(recetaData);

    // Insertar el HTML en el modal
    $('#detallesReceta').html(detallesHTML);

    // Mostrar el modal
    var recetaModal = new bootstrap.Modal(document.getElementById('recetaModal'));
    recetaModal.show();

    // Manejar el clic en el botón Confirmar Envío
    $('#confirmarEnvio').off('click').on('click', function() {
        enviarRecetaAlServidor();
        recetaModal.hide();
    });

    // Manejar el clic en el botón Imprimir
    $('#imprimirReceta').off('click').on('click', function() {
        imprimirReceta(recetaData); // Pasar recetaData aquí
    });
}


// Función para procesar los datos del formulario y estructurarlos
function procesarDatosReceta(formData) {
    var recetaData = {};
    var prescripciones = [];
    var fields = {};

    // Inicializar arrays vacíos para campos de prescripciones
    var prescripcionFields = [
        'medicamento[]', 'codigo_medicamento[]', 'dosis_por_toma[]', 'unidad_dosis[]',
        'posologia[]', 'duracion[]', 'via[]', 'observacion[]'
    ];

    prescripcionFields.forEach(function(field) {
        fields[field] = [];
    });

    // Procesar los datos del formulario
    formData.forEach(function(item) {
        if (item.name.endsWith('[]')) {
            fields[item.name].push(item.value);
        } else {
            recetaData[item.name] = item.value;
        }
    });

    // Reorganizar las prescripciones en un array de objetos
    var numPrescripciones = fields['medicamento[]'].length;
    for (var i = 0; i < numPrescripciones; i++) {
        var prescripcion = {
            medicamento: fields['medicamento[]'][i],
            codigo_medicamento: fields['codigo_medicamento[]'][i],
            dosis_por_toma: fields['dosis_por_toma[]'][i],
            unidad_dosis: fields['unidad_dosis[]'][i],
            posologia: fields['posologia[]'][i],
            duracion: fields['duracion[]'][i],
            via: fields['via[]'][i],
            observacion: fields['observacion[]'][i]
        };
        prescripciones.push(prescripcion);
    }

    recetaData.prescripciones = prescripciones;
    return recetaData;
}

// Función para generar el HTML de los detalles de la receta
function generarHTMLReceta(recetaData) {
    let html = `
        <div class="card mb-3">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">Información del Paciente</h5>
            </div>
            <div class="card-body">
                <p><strong>RUT:</strong> ${recetaData.rut}</p>
                <p><strong>Nombre:</strong> ${recetaData.nombre}</p>
                <p><strong>Fecha de Nacimiento:</strong> ${recetaData.fecha_nacimiento}</p>
                <p><strong>Sexo:</strong> ${recetaData.sexo}</p>
                <p><strong>Edad:</strong> ${recetaData.edad}</p>
            </div>
        </div>

        <div class="card mb-3">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0">Diagnóstico</h5>
            </div>
            <div class="card-body">
                <p>${recetaData.diagnostico}</p>
            </div>
        </div>

        <div class="card mb-3">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0">Datos del Profesional</h5>
            </div>
            <div class="card-body">
                <p><strong>RUN Profesional:</strong> ${recetaData.run_profesional}</p>
                <p><strong>Nombre:</strong> ${recetaData.nombre_profesional} ${recetaData.apellido_profesional}</p>
                <p><strong>Tipo Profesional:</strong> ${recetaData.tipo_profesional}</p>
            </div>
        </div>

        <h5 class="mt-4">Prescripciones</h5>
        ${generarTablaPrescripciones(recetaData.prescripciones)}
    `;

    return html;
}

function generarTablaPrescripciones(prescripciones) {
    let tabla = `
        <table class="table table-striped table-bordered">
            <thead class="table-dark">
                <tr>
                    <th>N°</th>
                    <th>Medicamento</th>
                    <th>Dosis</th>
                    <th>Unidad</th>
                    <th>Posología</th>
                    <th>Duración</th>
                    <th>Vía</th>
                    <th>Observaciones</th>
                </tr>
            </thead>
            <tbody>
    `;

    prescripciones.forEach((prescripcion, index) => {
        tabla += `
            <tr>
                <td>${index + 1}</td>
                <td>${prescripcion.medicamento}</td>
                <td>${prescripcion.dosis_por_toma}</td>
                <td>${prescripcion.unidad_dosis}</td>
                <td>${prescripcion.posologia}</td>
                <td>${prescripcion.duracion}</td>
                <td>${prescripcion.via}</td>
                <td>${prescripcion.observacion}</td>
            </tr>
        `;
    });

    tabla += `
            </tbody>
        </table>
    `;

    return tabla;
}

// Función para enviar la receta al servidor
function enviarRecetaAlServidor() {
  var formData = $('form').serialize();

  // Extraer el token CSRF desde el formulario
  var csrfToken = $('input[name="csrf_token"]').val();

  $.ajax({
      url: '/enviar',
      type: 'POST',
      data: formData,
      headers: {
          'X-CSRFToken': csrfToken // Enviar el token en la cabecera
      },
      success: function(data) {
          if (data.status === "Prescripción enviada") {
              showConfirmationModal();
          } else {
              alert('Hubo un error al enviar la receta.');
          }
      },
      error: function(error) {
          console.error('Error al enviar la receta:', error);
          alert('Hubo un error al enviar la receta.');
      }
  });



// Función para mostrar el modal de confirmación de envío exitoso
function showConfirmationModal() {
    var confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    confirmModal.show();

    // Cerrar el modal automáticamente después de 10 segundos
    setTimeout(function() {
        confirmModal.hide();
    }, 10000);
}

// Función para imprimir la receta
function imprimirReceta(data) {
    if (!data || !data.nombre) {
        console.error("Los datos de la receta no están definidos correctamente.");
        return;
    }

    const ventanaImpresion = window.open('', '', 'height=800,width=1000');

    ventanaImpresion.document.write(`
        <html>
        <head>
            <title>Receta Médica</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { text-align: center; margin-bottom: 20px; }
                .header img { max-height: 100px; }
                .info { margin-top: 20px; }
                .info h5 { margin-bottom: 10px; }
                .prescription { margin-top: 20px; }
                .table { width: 100%; margin-top: 10px; }
                .signature { margin-top: 40px; text-align: center; }
                .footer { margin-top: 20px; text-align: center; font-size: 0.9em; color: #555; }
                .buttons { text-align: center; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="header">
                <img src="http://www.hospitalelcarmen.cl/hec/wp-content/uploads/2024/01/isologo-pagina-web-275-x-275.png" alt="Logo Hospital El Carmen">
                <h4>Hospital El Carmen</h4>
                <p>Dirección: Camino A Rinconada 1201, Avenida El Olimpo, Maipú, Región Metropolitana.</p>
                <p>Teléfono: (2) 2612 0491</p>
            </div>
            <div class="info">
                <h5>Información del Paciente</h5>
                <p><strong>Nombre:</strong> ${data.nombre}</p>
                <p><strong>RUT:</strong> ${data.rut}</p>
                <p><strong>Edad:</strong> ${data.edad}</p>
                <p><strong>Dirección:</strong> ${data.direccion || 'N/A'}</p>
            </div>
            <div class="prescription">
                <h5>Prescripción</h5>
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Medicamento</th>
                            <th>Dosis</th>
                            <th>Unidad</th>
                            <th>Posología</th>
                            <th>Duración</th>
                            <th>Vía</th>
                            <th>Observaciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.prescripciones.map(p => `
                            <tr>
                                <td>${p.medicamento}</td>
                                <td>${p.dosis_por_toma}</td>
                                <td>${p.unidad_dosis}</td>
                                <td>${p.posologia}</td>
                                <td>${p.duracion}</td>
                                <td>${p.via}</td>
                                <td>${p.observacion}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            <div class="signature">
                <p>______________________</p>
                <p>Firma del Profesional</p>
            </div>
            <div class="footer">
                <p>Esta receta es válida únicamente en el Hospital El Carmen.</p>
            </div>
            <div class="buttons">
                <button onclick="window.print()" class="btn btn-primary">Imprimir</button>
                <button onclick="window.close()" class="btn btn-secondary">Cerrar</button>
            </div>
        </body>
        </html>
    `);

    ventanaImpresion.document.close();
    ventanaImpresion.print();
    ventanaImpresion.close();
}


}});
