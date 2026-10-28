#!/usr/bin/env python3
import curses
import datetime as dt
import time
import socket
import urllib.request
import threading
import textwrap
from zoneinfo import ZoneInfo

try:
    import jdatetime
except ImportError:
    jdatetime = None

IRAN = "Asia/Tehran"
UTC = "UTC"

COUNTRIES = [
    ("United States — New York", "America/New_York", "NYSE / Nasdaq", "09:30-16:00", [0,1,2,3,4]),
    ("United Kingdom — London", "Europe/London", "London Stock Exchange", "08:00-16:30", [0,1,2,3,4]),
    ("Japan — Tokyo", "Asia/Tokyo", "Tokyo Stock Exchange", "09:00-11:30, 12:30-15:30", [0,1,2,3,4]),
    ("South Korea — Seoul", "Asia/Seoul", "Korea Exchange", "09:00-15:30", [0,1,2,3,4]),
    ("Singapore", "Asia/Singapore", "Singapore Exchange", "09:00-12:00, 13:00-17:00", [0,1,2,3,4]),
    ("Hong Kong", "Asia/Hong_Kong", "Hong Kong Exchange", "09:30-12:00, 13:00-16:00", [0,1,2,3,4]),
    ("China — Shanghai", "Asia/Shanghai", "Shanghai Stock Exchange", "09:30-11:30, 13:00-15:00", [0,1,2,3,4]),
    ("United Arab Emirates — Dubai", "Asia/Dubai", "Dubai Financial Market", "10:00-14:45", [6,0,1,2,3]),
    ("Saudi Arabia — Riyadh", "Asia/Riyadh", "Saudi Exchange", "10:00-15:00", [6,0,1,2,3]),
    ("India — Mumbai", "Asia/Kolkata", "National Stock Exchange", "09:15-15:30", [0,1,2,3,4]),
    ("Turkey — Istanbul", "Europe/Istanbul", "Borsa Istanbul", "10:00-18:00", [0,1,2,3,4]),
    ("Iran — Tehran", "Asia/Tehran", "Tehran Stock Exchange", "09:00-12:30", [5,6,0,1,2]),
    ("Germany — Frankfurt", "Europe/Berlin", "Frankfurt / Xetra", "09:00-17:30", [0,1,2,3,4]),
    ("Australia — Sydney", "Australia/Sydney", "ASX", "10:00-16:00", [0,1,2,3,4]),
]

COLORS = [1, 2, 3, 4, 5, 6]

def now(zone):
    return dt.datetime.now(ZoneInfo(zone))

def date_gregorian(value):
    return value.strftime("%A, %d %B %Y")

def date_jalali(value):
    if jdatetime:
        try:
            return jdatetime.date.fromgregorian(date=value.date()).strftime("%Y/%m/%d  •  %d %B %Y")
        except Exception:
            pass
    return "Install jdatetime: pip install jdatetime"

