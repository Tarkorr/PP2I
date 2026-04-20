document.addEventListener("DOMContentLoaded", () => {
  document.body.classList.add("is-ready");

  const cards = document.querySelectorAll(".auth-card, .hero-card");
  cards.forEach((card) => {
    const resetSpotlight = () => {
      card.style.setProperty("--spotlight-x", "50%");
      card.style.setProperty("--spotlight-y", "30%");
    };

    resetSpotlight();

    card.addEventListener("mousemove", (event) => {
      const rect = card.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width) * 100;
      const y = ((event.clientY - rect.top) / rect.height) * 100;
      card.style.setProperty("--spotlight-x", `${x}%`);
      card.style.setProperty("--spotlight-y", `${y}%`);
    });

    card.addEventListener("mouseleave", resetSpotlight);
  });
});
