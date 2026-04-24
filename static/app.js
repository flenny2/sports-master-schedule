/**
 * Sports Master Schedule — frontend logic
 *
 * Architecture:
 *   - Fetch games from /api/schedule (month-based)
 *   - Desktop: month grid overview + detail panel for selected day
 *   - Mobile: 2-week vertical list with inline game cards
 *   - Today view: command center with live/upcoming/completed sections
 *   - Tables view: standings + title race widgets
 *   - Game cards: "upcoming" layout (pre-game) vs "scoreboard" layout (live/final)
 *   - Click any card to expand for venue, broadcast, standings context
 */

// ── State ────────────────────────────────────────────────────────
var now          = new Date();
var currentYear  = now.getFullYear();
var currentMonth = now.getMonth() + 1;  // 1-indexed (1=Jan, 12=Dec)
var currentView  = "week";   // "week" = calendar tab, "today", "tables"
var currentSport = "all";
var selectedDate = null;
var allGames     = [];
var rangeInfo    = null;     // { start: "YYYY-MM-DD", end: "YYYY-MM-DD" }
var standingsData = [];
var standingsLoaded = false;
var titleRacesData = [];
var countdownTimer = null;
var lastMobileState = null;  // track viewport changes
var storylinesData = [];     // [{id, label, description}]
var activeStorylineId = null; // currently-selected filter, or null
var initialScrollDone = false; // desktop: scroll-to-today only once per load
var mobileWindowStart = null;  // mobile 7-day window start, "YYYY-MM-DD"

var MOBILE_BP = 640;

// ── DOM ──────────────────────────────────────────────────────────
var monthLabel   = document.getElementById("week-label");
var btnPrev      = document.getElementById("btn-prev");
var btnNext      = document.getElementById("btn-next");
var btnRefresh   = document.getElementById("btn-refresh");
var todayStrip   = document.getElementById("today-strip");
var tsContent    = document.getElementById("ts-content");
var calGrid      = document.getElementById("calendar-grid");
var detPanel     = document.getElementById("detail-panel");
var weekView     = document.getElementById("week-view");
var todayView    = document.getElementById("today-view");
var playoffsView = document.getElementById("playoffs-view");
var tablesView   = document.getElementById("tables-view");
var statusMsg    = document.getElementById("status-message");
var storylineFilters = document.getElementById("storyline-filters");

// ── Helpers ──────────────────────────────────────────────────────

function el(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt != null) n.textContent = txt;
    return n;
}

function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
function hide(n)  { n.classList.add("hidden"); }
function show(n)  { n.classList.remove("hidden"); }

function todayStr() { return new Date().toLocaleDateString("en-CA"); }

function isMobile() { return window.innerWidth <= MOBILE_BP; }

function fmtTime(iso) {
    return new Date(iso).toLocaleTimeString("en-US", {
        hour: "numeric", minute: "2-digit", hour12: true
    });
}

function fmtDateLong(dateStr) {
    var d = new Date(dateStr + "T12:00:00");
    return d.toLocaleDateString("en-US", {
        weekday: "long", month: "short", day: "numeric"
    });
}

function fmtDateShort(dateStr) {
    var d = new Date(dateStr + "T12:00:00");
    return d.toLocaleDateString("en-US", {
        weekday: "short", month: "short", day: "numeric"
    });
}

/** Create a team logo <img>, or null if no URL */
function logoImg(url, size) {
    if (!url) return null;
    var img = document.createElement("img");
    img.src = url;
    img.className = "team-logo";
    img.width = size || 20;
    img.height = size || 20;
    img.loading = "lazy";
    img.alt = "";
    img.onerror = function() { this.style.display = "none"; };
    return img;
}

/** Append a child node only if it's not null */
function appendIf(parent, child) {
    if (child) parent.appendChild(child);
}

function groupByDay(games) {
    var g = {};
    games.forEach(function(gm) {
        var k = new Date(gm.date).toLocaleDateString("en-CA");
        if (!g[k]) g[k] = [];
        g[k].push(gm);
    });
    return g;
}

/** All dates from the loaded range (for the month grid) */
function rangeDates() {
    if (!rangeInfo) return [];
    var out = [];
    var d = new Date(rangeInfo.start + "T12:00:00");
    var end = new Date(rangeInfo.end + "T12:00:00");
    while (d <= end) {
        out.push(d.toLocaleDateString("en-CA"));
        d.setDate(d.getDate() + 1);
    }
    return out;
}

/** Seven date strings starting at mobileWindowStart (mobile view) */
function mobileWindowDates() {
    if (!mobileWindowStart) return [];
    var dates = [];
    var d = new Date(mobileWindowStart + "T12:00:00");
    for (var i = 0; i < 7; i++) {
        dates.push(d.toLocaleDateString("en-CA"));
        d.setDate(d.getDate() + 1);
    }
    return dates;
}

/** Month that contains the window's midpoint (day 4 of 7) — this is
 *  the month we fetch so a single padded month fetch covers the window.
 *  In rare month-boundary cases (month ends Sun → Mon), 1–3 trailing
 *  days may render empty until the next arrow click shifts the midpoint
 *  into the new month. Accepted trade-off per project spec. */
function mobileWindowMidpointMonth() {
    var d = new Date(mobileWindowStart + "T12:00:00");
    d.setDate(d.getDate() + 3);
    return { year: d.getFullYear(), month: d.getMonth() + 1 };
}

/** Lazy init of the mobile window state. Runs on first mobile render
 *  and on resize from desktop → mobile when state hasn't been set.
 *  Returns true if currentYear/currentMonth shifted (caller may need
 *  to refetch). */
function initMobileWindowIfNeeded() {
    if (mobileWindowStart) return false;
    mobileWindowStart = todayStr();
    var mid = mobileWindowMidpointMonth();
    var changed = mid.year !== currentYear || mid.month !== currentMonth;
    currentYear = mid.year;
    currentMonth = mid.month;
    return changed;
}

function shiftMobileWindow(days) {
    var d = new Date(mobileWindowStart + "T12:00:00");
    d.setDate(d.getDate() + days);
    mobileWindowStart = d.toLocaleDateString("en-CA");

    var mid = mobileWindowMidpointMonth();
    if (mid.year !== currentYear || mid.month !== currentMonth) {
        // Window's midpoint crossed into a different month — refetch
        currentYear = mid.year;
        currentMonth = mid.month;
        loadSchedule();
    } else {
        updateNav();
        render();
    }
}

/** Format for the nav label on mobile:
 *    same month:   "Apr 23 – 29"
 *    crosses mo:   "Apr 27 – May 3"
 *    crosses yr:   "Dec 30 – Jan 5, 2027" */
function formatMobileWindowLabel() {
    var start = new Date(mobileWindowStart + "T12:00:00");
    var end = new Date(start);
    end.setDate(end.getDate() + 6);
    var sameMonth = start.getMonth() === end.getMonth() &&
                    start.getFullYear() === end.getFullYear();
    var sameYear = start.getFullYear() === end.getFullYear();
    var mShort = function(d) {
        return d.toLocaleDateString("en-US", { month: "short" });
    };
    if (sameMonth) {
        return mShort(start) + " " + start.getDate() +
               " – " + end.getDate();
    }
    if (sameYear) {
        return mShort(start) + " " + start.getDate() +
               " – " + mShort(end) + " " + end.getDate();
    }
    return mShort(start) + " " + start.getDate() +
           " – " + mShort(end) + " " + end.getDate() +
           ", " + end.getFullYear();
}

