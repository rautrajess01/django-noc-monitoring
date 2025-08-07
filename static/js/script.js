/**
 * This script handles rendering charts for the Network Dashboard.
 * It has two main sections:
 * 1. Logic for the aggregate uptime chart on the index page.
 * 2. Logic for the three per-host charts on the details page.
 *
 * It dynamically reads the URL's query parameters (e.g., ?start_date=...)
 * to ensure that when the user filters the data, the charts update accordingly.
 */

document.addEventListener("DOMContentLoaded", function() {
 // =====================================================================
 // SECTION 1: LOGIC FOR THE AGGREGATE CHART (runs only on index page)
 // =====================================================================
 const aggregateChartCtx = document.getElementById("aggregateUptimeChart");
if (aggregateChartCtx) {
  const apiUrl = `/api/aggregate-uptime/${window.location.search}`;

  fetch(apiUrl)
    .then((response) => {
      if (!response.ok) {
        return response.json().then((err) => {
          throw new Error(err.error || "Server error");
        });
      }
      return response.json();
    })
    .then((data) => {
      new Chart(aggregateChartCtx, {
        type: "bar",
        data: {
          labels: data.labels,
          datasets: [
            {
              label: "Average Uptime",
              data: data.data,
              backgroundColor: [
                "rgba(75, 192, 192, 0.6)",
                "rgba(153, 102, 255, 0.6)",
              ],
              borderColor: [
                "rgba(75, 192, 192, 1)",
                "rgba(153, 102, 255, 1)",
              ],
              borderWidth: 1,
            },
          ],
        },
        options: {
          scales: {
            y: {
              beginAtZero: false,
              min: 80,
              max: 100,
              title: {
                display: true,
                text: "Average Uptime Percentage (%)",
              },
            },
          },
          plugins: {
            legend: {
              display: false,
            },
            tooltip: {
              callbacks: {
                label: function (context) {
                  return `Average Uptime: ${context.raw}%`;
                },
              },
            },
            datalabels: {
              anchor: 'end',
              align: 'top',
              formatter: function (value) {
                return `${value}%`;
              },
              color: '#000',
              font: {
                weight: 'bold',
              },
            },
          },
        },
        plugins: [ChartDataLabels],
      });
    })
    .catch((error) => {
      console.error("Error fetching or rendering aggregate chart:", error);
      const context = aggregateChartCtx.getContext("2d");
      context.font = "16px Arial";
      context.fillStyle = "red";
      context.textAlign = "center";
      context.fillText(
        `Error: ${error.message}`,
        aggregateChartCtx.width / 2,
        aggregateChartCtx.height / 2
      );
    });
}

 // =====================================================================
 // SECTION 2: LOGIC FOR PER-HOST CHARTS (runs only on per_host page)
 // =====================================================================
 const perHostContainer = document.getElementById("perHostCharts");

 if (perHostContainer) {
  const pk = perHostContainer.dataset.pk;
  if (!pk) {
   console.error("Host PK is missing from the data-pk attribute.");
   return;
  }

  // Construct the API URL, including any search filters from the current page's URL.
  const fetchUrl = `/api/host/${pk}/charts/${window.location.search}`;

  console.log("Fetching per-host chart data from:", fetchUrl);

  // Fetch the data ONCE for all three charts
  fetch(fetchUrl)
   .then((response) => {
    if (!response.ok) {
     return response.json().then((err) => {
      throw new Error(err.error || "Server error");
     });
    }
    return response.json();
   })
   .then((data) => {
    if (data.error) {
     throw new Error(data.error);
    }

    // --- Chart 1: Uptime vs. Downtime (Pie Chart) ---
    const pieCtx = document
     .getElementById("uptimePieChart")
     .getContext("2d");
    new Chart(pieCtx, {
     type: "pie",
     data: {
      labels: data.uptime_pie.labels,
      datasets: [
       {
        label: "Uptime vs Downtime (minutes)",
        data: data.uptime_pie.data,
        backgroundColor: [
         "rgba(75, 192, 192, 0.8)", // Uptime
         "rgba(255, 99, 132, 0.8)", // Downtime
        ],
       },
      ],
     },
     options: {
        responsive: true,
    maintainAspectRatio: false,
      plugins: {
       datalabels: {
        formatter: (value, ctx) => {
         let datasets = ctx.chart.data.datasets;
         if (datasets.length) {
          let total = datasets[0].data.reduce((a, b) => a + b, 0);
          let percentage = ((value / total) * 100).toFixed(1);
          return `${percentage}%`;
         }
         return "";
        },
        color: "#fff",
        font: {
         weight: "bold",
         size: 14,
        },
       },
       tooltip: {
        enabled: true,
        callbacks: {
         label: function(context) {
          const data = context.dataset.data;
          const total = data.reduce((a, b) => a + b, 0);
          const value = context.raw;
          const percentage = ((value / total) * 100).toFixed(1);
          return `${context.label}: ${value} min (${percentage}%)`;
         },
        },
       },
      },
     },
     plugins: [ChartDataLabels],
    });

    // --- Chart 2: Daily Downtime (Bar Chart) ---
    const barCtx = document
     .getElementById("dailyBarChart")
     .getContext("2d");
    new Chart(barCtx, {
     type: "bar",
     data: {
      labels: data.daily_bar.labels,
      datasets: [
       {
        label: "Daily Downtime (minutes)",
        data: data.daily_bar.data,
        backgroundColor: "rgba(255, 159, 64, 0.8)",
       },
      ],
     },
     options: {
      plugins: {
       tooltip: {
        callbacks: {
         // Add the reason to the tooltip for extra context
         afterLabel: function(context) {
          const reason = data.daily_bar.reasons[context.dataIndex];
          return `Reason: ${reason}`;
         },
        },
       },
      },
     },
    });

    // --- Chart 3: Daily Outage Frequency (Line Chart) ---
    const lineCtx = document
     .getElementById("trendLineChart")
     .getContext("2d");
    new Chart(lineCtx, {
     type: "line",
     data: {
      labels: data.trend_line.labels,
      datasets: [
       {
        label: "Daily Outage Count",
        data: data.trend_line.data,
        borderColor: "rgba(54, 162, 235, 1)",
        backgroundColor: "rgba(54, 162, 235, 0.2)",
        fill: true,
        tension: 0.1,
       },
      ],
     },
    });
   })
   .catch((error) => {
    console.error("Error fetching or rendering per-host charts:", error);
    perHostContainer.innerHTML = `<p style="color: red; font-weight: bold;">Could not load chart data: ${error.message}</p>`;
   });
 }

 // =====================================================================
 // SECTION 3: ADDITIONAL CHARTS FOR DASHBOARD (fixed URLs)
 // =====================================================================
 
 // Get the entire query string from the browser URL (e.g., "?name=&type=switch")
 const urlQueryString = window.location.search;

 // --- Dashboard Uptime Pie Chart (if different from per-host) ---
 // Only create this chart if the element exists AND it's not already handled above
 const dashboardPieChart = document.getElementById("uptimePieChart");
 if (dashboardPieChart && !perHostContainer) {
   // FIXED: Use the working API URL pattern
   const uptimeApiURL = `/api/aggregate-uptime/${urlQueryString}`;

   fetch(uptimeApiURL)
     .then((res) => res.json())
     .then((data) => {
       new Chart(dashboardPieChart, {
         type: "pie",
         data: {
           labels: data.labels,
           datasets: [
             {
               data: data.data,
               backgroundColor: ["#28a745", "#007bff"],
             },
           ],
         },
       });
     })
     .catch((error) => {
       console.error("Error fetching dashboard pie chart:", error);
     });
 }

 // --- Daily Trend Chart ---
 const dailyTrendChart = document.getElementById("dailyTrendChart");
 if (dailyTrendChart) {
   // Use the working API URL pattern
   const trendApiURL = `/daily_event_trend_api/${urlQueryString}`;

   fetch(trendApiURL)
     .then((res) => res.json())
     .then((data) => {
       new Chart(dailyTrendChart, {
         type: "line",
         data: {
           labels: data.labels,
           datasets: [
             {
               label: "Events per Day",
               data: data.data,
               fill: false,
               borderColor: "#ff6384",
               tension: 0.3,
             },
           ],
         },
       });
     })
     .catch((error) => {
       console.error("Error fetching daily trend chart:", error);
     });
 }
});

