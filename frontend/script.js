// script.js

// Global schedule variable
let currentAISchedule = [];
let currentSwapAvailability = null;
let currentSwapFromUser = null;


//let calendar = null;

// Handle Login

function convertTo24Hour(timeStr) {
    const [hour, modifier] = timeStr.split(" ");
    let h = parseInt(hour);
    if (modifier === "PM" && h !== 12) h += 12;
    if (modifier === "AM" && h === 12) h = 0;
    return `${h.toString().padStart(2, '0')}:00`;
}

function submitAvailability() {
    const date = document.getElementById("availability-date").value;
    const startTime = document.getElementById("start-time").value;
    const endTime = document.getElementById("end-time").value;
    const name = sessionStorage.getItem("username");
    const submitBtn = document.querySelector("button[onclick='submitAvailability()']");

    if (!name || !date || !startTime || !endTime) {
        showToast("Please complete all fields", "warning");
        return;
    }

    const start = new Date(`1970-01-01T${convertTo24Hour(startTime)}`);
    const end = new Date(`1970-01-01T${convertTo24Hour(endTime)}`);

    if (start >= end) {
        showToast("End time must be after start time", "warning");
        return;
    }

    const availability = `${startTime} - ${endTime}`;

    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting...";

    fetch("/add_availability", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ name, date, availability })
    })
    .then(async response => {
        const data = await response.json();
        if (!response.ok) {
            showToast(data.error || "Something went wrong.", "error");
        } else {
            showToast(data.message, "success");
            document.getElementById("availability-date").value = "";
            document.getElementById("start-time").value = "";
            document.getElementById("end-time").value = "";
        }
    })
    .catch(error => {
        console.error("Error submitting availability:", error);
        showToast("Failed to submit availability.", "error");
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit";
    });
}





function loginUser(event) {
    event.preventDefault();
    
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();

    if (!username || !password) {
        showToast("Username and password are required.", "warning");
        return;
    }

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
            showToast("Login successful! ✅", "success");

            // ✅ Redirect based on role
            if (data.role === "owner") {
                window.location.href = "dashboard.html";
            } else {
                window.location.href = "calendar.html";
            }
        } else {
            showToast("Unexpected response from server.", "error");
        }
    })
    .catch(err => {
        console.error("Login error:", err);
        showToast("Network or server error.", "error");
    });
}



// Handle Registration
function registerUser(event) {
    event.preventDefault();

    const username = document.getElementById("newUsername").value;
    const email = document.getElementById("newEmail").value;
    const password = document.getElementById("newPassword").value;
    const role = document.querySelector("input[name='role']:checked").value;

    fetch("/register", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ username, email, password, role })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            alert("Registered successfully!");
            window.location.href = "login.html";
        } else {
            alert(data.error || "Registration failed.");
        }
    });
}

function postSchedule() {
    const spinner = document.getElementById("loadingSpinner");
    const spinnerMsg = document.getElementById("spinnerMessage");

    spinnerMsg.innerText = "Posting schedule and sending emails...";
    spinner.style.display = "block";

    // Get modified shifts from the calendar
    const events = calendar.getEvents();

    const scheduleToPost = events.map(event => ({
        name: event.extendedProps.name || "Unknown",
        availability: event.extendedProps.availability,
        date: event.start.toISOString().split("T")[0]
    }));

    fetch("/post_schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ schedule: scheduleToPost })
    })
        .then(res => res.json())
        .then(postRes => {
            showToast(postRes.message || "Schedule posted!", "success");
        })
        .catch(err => {
            console.error("Error posting schedule:", err);
            showToast("Error posting schedule.", "error");
        })
        .finally(() => {
            spinner.style.display = "none";
        });
}