/** Look up a team's standings position from pre-fetched data */
function findTeamStanding(teamId) {
    if (!standingsData || !standingsData.length) return null;
    for (var i = 0; i < standingsData.length; i++) {
        var league = standingsData[i];
        for (var j = 0; j < league.groups.length; j++) {
            var group = league.groups[j];
            for (var k = 0; k < group.teams.length; k++) {
                if (group.teams[k].team.id === teamId) {
                    return {
                        league: league.name,
                        rank: group.teams[k].rank,
                        stats: group.teams[k].stats,
                        zone: group.teams[k].zone
                    };
                }
            }
        }
    }
    return null;
}

/** Human-readable countdown: "2h 14m", "35m", "3d 5h" */
function countdownText(isoDate) {
    var diff = new Date(isoDate).getTime() - Date.now();
    if (diff <= 0) return "Starting soon";
    var hours = Math.floor(diff / 3600000);
    var mins  = Math.floor((diff % 3600000) / 60000);
    if (hours > 24) {
        var days = Math.floor(hours / 24);
        return days + "d " + (hours % 24) + "h";
    }
    if (hours > 0) return hours + "h " + mins + "m";
    return mins + "m";
}

/** Convert number to ordinal: 1 → "1st", 2 → "2nd", etc. */
function ordinal(n) {
    var num = parseInt(n, 10);
    if (isNaN(num)) return n;
    var s = ["th", "st", "nd", "rd"];
    var v = num % 100;
    return num + (s[(v - 20) % 10] || s[v] || s[0]);
}

/** Build a detail row (label + value) for expanded cards */
function buildDetailRow(label, value) {
    var row = el("div", "gd-row");
    row.appendChild(el("span", "gd-label", label));
    row.appendChild(el("span", "gd-val", value));
    return row;
}

var MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
];
var DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// ── Events ───────────────────────────────────────────────────────

// Nav arrows: mobile shifts the 7-day window by ±7 days; desktop
// navigates whole months. Swipe-to-nav piggybacks on these clicks.
btnPrev.addEventListener("click", function() {
    if (isMobile()) {
        shiftMobileWindow(-7);
    } else {
        currentMonth--;
        if (currentMonth < 1) { currentMonth = 12; currentYear--; }
        selectedDate = null;
        loadSchedule();
    }
});

btnNext.addEventListener("click", function() {
    if (isMobile()) {
        shiftMobileWindow(+7);
    } else {
        currentMonth++;
        if (currentMonth > 12) { currentMonth = 1; currentYear++; }
        selectedDate = null;
        loadSchedule();
    }
});

btnRefresh.addEventListener("click", function() { loadSchedule(true); });

// Clicking the today strip jumps to the Today view
todayStrip.addEventListener("click", function() {
    var todayTab = document.querySelector('.tab[data-view="today"]');
    if (todayTab) todayTab.click();
});
todayStrip.addEventListener("keydown", function(e) {
    if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        todayStrip.click();
    }
});

document.querySelectorAll(".tab").forEach(function(t) {
    t.addEventListener("click", function() {
        document.querySelectorAll(".tab").forEach(function(x) {
            x.classList.remove("active");
            x.removeAttribute("aria-current");
        });
        t.classList.add("active");
        t.setAttribute("aria-current", "page");
        currentView = t.dataset.view;
        render();
    });
});

document.querySelectorAll(".pill").forEach(function(b) {
    b.addEventListener("click", function() {
        document.querySelectorAll(".pill").forEach(function(x) {
            x.classList.remove("active");
            x.setAttribute("aria-pressed", "false");
        });
        b.classList.add("active");
        b.setAttribute("aria-pressed", "true");
        currentSport = b.dataset.sport;
        render();
    });
});

// Re-render when crossing the mobile breakpoint
window.addEventListener("resize", function() {
    var mobile = isMobile();
    if (lastMobileState !== null && mobile !== lastMobileState) {
        render();
    }
    lastMobileState = mobile;
});

// ── Swipe-to-navigate months (mobile Calendar view) ─────────────
// Horizontal swipe on the calendar view triggers prev/next month, the
// same as tapping the nav arrows. Only active on mobile and only on
// the Calendar view so the Today / Playoffs / Tables views can scroll
// without triggering navigation.
(function attachSwipeNav() {
    var SWIPE_THRESHOLD_PX = 60;     // must travel at least this far
    var SWIPE_MAX_VERTICAL = 40;     // reject if it looks like a scroll
    var SWIPE_MAX_DURATION_MS = 500; // fling, not a drag

    var startX = 0, startY = 0, startT = 0, tracking = false;

    function onStart(e) {
        if (!isMobile() || currentView !== "week") return;
        var t = e.touches ? e.touches[0] : e;
        startX = t.clientX;
        startY = t.clientY;
        startT = Date.now();
        tracking = true;
    }
    function onEnd(e) {
        if (!tracking) return;
        tracking = false;
        var t = (e.changedTouches && e.changedTouches[0]) || e;
        var dx = t.clientX - startX;
        var dy = t.clientY - startY;
        var dt = Date.now() - startT;
        if (dt > SWIPE_MAX_DURATION_MS) return;
        if (Math.abs(dy) > SWIPE_MAX_VERTICAL) return;
        if (Math.abs(dx) < SWIPE_THRESHOLD_PX) return;
        if (dx < 0) btnNext.click();
        else        btnPrev.click();
    }

    // Attach to the week view (calendar area only).
    weekView.addEventListener("touchstart", onStart, { passive: true });
    weekView.addEventListener("touchend", onEnd, { passive: true });
})();

// ── Data ─────────────────────────────────────────────────────────

function loadSchedule(refresh) {
    clear(calGrid);
    clear(detPanel);
    clear(todayView);
    clear(playoffsView);
    clear(tablesView);
    if (refresh) standingsLoaded = false;
    statusMsg.textContent = "Loading\u2026";
    show(statusMsg);

    // Fetch month's games
    var monthStr = currentYear + "-" + String(currentMonth).padStart(2, "0");
    var url = "/api/schedule?month=" + monthStr;
    if (refresh) url += "&refresh=true";

    fetch(url).then(function(r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
    }).then(function(data) {
        allGames = data.games || [];
        rangeInfo = data.range;
        updateNav();
        hide(statusMsg);

        // Auto-select today if visible, otherwise first day with games
        var today = todayStr();
        var dates = rangeDates();
        if (dates.indexOf(today) >= 0) {
            selectedDate = today;
        } else {
            var gbd = groupByDay(allGames);
            var keys = Object.keys(gbd).sort();
            selectedDate = keys[0] || dates[0];
        }

        render();
        renderTodayStrip();
        updatePlayoffsTabBadge();
    }).catch(function(err) {
        hide(weekView);
        hide(todayView);
        clear(statusMsg);
        statusMsg.appendChild(el("div", null, "Failed to load schedule"));
        statusMsg.appendChild(el("div", "hint", err.message));
        show(statusMsg);
    });
}