// =====================================================================
// UTILITY FUNCTIONS
// =====================================================================

function openPopup(id) {
  document.getElementById(id).style.display = "block";
}

function closePopup(id) {
  document.getElementById(id).style.display = "none";
}

// Optional: close when clicking outside
window.onclick = function(event) {
  document.querySelectorAll('.popup-overlay').forEach(popup => {
    if (event.target === popup) {
      popup.style.display = "none";
    }
  });
};

document.addEventListener("DOMContentLoaded", function () {
  const showMoreBtn = document.getElementById("showMoreBtn");

  if (showMoreBtn) {
    showMoreBtn.addEventListener("click", function (e) {
      e.preventDefault(); // stop form submission
      const hiddenRows = document.querySelectorAll(".hidden-row");
      hiddenRows.forEach(row => {
        row.classList.remove("hidden-row");
      });
      showMoreBtn.style.display = "none"; // hide the button after showing all
    });
  }
});

document.addEventListener("DOMContentLoaded", function () {
  const transitionEl = document.querySelector('.page-transition');
  const spinner = document.getElementById('loading-spinner');

  // Hide spinner and show content with fade-in
  requestAnimationFrame(() => {
    transitionEl.classList.add('fade-in');
    spinner.style.display = 'none';
  });

  // Handle all link clicks
  document.querySelectorators('a[href]').forEach(link => {
    const href = link.getAttribute('href');

    // Skip anchors, javascript voids, or external targets
    if (
      href.startsWith('#') || 
      href.startsWith('javascript:') || 
      link.getAttribute('target') === '_blank'
    ) return;

    link.addEventListener('click', function (e) {
      e.preventDefault();
      transitionEl.classList.remove('fade-in');
      transitionEl.classList.add('fade-out');

      spinner.style.display = 'flex'; // Show loading spinner again

      setTimeout(() => {
        window.location.href = this.href;
      }, 400); // Sync with fade-out
    });
  });
});
function updateDurations() {
    const elements = document.querySelectorAll('.live-duration');
    elements.forEach(el => {
        const downTimeStr = el.dataset.downTime;

        // Gracefully handle cases where the data attribute is missing
        if (!downTimeStr) {
            el.textContent = 'Unknown';
            return;
        }

        const downTime = new Date(downTimeStr);

        if (isNaN(downTime)) {
            el.textContent = 'Invalid date';
            return;
        }

        const now = new Date();
        const diffMs = now - downTime;

        // Prevent showing negative time
        if (diffMs < 0) {
            el.textContent = '00:00:00';
            return;
        }

        // --- NEW CALCULATION LOGIC ---

        // 1. Calculate total days
        const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        // 2. Calculate hours remaining in the current day
        const hours = String(Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))).padStart(2, '0');

        // 3. Calculate minutes remaining in the current hour
        const minutes = String(Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))).padStart(2, '0');

        // 4. Calculate seconds remaining in the current minute
        const seconds = String(Math.floor((diffMs % (1000 * 60)) / 1000)).padStart(2, '0');


        // --- DYNAMICALLY BUILD THE OUTPUT STRING ---
        let durationStr = `${hours}:${minutes}:${seconds}`;

        if (days > 0) {
            // Handle plural 'day' vs 'days'
            const dayText = days === 1 ? 'day' : 'days';
            durationStr = `${days} ${dayText}, ${durationStr}`;
        }

        el.textContent = durationStr;
    });
}