// Load posted schedule (EMPLOYEE & CALENDAR VIEW)
function loadPostedSchedule(calendar) {
    console.log("📥 Fetching posted schedule...");

    fetch("/view_schedule")
        .then(res => res.json())
        .then(data => {
            const username = sessionStorage.getItem("username") || "anonymous";
            const isOwner = sessionStorage.getItem("role") === "owner";

            console.log("👤 Logged in as:", username);
            console.log("👑 Role:", isOwner ? "owner" : "employee");
            console.log("📦 Raw data.schedule from backend:", data.schedule);

            const events = data.schedule.map(entry => ({
                title: `${entry.name}: ${entry.availability}`,
                start: entry.date, // use plain date string directly
                allDay: true,
                editable: isOwner,
                backgroundColor: entry.name === username ? "#00d1b2" : "#3273dc",
                extendedProps: {
                    name: entry.name,
                    availability: entry.availability
                }
            }));

            console.log("🔍 First event object for debugging:", events[0]);
            console.log("🗓️ Events being added to calendar:", events);

            calendar.removeAllEvents();
            calendar.addEventSource(events);

            // ✅ Owners can drag-drop
            if (isOwner) {
                calendar.setOption("editable", true);
                calendar.setOption("eventDrop", function (info) {
                    showToast(`Moved to ${info.event.start.toDateString()}`, "info");
                    info.event.setExtendedProp("date", info.event.startStr);
                });
            }

            // ✅ Both owners & employees can request swaps
            calendar.setOption("eventClick", function (info) {
                const currentUser = sessionStorage.getItem("username");
                const shiftOwner = info.event.extendedProps.name;

                if (shiftOwner === currentUser) {
                    const dropdown = document.getElementById("swapUserDropdown");
                    if (!dropdown) return;

                    // 🧠 Assign global swap variables
                    currentSwapFromUser = shiftOwner;
                    currentSwapAvailability = info.event.extendedProps.availability;

                    dropdown.innerHTML = "";
                    fetch("/all_usernames")
                        .then(res => res.json())
                        .then(data => {
                            data.usernames
                                .filter(user => user !== currentUser)
                                .forEach(user => {
                                    const option = document.createElement("option");
                                    option.value = user;
                                    option.textContent = user;
                                    dropdown.appendChild(option);
                                });

                            const confirmBtn = document.getElementById("confirmSwapBtn");
                            if (confirmBtn) {
                                confirmBtn.dataset.date = info.event.startStr;
                            }

                            document.getElementById("swapModal").style.display = "flex";
                        });
                } else {
                    showToast("You can only request swaps for your own shifts.", "warning");
                }
            });
        })
        .catch(error => {
            console.error("❌ Error loading schedule:", error);
            showToast("Failed to load schedule.", "error");
        });
}






// AI Scheduler to calendar (DASHBOARD OWNER ONLY)
function fetchAISchedule() {
    const spinner = document.getElementById("loadingSpinner");
    const spinnerMsg = document.getElementById("spinnerMessage");

    spinnerMsg.innerText = "Generating schedule...";
    spinner.style.display = "block";

    fetch("/generate_optimized_schedule")
        .then(response => response.json())
        .then(data => {
            if (!data.schedule || !Array.isArray(data.schedule)) {
                alert("Failed to load schedule");
                return;
            }

            // Clear current events
            calendar.removeAllEvents();

            // Add new events
            const aiEvents = data.schedule.map(entry => ({
                title: `${entry.name}: ${entry.availability}`,
                start: entry.date,
                editable: true,
                allDay: true,
                backgroundColor: "#ff9800", // Optional
                extendedProps: {
                    name: entry.name,
                    availability: entry.availability,
                    date: entry.date
                }
            }));

            calendar.addEventSource(aiEvents);
        })
        .catch(err => {
            console.error("Error generating schedule:", err);
            alert("Schedule generation failed.");
        })
        .finally(() => {
            spinner.style.display = "none";
        });
}






// Adjust UI based on role
// 🔥 Make sure this is declared near the top of your script file:


function setupDashboard() {
    const role = sessionStorage.getItem("role");
    if (!role || role !== "owner") {
        window.location.href = "login.html";
        return;
    }

    document.getElementById("ownerControls").style.display = "block";

    const calendarEl = document.getElementById("calendar");
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: "dayGridMonth",
        editable: true, // ✅ Allow drag-and-drop
        events: [],
    });

    calendar.render();
    calendar.addEvent({
        title: "Debug Shift",
        start: new Date().toISOString().split("T")[0],
        allDay: true
    });
    loadPostedSchedule(calendar);  // Load shifts into it
}



// Update navbar visibility based on role
function updateNavbarVisibility() {
    const role = sessionStorage.getItem("role");

    const dashboardItem = document.getElementById("dashboardItem");
    const manageShiftsItem = document.getElementById("manageShiftsItem");
    const loginItem = document.getElementById("loginItem");
    const registerItem = document.getElementById("registerItem");
    const logoutItem = document.getElementById("logoutItem");

    if (role) {
        if (dashboardItem) dashboardItem.style.display = (role === "owner") ? "inline" : "none";
        if (manageShiftsItem) manageShiftsItem.style.display = (role === "owner") ? "inline" : "none";
        if (loginItem) loginItem.style.display = "none";
        if (registerItem) registerItem.style.display = "none";
        if (logoutItem) logoutItem.style.display = "inline";
    } else {
        if (dashboardItem) dashboardItem.style.display = "none";
        if (manageShiftsItem) manageShiftsItem.style.display = "none";
        if (loginItem) loginItem.style.display = "inline";
        if (registerItem) registerItem.style.display = "inline";
        if (logoutItem) logoutItem.style.display = "none";
    }
}