/** Persistent banner summarising today across all views */
function renderTodayStrip() {
    if (!todayStrip || !tsContent) return;
    clear(tsContent);

    var today = todayStr();
    var gbd = groupByDay(allGames);
    var todayGames = gbd[today] || [];

    // Nothing today — still show the strip so the next-up game stays visible
    if (todayGames.length === 0) {
        var nextUp = findNextGame(allGames);
        if (!nextUp) {
            hide(todayStrip);
            return;
        }
        tsContent.appendChild(el("span", "ts-empty", "No games today"));
        tsContent.appendChild(el("span", "ts-sep", "\u00b7"));
        var nextLabel = el("span", "ts-next");
        nextLabel.appendChild(document.createTextNode("Next: "));
        var nb = el("b", null,
            nextUp.away_team.abbreviation + " @ " + nextUp.home_team.abbreviation);
        nextLabel.appendChild(nb);
        var nextDateStr = new Date(nextUp.date).toLocaleDateString("en-CA");
        nextLabel.appendChild(document.createTextNode(
            " \u00b7 " + fmtDateShort(nextDateStr) + " " + fmtTime(nextUp.date)));
        tsContent.appendChild(nextLabel);
        show(todayStrip);
        return;
    }

    var live = todayGames.filter(function(g) { return g.status === "in"; });
    var upcoming = todayGames.filter(function(g) { return g.status === "pre"; });
    upcoming.sort(function(a, b) { return a.date.localeCompare(b.date); });

    // Count + sport dots
    var count = el("span", "ts-count",
        todayGames.length + (todayGames.length === 1 ? " game today" : " games today"));
    tsContent.appendChild(count);

    var sportsSet = {};
    todayGames.forEach(function(g) { sportsSet[g.sport] = true; });
    var dots = el("span", "ts-dots");
    ["soccer", "basketball", "football"].forEach(function(sp) {
        if (sportsSet[sp]) dots.appendChild(el("span", "ts-dot " + sp));
    });
    tsContent.appendChild(dots);

    // Live indicator takes priority
    if (live.length > 0) {
        var liveEl = el("span", "ts-live",
            live.length + (live.length === 1 ? " live" : " live"));
        tsContent.appendChild(liveEl);
        var g = live[0];
        var liveInfo = el("span", "ts-next");
        liveInfo.appendChild(el("b", null,
            g.away_team.abbreviation + " " +
            (g.score ? g.score.away : "0") + "\u2013" +
            (g.score ? g.score.home : "0") + " " + g.home_team.abbreviation));
        tsContent.appendChild(liveInfo);
    } else if (upcoming.length > 0) {
        var next = upcoming[0];
        var upEl = el("span", "ts-next");
        upEl.appendChild(document.createTextNode("Next: "));
        upEl.appendChild(el("b", null,
            next.away_team.abbreviation + " @ " + next.home_team.abbreviation));
        upEl.appendChild(document.createTextNode(" at " + fmtTime(next.date)));
        tsContent.appendChild(upEl);
    } else {
        // All of today's games are completed
        tsContent.appendChild(el("span", "ts-next", "All games finished"));
    }

    show(todayStrip);
}

/** Pulse red dot on the Playoffs tab when a playoff game is live */
function updatePlayoffsTabBadge() {
    var tab = document.querySelector('.tab-playoffs');
    if (!tab) return;
    var hasLive = allGames.some(function(g) {
        return g.is_playoff && g.status === "in";
    });
    tab.classList.toggle("has-live", hasLive);
}

/** Fetch the active storylines and build the chip row once */
function loadStorylines() {
    fetch("/api/storylines").then(function(r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
    }).then(function(data) {
        storylinesData = data.storylines || [];
        renderStorylineFilters();
    }).catch(function() {
        // Non-critical — chip bar just won't appear
    });
}

/** Build the chip-row DOM (once per page load) */
function renderStorylineFilters() {
    if (!storylineFilters) return;
    clear(storylineFilters);
    if (!storylinesData.length) {
        hide(storylineFilters);
        return;
    }

    storylineFilters.appendChild(el("span", "sl-filters-label", "Stories"));

    storylinesData.forEach(function(sl) {
        var chip = el("button", "sl-chip", sl.label);
        chip.type = "button";
        chip.setAttribute("data-storyline-id", sl.id);
        chip.setAttribute("aria-pressed", "false");
        if (sl.description) chip.title = sl.description;
        chip.addEventListener("click", function() {
            // Click-again clears; only one active at a time
            activeStorylineId =
                activeStorylineId === sl.id ? null : sl.id;
            applyStorylineChipState();
            render();
        });
        storylineFilters.appendChild(chip);
    });

    updateStorylineFilterVisibility();
    applyStorylineChipState();
}

/** Sync chip "active" state from activeStorylineId */
function applyStorylineChipState() {
    if (!storylineFilters) return;
    var chips = storylineFilters.querySelectorAll(".sl-chip");
    chips.forEach(function(c) {
        var on = c.getAttribute("data-storyline-id") === activeStorylineId;
        c.classList.toggle("active", on);
        c.setAttribute("aria-pressed", on ? "true" : "false");
    });
}

/** Chip bar is scoped to the Calendar view only */
function updateStorylineFilterVisibility() {
    if (!storylineFilters) return;
    if (currentView === "week" && storylinesData.length > 0) {
        show(storylineFilters);
    } else {
        hide(storylineFilters);
    }
}

/** Eagerly load standings so expanded cards can show context */
function loadStandings() {
    fetch("/api/standings").then(function(r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
    }).then(function(data) {
        standingsData = data.leagues || [];
        titleRacesData = data.title_races || [];
        standingsLoaded = true;
    }).catch(function() {
        // Non-critical — standings just won't appear in card detail
    });
}

function updateNav() {
    if (isMobile() && mobileWindowStart) {
        monthLabel.textContent = formatMobileWindowLabel();
    } else {
        monthLabel.textContent = MONTH_NAMES[currentMonth] + " " + currentYear;
    }
    btnPrev.disabled = false;
    btnNext.disabled = false;
}

// ── Render dispatcher ────────────────────────────────────────────

function render() {
    stopCountdownTimer();
    updateStorylineFilterVisibility();

    // On mobile, lazily anchor the 7-day window at today and align
    // currentMonth to the midpoint's month. If that shifts the month,
    // trigger a refetch and bail — loadSchedule will call render() again.
    if (isMobile() && initMobileWindowIfNeeded()) {
        loadSchedule();
        return;
    }
    updateNav();

    var games = currentSport === "all"
        ? allGames
        : allGames.filter(function(g) { return g.sport === currentSport; });

    if (currentView === "week") {
        show(weekView);
        hide(todayView);
        hide(playoffsView);
        hide(tablesView);
        renderCalendar(games);
    } else if (currentView === "today") {
        hide(weekView);
        show(todayView);
        hide(playoffsView);
        hide(tablesView);
        renderToday(games);
    } else if (currentView === "playoffs") {
        hide(weekView);
        hide(todayView);
        show(playoffsView);
        hide(tablesView);
        renderPlayoffs(games);
    } else if (currentView === "tables") {
        hide(weekView);
        hide(todayView);
        hide(playoffsView);
        show(tablesView);
        loadAndRenderTables();
    }
}

// ═════════════════════════════════════════════════════════════════
// CALENDAR VIEW
// ═════════════════════════════════════════════════════════════════

function renderCalendar(games) {
    // Apply the active storyline filter (scoped to the Calendar view —
    // Today / Playoffs / Tables are rendered unfiltered).
    var filtered = games;
    if (activeStorylineId) {
        filtered = games.filter(function(g) {
            if (!g.storylines || !g.storylines.length) return false;
            for (var i = 0; i < g.storylines.length; i++) {
                if (g.storylines[i].id === activeStorylineId) return true;
            }
            return false;
        });
    }
    if (isMobile()) {
        renderMobileCalendar(filtered);
    } else {
        renderDesktopCalendar(filtered);
    }
}