// This part stays the same
document.addEventListener('DOMContentLoaded', () => {
    updateDurations();
    setInterval(updateDurations, 1000);
});

document.addEventListener('DOMContentLoaded', function() {
  const nepaliMonthDays = JSON.parse(document.getElementById('nepali-month-data').textContent);
  const monthSelector = document.querySelector('.month-selector');
  const dateGridContainer = document.getElementById('date-grid-container');
  const monthTitle = document.getElementById('month-title');
  const tableTitle = document.getElementById('table-title');
  const hostRows = document.querySelectorAll('.host-row');
  const noEventsRow = document.getElementById('no-events-row');

  const initialUrlParams = new URLSearchParams(window.location.search);
  const initialMonth = initialUrlParams.get('month');
  const initialDay = initialUrlParams.get('day');

  function getOrdinalSuffix(n) {
    if (!n) return '';
    const i = parseInt(n, 10);
    const s = ["th", "st", "nd", "rd"];
    const v = i % 100;
    return i + (s[(v - 20) % 10] || s[v] || s[0]);
  }

  function updateURL(month, day) {
    const url = new URL(window.location);
    if (month) {
      url.searchParams.set('month', month);
    } else {
      url.searchParams.delete('month');
    }
    
    if (day) {
      url.searchParams.set('day', day);
    } else {
      url.searchParams.delete('day');
    }
    window.history.pushState({}, '', url);
  }

  function generateDateGrid(monthName) {
    dateGridContainer.innerHTML = '';
    if (!monthName || !nepaliMonthDays[monthName]) {
      monthTitle.textContent = '';
      document.querySelector('.month-dates').style.display = 'none';
      return;
    }
    
    document.querySelector('.month-dates').style.display = 'block';
    
    const daysInMonth = nepaliMonthDays[monthName];

    // Add "All" button first
    const allBox = document.createElement('a');
    allBox.className = 'date-box all-dates';
    allBox.href = `?month=${monthName}`;
    allBox.dataset.day = 'all';
    allBox.innerHTML = 'All';
    dateGridContainer.appendChild(allBox);

    // Then add individual days
    for (let i = 1; i <= daysInMonth; i++) {
      const dayBox = document.createElement('a');
      dayBox.className = 'date-box';
      dayBox.href = `?month=${monthName}&day=${i}`;
      dayBox.dataset.day = String(i); // Ensure it's a string
      dayBox.innerHTML = `${getOrdinalSuffix(i)} <span>${monthName}</span>`;
      dateGridContainer.appendChild(dayBox);
    }
  }

  function filterEvents(selectedMonth, selectedDay) {
    console.log('=== FILTER DEBUG ===');
    console.log(`Selected Month: "${selectedMonth}"`);
    console.log(`Selected Day: "${selectedDay}"`);
    
    let eventsFound = 0;
    
    hostRows.forEach((row, index) => {
      const rowMonth = row.dataset.month;
      const rowDay = row.dataset.day;
      
      // Debug first few rows
      if (index < 5) {
        console.log(`Row ${index}: month="${rowMonth}", day="${rowDay}"`);
      }
      
      let show = false;
      
      if (!selectedMonth) {
        // Show all events
        show = true;
      } else if (!selectedDay || selectedDay === 'all') {
        // Show all events for selected month
        show = (rowMonth === selectedMonth);
      } else {
        // Show events for specific day and month
        // Convert both to strings for comparison
        const dayMatch = String(rowDay) === String(selectedDay);
        const monthMatch = rowMonth === selectedMonth;
        show = dayMatch && monthMatch;
        
        // Debug comparison
        if (index < 5) {
          console.log(`  Day comparison: "${rowDay}" === "${selectedDay}" = ${dayMatch}`);
          console.log(`  Month comparison: "${rowMonth}" === "${selectedMonth}" = ${monthMatch}`);
          console.log(`  Show: ${show}`);
        }
      }
      
      row.style.display = show ? '' : 'none';
      if (show) eventsFound++;
    });

    console.log(`Total events shown: ${eventsFound}`);
    
    // Update table title
    if (selectedMonth && selectedDay && selectedDay !== 'all') {
      tableTitle.textContent = `Events for ${selectedMonth} ${getOrdinalSuffix(selectedDay)}`;
    } else if (selectedMonth) {
      tableTitle.textContent = `All Events for ${selectedMonth}`;
    } else {
      tableTitle.textContent = 'All Events';
    }
    
    noEventsRow.style.display = eventsFound === 0 ? '' : 'none';
  }

  function updateUI(selectedMonth, selectedDay) {
    console.log('=== UPDATE UI ===');
    console.log(`Month: "${selectedMonth}", Day: "${selectedDay}"`);
    
    // Update month selection
    document.querySelectorAll('.month-box').forEach(box => {
      box.classList.toggle('selected', box.dataset.monthName === selectedMonth);
    });

    // Generate date grid
    generateDateGrid(selectedMonth);

    // Update day selection
    if (selectedMonth) {
      document.querySelectorAll('.date-box').forEach(box => {
        if (selectedDay === 'all' || !selectedDay) {
          box.classList.toggle('selected', box.dataset.day === 'all');
        } else {
          box.classList.toggle('selected', box.dataset.day === String(selectedDay));
        }
      });
    }

    // Filter events
    filterEvents(selectedMonth, selectedDay);
    
    // Update URL
    if (selectedMonth) {
      updateURL(selectedMonth, selectedDay === 'all' ? null : selectedDay);
    }
  }

  // Event listeners
  monthSelector.addEventListener('click', function(e) {
    e.preventDefault();
    const target = e.target.closest('.month-box');
    if (!target) return;
    const monthName = target.dataset.monthName;
    updateUI(monthName, 'all'); // Default to show all days
  });

  dateGridContainer.addEventListener('click', function(e) {
    e.preventDefault();
    const target = e.target.closest('.date-box');
    if (!target) return;
    
    const day = target.dataset.day;
    const currentMonth = document.querySelector('.month-box.selected')?.dataset.monthName;
    
    console.log('Date clicked:', day, 'Month:', currentMonth);
    updateUI(currentMonth, day);
  });
  
  // Initialization
  console.log('=== INITIALIZATION ===');
  console.log(` Initial Day: "${initialDay}",Initial Month: "${initialMonth}"`);
  
  if (initialMonth) {
    updateUI(initialDay, initialMonth || 'all');
  } else {
    updateUI(null, null);
  }
});

  function refreshPage() {
    window.location.href = window.location.href;
  }
