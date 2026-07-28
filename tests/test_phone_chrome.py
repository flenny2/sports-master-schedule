"""
Tests for the phone chrome contract (safe areas + tap targets).

These read the stylesheet as text, which is unusual here — the rest of the
suite tests Python. They exist because the defects they pin are invisible
to every other check: the app renders perfectly in a desktop browser and in
headless Chrome, and only breaks on a real notched phone, where nobody is
running pytest. The live proof is `tools/qa-phone-chrome.py`, which measures
the running app at a true 390px; these are the cheap guards that fail in CI
if someone unpicks the wiring that harness verified.

Measured 2026-07-27 before the fix: the four tab labels sat behind the iOS
status bar whenever the page was scrolled, and the footer's last line sat
under the home indicator, because `index.html` asked for `viewport-fit=cover`
(page extends under the cutouts) while `style.css` contained no `env()` at
all. Screenshots: docs/overnight/shots/sms-4-chrome-before.png vs -after.png
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "static" / "style.css").read_text()
HTML = (ROOT / "templates" / "index.html").read_text()


def block(selector):
    """The declarations of the FIRST rule for `selector`, as one string.

    Deliberately naive — the stylesheet has no nested at-rules inside the
    blocks these tests look at, so matching to the first `}` is enough and
    keeps the helper readable.
    """
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    assert m, f"no rule found for {selector!r} in style.css"
    return m.group(1)


def test_cover_viewport_implies_safe_area_insets():
    """`viewport-fit=cover` without env() is the bug, not a style choice.

    Asking for cover tells iOS to draw the page under the notch, the status
    bar and the home indicator. A stylesheet that then ignores the insets
    puts real content in places the user cannot see or tap.
    """
    if "viewport-fit=cover" not in HTML:
        pytest.skip("the viewport no longer asks to cover the cutouts")
    for edge in ("top", "bottom", "left", "right"):
        assert f"env(safe-area-inset-{edge}" in CSS, (
            f"index.html asks for viewport-fit=cover but style.css never "
            f"reads safe-area-inset-{edge} — content will sit under that cutout"
        )


def test_sticky_tab_bar_pins_below_the_notch():
    """The tab bar is the topmost thing on screen once the masthead scrolls
    away, so `top: 0` puts the tab labels behind the iOS clock in an
    Add-to-Home-Screen launch."""
    decls = block(".tab-bar")
    assert "position: sticky" in decls
    top = re.search(r"top:\s*([^;]+);", decls)
    assert top, ".tab-bar lost its sticky offset"
    assert "--sa-top" in top.group(1), (
        f"tab bar pins at {top.group(1).strip()!r}; it must pin at the top "
        f"safe-area inset or its labels hide behind the status bar"
    )


def test_masthead_and_footer_pay_back_the_insets():
    assert "--sa-top" in block("header"), (
        "the masthead must add the top inset or the brand sits under the clock"
    )
    assert "--sa-bottom" in block("footer"), (
        "the footer must add the bottom inset or its last line sits under "
        "the home indicator"
    )


PHONE_BLOCK = re.search(r"@media\s*\(max-width:\s*640px\)\s*\{(.*?)\n\}",
                        CSS, re.S)


def phone_height(selector):
    """The height a control ends up with ON A PHONE, as a string.

    The ≤640px block is the last one in the file, so where it declares a
    height for a selector that value wins over the base rule. Returning the
    winner — rather than checking every rule — is what makes these asserts
    match what tools/qa-phone-chrome.py actually measured; the base `.pill`
    stays at its desktop 36px on purpose, because 44px is a FINGER minimum,
    not a mouse one.
    """
    assert PHONE_BLOCK, "the ≤640px breakpoint moved — re-point these tests"
    for source in (PHONE_BLOCK.group(1), CSS):
        m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", source)
        if not m:
            continue
        # The lookbehind keeps `line-height` and `max-height` out of it.
        sizes = re.findall(r"(?<![-\w])(?:min-)?height:\s*([^;]+);", m.group(1))
        if sizes:
            return sizes[-1].strip()
    raise AssertionError(f"{selector} declares no height anywhere")


@pytest.mark.parametrize("selector", [".pill", ".nav-arrow", ".gc-watched",
                                      ".mini-more", ".refresh-btn", ".tab",
                                      ".sl-chip", ".read-btn", ".read-refresh"])
def test_named_controls_reach_the_tap_minimum(selector):
    """Every one of these measured under 44px at 390px on 2026-07-27, except
    `.tab`, which is here so a future tightening of the tab bar cannot
    quietly take the main navigation below the minimum.

    `.sl-chip`, `.read-btn` and `.read-refresh` are here for a different
    reason worth remembering: a live pass could not see any of them. The
    filter chip rendered 0x0 because no storyline was active that day, and
    the two read buttons only exist inside an expanded card of an UPCOMING
    soccer or NFL game — of which the off-season Calendar was showing none.
    A measurement harness only covers what is on screen, so a static check
    earns its place for controls that appear seasonally or behind a flow.

    The read buttons matter more than their size suggests: both of them
    SPEND. A mis-tap there costs money rather than a wasted second.
    """
    size = phone_height(selector)
    ok = "--tap-min" in size or _px_at_least(size, 44)
    assert ok, (
        f"{selector} is {size} on a phone; 44px is the documented tap "
        f"minimum (--tap-min), and a smaller control is a mis-tap"
    )


def _px_at_least(value, floor):
    m = re.match(r"\s*(\d+)px\s*$", value)
    return bool(m) and int(m.group(1)) >= floor


def test_banner_card_wraps_long_team_names_instead_of_cutting_them():
    """Measured at 390px on 2026-07-27: the headline game read "CAROLINA
    PANTHE…" because the banner's team name was 6px too wide.

    The fix is a wrap, not a smaller font — buying back six pixels would
    have fixed that one name and still failed on "Wolverhampton Wanderers".
    This pins the wrap so a future tidy-up cannot quietly restore `nowrap`,
    which would look identical on every short name and only break on the
    long ones.
    """
    m = re.search(r"\.game-card--marquee \.up-name,\s*"
                  r"\.game-card--marquee \.sb-name\s*\{([^}]*)\}", CSS)
    assert m, "the banner's name-wrapping rule is gone"
    decls = m.group(1)
    assert "white-space: normal" in decls, (
        "the banner name is back to nowrap; long names will be cut again"
    )
    assert "-webkit-line-clamp: 2" in decls, (
        "without a line cap the banner card can grow without limit"
    )


def test_ordinary_cards_still_truncate_on_one_line():
    """The wrap is deliberately banner-only. Ordinary cards are a list, and
    an uneven list is harder to scan than a shortened name — so this pins
    that the base rule was NOT changed along with the banner."""
    assert "white-space: nowrap" in block(".up-team .up-name")
    assert "white-space: nowrap" in block(".sb-name")