/** Desktop: full month grid + detail panel below */
function renderDesktopCalendar(games) {
    clear(calGrid);
    show(detPanel);
    calGrid.className = "calendar-grid";

    var dates = rangeDates();
    var gbd = groupByDay(games);
    var today = todayStr();

    // Day-of-week headers
    DAY_NAMES.forEach(function(name) {
        calGrid.appendChild(el("div", "day-header", name));
    });

    // Day cells
    dates.forEach(function(dk) {
        var dg = gbd[dk] || [];
        var dateObj = new Date(dk + "T12:00:00");
        var dayNum = dateObj.getDate();
        var cellMonth = dateObj.getMonth() + 1;

        var cell = el("div", "day-cell");
        if (dk === today) cell.classList.add("is-today");
        if (dk === selectedDate) cell.classList.add("selected");
        if (dg.length > 0) cell.classList.add("has-games");
        if (cellMonth !== currentMonth) cell.classList.add("outside");

        cell.addEventListener("click", function() {
            selectedDate = dk;
            render();
        });

        // Date number
        cell.appendChild(el("div", "dc-num", String(dayNum)));

        // Game indicator dots (sport-colored, dimmed if finished)
        if (dg.length > 0) {
            var indicators = el("div", "dc-indicators");
            var maxDots = 5;
            for (var i = 0; i < Math.min(dg.length, maxDots); i++) {
                var dot = el("span", "dc-dot " + dg[i].sport);
                if (dg[i].status === "post") dot.classList.add("dimmed");
                indicators.appendChild(dot);
            }
            if (dg.length > maxDots) {
                indicators.appendChild(
                    el("span", "dc-dot-more", "+" + (dg.length - maxDots))
                );
            }
            cell.appendChild(indicators);
            cell.appendChild(el("div", "dc-count",
                dg.length + (dg.length === 1 ? " game" : " games")));
        }

        calGrid.appendChild(cell);
    });

    // On the first desktop render after page load, scroll the row
    // containing today to the top of the viewport so the user lands
    // on "now" instead of week 1 of the padded calendar. Skipped
    // when today is already in the first row (e.g., early in the
    // month) or not present in this month at all.
    if (!initialScrollDone) {
        initialScrollDone = true;
        // Defer one frame so the browser has a chance to lay out the
        // grid before we compute target positions.
        requestAnimationFrame(function() {
            var todayCell = calGrid.querySelector(".day-cell.is-today");
            var firstCell = calGrid.querySelector(".day-cell");
            if (!todayCell || !firstCell || todayCell === firstCell) return;
            var todayTop = todayCell.getBoundingClientRect().top;
            var firstTop = firstCell.getBoundingClientRect().top;
            // Same row → same y-offset. Skip if today is in row 1.
            if (todayTop - firstTop > 5) {
                todayCell.scrollIntoView({
                    block: "start", behavior: "auto",
                });
            }
        });
    }

    // Detail panel for the selected date
    renderDetail(games);
}

/** Mobile: 2-week vertical list with game cards inline */
function renderMobileCalendar(games) {
    clear(calGrid);
    hide(detPanel);
    calGrid.className = "mobile-calendar";

    var dates = mobileWindowDates();
    var gbd = groupByDay(games);
    var today = todayStr();

    dates.forEach(function(dk) {
        var dg = gbd[dk] || [];
        var dateObj = new Date(dk + "T12:00:00");

        var day = el("div", "mobile-day");
        if (dk === today) day.classList.add("is-today");

        // Day header
        var header = el("div", "mobile-day-header");
        var nameStr = dateObj.toLocaleDateString("en-US", {
            weekday: "short", month: "short", day: "numeric"
        });
        var nameEl = el("span", "mobile-day-name", nameStr);
        if (dk === today) {
            nameEl.appendChild(el("span", "mobile-today-badge", "Today"));
        }
        header.appendChild(nameEl);

        if (dg.length > 0) {
            header.appendChild(el("span", "mobile-day-count",
                dg.length + (dg.length === 1 ? " game" : " games")));
        }
        day.appendChild(header);

        // Game cards or "no games"
        if (dg.length === 0) {
            day.appendChild(el("div", "mobile-day-off", "No games"));
        } else {
            var gamesDiv = el("div", "mobile-day-games");
            dg.forEach(function(g) {
                gamesDiv.appendChild(buildCard(g));
            });
            day.appendChild(gamesDiv);
        }

        calGrid.appendChild(day);
    });
}

// ═════════════════════════════════════════════════════════════════
// DETAIL PANEL (desktop, below calendar grid)
// ═════════════════════════════════════════════════════════════════

function renderDetail(games) {
    clear(detPanel);
    if (!selectedDate) {
        detPanel.classList.add("empty");
        return;
    }
    detPanel.classList.remove("empty");

    var gbd = groupByDay(games);
    var dg = gbd[selectedDate] || [];

    // Header
    var head = el("div", "dp-head");
    var title = el("span", "dp-date", fmtDateLong(selectedDate).toUpperCase());
    if (selectedDate === todayStr()) {
        title.appendChild(el("span", "dp-today", "Today"));
    }
    head.appendChild(title);
    head.appendChild(el("span", "dp-count",
        dg.length + (dg.length === 1 ? " game" : " games")));
    detPanel.appendChild(head);

    // Cards
    var container = el("div", "dp-games");
    if (dg.length === 0) {
        container.appendChild(el("div", "dp-empty",
            "Nothing scheduled \u2014 enjoy the downtime."));
    } else {
        dg.forEach(function(g) {
            container.appendChild(buildCard(g));
        });
    }
    detPanel.appendChild(container);
}

// ═════════════════════════════════════════════════════════════════
// TODAY VIEW — Command Center
// ═════════════════════════════════════════════════════════════════

function renderToday(games) {
    clear(todayView);
    show(todayView);

    var today = todayStr();
    var gbd = groupByDay(games);
    var todayGames = gbd[today] || [];

    // Header
    var head = el("div", "today-head");
    head.appendChild(el("span", "th-dot"));
    head.appendChild(el("span", "th-text",
        fmtDateLong(today).toUpperCase()));
    todayView.appendChild(head);

    // No games today — show next upcoming game
    if (todayGames.length === 0) {
        var nextUp = findNextGame(games);
        var empty = el("div", "today-empty-state");
        empty.appendChild(el("div", "today-empty-msg", "No games today"));

        if (nextUp) {
            var nextBox = el("div", "today-next-up");
            nextBox.appendChild(el("div", "today-next-label", "Next Up"));

            var matchup = el("div", "today-next-game");
            appendIf(matchup, logoImg(nextUp.away_team.logo, 22));
            matchup.appendChild(
                document.createTextNode(" " + nextUp.away_team.name + " "));
            matchup.appendChild(el("span", "vs", " @ "));
            matchup.appendChild(
                document.createTextNode(" " + nextUp.home_team.name + " "));
            appendIf(matchup, logoImg(nextUp.home_team.logo, 22));
            nextBox.appendChild(matchup);

            var nextDateStr = new Date(nextUp.date).toLocaleDateString("en-CA");
            nextBox.appendChild(el("div", "today-next-meta",
                nextUp.league_name + " \u00b7 " +
                fmtDateShort(nextDateStr) + " \u00b7 " +
                fmtTime(nextUp.date)));
            empty.appendChild(nextBox);
        }

        todayView.appendChild(empty);
        return;
    }

    // Partition today's games into live / upcoming / completed
    var live = [], upcoming = [], completed = [];
    todayGames.forEach(function(g) {
        if (g.status === "in") live.push(g);
        else if (g.status === "post") completed.push(g);
        else upcoming.push(g);
    });

    // Sort upcoming by kickoff time
    upcoming.sort(function(a, b) { return a.date.localeCompare(b.date); });

    // ── LIVE NOW ──
    if (live.length > 0) {
        var liveSection = el("div", "today-section");
        var liveLabel = el("div", "today-section-label");
        liveLabel.appendChild(el("span", "live-dot"));
        liveLabel.appendChild(document.createTextNode("Live Now"));
        liveSection.appendChild(liveLabel);
        live.forEach(function(g) {
            liveSection.appendChild(buildCard(g));
        });
        todayView.appendChild(liveSection);
    }

    // ── COMING UP ──
    if (upcoming.length > 0) {
        var upSection = el("div", "today-section");
        upSection.appendChild(el("div", "today-section-label", "Coming Up"));
        upcoming.forEach(function(g) {
            var card = buildCard(g);
            // Insert countdown before the meta row
            var cdEl = el("div", "card-countdown",
                "\u23f1 " + countdownText(g.date));
            cdEl.setAttribute("data-kickoff", g.date);
            var meta = card.querySelector(".gc-meta");
            if (meta) card.insertBefore(cdEl, meta);
            upSection.appendChild(card);
        });
        todayView.appendChild(upSection);
    }

    // ── COMPLETED ──
    if (completed.length > 0) {
        var compSection = el("div", "today-section");
        compSection.appendChild(el("div", "today-section-label", "Completed"));
        completed.forEach(function(g) {
            compSection.appendChild(buildCard(g));
        });
        todayView.appendChild(compSection);
    }

    // Start countdown refresh timer
    startCountdownTimer();
}

