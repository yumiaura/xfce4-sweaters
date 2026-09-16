# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Checks before every commit

Run all four; they mirror `.github/workflows/test.yml`:

```bash
ruff check .
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 -m compileall -q xfce4_sweaters scripts && /usr/bin/python3 -m xfce4_sweaters check-config
dbus-run-session -- xvfb-run -a -s '-screen 0 1280x800x24 +extension Composite' /usr/bin/python3 tests/smoke_x11.py
```

- Ruff runs only the pyflakes rules (`select = ["F"]` in `pyproject.toml`): unused imports and names, undefined names. It is not a formatter and has no style rules on purpose.
- `tests/smoke_x11.py` is a plain script, not discovered by unittest. It spawns `xfwm4 --replace`; run it only inside `xvfb-run`, never against a real session. Needs `xvfb xfwm4 dbus-x11 x11-utils` plus the runtime packages below.
- After changing `xfce4_sweaters/textures.py`, `data/patterns.json` or `scripts/gallery.py`, regenerate the README image: `/usr/bin/python3 scripts/gallery.py` (writes `docs/textures.png`, no display needed) and commit it.

## Code style (differs from PEP 8)

- Keep the existing dense style: no spaces around `=` or after commas, several statements per line with `;`, long lines, single quotes, no type hints. Match the surrounding code; do not "clean it up".
- Never run black, ruff format or any formatter on this project.
- No leading-underscore names.
- In documentation and comments do not use the em dash `—` or a double hyphen `--` as punctuation (command flags like `--autostart` are fine). Use a colon, comma or parentheses instead.
- Everything in the repository is English: docs, comments, UI strings, commit messages.

## Runtime facts that shape changes

- Runtime deps come from apt, not pip: `python3-gi python3-gi-cairo python3-cairo python3-pil python3-xlib gir1.2-gtk-3.0`. `pyproject.toml` lists only Pillow and python-xlib on purpose. Both install paths are supported: `scripts/install.py` (per-user, copies the package to `$XDG_DATA_HOME/xfce4-sweaters/app`) and `pip install .`.
- Three install paths ship: `scripts/install.py`, `pip install .` and the `.deb` from `debian/` (built in `.github/workflows/package.yml` with `dpkg-buildpackage -us -uc -b`, needs `debhelper dh-python pybuild-plugin-pyproject`). A version bump touches `xfce4_sweaters/__init__.py`, `pyproject.toml`, `tests/test_install.py`, the README download URL and `debian/changelog` (`dch -v <version> --distribution unstable`); CI fails when they disagree or when a `v*` tag does not match. Tags `v*` also publish to PyPI via trusted publishing (`publish.yml`) and rebuild the signed flat APT repository on GitHub Pages (job `apt` in `package.yml`: every release's `.deb`, signed with the `APT_GPG_PRIVATE_KEY` secret, key `5C4F1331F4E3ED1F7998C19A2EBFC7F4FB5DB182` in Olya's keyring; `workflow_dispatch` rebuilds it). Never hardcode a version in install instructions: use the repository or `releases/latest/download/xfce4-sweaters_all.deb`.
- X11 only. `__main__.py` refuses Wayland or empty `DISPLAY`, forces `GDK_BACKEND=x11` and `GDK_SCALE=1`; `Controller` raises on a monitor scale factor other than 1. A running compositor (`_NET_WM_CM_S<n>` owner) and the SHAPE extension are required.
- One instance per display via `fcntl.flock` on `$XDG_RUNTIME_DIR/xfce4-sweaters-<hash>.lock`; a second `settings` invocation sends `SIGUSR1` to the running process instead of starting.
- Overlays are override-redirect popups restacked with a separate Xlib connection; overlay XIDs go into `tracker.ignored`. Only `desktop.py`, `settings.py` and `x11.py` may import GTK/Xlib; `config.py` and `textures.py` stay toolkit-free so `preview`, `list-textures` and `check-config` work without a display.
- `config.json` is versioned (`version: 1`) with an exact key set; unknown keys raise. Adding a setting means updating `config.py` validation, defaults, the README example and `tests/test_core.py` together.
- `xfce4_sweaters/data/patterns.json` is a regular project file and may be edited like code.

## Repo etiquette

Non-trivial changes follow the branch-per-phase / PR-per-phase / `CHANGELOG.md` protocol from the global `~/.claude/CLAUDE.md`. Details on architecture and manual verification: `@docs/ARCHITECTURE.md`, `@docs/TESTING.md`.
