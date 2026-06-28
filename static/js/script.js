// script.js
// Handles the async (background) status update on the Student Detail page.
// When the admin changes the dropdown, this sends the new status
// to Flask without reloading the page.


// Wait until the full page has loaded before running anything
document.addEventListener("DOMContentLoaded", function () {

  // Find the status dropdown element on the page
  const statusSelect = document.getElementById("status-select");

  // If we're not on the detail page, statusSelect will be null
  // This check prevents errors on pages that don't have this dropdown
  if (!statusSelect) return;

  // Read the student's ID from the data-id attribute we set in detail.html
  // e.g. <select id="status-select" data-id="3"> → studentId = "3"
  const studentId = statusSelect.dataset.id;

  // ── Listen for when the user changes the dropdown ────────────
  statusSelect.addEventListener("change", function () {

    // Get the newly selected value ("admitted", "undecided", "not admitted")
    const newStatus = this.value;

    // ── Send the new status to Flask in the background ───────
    // fetch() makes an HTTP request without reloading the page
    fetch(`/update-status/${studentId}`, {
      method: "POST",                         // same as a form POST
      headers: {
        "Content-Type": "application/json"    // tell Flask we're sending JSON
      },
      body: JSON.stringify({ status: newStatus })
      // JSON.stringify converts the JS object { status: "admitted" }
      // into a JSON string '{"status":"admitted"}' that Flask can read
    })

    // .then() runs when Flask responds — response is the raw HTTP response
    .then(function (response) {
      return response.json();   // convert the response into a JS object
    })

    // data is now the object Flask sent back: { message: "...", status: "..." }
    .then(function (data) {

      // Find the status badge on the profile card and update its text
      const badge = document.querySelector(".status-badge");
      if (badge) {
        badge.textContent = data.status;
      }

      // Give the user a quick confirmation message
      alert("Status updated to: " + data.status);
    })

    // .catch() runs if something went wrong (network error, server error etc.)
    .catch(function (error) {
      console.error("Error updating status:", error);
      alert("Something went wrong. Please try again.");
    });

  });

});