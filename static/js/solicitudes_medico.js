// solicitudes_medico.js

document.addEventListener('DOMContentLoaded', function () {
  // Autocompletar datos del profesional al cargar la página
  completarDatosProfesional();

  // Evento para autocompletar datos del paciente al salir del campo de RUT
  document.getElementById('rut').addEventListener('blur', completarDatosPaciente);

  // Botón para agregar una nueva fila de medicamentos
  document.getElementById('addRowBtn').addEventListener('click', agregarFilaMedicamento);

  // Botón para ver la receta antes de enviarla
  document.getElementById('verRecetaBtn').addEventListener('click', verReceta);

  // Botón para confirmar y enviar la solicitud
  document.getElementById('confirmarEnvio').addEventListener('click', enviarSolicitudReceta);

  // Botón para imprimir la receta desde el modal
  document.getElementById('imprimirReceta').addEventListener('click', function () {
      window.print();
  });
});

// Función para autocompletar datos del profesional desde la sesión
function completarDatosProfesional() {
  const runProfesional = '{{ session["run_profesional"] }}';
  const nombreProfesional = '{{ session["nombre_profesional"] }}';
  const apellidoProfesional = '{{ session["apellido_profesional"] }}';
  const tipoProfesional = '{{ session["tipo_profesional"] }}';

  document.getElementById('run_profesional').value = runProfesional;
  document.getElementById('nombre_profesional').value = nombreProfesional;
  document.getElementById('apellido_profesional').value = apellidoProfesional;
  document.getElementById('tipo_profesional').value = tipoProfesional;
}

// Función para autocompletar datos del paciente mediante una llamada AJAX
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




// Función para calcular la edad a partir de la fecha de nacimiento
function calcularEdad(fechaNacimiento) {
  const hoy = new Date();
  const nacimiento = new Date(fechaNacimiento);
  let edad = hoy.getFullYear() - nacimiento.getFullYear();
  const mes = hoy.getMonth() - nacimiento.getMonth();
  if (mes < 0 || (mes === 0 && hoy.getDate() < nacimiento.getDate())) {
      edad--;
  }
  document.getElementById('edad').value = edad;
}

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
// Función para agregar una nueva fila de medicamentos
function agregarFilaMedicamento() {
  const tabla = document.getElementById('medicamentos-list');
  const fila = tabla.insertRow();
  const numeroFila = tabla.rows.length;

  fila.innerHTML = `
      <td>${numeroFila}</td>
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
          </select>
      </td>
      <td><input type="text" name="observacion[]" placeholder="Observaciones..." class="form-control"></td>
  `;
  const nuevoInput = fila.querySelector('input[name="medicamento[]"]');
  applyAutocomplete(nuevoInput);
}

// Función para mostrar la receta en el modal antes de enviarla
function verReceta() {
  const modal = new bootstrap.Modal(document.getElementById('recetaModal'));
  const detalles = document.getElementById('detallesReceta');
  detalles.innerHTML = generarHTMLReceta();
  modal.show();
}

// Generar HTML de la receta para mostrar en el modal
function generarHTMLReceta() {
  const rut = document.getElementById('rut').value;
  const nombre = document.getElementById('nombre').value;
  const fechaNacimiento = document.getElementById('fecha_nacimiento').value;
  const sexo = document.getElementById('sexo').value;
  const edad = document.getElementById('edad').value;
  const servicio = document.getElementById('servicio').value;
  const cama = document.getElementById('cama').value;

  let html = `
    <div class="container">
      <h5 class="fw-bold text-center mb-3">Receta Médica - Uso Interno</h5>

      <h6 class="fw-bold">Datos del Paciente</h6>
      <p><strong>RUT:</strong> ${rut}</p>
      <p><strong>Nombre:</strong> ${nombre}</p>
      <p><strong>Fecha de Nacimiento:</strong> ${fechaNacimiento}</p>
      <p><strong>Sexo:</strong> ${sexo}</p>
      <p><strong>Edad:</strong> ${edad} años</p>
      <p><strong>Servicio:</strong> ${servicio}</p>
      <p><strong>Cama:</strong> ${cama}</p>

      <hr>
      <h6 class="fw-bold mt-3">Prescripción</h6>
      <table class="table table-bordered table-sm">
        <thead class="table-light">
          <tr>
            <th>#</th>
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

  const medicamentos = document.querySelectorAll('#medicamentos-list tr');
  medicamentos.forEach((fila, index) => {
      const medicamento = fila.querySelector('input[name="medicamento[]"]').value;
      const dosis = fila.querySelector('input[name="dosis_por_toma[]"]').value;
      html += `<li><strong>${index + 1}.</strong> ${medicamento} - ${dosis}</li>`;
  });

  html += '</ul>';
  return html;
}

// Función para enviar la solicitud de receta
function enviarSolicitudReceta() {
  const form = document.getElementById('recetaForm');
  const formData = new FormData(form);

  fetch('/crear_solicitud_receta', {
      method: 'POST',
      body: formData
  })
      .then(response => response.json())
      .then(data => {
          if (data.ok) {
              alert('Solicitud enviada con éxito.');
              window.location.reload();
          } else {
              alert(`Error: ${data.error}`);
          }
      })
      .catch(error => console.error('Error al enviar la solicitud:', error));
}