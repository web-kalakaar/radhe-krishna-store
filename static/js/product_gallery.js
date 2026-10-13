const mainImage = document.getElementById("main-image");
const thumbs = document.querySelectorAll(".thumb");

if (mainImage && thumbs.length > 0) {
  thumbs[0].classList.add("is-active");

  thumbs.forEach((thumb) => {
    thumb.addEventListener("click", () => {
      mainImage.src = thumb.src;
      thumbs.forEach((item) => item.classList.remove("is-active"));
      thumb.classList.add("is-active");
    });
  });
}