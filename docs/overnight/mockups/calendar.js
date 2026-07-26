/* ══════════════════════════════════════════════════════════════════
   MOCKUP RENDERER — phone month calendar (overnight lane, 2026-07-26)

   Inert. Loaded only by the two mockup pages in this folder; the app
   never sees it. It renders REAL captured ESPN data (data.js) in the
   app's real design language so the two layouts can be compared on a
   phone without touching shipped code.

   MODE is set by each page before this file runs:
     "replace" — the month grid IS the phone calendar. Tap a day and
                 that day's games appear in a panel under the grid.
                 The rolling 7-day list is gone.
     "both"    — the month grid sits on top as the glance layer and
                 the existing rolling 7-day list stays underneath.
                 Tapping a day moves the list to start on that day,
                 so the grid becomes the navigator for the feed.

   Style follows the app: var + function declarations, and DOM built
   with createElement/textContent only (no innerHTML anywhere).
   ══════════════════════════════════════════════════════════════════ */

/* "Today" is PINNED for the mockup. The captured data runs Jul-Oct
   2026 and the real today (Jul 26) sits in a dead week between the
   World Cup final and the NFL opener, so a mockup anchored there
   would show an empty grid and say nothing about the design. Pinning
   to an NFL Sunday shows the today marker under real load. The app
   itself always uses the actual date. */
var MOCK_TODAY = "2026-09-13";
var START_MONTH = "2026-09";

/* Dylan is in PT and the app labels every kickoff "PT", so the mockup
   formats and groups in PT explicitly. That keeps the screenshots
   identical whatever timezone the reviewing phone is in. */
var TZ = "America/Los_Angeles";

var DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
var SPORT_SEAM = {
    soccer:     ["#0E7C3A", "#075E2C"],
    basketball: ["#E25A00", "#A84300"],
    football:   ["#2352E0", "#16359C"]
};

var MONTHS = Object.keys(window.SMS_SNAPSHOT).sort();
var currentMonth = START_MONTH;
var selectedDate = MOCK_TODAY;
var windowStart  = MOCK_TODAY;   /* mode "both": first day of the 7-day list */

/* ── Small helpers (mirrors of the app's) ───────────────────────── */

function el(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt != null) n.textContent = txt;
    return n;
}

function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

/* ISO instant → "YYYY-MM-DD" in PT. Doing this with formatToParts
   rather than date maths is what keeps a 00:20Z kickoff (Sunday
   5:20pm PT) on Sunday instead of sliding to Monday. */
var YMD_FMT = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit"
});
function ptDay(iso) { return YMD_FMT.format(new Date(iso)); }

var TIME_FMT = new Intl.DateTimeFormat("en-US", {
    timeZone: TZ, hour: "numeric", minute: "2-digit", hour12: true
});
function ptTime(iso) { return TIME_FMT.format(new Date(iso)); }

/* "YYYY-MM-DD" → Date at local noon. Noon, not midnight, so that a
   DST shift can never round the date to the previous day. */
function dayDate(ymd) { return new Date(ymd + "T12:00:00"); }

function addDays(ymd, n) {
    var d = dayDate(ymd);
    d.setDate(d.getDate() + n);
    return d.toLocaleDateString("en-CA");
}

