document.addEventListener("DOMContentLoaded", function () {
    console.log("✅ script.js loaded!");

    fetchSchedule(); // Load schedule when the page loads

    // Function to submit availability
    window.submitAvailability = function () {
        const name = document.getElementById("name").value.trim();
        const availability = document.getElementById("availability").value.trim();

        if (!name || !availability) {
            alert("Please enter both name and availability.");
            return;
        }

        fetch("http://127.0.0.1:5000/add_availability", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, availability })
        })
        .then(response => response.json())
        .then(data => {
            console.log("✅ Availability Added:", data);
            alert("Availability Added Successfully!");
            fetchSchedule(); // Refresh schedule after adding
        })
        .catch(error => console.error("❌ Error:", error));
    };

    // Function to fetch and display schedule
    window.fetchSchedule = function () {
        fetch("http://127.0.0.1:5000/generate_schedule")
            .then(response => response.json())
            .then(data => {
                console.log("📡 Schedule Fetched:", data);

                const scheduleList = document.getElementById("scheduleList");
                scheduleList.innerHTML = ""; // Clear previous list

                data.schedule.forEach(entry => {
                    const listItem = document.createElement("li");
                    listItem.textContent = `${entry.name}: ${entry.availability}`;
                    scheduleList.appendChild(listItem);
                });
            })
            .catch(error => console.error("❌ Fetch error:", error));
    };
});
