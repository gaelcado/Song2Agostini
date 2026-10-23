// Outils communs aux formulaires : validation à l'envoi, erreurs à côté des champs, envoi JSON.
window.SiteForms = (() => {
  const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const EMAIL_KEY = "christophe-arent:email";

  const checks = {
    email: (v) => (!v ? "Indiquez votre adresse e-mail." : EMAIL.test(v) ? "" : "Saisissez une adresse e-mail au format nom@exemple.fr."),
    required: (message) => (v) => (v ? "" : message),
    checked: (message) => (_, field) => (field.checked ? "" : message),
  };

  function showError(field, message) {
    const error = document.getElementById(field.getAttribute("aria-describedby")?.split(" ")[0]);
    if (error) {
      error.textContent = message;
      error.hidden = !message;
    }
    if (message) field.setAttribute("aria-invalid", "true");
    else field.removeAttribute("aria-invalid");
  }

  // rules : { nomDuChamp: fonction(valeur, champ) → message d'erreur ou "" }
  function bind(form, rules, onSubmit) {
    const submit = form.querySelector('button[type="submit"]');
    const status = form.querySelector(".form-status");
    const label = submit.innerHTML;
    const run = (name) => rules[name](form.elements[name].value.trim(), form.elements[name]);

    // Préremplit l'e-mail déjà saisi sur ce navigateur.
    if (form.elements.email && !form.elements.email.value) form.elements.email.value = localStorage.getItem(EMAIL_KEY) ?? "";

    form.addEventListener("input", (event) => {
      const field = event.target;
      if (field.getAttribute("aria-invalid") === "true" && rules[field.name] && !run(field.name)) showError(field, "");
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (status) status.textContent = "";
      let firstInvalid = null;
      for (const name of Object.keys(rules)) {
        const message = run(name);
        showError(form.elements[name], message);
        if (message && !firstInvalid) firstInvalid = form.elements[name];
      }
      if (firstInvalid) return firstInvalid.focus();

      submit.disabled = true;
      submit.setAttribute("aria-busy", "true");
      submit.textContent = submit.dataset.busy ?? "Envoi en cours…";
      try {
        if (form.elements.email) localStorage.setItem(EMAIL_KEY, form.elements.email.value.trim());
        await onSubmit(new FormData(form));
      } catch {
        if (status) status.textContent = "Envoi impossible. Vérifiez votre connexion et réessayez.";
      } finally {
        submit.disabled = false;
        submit.removeAttribute("aria-busy");
        submit.innerHTML = label;
      }
    });
  }

  async function postJson(url, data) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || String(response.status));
    return body;
  }

  return { checks, bind, postJson };
})();
