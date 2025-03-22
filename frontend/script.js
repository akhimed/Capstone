// script.js

// Global schedule variable
let currentAISchedule = [];

// Handle Login

function submitAvailability() {
    const name = document.getElementById("name").value;
    const availability = document.getElementById("availability").value;

    fetch("/add_availability", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ name, availability })
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message || data.error);
    })
    .catch(error => {
        console.error("Error submitting availability:", error);
    });
}


function loginUser(event) {
    event.preventDefault();
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    })
    .then(res => res.json())
    .then(data => {
        if (data.role) {
            sessionStorage.setItem("role", data.role);
            sessionStorage.setItem("username", data.username);
            window.location.href = "dashboard.html";
        } else {
            alert("Login failed");
        }
    });
}

// Handle Registration
function registerUser(event) {
    event.preventDefault();
    const username = document.getElementById("newUsername").value;
    const password = document.getElementById("newPassword").value;
    const role = document.querySelector('input[name="role"]:checked').value;

    fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role })
    })
    .then(res => {
        if (!res.ok) throw new Error("Registration failed");
        return res.json();
    })
    .then(data => {
        alert(data.message || "Registered successfully!");
        window.location.href = "login.html";
    })
    .catch(err => {
        console.error(err);
        alert("Registration failed.");
    });
}

// Post the generated schedule (OWNER ONLY)
function postSchedule() {
    if (!currentAISchedule.length) return alert("Generate a schedule first");

    fetch("/post_schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ schedule: currentAISchedule })
    })
    .then(res => res.json())
    .then(data => alert(data.message))
    .catch(err => {
        console.error("Error posting schedule:", err);
        alert("Failed to post schedule.");
    });
}

// Load posted schedule (EMPLOYEE & CALENDAR VIEW)
function loadPostedSchedule(calendar) {
    fetch("/view_schedule")
        .then(res => res.json())
        .then(data => {
            const schedule = data.schedule;
            console.log("Loaded schedule from backend:", schedule);  // Debug log

            if (schedule.length === 0) {
                const msg = document.getElementById("scheduleMessage");
                if (msg) msg.innerText = "No schedule posted yet.";
            } else {
                const msg = document.getElementById("scheduleMessage");
                if (msg) msg.innerText = "";
            }

            const events = schedule.map(entry => {
                const dateObj = new Date(entry.date);
                const isoDate = dateObj.toISOString().split("T")[0]; // Format: YYYY-MM-DD

                return {
                    title: `${entry.name}: ${entry.availability}`,
                    start: isoDate,
                    allDay: true
                };
            });

            calendar.removeAllEvents();
            calendar.addEventSource(events);
        })
        .catch(error => {
            console.error("Error loading schedule:", error);
        });
}



// AI Scheduler to calendar (DASHBOARD OWNER ONLY)
function fetchAISchedule() {
    fetch("/generate_optimized_schedule")
        .then(response => response.json())
        .then(data => {
            if (!data.schedule || !Array.isArray(data.schedule)) {
                alert("Failed to load schedule");
                return;
            }
            currentAISchedule = data.schedule;

            const calendarEl = document.getElementById("calendar");
            const calendar = new FullCalendar.Calendar(calendarEl, {
                initialView: "dayGridMonth",
                events: currentAISchedule.map(entry => ({
                    title: `${entry.name}: ${entry.availability}`,
                    start: entry.date,
                    allDay: true,
                }))
            });
            calendar.render();
        });
}

// Adjust UI based on role
function setupDashboard() {
    const role = sessionStorage.getItem("role");

    if (!role || role !== "owner") {
        window.location.href = "login.html"; // block non-owners
        return;
    }

    document.getElementById("ownerControls").style.display = "block";

    const calendarEl = document.getElementById("calendar");
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: "dayGridMonth",
        events: []
    });
    calendar.render();

    // Owner dashboard shows posted schedule too
    loadPostedSchedule(calendar);
}

// Update navbar visibility based on role
function updateNavbarVisibility() {
    const role = sessionStorage.getItem("role");

    const dashboardItem = document.getElementById("dashboardItem");
    const loginItem = document.getElementById("loginItem");
    const registerItem = document.getElementById("registerItem");
    const logoutItem = document.getElementById("logoutItem");

    if (role) {
        if (dashboardItem) dashboardItem.style.display = (role === "owner") ? "inline" : "none";
        if (loginItem) loginItem.style.display = "none";
        if (registerItem) registerItem.style.display = "none";
        if (logoutItem) logoutItem.style.display = "inline";
    } else {
        if (dashboardItem) dashboardItem.style.display = "none";
        if (loginItem) loginItem.style.display = "inline";
        if (registerItem) registerItem.style.display = "inline";
        if (logoutItem) logoutItem.style.display = "none";
    }
}


function logoutUser() {
    sessionStorage.clear();
    window.location.href = "login.html";
}

document.addEventListener("DOMContentLoaded", updateNavbarVisibility);