function logoutUser() {
    sessionStorage.clear();
    window.location.href = "login.html";
}

function loadShiftManagement() {
    if (sessionStorage.getItem("role") !== "owner") {
        alert("You are not authorized to view this page.");
        window.location.href = "index.html";
        return;
    }

    fetch("/all_availabilities", { credentials: "include" })
        .then(res => res.json())
        .then(data => {
            console.log("📥 Raw availabilities from backend:", data.availabilities);

            const container = document.getElementById("shiftList");
            container.innerHTML = "";

            if (!data.availabilities || data.availabilities.length === 0) {
                container.innerHTML = "<p>No shifts available.</p>";
                return;
            }

            const validShifts = data.availabilities.filter(s => {
                return s.date && /^\d{4}-\d{2}-\d{2}$/.test(s.date);
            });

            validShifts.sort((a, b) => {
                const [ay, am, ad] = a.date.split("-");
                const [by, bm, bd] = b.date.split("-");
                return new Date(ay, am - 1, ad) - new Date(by, bm - 1, bd);
            });

            validShifts.forEach((shift) => {
                const rawDate = shift.date;
                let formattedDate = "Invalid date";
                let isoDate = rawDate;

                try {
                    const [year, month, day] = rawDate.split("-");
                    const dateObj = new Date(Number(year), Number(month) - 1, Number(day));
                    if (!isNaN(dateObj)) {
                        formattedDate = dateObj.toLocaleDateString("en-US", {
                            weekday: "short",
                            year: "numeric",
                            month: "short",
                            day: "numeric"
                        });
                    }
                } catch (err) {
                    console.warn("⚠️ Could not parse date:", rawDate);
                }

                const div = document.createElement("div");
                div.innerHTML = `
                    <strong>${shift.name}</strong> – ${formattedDate} : ${shift.availability}
                    <button onclick="removeShift('${shift.name}', '${shift.availability}', '${isoDate}')">Remove</button>
                `;
                container.appendChild(div);
            });
        })
        .catch(error => {
            console.error("Error loading shifts:", error);
            document.getElementById("shiftList").innerHTML = "<p>Failed to load shifts.</p>";
        });
}







function removeShift(name, availability, date) {
    let parsedDate = new Date(date);
    if (isNaN(parsedDate)) {
        alert("❌ Cannot delete shift: invalid date.");
        return;
    }

    const formattedDate = parsedDate.toISOString().split("T")[0]; // → 'YYYY-MM-DD'

    fetch("/delete_availability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
            name,
            availability,
            date: formattedDate
        })
    })
    .then(() => loadShiftManagement());
}



function addShift() {
    const name = document.getElementById("newName").value.trim();
    const date = document.getElementById("newDate").value;
    const startTime = document.getElementById("newStartTime").value;
    const endTime = document.getElementById("newEndTime").value;

    if (!name || !date || !startTime || !endTime) {
        alert("Please fill out all fields.");
        return;
    }

    const availability = `${startTime} - ${endTime}`;

    // 🧠 Debugging: Log what's being submitted
    console.log("📤 Submitting shift:", {
        name,
        date,
        availability
    });

    fetch("/add_availability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ name, date, availability })
    })
        .then(res => res.json())
        .then(data => {
            if (data.message) {
                alert(data.message);
                loadShiftManagement(); // refresh the list
                document.getElementById("newName").value = "";
                document.getElementById("newDate").value = "";
                document.getElementById("newStartTime").value = "";
                document.getElementById("newEndTime").value = "";
            } else {
                alert(data.error || "Something went wrong.");
            }
        })
        .catch(err => {
            console.error("Add shift failed:", err);
            alert("Error adding shift.");
        });
}

  