def init_colors():
    try:
        curses.start_color()
        curses.use_default_colors()
        curses.curs_set(0)
        for n, color in [
            (1, curses.COLOR_CYAN), (2, curses.COLOR_GREEN),
            (3, curses.COLOR_MAGENTA), (4, curses.COLOR_YELLOW),
            (5, curses.COLOR_BLUE), (6, curses.COLOR_RED),
            (7, curses.COLOR_WHITE)
        ]:
            try:
                curses.init_pair(n, color, -1)
            except curses.error:
                pass
        try:
            curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_GREEN)
            curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_RED)
            curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(11, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        except curses.error:
            pass
    except curses.error:
        pass

def safe_add(stdscr, y, x, text, attr=0, width=None):
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    limit = w - x - 1
    if width is not None:
        limit = min(limit, width)
    try:
        stdscr.addnstr(y, x, str(text), max(0, limit), attr)
    except curses.error:
        pass

def centered(stdscr, y, text, attr=0):
    _, w = stdscr.getmaxyx()
    text = str(text)
    safe_add(stdscr, y, max(0, (w - len(text)) // 2), text, attr)

def draw_box(stdscr, y, x, height, width, title="", border_attr=0, title_attr=0, double=False):
    h, w = stdscr.getmaxyx()
    if y >= h or x >= w or height < 2 or width < 4:
        return
    height = min(height, h - y)
    width = min(width, w - x - 1)
    if double:
        tl, tr, bl, br, hz, vt = "╔", "╗", "╚", "╝", "═", "║"
    else:
        tl, tr, bl, br, hz, vt = "╭", "╮", "╰", "╯", "─", "│"

    safe_add(stdscr, y, x, tl + (hz * (width - 2)) + tr, border_attr)
    for row in range(y + 1, y + height - 1):
        safe_add(stdscr, row, x, vt, border_attr)
        safe_add(stdscr, row, x + width - 1, vt, border_attr)
    safe_add(stdscr, y + height - 1, x, bl + (hz * (width - 2)) + br, border_attr)

    if title:
        label = f" {title} "
        tx = x + max(2, (width - len(label)) // 2)
        safe_add(stdscr, y, tx, label, title_attr if title_attr else border_attr)

def draw_divider(stdscr, y, x, width, border_attr=0):
    _, w = stdscr.getmaxyx()
    width = min(width, w - x - 1)
    if width >= 4:
        safe_add(stdscr, y, x, "├" + ("─" * (width - 2)) + "┤", border_attr)

def internet_status():
    try:
        request = urllib.request.Request(
            "https://www.google.com/generate_204",
            headers={"User-Agent": "TIMEE/2.0"}
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            return "ONLINE" if response.status < 500 else "LIMITED"
    except Exception:
        return "OFFLINE"

_net_lock = threading.Lock()
_net_value = "CHECKING"
_net_last_check = 0

def update_network_status():
    global _net_value, _net_last_check
    while True:
        result = internet_status()
        with _net_lock:
            _net_value = result
            _net_last_check = time.time()
        time.sleep(60)

def network_status():
    global _net_last_check
    with _net_lock:
        value = _net_value
        last = _net_last_check
    if time.time() - last > 65:
        return "CHECKING"
    return value

def parse_sessions(hours):
    sessions = []
    for part in hours.split(","):
        part = part.strip().replace("–", "-")
        if "-" not in part:
            continue
        try:
            start, end = part.split("-", 1)
            sh, sm = map(int, start.strip().split(":"))
            eh, em = map(int, end.strip().split(":"))
            sessions.append((sh * 60 + sm, eh * 60 + em))
        except (ValueError, TypeError):
            continue
    return sessions

def market_status(zone, hours, weekdays):
    local = now(zone)
    minute = local.hour * 60 + local.minute
    if local.weekday() not in weekdays:
        return "CLOSED", "Non-trading day", None

    sessions = parse_sessions(hours)
    for start, end in sessions:
        if start <= minute < end:
            end_dt = local.replace(
                hour=end // 60, minute=end % 60, second=0, microsecond=0
            )
            return "OPEN", "Market session active", end_dt

    future = [(start, end) for start, end in sessions if start > minute]
    if future:
        start = future[0][0]
        next_dt = local.replace(
            hour=start // 60, minute=start % 60, second=0, microsecond=0
        )
        return "CLOSED", "Next session today", next_dt

    return "CLOSED", "Next trading day", next_market_open(local, hours, weekdays)

def next_market_open(local, hours, weekdays):
    sessions = parse_sessions(hours)
    if not sessions:
        return None
    first_start = min(start for start, _ in sessions)
    for days_ahead in range(1, 9):
        candidate = local + dt.timedelta(days=days_ahead)
        if candidate.weekday() in weekdays:
            return candidate.replace(
                hour=first_start // 60,
                minute=first_start % 60,
                second=0,
                microsecond=0
            )
    return None

def countdown(target):
    if target is None:
        return "N/A"
    seconds = max(0, int((target - now(target.tzinfo.key)).total_seconds()))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days:
        return f"{days}d {hours:02}:{minutes:02}:{seconds:02}"
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def clock_screen(stdscr):
    pulse = 0
    stdscr.nodelay(True)
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        pulse = (pulse + 1) % len(COLORS)
        accent = curses.color_pair(COLORS[pulse]) | curses.A_BOLD
        utc = now(UTC)
        iran = now(IRAN)

        box_w = min(w - 4, 52)
        bx = max(2, (w - box_w) // 2)
        top_y = max(1, (h - 22) // 2)

        # Header Banner
        draw_box(stdscr, top_y, bx, 3, box_w, border_attr=curses.color_pair(1) | curses.A_BOLD, double=True)
        centered(stdscr, top_y + 1, "⚡ T I M E E  //  WORLD CLOCK ⚡", curses.A_BOLD | curses.color_pair(1))

        # UTC Card
        utc_y = top_y + 4
        draw_box(
            stdscr, utc_y, bx, 5, box_w,
            title="UTC · UNIVERSAL TIME",
            border_attr=curses.color_pair(4),
            title_attr=curses.color_pair(4) | curses.A_BOLD
        )
        centered(stdscr, utc_y + 1, f"◄  {utc.strftime('%H : %M : %S')}  ►", accent)
        centered(stdscr, utc_y + 3, utc.strftime("%A  •  %d %B %Y"), curses.color_pair(7) | curses.A_BOLD)

        # IRAN Card
        iran_y = utc_y + 6
        draw_box(
            stdscr, iran_y, bx, 5, box_w,
            title="IRAN · TEHRAN (IRST)",
            border_attr=curses.color_pair(2),
            title_attr=curses.color_pair(2) | curses.A_BOLD
        )
        centered(stdscr, iran_y + 1, f"◄  {iran.strftime('%H : %M : %S')}  ►", accent)
        centered(stdscr, iran_y + 3, "SHAMSI: " + date_jalali(iran), curses.color_pair(7) | curses.A_BOLD)

        # Status & Action Panel
        ctrl_y = iran_y + 6
        draw_box(
            stdscr, ctrl_y, bx, 5, box_w,
            title="SYSTEM & NAVIGATION",
            border_attr=curses.color_pair(5),
            title_attr=curses.color_pair(1) | curses.A_BOLD
        )
        net = network_status()
        net_badge = curses.color_pair(8 if net == "ONLINE" else 9) | curses.A_BOLD
        net_label = f" ● {net} "
        centered(stdscr, ctrl_y + 1, net_label, net_badge)
        centered(stdscr, ctrl_y + 2, "[ C / ENTER ]  Global Markets Directory", curses.color_pair(1) | curses.A_BOLD)
        centered(stdscr, ctrl_y + 3, "[ E ]  Exit Application", curses.color_pair(6) | curses.A_BOLD)

        # Footer
        centered(stdscr, h - 2, "━" * min(w - 6, 40), curses.color_pair(5))
        centered(stdscr, h - 1, "m_sgn  •  TIMEE LIVE SYSTEM", curses.color_pair(3) | curses.A_BOLD)
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord("e"), ord("E")):
            return False
        if key in (ord("c"), ord("C"), 10, 13, curses.KEY_ENTER):
            result = country_menu(stdscr)
            if result == "exit":
                return False
        time.sleep(0.05)

def country_menu(stdscr):
    index = 0
    top = 0
    stdscr.nodelay(False)
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        box_w = min(w - 2, 56)
        bx = max(1, (w - box_w) // 2)

        # Header
        draw_box(stdscr, 1, bx, 4, box_w, border_attr=curses.color_pair(1) | curses.A_BOLD, double=True)
        centered(stdscr, 2, "GLOBAL EXCHANGES DIRECTORY", curses.A_BOLD | curses.color_pair(1))
        centered(stdscr, 3, "↑/↓ Navigate   •   ENTER Select   •   E Back", curses.color_pair(4))

        # List Container
        list_h = max(5, h - 8)
        draw_box(
            stdscr, 5, bx, list_h, box_w,
            title=f"COUNTRIES ({index + 1}/{len(COUNTRIES)})",
            border_attr=curses.color_pair(5),
            title_attr=curses.color_pair(2) | curses.A_BOLD
        )

        visible = max(1, list_h - 2)
        if index < top:
            top = index
        elif index >= top + visible:
            top = index - visible + 1

        inner_w = box_w - 4
        for row_idx, i in enumerate(range(top, min(len(COUNTRIES), top + visible))):
            y = 6 + row_idx
            name, zone, _, hours, weekdays = COUNTRIES[i]
            status, _, _ = market_status(zone, hours, weekdays)
            badge_text = "● OPEN  " if status == "OPEN" else "○ CLOSED"
            badge_attr = curses.color_pair(2 if status == "OPEN" else 6) | curses.A_BOLD

            max_name_len = max(8, inner_w - len(badge_text) - 5)
            disp_name = name[:max_name_len]

            if i == index:
                row_str = f" ▶ {disp_name:<{max_name_len}} "
                safe_add(stdscr, y, bx + 2, " " * inner_w, curses.color_pair(10))
                safe_add(stdscr, y, bx + 2, row_str, curses.color_pair(10) | curses.A_BOLD, inner_w)
                safe_add(stdscr, y, bx + 2 + inner_w - len(badge_text) - 1, badge_text, curses.color_pair(10) | curses.A_BOLD)
            else:
                row_str = f"   {disp_name:<{max_name_len}} "
                safe_add(stdscr, y, bx + 2, row_str, curses.color_pair(7), inner_w)
                safe_add(stdscr, y, bx + 2 + inner_w - len(badge_text) - 1, badge_text, badge_attr)

        centered(stdscr, h - 1, "m_sgn  •  TIMEE LIVE SYSTEM", curses.A_BOLD | curses.color_pair(3))
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord("e"), ord("E"), 27):
            stdscr.nodelay(True)
            return "back"
        if key in (curses.KEY_UP, ord("k")):
            index = (index - 1) % len(COUNTRIES)
        elif key in (curses.KEY_DOWN, ord("j")):
            index = (index + 1) % len(COUNTRIES)
        elif key in (10, 13, curses.KEY_ENTER):
            result = country_detail(stdscr, COUNTRIES[index])
            if result == "exit":
                stdscr.nodelay(True)
                return "exit"

def country_detail(stdscr, country):
    name, zone, exchange, hours, weekdays = country
    stdscr.nodelay(True)
    pulse = 0
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        pulse = (pulse + 1) % len(COLORS)
        accent = curses.color_pair(COLORS[pulse]) | curses.A_BOLD
        local = now(zone)
        iran = now(IRAN)
        utc = now(UTC)
        status, note, target = market_status(zone, hours, weekdays)

        box_w = min(w - 2, 56)
        bx = max(1, (w - box_w) // 2)

        # Header Card
        draw_box(stdscr, 1, bx, 4, box_w, title="COUNTRY MARKET DASHBOARD", border_attr=curses.color_pair(1) | curses.A_BOLD, double=True)
        centered(stdscr, 2, name, curses.A_BOLD | curses.color_pair(2))
        centered(stdscr, 3, f"🏛  {exchange}", curses.color_pair(4) | curses.A_BOLD)

        # Timezones Card
        draw_box(
            stdscr, 5, bx, 5, box_w,
            title="WORLD TIMEZONES",
            border_attr=curses.color_pair(5),
            title_attr=curses.color_pair(4) | curses.A_BOLD
        )
        safe_add(stdscr, 6, bx + 3, "LOCAL TIME :", curses.A_BOLD | curses.color_pair(4))
        safe_add(stdscr, 6, bx + 17, local.strftime("%Y-%m-%d  %H:%M:%S %Z"), accent, box_w - 19)
        safe_add(stdscr, 7, bx + 3, "IRAN TIME  :", curses.A_BOLD | curses.color_pair(4))
        safe_add(stdscr, 7, bx + 17, iran.strftime("%Y-%m-%d  %H:%M:%S"), accent, box_w - 19)
        safe_add(stdscr, 8, bx + 3, "UTC TIME   :", curses.A_BOLD | curses.color_pair(4))
        safe_add(stdscr, 8, bx + 17, utc.strftime("%Y-%m-%d  %H:%M:%S UTC"), accent, box_w - 19)

        # Market Session Card
        draw_box(
            stdscr, 10, bx, 8, box_w,
            title="EXCHANGE SESSION",
            border_attr=curses.color_pair(2 if status == "OPEN" else 6),
            title_attr=curses.color_pair(4) | curses.A_BOLD
        )
        status_badge = curses.color_pair(8 if status == "OPEN" else 9) | curses.A_BOLD
        safe_add(stdscr, 11, bx + 3, "STATUS     :", curses.A_BOLD | curses.color_pair(4))
        safe_add(stdscr, 11, bx + 17, f" {status} ", status_badge)
        safe_add(stdscr, 11, bx + 19 + len(status), f"({note})", curses.color_pair(7), box_w - 22 - len(status))

        days_str = ",".join(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][d] for d in weekdays)
        safe_add(stdscr, 12, bx + 3, "HOURS      :", curses.A_BOLD | curses.color_pair(4))
        safe_add(stdscr, 12, bx + 17, hours, curses.color_pair(7) | curses.A_BOLD, box_w - 19)
        safe_add(stdscr, 13, bx + 3, "WORKDAYS   :", curses.A_BOLD | curses.color_pair(4))
        safe_add(stdscr, 13, bx + 17, days_str, curses.color_pair(7), box_w - 19)

        draw_divider(stdscr, 14, bx, box_w, curses.color_pair(5))

        safe_add(stdscr, 15, bx + 3, "NEXT EVENT :", curses.A_BOLD | curses.color_pair(4))
        if target:
            safe_add(stdscr, 15, bx + 17, target.strftime("%Y-%m-%d %H:%M %Z"), accent, box_w - 19)
            safe_add(stdscr, 16, bx + 3, "COUNTDOWN  :", curses.A_BOLD | curses.color_pair(4))
            safe_add(stdscr, 16, bx + 17, f"⏱  {countdown(target)}", curses.color_pair(2) | curses.A_BOLD, box_w - 19)
        else:
            safe_add(stdscr, 15, bx + 17, "Unavailable", accent, box_w - 19)

        # Notice Box
        notice_y = 18
        if notice_y + 4 < h - 1:
            draw_box(stdscr, notice_y, bx, 5, box_w, title="NOTICE", border_attr=curses.color_pair(6))
            msg1 = "Schedule-based estimate; public holidays not verified."
            msg2 = "Crypto operates 24/7; hours reflect local stock market."
            for idx, line in enumerate(textwrap.wrap(msg1, width=box_w - 4)[:2]):
                safe_add(stdscr, notice_y + 1 + idx, bx + 2, line, curses.color_pair(6) | curses.A_BOLD)
            for idx, line in enumerate(textwrap.wrap(msg2, width=box_w - 4)[:1]):
                safe_add(stdscr, notice_y + 3 + idx, bx + 2, line, curses.color_pair(7))

        centered(stdscr, h - 1, "[ E / ESC ] Back to List   •   m_sgn", curses.A_BOLD | curses.color_pair(3))
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord("e"), ord("E"), 27):
            stdscr.nodelay(False)
            return "back"
        time.sleep(0.25)

def goodbye():
    try:
        import shutil
        width, height = shutil.get_terminal_size((80, 24))
        for x in range(width):
            line = (" " * x) + "m_sgn  •  TIMEE CLOSED"
            print("\033[H\033[2J\033[1;35m" + "\n".join([line[:width]] * height) + "\033[0m", end="", flush=True)
            time.sleep(0.01)
        print("\033[2J\033[H", end="", flush=True)
    except Exception:
        print("\033[2J\033[H", end="", flush=True)

def main(stdscr):
    init_colors()
    threading.Thread(target=update_network_status, daemon=True).start()
    clock_screen(stdscr)

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        goodbye()
