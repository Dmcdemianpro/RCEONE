$(document).ready(function(){
    console.log("Documento listo. Registrando clicks en .aprobar-btn y .cancelar-btn");
    let solicitud_id = null;
    let accion = null;
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    // Si usas Flask-WTF con meta de CSRF:
    const csrfToken = $('meta[name="csrf-token"]').attr('content');
    
    // Botones Aprobar/Cancelar
    $('.aprobar-btn').click(function(){
        solicitud_id = $(this).data('id');
        accion = 'aprobar';
        $('#accionModal').text('aprobar');
        $('#confirmarAccionBtn').removeClass('btn-danger').addClass('btn-success').text('Aprobar');
        confirmModal.show();
    });
    $('.cancelar-btn').click(function(){
        console.log("Dentro de .aprobar-btn click, data-id=", $(this).data('id'))
        solicitud_id = $(this).data('id');
        accion = 'cancelar';
        $('#accionModal').text('cancelar');
        $('#confirmarAccionBtn').removeClass('btn-success').addClass('btn-danger').text('Cancelar');
        confirmModal.show();
    });
    
    // Confirmar acción
    $('#confirmarAccionBtn').click(function(){
        if(!solicitud_id || !accion){
            alert('No se ha seleccionado una solicitud.');
            return;
        }
        
        let url = accion === 'aprobar' ? '/aprobar_solicitud' : '/cancelar_solicitud';
        
        $.ajax({
            url: url,
            type: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            data: { solicitud_id: solicitud_id },
            success: function(response){
                if(response.ok){
                    alert(`Solicitud ${accion}ada correctamente.`);
                    location.reload();
                } else {
                    alert(`Error: ${response.error}`);
                }
            },
            error: function(xhr, status, error){
                console.error(error);
                alert('Ocurrió un error al procesar la solicitud.');
            }
        });
        
        confirmModal.hide();
    });
    
    // Botón Refrescar
    document.getElementById('refreshBtn').addEventListener('click', function(){
       location.reload();
    });
});