function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.textContent = message;

    // Apply toast type class for background color
    toast.className = `toast toast-${type}`;

    // ✅ Base toast styling (inline fallback, but no background)
    toast.style.position = "fixed";
    toast.style.top = "80px"; // 👇 Moved below navbar
    toast.style.left = "50%";
    toast.style.transform = "translateX(-50%) translateY(-10px)";
    toast.style.padding = "10px 20px";
    toast.style.borderRadius = "8px";
    toast.style.boxShadow = "0 4px 12px rgba(0,0,0,0.2)";
    toast.style.zIndex = "9999";
    toast.style.fontFamily = "'Poppins', sans-serif";
    toast.style.fontSize = "15px";
    toast.style.opacity = "0";
    toast.style.pointerEvents = "none";
    toast.style.transition = "opacity 0.3s ease, transform 0.3s ease";

    document.body.appendChild(toast);

    // 🌀 Animate in
    requestAnimationFrame(() => {
        toast.style.opacity = "1";
        toast.style.transform = "translateX(-50%) translateY(0)";
    });

    // ⏳ Auto remove
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(-50%) translateY(-10px)";
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}





function loadSwapRequests() {
    const username = sessionStorage.getItem("username");
    if (!username) return;

    fetch(`/get_swap_requests?username=${username}`)
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById("swapRequestsList");
            list.innerHTML = "";

            if (!data.length) {
                list.innerHTML = "<p>No incoming requests.</p>";
                return;
            }

            data.forEach(req => {
                const div = document.createElement("div");

                const readableDate = new Date(req.date).toLocaleDateString('en-US', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                });

                div.textContent = `${req.from_user} wants to swap: ${req.availability} on ${readableDate}`;

                const acceptBtn = document.createElement("button");
                acceptBtn.textContent = "Accept";
                acceptBtn.onclick = () => respondToSwap(req.id, "accepted");

                const rejectBtn = document.createElement("button");
                rejectBtn.textContent = "Reject";
                rejectBtn.onclick = () => respondToSwap(req.id, "rejected");

                div.appendChild(acceptBtn);
                div.appendChild(rejectBtn);
                list.appendChild(div);
            });
        });
}



function respondToSwap(id, decision) {
    fetch("/respond_swap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, decision })
    })
    .then(res => res.json())
    .then(data => {
        const isError = !!data.error;
        showToast(data.message || data.error, isError ? "error" : "success");

        loadSwapRequests();
        loadOutgoingSwapRequests();
        loadPostedSchedule(calendar);
    })
    .catch(err => {
        console.error("Swap response failed:", err);
        showToast("Failed to respond to swap.", "error");
    });
}




function loadOutgoingSwapRequests() {
    const username = sessionStorage.getItem("username");
    if (!username) return;

    fetch(`/get_swap_requests?from_user=${username}`)
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById("outgoingSwapRequestsList");
            list.innerHTML = "";

            if (!data.length) {
                list.innerHTML = "<p>No outgoing swap requests.</p>";
                return;
            }

            data.forEach(req => {
                const div = document.createElement("div");
                div.textContent = `You requested ${req.to_user} to take: ${req.availability}`;

                const cancelBtn = document.createElement("button");
                cancelBtn.textContent = "Cancel";
                cancelBtn.onclick = () => cancelSwapRequest(req.id);

                div.appendChild(cancelBtn);
                list.appendChild(div);
            });
        });
}


function cancelSwapRequest(id) {
    fetch("/respond_swap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, decision: "rejected" })
    })
    .then(res => res.json())
    .then(data => {
        const isError = !!data.error;
        showToast(data.message || data.error, isError ? "error" : "success");
        loadOutgoingSwapRequests();
    })
    .catch(err => {
        console.error("Failed to cancel request:", err);
        showToast("Failed to cancel swap request.", "error");
    });
}


function closeSwapModal() {
    document.getElementById("swapModal").style.display = "none";
    currentSwapAvailability = null;
    currentSwapFromUser = null;
}

function confirmSwap() {
    const to_user = document.getElementById("swapUserDropdown").value;
    const confirmBtn = document.getElementById("confirmSwapBtn");
    const date = confirmBtn ? confirmBtn.dataset.date : null;
    const from_user = currentSwapFromUser;
    const availability = currentSwapAvailability;

    console.log("🧠 SWAP DEBUG:", { from_user, to_user, availability, date });

    if (!to_user || !from_user || !availability || !date) {
        showToast("Missing swap information.", "warning");
        return;
    }

    fetch("/request_swap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            from_user,
            to_user,
            availability,
            date
        })
    })
    .then(res => res.json())
    .then(data => {
        const isError = !!data.error;
        showToast(data.message || data.error, isError ? "error" : "success");
        document.getElementById("swapModal").style.display = "none";
        loadOutgoingSwapRequests();
    })
    .catch(err => {
        console.error("Swap request failed:", err);
        showToast("Swap request failed.", "error");
    });
}