/** Find the next pre-game across all loaded data */
function findNextGame(games) {
    var nowISO = new Date().toISOString();
    var future = games.filter(function(g) {
        return g.status === "pre" && g.date > nowISO;
    });
    future.sort(function(a, b) { return a.date.localeCompare(b.date); });
    return future[0] || null;
}

function startCountdownTimer() {
    stopCountdownTimer();
    countdownTimer = setInterval(function() {
        document.querySelectorAll(".card-countdown[data-kickoff]")
            .forEach(function(cdEl) {
                cdEl.textContent = "\u23f1 " +
                    countdownText(cdEl.getAttribute("data-kickoff"));
            });
    }, 60000); // update every minute
}

function stopCountdownTimer() {
    if (countdownTimer) {
        clearInterval(countdownTimer);
        countdownTimer = null;
    }
}

// ── User Data Persistence ────────────────────────────────────────

function toggleWatched(gameId, watched, btn, card) {
    fetch("/api/games/" + gameId + "/watched", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ watched: watched })
    });
    if (watched) {
        btn.classList.add("is-watched");
        btn.textContent = "\u2713 Watched";
        card.classList.add("game-card--watched");
    } else {
        btn.classList.remove("is-watched");
        btn.textContent = "Watched?";
        card.classList.remove("game-card--watched");
    }
}

function saveNotes(gameId, notes) {
    fetch("/api/games/" + gameId + "/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: notes })
    });
}

// ═════════════════════════════════════════════════════════════════
// GAME CARD BUILDER
// ═════════════════════════════════════════════════════════════════

