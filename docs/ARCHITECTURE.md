# Architecture

`config.py` validates a versioned JSON document and writes it atomically.
A missing file uses defaults; malformed updates keep the last good runtime
configuration. Rules match case-insensitive WM_CLASS/title globs in list order.

`textures.py` loads 47 data-driven stitch charts and validated PNG tiles. A
SHA-256 selection derived from seed, WM_CLASS and XID gives each live window a
stable random texture and colour. Explicit choices bypass that selection.
The independent Pillow renderer caches up to 64 fabric tiles and paints four
mitred strips around a transparent centre, then rounds the outer corners with
a radius of half the border width. Each side rotates its texture to follow
the window edge. Each overlay keeps only its current rendered image.

`x11.py` observes the EWMH client list, active window, desktop and state atoms.
It walks each client to its top-level reparenting frame and converts that frame's
geometry into root coordinates. Property/structure events trigger updates;
a periodic reconciliation catches missed events and compositor changes.
Override-redirect overlay events are ignored to avoid self-triggered redraws.

`desktop.py` owns one undecorated GTK POPUP window per eligible client. Each has
an RGBA visual, transparent centre and empty input shape. After GTK requests
are synchronized, the independent Xlib connection places the overlay immediately
above its own frame. It never uses an always-on-top hint. This preserves client
stacking, including occlusion by higher windows, panels and popups. Hidden,
closed, fullscreen, off-workspace and optionally maximized clients lose their
overlay. Rendering changes only when size, style or focus opacity changes.

`settings.py` provides the tray-accessible GTK interface, preview, imports,
session overrides and persistent application/title rules. Custom files are
validated before import, and duplicate names are not overwritten.

`__main__.py` exposes desktop-independent CLI commands, checks X11 session
requirements and holds a per-display flock. A second settings invocation signals
the existing same-user process with SIGUSR1. No service runs as root, no server
port is opened, and no network connection is needed at runtime.

Future work: live desktop validation across distributions, per-monitor scaling,
optional rounded/shaped window contours and window-manager-native integration.
