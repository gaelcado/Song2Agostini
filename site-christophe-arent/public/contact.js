// Formulaire de contact, envoyé vers /api/contact.
(() => {
  const form = document.querySelector(".contact-form");
  if (!form) return;
  const { checks, bind, postJson } = window.SiteForms;
  const status = form.querySelector(".form-status");

  bind(
    form,
    {
      name: checks.required("Indiquez votre nom."),
      email: checks.email,
      subject: checks.required("Choisissez l’objet de votre message."),
      message: checks.required("Écrivez votre message."),
      consent: checks.checked("Cochez cette case pour envoyer votre message."),
    },
    async (data) => {
      await postJson(form.action, Object.fromEntries(data));
      form.reset();
      status.textContent = "Message envoyé. Christophe vous répondra par e-mail.";
    },
  );
})();