function buildCard(g) {
    var card = el("div", "game-card sport-" + g.sport);

    // Dim finished games, highlight if user watched
    if (g.status === "post") {
        card.classList.add("game-card--post");
        if (g.watched) card.classList.add("game-card--watched");
    }

    // Click to expand/collapse detail
    card.addEventListener("click", function() {
        card.classList.toggle("expanded");
    });

    if (g.status === "post" || g.status === "in") {
        // ── Scoreboard layout ────────────────────────────────
        var sb = el("div", "gc-scoreboard");

        var awayTeam = el("span", "sb-team away");
        appendIf(awayTeam, logoImg(g.away_team.logo, 22));
        awayTeam.appendChild(
            document.createTextNode(" " + g.away_team.abbreviation));
        sb.appendChild(awayTeam);

        var score = el("span", "sb-score");
        score.appendChild(
            document.createTextNode(g.score ? g.score.away : "0"));
        score.appendChild(el("span", "sb-dash", "\u2013"));
        score.appendChild(
            document.createTextNode(g.score ? g.score.home : "0"));
        sb.appendChild(score);

        var homeTeam = el("span", "sb-team home");
        homeTeam.appendChild(
            document.createTextNode(g.home_team.abbreviation + " "));
        appendIf(homeTeam, logoImg(g.home_team.logo, 22));
        sb.appendChild(homeTeam);
        card.appendChild(sb);

        // Status line
        if (g.status === "in") {
            card.appendChild(el("div", "sb-status live", "Live"));
        } else {
            card.appendChild(el("div", "sb-status final", "Full Time"));
        }

        // Full team names below score
        var names = el("div", "gc-meta");
        names.appendChild(el("span", "gc-league",
            g.away_team.name + "  vs  " + g.home_team.name));
        card.appendChild(names);

    } else {
        // ── Upcoming layout ──────────────────────────────────
        var main = el("div", "gc-main");

        var info = el("div", null);
        var matchup = el("div", "gc-matchup");
        appendIf(matchup, logoImg(g.away_team.logo, 18));
        matchup.appendChild(
            document.createTextNode(" " + g.away_team.name));
        matchup.appendChild(el("span", "vs", " @ "));
        matchup.appendChild(
            document.createTextNode(g.home_team.name + " "));
        appendIf(matchup, logoImg(g.home_team.logo, 18));
        info.appendChild(matchup);

        // Team records (if available from ESPN)
        if (g.away_team.record || g.home_team.record) {
            var recLine = el("div", "gc-records");
            if (g.away_team.record) {
                recLine.appendChild(el("span", null,
                    g.away_team.abbreviation +
                    " (" + g.away_team.record + ")"));
            }
            if (g.away_team.record && g.home_team.record) {
                recLine.appendChild(el("span", "gc-rec-sep", " \u00b7 "));
            }
            if (g.home_team.record) {
                recLine.appendChild(el("span", null,
                    g.home_team.abbreviation +
                    " (" + g.home_team.record + ")"));
            }
            info.appendChild(recLine);
        }

        // Broadcast channels (prominent for upcoming games)
        if (g.broadcasts && g.broadcasts.length) {
            info.appendChild(el("div", "gc-broadcast",
                g.broadcasts.join(", ")));
        }

        main.appendChild(info);

        // Kickoff time
        var td = el("div", "gc-time");
        td.appendChild(el("div", "t", fmtTime(g.date)));
        main.appendChild(td);

        card.appendChild(main);
    }

    // ── Meta row (all statuses) ──────────────────────────────
    var meta = el("div", "gc-meta");

    var tierCls = (g.tier || "notable").replace(/_/g, "-");
    var tierTxt = (g.tier || "notable").replace(/_/g, " ");
    meta.appendChild(el("span", "tier " + tierCls, tierTxt));

    // Post-Season tag — separate from tier, stacks next to it
    if (g.is_playoff) {
        meta.appendChild(el("span", "tier post-season", "post-season"));
    }

    // Series context (NBA series state, UCL leg + aggregate).
    // Muted italic pill — contextual info, not a primary tag.
    if (g.series_summary) {
        meta.appendChild(el("span", "gc-series", g.series_summary));
    }

    // Storyline pills — gold-outlined, cap 3 visible + overflow counter
    if (g.storylines && g.storylines.length) {
        var maxPills = 3;
        var shown = g.storylines.slice(0, maxPills);
        shown.forEach(function(sl) {
            var pill = el("span", "sl-pill", sl.label);
            pill.title = sl.label;
            meta.appendChild(pill);
        });
        var overflow = g.storylines.length - maxPills;
        if (overflow > 0) {
            var moreLabels = g.storylines.slice(maxPills)
                .map(function(s) { return s.label; }).join(", ");
            var more = el("span", "sl-pill more", "+" + overflow);
            more.title = moreLabels;
            meta.appendChild(more);
        }
    }

    meta.appendChild(el("span", "gc-league", g.league_name));
    meta.appendChild(el("span", "gc-sep", "\u00b7"));

    var availCls = (g.availability || "can_watch").replace(/_/g, "-");
    var availTxt = (g.availability || "can_watch").replace(/_/g, " ");
    var avail = el("span", "gc-avail " + availCls);
    avail.appendChild(el("span", "gc-avail-dot"));
    avail.appendChild(document.createTextNode(availTxt));
    meta.appendChild(avail);

    // Broadcast channels (for finished/live games in meta row)
    if (g.status !== "pre" && g.broadcasts && g.broadcasts.length) {
        meta.appendChild(el("span", "gc-sep", "\u00b7"));
        meta.appendChild(el("span", "gc-broadcast",
            g.broadcasts.join(", ")));
    }

    // Watched toggle (post-game only)
    if (g.status === "post") {
        var watchedBtn = el("span", "gc-watched",
            g.watched ? "\u2713 Watched" : "Watched?");
        if (g.watched) watchedBtn.classList.add("is-watched");
        watchedBtn.addEventListener("click", function(e) {
            e.stopPropagation();
            var nowWatched = !watchedBtn.classList.contains("is-watched");
            toggleWatched(g.id, nowWatched, watchedBtn, card);
        });
        meta.appendChild(watchedBtn);
    }

    card.appendChild(meta);

    // ── Expandable detail ────────────────────────────────────
    var detail = el("div", "gc-detail");
    var inner = el("div", "gc-detail-inner");

    if (g.venue) {
        inner.appendChild(buildDetailRow("Venue", g.venue));
    }

    if (g.broadcasts && g.broadcasts.length) {
        inner.appendChild(buildDetailRow("Broadcast",
            g.broadcasts.join(", ")));
    }

    if (g.nfl_slot) {
        inner.appendChild(buildDetailRow("Slot", g.nfl_slot));
    }

    // Series context — NBA series breakdown, or UCL first-leg score.
    // First-leg-only soccer games get no row here (compact pill is enough).
    if (g.series_detail) {
        var sd = g.series_detail;
        if (sd.sport === "basketball" && sd.teams && sd.teams.length === 2) {
            var t1 = sd.teams[0];
            var t2 = sd.teams[1];
            var seriesVal = t1.abbr + " " + t1.wins +
                            "  ·  " + t2.abbr + " " + t2.wins;
            if (sd.best_of) {
                seriesVal += "  (Best of " + sd.best_of + ")";
            }
            inner.appendChild(buildDetailRow("Series", seriesVal));
        } else if (sd.sport === "soccer" && sd.leg === 2 && sd.first_leg) {
            var fl = sd.first_leg;
            var flVal = fl.home_abbr + " " + fl.home_score +
                        "–" + fl.away_score + " " + fl.away_abbr;
            if (fl.date) {
                var flDate = new Date(fl.date).toLocaleDateString("en-US", {
                    month: "short", day: "numeric"
                });
                flVal += "  ·  " + flDate;
            }
            inner.appendChild(buildDetailRow("First Leg", flVal));
        }
    }

    if (g.notes) {
        var notesRow = buildDetailRow("Notes", g.notes);
        notesRow.querySelector(".gd-val").classList.add("accent");
        inner.appendChild(notesRow);
    }

    // Standings context (from pre-fetched standings data)
    var homeStanding = findTeamStanding(g.home_team.id);
    var awayStanding = findTeamStanding(g.away_team.id);

    if (homeStanding || awayStanding) {
        var parts = [];
        if (awayStanding) {
            parts.push(g.away_team.abbreviation + ": " +
                ordinal(awayStanding.rank) + " in " +
                awayStanding.league);
        }
        if (homeStanding) {
            parts.push(g.home_team.abbreviation + ": " +
                ordinal(homeStanding.rank) + " in " +
                homeStanding.league);
        }
        inner.appendChild(
            buildDetailRow("Standings", parts.join("  \u00b7  ")));
    }

    // Season type context
    if (g.season_type === 3) {
        inner.appendChild(buildDetailRow("Round", "Postseason"));
    } else if (g.season_type === 5) {
        inner.appendChild(buildDetailRow("Round", "Play-In Tournament"));
    }

    // Notes textarea (auto-saves on blur)
    var notesRow = el("div", "gd-notes-row");
    notesRow.appendChild(el("span", "gd-label", "Your Notes"));
    var notesArea = document.createElement("textarea");
    notesArea.className = "gc-notes";
    notesArea.placeholder = "Add notes about this game\u2026";
    notesArea.value = g.user_notes || "";
    notesArea.addEventListener("click", function(e) {
        e.stopPropagation();
    });
    notesArea.addEventListener("blur", function() {
        saveNotes(g.id, notesArea.value);
    });
    notesRow.appendChild(notesArea);
    inner.appendChild(notesRow);

    detail.appendChild(inner);
    card.appendChild(detail);

    return card;
}

// ═════════════════════════════════════════════════════════════════
// PLAYOFFS VIEW — knockout rounds, cup finals, postseason
// ═════════════════════════════════════════════════════════════════

function renderPlayoffs(games) {
    clear(playoffsView);

    var playoffGames = games.filter(function(g) { return g.is_playoff; });

    // Header
    var head = el("div", "playoffs-head");
    head.appendChild(el("span", "ph-title", "Playoffs & Finals"));
    head.appendChild(el("span", "ph-count",
        playoffGames.length +
        (playoffGames.length === 1 ? " game" : " games") +
        " this month"));
    playoffsView.appendChild(head);

    if (playoffGames.length === 0) {
        playoffsView.appendChild(el("div", "po-empty",
            "No playoff or knockout games in this month. " +
            "Browse another month with the arrows above."));
        return;
    }

    // Partition by status
    var live = [], upcoming = [], completed = [];
    playoffGames.forEach(function(g) {
        if (g.status === "in") live.push(g);
        else if (g.status === "post") completed.push(g);
        else upcoming.push(g);
    });

    // Live now — flat list (always visible, it's happening right now)
    if (live.length > 0) {
        var liveSection = el("div", "po-section");
        var liveLabel = el("div", "po-section-label live");
        liveLabel.appendChild(el("span", "po-live-dot"));
        liveLabel.appendChild(document.createTextNode("Live Now"));
        liveSection.appendChild(liveLabel);
        var liveList = el("div", "po-games");
        live.forEach(function(g) { liveList.appendChild(buildCard(g)); });
        liveSection.appendChild(liveList);
        playoffsView.appendChild(liveSection);
    }

    // Upcoming — collapsible by date; today + tomorrow auto-expanded
    if (upcoming.length > 0) {
        var upSection = el("div", "po-section");
        upSection.appendChild(el("div", "po-section-label", "Upcoming"));
        buildPlayoffDateGroups(upcoming, upSection, "upcoming");
        playoffsView.appendChild(upSection);
    }

    // Recent results — collapsible by date; only the most recent day open
    if (completed.length > 0) {
        var compSection = el("div", "po-section");
        compSection.appendChild(el("div", "po-section-label", "Recent Results"));
        buildPlayoffDateGroups(completed, compSection, "recent");
        playoffsView.appendChild(compSection);
    }
}

/**
 * Group playoff games by calendar day and append one collapsible
 * section per date to `container`.
 *
 * mode="upcoming": dates ascending; Today + Tomorrow auto-expand.
 * mode="recent":   dates descending; only the most recent day expands.
 */
