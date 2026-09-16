# Validation

## Results at preparation (2026-09-16)

- Passed: 12 unittest cases covering all 47 chart dimensions/colour references
  and rendering; stable random assignment and reshuffling; explicit selections;
  first-match rules and title filters; malformed configuration; atomic writes;
  mutable-default isolation; alpha/transparent centres; custom PNG validation;
  border dimension limits; real install/launch/uninstall in a temporary user
  directory (including spaces and shell metacharacters), preserved user assets
  and missing-dependency handling. Only dependency detection was mocked for
  the installation test; copied files and the executable launcher were real.
- Passed: compilation, CLI version/config checks and expected display-less
  startup error. Rendered `docs/textures.png` was visually inspected.
- Not run here: GTK/Xfwm4 integration, interactive settings, installer on an
  actual desktop, compositor layering, pointer passthrough and HiDPI.
  This environment has no X11 desktop or PyGObject and cannot install the
  missing system packages. No live-desktop pass is claimed.

## Automated integration

On Ubuntu/Xubuntu install the normal runtime dependencies plus:

```bash
sudo apt install xvfb xfwm4 dbus-x11 x11-utils
dbus-run-session -- xvfb-run -a -s '-screen 0 1280x800x24 +extension Composite' /usr/bin/python3 tests/smoke_x11.py
```

This starts a disposable X server and xfwm4. It checks empty input shape,
stack order, movement/resizing, overrides, minimize/restore, fullscreen/restore,
settings construction, pause/resume and close cleanup. It never uses your real
window manager. GitHub Actions runs the same scenario after core tests.

## Manual release gate

1. Start in an XFCE X11 session with compositing. Open two overlapping windows;
   inspect each edge and corner and verify lower borders do not cover higher apps.
2. Click, type, scroll and drag through the overlay area. Resize at all four
   corners; confirm the app never steals focus or blocks window controls.
3. Move windows rapidly, across monitors and partly outside the screen. Switch
   workspaces, use Show Desktop, minimize, shade, maximize and fullscreen.
4. Change global style, width, stitch size and inactive opacity. Assign a
   temporary window override and a persistent app/title rule. Restart and
   confirm only the permanent rule survives.
5. Shuffle; confirm fixed styles remain fixed. Import a small transparent PNG;
   test corrupt files, duplicate names and oversized images.
6. Pause/resume, close decorated windows, quit/relaunch and invoke settings from
   a second terminal. Confirm no duplicate process or orphan overlay remains.
7. Turn the compositor off and on. Verify automatic hiding/recovery.
8. Test 100% and 200% desktop scaling, negative monitor coordinates, a VNC
   session and many windows. Record CPU/RAM and latency before a stable release.
