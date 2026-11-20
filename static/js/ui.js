// Site-wide UI polish: scroll reveals, header shadow, dismissible messages,
// cart-count bump and button loading state. Everything here is optional:
// the site works the same without it, just with fewer animations.
(function () {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- Header shadow once the page scrolls ---- */
  const header = document.querySelector(".site-header");
  if (header) {
    let ticking = false;
    const update = () => {
      header.classList.toggle("is-scrolled", window.scrollY > 8);
      ticking = false;
    };
    window.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          window.requestAnimationFrame(update);
          ticking = true;
        }
      },
      { passive: true }
    );
    update();
  }

  /* ---- Flash messages: close button + auto-dismiss ---- */
  document.querySelectorAll(".message").forEach((message) => {
    const close = document.createElement("button");
    close.type = "button";
    close.className = "message__close";
    close.setAttribute("aria-label", "Dismiss message");
    close.innerHTML = "&times;";
    message.appendChild(close);

    const dismiss = () => {
      message.classList.add("is-leaving");
      setTimeout(() => message.remove(), 350);
    };

    close.addEventListener("click", dismiss);

    // Errors stay until dismissed; everything else leaves on its own
    if (!message.classList.contains("message--error")) {
      setTimeout(dismiss, 6000);
    }
  });

  /* ---- Cart count: small bump when the number changes ---- */
  const cartCount = document.querySelector(".cart-count");
  if (cartCount) {
    const key = "rk-cart-count";
    const current = cartCount.textContent.trim();
    try {
      const previous = sessionStorage.getItem(key);
      if (previous !== null && previous !== current) {
        cartCount.classList.add("is-bumped");
      }
      sessionStorage.setItem(key, current);
    } catch (e) {
      /* storage can be blocked; the bump is purely cosmetic */
    }
  }

  /* ---- Buttons: disable after submit to stop double-clicks ---- */
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector('button[type="submit"].btn, button.btn:not([type])');
      if (!button || button.disabled) return;
      // Wait a tick so the submit button's own name/value is still sent
      setTimeout(() => {
        button.classList.add("is-loading");
        button.disabled = true;
      }, 0);
    });
  });
  // Coming back with the browser's back button should not leave buttons stuck
  window.addEventListener("pageshow", (event) => {
    if (!event.persisted) return;
    document.querySelectorAll(".btn.is-loading").forEach((button) => {
      button.classList.remove("is-loading");
      button.disabled = false;
    });
  });

  /* ---- Scroll reveal ---- */
  if (reduceMotion || !("IntersectionObserver" in window)) return;

  const targets = document.querySelectorAll(
    [
      "main .section",
      ".product-grid > *",
      ".category-grid > *",
      ".order-card",
      ".stat",
      ".profile-grid > *",
      ".checkout > *",
      ".info-grid > *",
    ].join(",")
  );
  if (!targets.length) return;

  document.documentElement.classList.add("js-reveal");

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        el.classList.add("is-visible");
        observer.unobserve(el);
        // After the reveal finishes, let hover transitions take over again
        setTimeout(() => el.classList.add("is-done"), 900);
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
  );

  targets.forEach((el) => {
    // Stagger siblings that enter the screen together (capped so it never drags)
    const index = Array.prototype.indexOf.call(el.parentElement.children, el);
    el.style.setProperty("--reveal-delay", Math.min(index, 8) * 0.06 + "s");
    el.classList.add("reveal");
    observer.observe(el);
  });
})();