function buildPlayoffDateGroups(games, container, mode) {
    var today = todayStr();
    var tomorrowDate = new Date();
    tomorrowDate.setDate(tomorrowDate.getDate() + 1);
    var tomorrow = tomorrowDate.toLocaleDateString("en-CA");

    // Group by local calendar date
    var byDate = {};
    var dates = [];
    games.forEach(function(g) {
        var k = new Date(g.date).toLocaleDateString("en-CA");
        if (!byDate[k]) {
            byDate[k] = [];
            dates.push(k);
        }
        byDate[k].push(g);
    });

    dates.sort(function(a, b) {
        return mode === "recent" ? b.localeCompare(a) : a.localeCompare(b);
    });

    dates.forEach(function(dk, idx) {
        var dayGames = byDate[dk];
        dayGames.sort(function(a, b) { return a.date.localeCompare(b.date); });

        var isToday = dk === today;
        var isTomorrow = dk === tomorrow;
        var openByDefault = (mode === "upcoming")
            ? (isToday || isTomorrow)
            : (idx === 0);

        var group = el("div", "po-date-group" + (openByDefault ? " open" : ""));

        var dhead = el("div", "po-date-head");
        var caret = el("span", "po-caret", openByDefault ? "\u25BE" : "\u25B8");
        dhead.appendChild(caret);

        var dateObj = new Date(dk + "T12:00:00");
        var dateLabel = dateObj.toLocaleDateString("en-US", {
            weekday: "long", month: "short", day: "numeric"
        });
        var dLabel = el("span", "po-date-label");
        dLabel.appendChild(document.createTextNode(dateLabel));
        if (isToday) {
            dLabel.appendChild(el("span", "po-date-badge today", "Today"));
        } else if (isTomorrow) {
            dLabel.appendChild(el("span", "po-date-badge tomorrow", "Tomorrow"));
        }
        dhead.appendChild(dLabel);

        // Compact sport summary (e.g. "5 NBA · 1 FA Cup") so a collapsed
        // date still tells you what's on without expanding.
        var byComp = {};
        dayGames.forEach(function(g) {
            var name = g.league_name || "Other";
            byComp[name] = (byComp[name] || 0) + 1;
        });
        var summary = Object.keys(byComp).map(function(name) {
            return byComp[name] + " " + name;
        }).join(" \u00b7 ");
        dhead.appendChild(el("span", "po-date-summary", summary));
        dhead.appendChild(el("span", "po-date-count",
            dayGames.length + (dayGames.length === 1 ? " game" : " games")));

        dhead.addEventListener("click", function() {
            var isOpen = group.classList.toggle("open");
            caret.textContent = isOpen ? "\u25BE" : "\u25B8";
        });
        group.appendChild(dhead);

        var body = el("div", "po-date-body");
        var list = el("div", "po-games");
        dayGames.forEach(function(g) { list.appendChild(buildCard(g)); });
        body.appendChild(list);
        group.appendChild(body);

        container.appendChild(group);
    });
}

// ═════════════════════════════════════════════════════════════════
// STANDINGS / TABLES
// ═════════════════════════════════════════════════════════════════

function loadAndRenderTables() {
    if (standingsLoaded && standingsData.length) {
        renderTables(standingsData);
        return;
    }

    clear(tablesView);
    tablesView.appendChild(
        el("div", "status-message", "Loading standings\u2026"));

    fetch("/api/standings").then(function(r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
    }).then(function(data) {
        standingsData = data.leagues || [];
        titleRacesData = data.title_races || [];
        standingsLoaded = true;
        renderTables(standingsData);
    }).catch(function(err) {
        clear(tablesView);
        tablesView.appendChild(el("div", "status-message",
            "Failed to load standings: " + err.message));
    });
}

function renderTables(leagues) {
    clear(tablesView);

    // Title race widgets first
    titleRacesData.forEach(function(race) {
        if (currentSport === "all" || currentSport === "soccer") {
            tablesView.appendChild(buildTitleRace(race));
        }
    });

    var filtered = leagues;
    if (currentSport !== "all") {
        filtered = leagues.filter(function(lg) {
            return lg.sport === currentSport;
        });
    }

    if (filtered.length === 0 && titleRacesData.length === 0) {
        tablesView.appendChild(
            el("div", "status-message", "No standings for this sport."));
        return;
    }

    filtered.forEach(function(league) {
        tablesView.appendChild(buildLeagueSection(league));
    });
}

// ── Title Race Widget ────────────────────────────────────────────

function buildTitleRace(race) {
    var widget = el("div", "race-widget");

    // Header
    var head = el("div", "race-head");
    head.appendChild(el("span", "race-label", race.label));
    var gapText = race.gap + " point" + (race.gap !== 1 ? "s" : "");
    if (race.games_in_hand > 0) {
        gapText += " \u00b7 " + race.contenders[1].team.name + " have " +
            race.games_in_hand +
            " game" + (race.games_in_hand !== 1 ? "s" : "") + " in hand";
    } else if (race.games_in_hand < 0) {
        gapText += " \u00b7 " + race.contenders[0].team.name + " have " +
            Math.abs(race.games_in_hand) +
            " game" + (Math.abs(race.games_in_hand) !== 1 ? "s" : "") +
            " in hand";
    }
    head.appendChild(el("span", "race-gap", gapText));
    widget.appendChild(head);

    // Contender rows
    var body = el("div", "race-body");
    race.contenders.forEach(function(c, idx) {
        var row = el("div",
            "race-row" + (idx === 0 ? " race-leader" : ""));

        // Rank + logo + team name
        var team = el("div", "race-team");
        team.appendChild(el("span", "race-rank", c.rank + "."));
        appendIf(team, logoImg(c.team.logo, 22));
        team.appendChild(el("span", "race-name", c.team.name));
        row.appendChild(team);

        // Stats
        var stats = el("div", "race-stats");
        var statItems = [
            { val: c.pts, label: "Pts" },
            { val: c.gp, label: "GP" },
            { val: c.remaining, label: "Left" },
            { val: c.max_pts, label: "Max" },
            { val: c.ppg, label: "PPG" }
        ];
        statItems.forEach(function(s) {
            var box = el("div", "race-stat");
            box.appendChild(
                el("span", "race-stat-val", String(s.val)));
            box.appendChild(
                el("span", "race-stat-label", s.label));
            stats.appendChild(box);
        });
        row.appendChild(stats);

        // Upcoming fixtures
        if (c.upcoming && c.upcoming.length > 0) {
            var fixtures = el("div", "race-fixtures");
            fixtures.appendChild(
                el("span", "race-fix-label", "Next:"));
            c.upcoming.forEach(function(f) {
                var fix = el("span", "race-fix");
                var prefix = f.home ? "vs " : "@ ";
                fix.textContent = prefix + f.opponent;
                fix.title = (f.home ? "Home vs " : "Away at ") +
                    f.opponent_name;
                fixtures.appendChild(fix);
            });
            row.appendChild(fixtures);
        }

        body.appendChild(row);
    });

    widget.appendChild(body);
    return widget;
}

function buildLeagueSection(league) {
    var section = el("div", "tbl-section");

    // Clickable header
    var head = el("div", "tbl-section-head");
    head.appendChild(el("span", "tbl-league-name", league.name));
    head.appendChild(el("span", "tbl-toggle", "\u25BE"));
    head.addEventListener("click", function() {
        section.classList.toggle("collapsed");
    });
    section.appendChild(head);

    // Body: groups
    var body = el("div", "tbl-section-body");

    league.groups.forEach(function(group) {
        if (league.groups.length > 1) {
            body.appendChild(el("div", "tbl-group-name", group.name));
        }

        // Wrap each table so it can scroll horizontally on narrow
        // screens without forcing the page to scroll sideways.
        var scroll = el("div", "tbl-scroll");
        if (league.sport === "soccer") {
            scroll.appendChild(buildSoccerTable(group, league.id));
        } else {
            scroll.appendChild(buildNbaTable(group));
        }
        body.appendChild(scroll);
    });

    // Zone legend
    if (league.sport === "soccer") {
        body.appendChild(buildSoccerLegend(league.id));
    } else {
        body.appendChild(buildNbaLegend());
    }

    section.appendChild(body);
    return section;
}

