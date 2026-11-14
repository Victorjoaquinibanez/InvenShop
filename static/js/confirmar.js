/*
 * Confirmación con modal de Bootstrap (reemplaza al confirm() del navegador).
 *
 * Uso en un <form>:
 *   data-confirmar="Texto de la pregunta"
 *   data-confirmar-titulo="Título"            (opcional)
 *   data-confirmar-boton="Sí, vaciar"         (opcional)
 *   data-confirmar-campo="estado"             (opcional: solo pide confirmación
 *   data-confirmar-valor="Cancelado"           cuando ese campo tiene ese valor)
 */
document.addEventListener('DOMContentLoaded', () => {
  const elemento = document.getElementById('modalConfirmar');
  if (!elemento) return;

  const modal = new bootstrap.Modal(elemento);
  const titulo = elemento.querySelector('.modal-title');
  const mensaje = elemento.querySelector('[data-mensaje]');
  const botonAceptar = elemento.querySelector('[data-aceptar]');
  let formPendiente = null;

  document.querySelectorAll('form[data-confirmar]').forEach((form) => {
    form.addEventListener('submit', (evento) => {
      if (form.dataset.confirmado === 'si') return;  // ya confirmado: dejar enviar

      const campo = form.dataset.confirmarCampo;
      if (campo && form.elements[campo]?.value !== form.dataset.confirmarValor) return;

      evento.preventDefault();
      formPendiente = form;
      titulo.textContent = form.dataset.confirmarTitulo || '¿Estás seguro?';
      mensaje.textContent = form.dataset.confirmar;
      botonAceptar.textContent = form.dataset.confirmarBoton || 'Aceptar';
      modal.show();
    });
  });

  botonAceptar.addEventListener('click', () => {
    if (!formPendiente) return;
    formPendiente.dataset.confirmado = 'si';
    modal.hide();
    formPendiente.requestSubmit();
  });

  elemento.addEventListener('hidden.bs.modal', () => {
    if (formPendiente) delete formPendiente.dataset.confirmado;
    formPendiente = null;
  });
});
