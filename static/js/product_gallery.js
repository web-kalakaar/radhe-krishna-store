// Product gallery: click (or keyboard) a thumbnail to swap the main image
// with a soft cross-fade.
(function () {
  const mainImage = document.getElementById("main-image");
  const thumbs = document.querySelectorAll(".thumb");

  if (!mainImage || thumbs.length === 0) return;

  const FADE_MS = 250;
  let swapTimer = null;

  // Warm the browser cache so swaps feel instant
  thumbs.forEach((thumb) => {
    const preload = new Image();
    preload.src = thumb.src;
  });

  function setActive(thumb) {
    thumbs.forEach((item) => item.classList.remove("is-active"));
    thumb.classList.add("is-active");
  }

  function showImage(thumb) {
    if (thumb.src === mainImage.src) return;

    setActive(thumb);
    clearTimeout(swapTimer);
    mainImage.classList.add("is-swapping");

    swapTimer = setTimeout(() => {
      mainImage.src = thumb.src;
      // Fade back in once the new image is ready
      const reveal = () => mainImage.classList.remove("is-swapping");
      if (mainImage.complete) {
        reveal();
      } else {
        mainImage.addEventListener("load", reveal, { once: true });
        mainImage.addEventListener("error", reveal, { once: true });
      }
    }, FADE_MS);
  }

  setActive(thumbs[0]);

  thumbs.forEach((thumb) => {
    thumb.setAttribute("tabindex", "0");
    thumb.setAttribute("role", "button");

    thumb.addEventListener("click", () => showImage(thumb));
    thumb.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        showImage(thumb);
      }
    });
  });
})();