function loadIncomingSwapRequests() {
    const username = sessionStorage.getItem("username");

    fetch(`/get_swap_requests?username=${username}`)
        .then(res => res.json())
        .then(requests => {
            const list = document.getElementById("swapRequestsList");
            list.innerHTML = ""; // Clear old ones

            if (!requests.length) {
                list.textContent = "No incoming swap requests.";
                showToast("No incoming swap requests.", "info");
                return;
            }

            requests.forEach(request => {
                const wrapper = document.createElement("div");
                wrapper.classList.add("swap-request");

                const readableDate = new Date(request.date).toLocaleDateString('en-US', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                });

                const swapText = document.createElement("p");
                swapText.textContent = `${request.from_user} wants to swap: ${request.availability} on ${readableDate}`;
                wrapper.appendChild(swapText);

                const acceptBtn = document.createElement("button");
                acceptBtn.textContent = "Accept";
                acceptBtn.onclick = () => respondSwap(request.id, "accepted");

                const rejectBtn = document.createElement("button");
                rejectBtn.textContent = "Reject";
                rejectBtn.onclick = () => respondSwap(request.id, "rejected");

                wrapper.appendChild(acceptBtn);
                wrapper.appendChild(rejectBtn);

                list.appendChild(wrapper);
            });
        })
        .catch(err => {
            console.error("Error loading incoming swap requests:", err);
            showToast("Could not load swap requests.", "error");
        });
}


function confirmAISchedule() {
    showConfirmation(
        "Are you sure you want to generate a new AI schedule? This will overwrite the existing one.",
        fetchAISchedule
    );
}


  
  function confirmPostSchedule() {
    showConfirmation("Are you sure you want to post this schedule? All employees will be notified by email.", postSchedule);
  }
  

function showConfirmation(message, onConfirm) {
    document.getElementById("confirmationMessage").innerText = message;
    document.getElementById("confirmationModal").style.display = "flex";
  
    const yesBtn = document.getElementById("confirmYes");
    const noBtn = document.getElementById("confirmNo");
  
    // Cleanup old listeners
    const newYesBtn = yesBtn.cloneNode(true);
    yesBtn.parentNode.replaceChild(newYesBtn, yesBtn);
  
    newYesBtn.addEventListener("click", () => {
      document.getElementById("confirmationModal").style.display = "none";
      onConfirm();
    });
  
    noBtn.onclick = () => {
      document.getElementById("confirmationModal").style.display = "none";
    };
  }
  

function allowDrop(ev) {
    ev.preventDefault();
}

function drag(ev) {
    ev.dataTransfer.setData("text", ev.target.id);
}

function drop(ev) {
    ev.preventDefault();
    const data = ev.dataTransfer.getData("text");
    const dragged = document.getElementById(data);
    const target = ev.currentTarget;

    // Update internal shift data (if needed)
    const newDate = target.id; // 'monday', 'tuesday', etc.
    dragged.dataset.date = newDate;

    target.appendChild(dragged);
}


function renderAISchedule(schedule) {
    // Clear all columns first
    const days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
    days.forEach(day => {
        const column = document.getElementById(day);
        if (column) column.innerHTML = `<h3>${day.charAt(0).toUpperCase() + day.slice(1)}</h3>`;
    });

    schedule.forEach((shift, index) => {
        const dateObj = new Date(shift.date);
        const weekday = dateObj.toLocaleDateString("en-US", { weekday: "long" }).toLowerCase(); // e.g., "monday"

        const shiftDiv = document.createElement("div");
        shiftDiv.className = "shift-card";
        shiftDiv.id = `shift-${index}`;
        shiftDiv.draggable = true;
        shiftDiv.ondragstart = drag;

        // Set custom data attributes
        shiftDiv.dataset.name = shift.name;
        shiftDiv.dataset.availability = shift.availability;
        shiftDiv.dataset.date = shift.date;

        shiftDiv.innerHTML = `
            <strong>${shift.name}</strong><br>${shift.availability}
        `;

        const targetColumn = document.getElementById(weekday);
        if (targetColumn) {
            targetColumn.appendChild(shiftDiv);
        }
    });
}



document.addEventListener("DOMContentLoaded", updateNavbarVisibility);
