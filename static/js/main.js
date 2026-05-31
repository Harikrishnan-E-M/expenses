document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => new bootstrap.Tooltip(el));

  document.querySelectorAll('[data-confirm-text]').forEach((button) => {
    button.addEventListener('click', (event) => {
      const message = button.getAttribute('data-confirm-text') || 'Are you sure?';
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  window.setTimeout(() => {
    document.querySelectorAll('.alert').forEach((alert) => {
      const instance = bootstrap.Alert.getOrCreateInstance(alert);
      instance.close();
    });
  }, 3500);
});