function hexLuma(hex) {
    var r = parseInt(hex.substr(0, 2), 16) / 255;
    var g = parseInt(hex.substr(2, 2), 16) / 255;
    var b = parseInt(hex.substr(4, 2), 16) / 255;
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/* Same rule as the app's seamColor(): reject a kit colour that is too
   light to read against a white card (white kits like England's) and
   fall back to the alternate, then to the sport pair. */
function seamColor(team, fallback) {
    var hex = (team.c || "").trim();
    if (/^[0-9a-fA-F]{6}$/.test(hex) && hexLuma(hex) <= 0.82) return "#" + hex;
    var alt = (team.ac || "").trim();
    if (/^[0-9a-fA-F]{6}$/.test(alt) && hexLuma(alt) <= 0.82) return "#" + alt;
    return fallback;
}

/* ── Data access ────────────────────────────────────────────────── */

/* All games in the loaded month's padded range, keyed by PT day. The
   snapshot stores one padded month per key, exactly as the real
   /api/schedule returns it. */
function gamesByDay(month) {
    var payload = window.SMS_SNAPSHOT[month];
    var out = {};
    if (!payload) return out;
    payload.games.forEach(function(g) {
        var k = ptDay(g.date);
        if (!out[k]) out[k] = [];
        out[k].push(g);
    });
    Object.keys(out).forEach(function(k) {
        out[k].sort(function(a, b) { return a.date < b.date ? -1 : 1; });
    });
    return out;
}

/* Every day the month grid draws: the padded range from the capture,
   which already starts on a Sunday and ends on a Saturday. */
function monthDays(month) {
    var payload = window.SMS_SNAPSHOT[month];
    if (!payload) return [];
    var out = [];
    var d = payload.range.start;
    while (d <= payload.range.end) {
        out.push(d);
        d = addDays(d, 1);
    }
    return out;
}

/* Games for an arbitrary day, looked up across every captured month.
   Needed because mode "both" lets the 7-day list run past the end of
   the month currently shown in the grid. */
function gamesForDay(ymd) {
    var seen = {}, out = [];
    MONTHS.forEach(function(m) {
        (window.SMS_SNAPSHOT[m].games || []).forEach(function(g) {
            if (ptDay(g.date) !== ymd || seen[g.id]) return;
            seen[g.id] = 1;
            out.push(g);
        });
    });
    out.sort(function(a, b) { return a.date < b.date ? -1 : 1; });
    return out;
}

/* ── Game card (the app's card, minus the interactive bits) ─────── */

function buildCard(g) {
    var isPost = g.st === "post";
    var card = el("div", "game-card sport-" + g.sport);
    if (isPost) card.classList.add("game-card--post");

    var fb = SPORT_SEAM[g.sport] || ["#4A5568", "#0C1522"];
    card.style.setProperty("--seam-a", seamColor(g.a, fb[0]));
    card.style.setProperty("--seam-b", seamColor(g.h, fb[1]));
    card.appendChild(el("div", "rail"));

    var kicker = el("div", "gc-kicker");
    var name = g.lg || "";
    if (g.rd) name += " · " + g.rd;
    else if (g.slot) name += " · " + g.slot;
    kicker.appendChild(el("span", "sport-name", name));
    if (g.tv) kicker.appendChild(el("span", "broadcast", g.tv));
    card.appendChild(kicker);

    if (isPost && g.sc) {
        var aw = g.sc.away == null ? null : parseInt(g.sc.away, 10);
        var hm = g.sc.home == null ? null : parseInt(g.sc.home, 10);
        var sb = el("div", "scoreboard");
        sb.appendChild(scoreRow(g.a, aw, aw != null && hm != null && aw < hm));
        sb.appendChild(scoreRow(g.h, hm, aw != null && hm != null && hm < aw));
        card.appendChild(sb);
    } else {
        var up = el("div", "upcoming");
        var teams = el("div", "up-teams");
        teams.appendChild(teamRow(g.a));
        teams.appendChild(el("div", "up-vs", "at"));
        teams.appendChild(teamRow(g.h));
        up.appendChild(teams);

        var time = el("div", "up-time");
        /* Modern Intl separates the meridiem with U+202F (narrow no-break
           space), not a plain space, so splitting on a plain space alone
           silently yields one token and drops the " AM PT" line. */
        var parts = ptTime(g.date).replace(/[\u202f\u00a0]/g, " ").split(" ");
        time.appendChild(document.createTextNode(parts[0]));
        var small = document.createElement("small");
        small.textContent = (parts[1] || "") + " PT";
        time.appendChild(small);
        up.appendChild(time);
        card.appendChild(up);
    }

    var meta = el("div", "gc-meta");
    meta.appendChild(el("span", "tier " + (g.tier || "notable").replace(/_/g, "-"),
                        (g.tier || "notable").replace(/_/g, " ")));
    if (g.po) meta.appendChild(el("span", "tier post-season", "post-season"));
    var avCls = (g.av || "can_watch").replace(/_/g, "-");
    var av = el("span", "gc-avail " + avCls);
    av.appendChild(el("span", "gc-avail-dot"));
    av.appendChild(document.createTextNode((g.av || "can_watch").replace(/_/g, " ")));
    meta.appendChild(av);
    card.appendChild(meta);

    return card;
}

function teamRow(t) {
    var row = el("div", "up-team");
    row.appendChild(el("span", "up-name", t.nm || t.ab));
    return row;
}

function scoreRow(t, score, isLoser) {
    var row = el("div", "sb-row" + (isLoser ? " loser" : ""));
    row.appendChild(el("span", "sb-name", t.nm || t.ab));
    row.appendChild(el("span", "sb-score", score == null ? "–" : String(score)));
    return row;
}

/* ── The month grid (the proposal) ──────────────────────────────── */

function buildMonthNav() {
    var nav = el("div", "month-nav");
    var idx = MONTHS.indexOf(currentMonth);

    var prev = el("button", "month-nav-btn", "‹");
    prev.setAttribute("aria-label", "Previous month");
    prev.disabled = idx <= 0;
    prev.addEventListener("click", function() { goMonth(-1); });

    var label = dayDate(currentMonth + "-15")
        .toLocaleDateString("en-US", { month: "long", year: "numeric" });

    var next = el("button", "month-nav-btn", "›");
    next.setAttribute("aria-label", "Next month");
    next.disabled = idx >= MONTHS.length - 1;
    next.addEventListener("click", function() { goMonth(1); });

    nav.appendChild(prev);
    nav.appendChild(el("div", "month-nav-label", label));
    nav.appendChild(next);
    return nav;
}

function goMonth(step) {
    var idx = MONTHS.indexOf(currentMonth) + step;
    if (idx < 0 || idx >= MONTHS.length) return;
    currentMonth = MONTHS[idx];
    render();
}

function buildGrid() {
    var grid = el("div", "month-grid");
    var gbd = gamesByDay(currentMonth);
    var monthNum = currentMonth.slice(5);

    DOW.forEach(function(d) { grid.appendChild(el("div", "mg-dow", d)); });

    monthDays(currentMonth).forEach(function(ymd) {
        var dg = gbd[ymd] || [];
        var cell = el("button", "mg-cell");
        cell.type = "button";
        if (ymd.slice(5, 7) !== monthNum) cell.classList.add("outside");
        if (ymd === MOCK_TODAY) cell.classList.add("is-today");
        if (ymd === selectedDate) cell.classList.add("selected");
        cell.setAttribute("aria-label",
            dayDate(ymd).toLocaleDateString("en-US",
                { weekday: "long", month: "long", day: "numeric" }) +
            ", " + dg.length + (dg.length === 1 ? " game" : " games"));

        cell.appendChild(el("div", "mg-num", String(dayDate(ymd).getDate())));

        /* WHICH SPORTS + HOW MANY — one dot per distinct sport, then
           the total when the day holds more than one game.
           The obvious version (one dot per game, capped at n) was built
           first and thrown away: on Sun Sep 13 it drew the three
           earliest games only, all NFL, so the Premier League fixture
           that same morning vanished from the month view entirely. A
           glance layer that hides a whole sport is worse than no glance
           layer. Deduping also ends the overflow problem for good —
           two dots and a two-digit number is ~30px inside a 49px cell,
           where four dots plus "+10" was clipping mid-glyph. */
        var dots = el("div", "mg-dots");
        var sports = [];
        dg.forEach(function(g) {
            if (sports.indexOf(g.sport) === -1) sports.push(g.sport);
        });
        sports.forEach(function(sp) {
            var dot = el("span", "mg-dot " + sp);
            /* Dim a sport only when every one of its games that day is
               finished, so a day that is half-played still reads live. */
            var allDone = dg.every(function(g) {
                return g.sport !== sp || g.st === "post";
            });
            if (allDone) dot.classList.add("dimmed");
            dots.appendChild(dot);
        });
        if (dg.length > 1) dots.appendChild(el("span", "mg-more", String(dg.length)));
        cell.appendChild(dots);

        cell.addEventListener("click", function() { pickDay(ymd); });
        grid.appendChild(cell);
    });

    return grid;
}

function buildLegend() {
    var wrap = el("div", "mg-legend");
    [["football", "NFL"], ["soccer", "Soccer"]].forEach(function(pair) {
        var s = el("span");
        s.appendChild(el("i", "mg-dot " + pair[0]));
        s.appendChild(document.createTextNode(pair[1]));
        wrap.appendChild(s);
    });
    var faded = el("span");
    faded.appendChild(el("i", "mg-dot football dimmed"));
    faded.appendChild(document.createTextNode("Played"));
    wrap.appendChild(faded);

    /* The number in a cell is not self-explanatory the first time you
       see it, and it is the busiest signal on the grid. */
    var count = el("span");
    count.appendChild(el("b", "mg-legend-num", "14"));
    count.appendChild(document.createTextNode("Games"));
    wrap.appendChild(count);
    return wrap;
}

function pickDay(ymd) {
    selectedDate = ymd;
    if (MODE === "both") windowStart = ymd;
    render();
    /* In "both" the useful thing after a tap is the feed, not the
       grid, so bring the list's first day up to the top. */
    if (MODE === "both") {
        var first = document.querySelector(".mobile-day");
        if (first) first.scrollIntoView({ block: "start", behavior: "smooth" });
    }
}

/* ── Mode "replace": selected-day panel under the grid ──────────── */

function buildDayPanel() {
    var panel = el("div", "day-panel");
    var dg = gamesForDay(selectedDate);

    var head = el("div", "day-panel-head");
    var label = dayDate(selectedDate).toLocaleDateString("en-US",
        { weekday: "long", month: "long", day: "numeric" });
    head.appendChild(el("span", "day-panel-date", label));
    head.appendChild(el("span", "day-panel-count",
        dg.length ? dg.length + (dg.length === 1 ? " game" : " games") : "No games"));
    panel.appendChild(head);

    if (!dg.length) {
        panel.appendChild(el("div", "day-panel-empty", "Nothing scheduled on this day."));
        return panel;
    }
    var box = el("div", "day-panel-games");
    dg.forEach(function(g) { box.appendChild(buildCard(g)); });
    panel.appendChild(box);
    return panel;
}

/* ── Mode "both": the existing rolling 7-day list, unchanged ────── */

function buildRollingList() {
    var wrap = el("div", "mobile-calendar");

    /* The feed needs a name once a grid sits above it, otherwise the
       first day header reads as a continuation of the grid. */
    var tagRow = el("div", "list-tag-row");
    var tag = el("span", "sec-tag", "Coming Up");
    tagRow.appendChild(tag);
    wrap.appendChild(tagRow);

    for (var i = 0; i < 7; i++) {
        var ymd = addDays(windowStart, i);
        var dg = gamesForDay(ymd);

        var day = el("div", "mobile-day");
        if (ymd === MOCK_TODAY) day.classList.add("is-today");

        var head = el("div", "mobile-day-header");
        var nameEl = el("span", "mobile-day-name",
            dayDate(ymd).toLocaleDateString("en-US",
                { weekday: "short", month: "short", day: "numeric" }));
        if (ymd === MOCK_TODAY) nameEl.appendChild(el("span", "mobile-today-badge", "Today"));
        head.appendChild(nameEl);
        if (dg.length) {
            head.appendChild(el("span", "mobile-day-count",
                dg.length + (dg.length === 1 ? " game" : " games")));
        }
        day.appendChild(head);

        if (!dg.length) {
            day.appendChild(el("div", "mobile-day-off", "No games"));
        } else {
            var box = el("div", "mobile-day-games");
            dg.forEach(function(g) { box.appendChild(buildCard(g)); });
            day.appendChild(box);
        }
        wrap.appendChild(day);
    }
    return wrap;
}

/* ── Render ─────────────────────────────────────────────────────── */

function render() {
    var root = document.getElementById("view");
    clear(root);
    root.appendChild(buildMonthNav());
    root.appendChild(buildGrid());
    root.appendChild(buildLegend());
    if (MODE === "replace") {
        root.appendChild(buildDayPanel());
    } else {
        root.appendChild(buildRollingList());
    }
}

render();
