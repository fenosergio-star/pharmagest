(function () {
  "use strict";

  var sidebar = document.getElementById("sidebar");
  var backdrop = document.getElementById("sidebarBackdrop");
  var toggle = document.getElementById("sidebarToggle");
  var closeBtn = document.getElementById("sidebarClose");

  function openSidebar() {
    if (!sidebar) return;
    sidebar.classList.add("open");
    document.body.classList.add("sidebar-open");
  }

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove("open");
    document.body.classList.remove("sidebar-open");
  }

  if (toggle) toggle.addEventListener("click", openSidebar);
  if (closeBtn) closeBtn.addEventListener("click", closeSidebar);
  if (backdrop) backdrop.addEventListener("click", closeSidebar);

  if (sidebar) {
    sidebar.querySelectorAll("a.nav-link").forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.innerWidth < 992) closeSidebar();
      });
    });
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeSidebar();
  });

  window.addEventListener("resize", function () {
    if (window.innerWidth >= 992) closeSidebar();
  });

  if (window.bootstrap && bootstrap.Alert) {
    document.querySelectorAll(".alert-dismissible").forEach(function (element) {
      window.setTimeout(function () {
        bootstrap.Alert.getOrCreateInstance(element).close();
      }, 8000);
    });
  }

  document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
    button.addEventListener("click", function () {
      var input = document.getElementById(button.getAttribute("data-toggle-password"));
      if (!input) return;
      var hidden = input.getAttribute("type") === "password";
      input.setAttribute("type", hidden ? "text" : "password");
      var icon = button.querySelector("i");
      if (icon) {
        icon.classList.toggle("bi-eye", !hidden);
        icon.classList.toggle("bi-eye-slash", hidden);
      }
    });
  });
})();