// ── Soccer standings table ───────────────────────────────────────

function buildSoccerTable(group, leagueId) {
    var table = el("table", "standings-table");

    var thead = el("thead");
    var hrow = el("tr");
    ["#", "Team", "GP", "W", "D", "L", "GF", "GA", "GD", "Pts"]
        .forEach(function(col, i) {
            var th = el("th", null, col);
            if (i >= 6 && i <= 8) th.classList.add("hide-mobile");
            hrow.appendChild(th);
        });
    thead.appendChild(hrow);
    table.appendChild(thead);

    var tbody = el("tbody");
    group.teams.forEach(function(entry) {
        var tr = el("tr");
        if (entry.is_watched) tr.classList.add("watched");
        if (entry.is_top6 && !entry.is_watched) tr.classList.add("top6");

        // Rank with zone color
        var rankTd = el("td", null, entry.rank);
        var zoneClass = getZoneClass(entry.zone);
        if (zoneClass) rankTd.classList.add(zoneClass);
        tr.appendChild(rankTd);

        // Team name with logo
        var nameTd = el("td");
        appendIf(nameTd, logoImg(entry.team.logo, 16));
        nameTd.appendChild(
            document.createTextNode(" " + entry.team.name));
        tr.appendChild(nameTd);

        var s = entry.stats;
        tr.appendChild(el("td", null, s.gp));
        tr.appendChild(el("td", null, s.w));
        tr.appendChild(el("td", null, s.d));
        tr.appendChild(el("td", null, s.l));
        tr.appendChild(el("td", "hide-mobile", s.gf));
        tr.appendChild(el("td", "hide-mobile", s.ga));
        tr.appendChild(el("td", "hide-mobile", s.gd));
        tr.appendChild(el("td", "pts-col", s.pts));

        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
}

function getZoneClass(zone) {
    if (!zone) return "";
    var z = zone.toLowerCase();
    if (z.indexOf("champions league") >= 0) return "zone-ucl";
    if (z.indexOf("europa league") >= 0) return "zone-uel";
    if (z.indexOf("conference league") >= 0) return "zone-uecl";
    if (z.indexOf("relegation") >= 0) return "zone-rel";
    if (z.indexOf("round of 16") >= 0 ||
        z.indexOf("qualifies") >= 0) return "zone-ucl";
    if (z.indexOf("knockout") >= 0 &&
        z.indexOf("seeded") >= 0) return "zone-uel";
    if (z.indexOf("knockout") >= 0 &&
        z.indexOf("unseeded") >= 0) return "zone-uecl";
    if (z.indexOf("eliminated") >= 0) return "zone-rel";
    return "";
}

function buildSoccerLegend(leagueId) {
    var legend = el("div", "tbl-zone-legend");

    if (leagueId === "uefa.champions") {
        addLegendItem(legend, "var(--soccer)", "Auto Round of 16");
        addLegendItem(legend, "var(--basketball)",
            "Knockout Playoffs (Seeded)");
        addLegendItem(legend, "#58a6ff",
            "Knockout Playoffs (Unseeded)");
        addLegendItem(legend, "var(--must-watch)", "Eliminated");
    } else {
        addLegendItem(legend, "var(--soccer)", "Champions League");
        addLegendItem(legend, "var(--basketball)", "Europa League");
        addLegendItem(legend, "#58a6ff", "Conference League");
        addLegendItem(legend, "var(--must-watch)", "Relegation");
    }

    return legend;
}

function addLegendItem(container, color, label) {
    var item = el("span", "tbl-zone-legend-item");
    var bar = el("span", "zl-bar");
    bar.style.background = color;
    item.appendChild(bar);
    item.appendChild(document.createTextNode(label));
    container.appendChild(item);
}

// ── NBA standings table ──────────────────────────────────────────

function buildNbaTable(group) {
    var table = el("table", "standings-table");

    var thead = el("thead");
    var hrow = el("tr");
    ["#", "Team", "W", "L", "Pct", "GB", "Strk", "L10"]
        .forEach(function(col, i) {
            var th = el("th", null, col);
            if (i >= 6) th.classList.add("hide-mobile");
            hrow.appendChild(th);
        });
    thead.appendChild(hrow);
    table.appendChild(thead);

    var tbody = el("tbody");
    group.teams.forEach(function(entry) {
        var tr = el("tr");
        if (entry.is_watched) tr.classList.add("watched");

        // Rank with playoff/play-in zone
        var rankTd = el("td", null, entry.rank);
        var seed = parseInt(entry.rank, 10);
        if (seed <= 6) {
            rankTd.classList.add("zone-playoff");
        } else if (seed <= 10) {
            rankTd.classList.add("zone-playin");
        }
        if (entry.clincher === "e") {
            rankTd.classList.add("zone-elim");
        }
        tr.appendChild(rankTd);

        // Team name with logo + clincher badge
        var nameTd = el("td");
        appendIf(nameTd, logoImg(entry.team.logo, 16));
        nameTd.appendChild(
            document.createTextNode(" " + entry.team.name));
        if (entry.clincher) {
            var badge = el("span",
                "clinch clinch-" + entry.clincher, entry.clincher);
            badge.title = entry.clinch_label;
            nameTd.appendChild(badge);
        }
        tr.appendChild(nameTd);

        var s = entry.stats;
        tr.appendChild(el("td", null, s.w));
        tr.appendChild(el("td", null, s.l));
        tr.appendChild(el("td", "pct-col", s.pct));
        tr.appendChild(el("td", null, s.gb || "-"));

        // Streak with color
        var strkTd = el("td", "hide-mobile");
        if (s.streak) {
            var strkSpan = el("span", null, s.streak);
            if (s.streak.charAt(0) === "W") strkSpan.className = "streak-w";
            if (s.streak.charAt(0) === "L") strkSpan.className = "streak-l";
            strkTd.appendChild(strkSpan);
        }
        tr.appendChild(strkTd);

        tr.appendChild(el("td", "hide-mobile", s.l10));

        // Boundary lines between playoff/play-in/lottery
        if (seed === 6 || seed === 10) {
            tr.style.borderBottom = "2px solid var(--border-hl)";
        }

        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
}

function buildNbaLegend() {
    var legend = el("div", "tbl-zone-legend");
    addLegendItem(legend, "var(--soccer)", "Playoff (1-6)");
    addLegendItem(legend, "var(--notable)", "Play-In (7-10)");
    addLegendItem(legend, "var(--must-watch)", "Eliminated");

    var sep = el("span", "lsep");
    legend.appendChild(sep);
    ["z = #1 seed", "y = div champ", "x = playoff",
     "pb = play-in", "e = eliminated"].forEach(function(txt) {
        legend.appendChild(el("span", null, txt));
    });

    return legend;
}

// ── Init ─────────────────────────────────────────────────────────
// On mobile, anchor the 7-day window at today BEFORE the initial fetch
// so currentMonth matches the window's midpoint on the first round-trip
// (avoids a wasted fetch when today is near a month boundary).
if (isMobile()) initMobileWindowIfNeeded();
loadSchedule();
loadStandings();
loadStorylines();
