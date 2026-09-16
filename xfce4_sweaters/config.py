"""Validated, atomic configuration; independent of the desktop toolkit."""
from __future__ import annotations
import copy
import fnmatch
import json
import os
from pathlib import Path
import re
import tempfile

COLORS = ['#bd7590', '#648e7b', '#7297b8', '#c78461', '#8279ab', '#b59b65']
DEFAULT = {
    'version': 1, 'enabled': True, 'texture': 'random', 'color': 'random',
    'width': 24, 'stitch': 5, 'inactive_opacity': 0.80,
    'hide_maximized': True, 'seed': 0, 'rules': [],
}

def config_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'xfce4-sweaters/config.json'

def texture_dir():
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'xfce4-sweaters/textures'

def validate_style(data, ids):
    if 'texture' in data and (not isinstance(data['texture'], str) or data['texture'] not in {*ids, 'random', 'off'}):
        raise ValueError(f"Unknown texture: {data['texture']}")
    if 'color' in data and (not isinstance(data['color'], str) or not (data['color'] == 'random' or re.fullmatch(r'#[0-9a-fA-F]{6}', data['color']))):
        raise ValueError('Color must be random or #RRGGBB')
    for key, low, high in [('width', 4, 64), ('stitch', 3, 12)]:
        if key in data and (type(data[key]) is not int or not low <= data[key] <= high):
            raise ValueError(f'{key} must be an integer between {low} and {high}')

def validate(data, ids):
    if not isinstance(data, dict):
        raise ValueError('Configuration must be an object')
    if set(data) - set(DEFAULT):
        raise ValueError('Unknown configuration keys: ' + ', '.join(set(data) - set(DEFAULT)))
    cfg = copy.deepcopy(DEFAULT)
    cfg.update(copy.deepcopy(data))
    if type(cfg['version']) is not int or cfg['version'] != 1:
        raise ValueError('Unsupported configuration version')
    for key in ('enabled', 'hide_maximized'):
        if type(cfg[key]) is not bool:
            raise ValueError(f'{key} must be boolean')
    if type(cfg['seed']) is not int or not 0 <= cfg['seed'] < 2**63:
        raise ValueError('seed must be a non-negative integer below 2^63')
    opacity = cfg['inactive_opacity']
    if type(opacity) not in (int, float) or not 0.1 <= opacity <= 1:
        raise ValueError('inactive_opacity must be between 0.1 and 1')
    validate_style(cfg, ids)
    if not isinstance(cfg['rules'], list) or len(cfg['rules']) > 256:
        raise ValueError('rules must be a list with at most 256 entries')
    for rule in cfg['rules']:
        if not isinstance(rule, dict) or set(rule) - {'wm_class', 'title', 'texture', 'color', 'width', 'stitch'}:
            raise ValueError('Invalid rule keys')
        if not any(k in rule for k in ('wm_class', 'title')):
            raise ValueError('Each rule needs wm_class or title')
        for key in ('wm_class', 'title'):
            if key in rule and (not isinstance(rule[key], str) or not 1 <= len(rule[key]) <= 256):
                raise ValueError(f'{key} must be a non-empty glob pattern up to 256 characters')
        validate_style(rule, ids)
    return cfg

def load(path, ids):
    if not path.exists():
        return validate({}, ids)
    if path.stat().st_size > 1_000_000:
        raise ValueError('Configuration is too large')
    return validate(json.loads(path.read_text()), ids)

def save(path, data, ids):
    cfg = validate(data, ids)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.config-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(cfg, out, indent=2, ensure_ascii=False)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def style_for(cfg, wm_class, title):
    """First matching rule wins; both match conditions are case-insensitive globs."""
    style = {k: cfg[k] for k in ('texture', 'color', 'width', 'stitch')}
    for rule in cfg['rules']:
        if all(fnmatch.fnmatchcase(value.casefold(), rule.get(key, '*').casefold())
               for key, value in [('wm_class', wm_class), ('title', title)]):
            style.update({k: rule[k] for k in style if k in rule})
            break
    return style
