"""Native GTK settings with live previews, per-window overrides and app rules."""
import copy
import shutil
from gi.repository import Gtk
from . import config
from .desktop import pixbuf
from .textures import Registry, border

class Settings(Gtk.Window):
    def __init__(self, controller):
        super().__init__(title='XFCE4 Sweaters Settings')
        self.controller = controller
        self.set_default_size(720,650)
        self.set_border_width(20)
        notebook = Gtk.Notebook()
        self.add(notebook)
        general = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin=16)
        notebook.append_page(general,Gtk.Label(label='Appearance'))
        headline = Gtk.Label(xalign=0)
        headline.set_markup('<span size="x-large" weight="bold">Warm borders for your windows</span>')
        general.pack_start(headline,False,False,0)
        self.preview = Gtk.Image()
        general.pack_start(self.preview,False,False,0)
        self.texture = self.combo()
        self.texture.set_active_id(controller.cfg['texture'])
        general.pack_start(self.row('Default texture',self.texture),False,False,0)
        self.color = Gtk.Entry(text=controller.cfg['color'])
        self.color.set_placeholder_text('random or #RRGGBB')
        general.pack_start(self.row('Main colour',self.color),False,False,0)
        self.width = Gtk.SpinButton.new_with_range(4,64,1)
        self.width.set_value(controller.cfg['width'])
        general.pack_start(self.row('Border width (px)',self.width),False,False,0)
        self.stitch = Gtk.SpinButton.new_with_range(3,12,1)
        self.stitch.set_value(controller.cfg['stitch'])
        general.pack_start(self.row('Stitch size (px)',self.stitch),False,False,0)
        self.opacity = Gtk.SpinButton.new_with_range(0.1,1,0.05)
        self.opacity.set_digits(2)
        self.opacity.set_value(controller.cfg['inactive_opacity'])
        general.pack_start(self.row('Inactive border opacity',self.opacity),False,False,0)
        self.enabled = Gtk.CheckButton(label='Show borders')
        self.enabled.set_active(controller.cfg['enabled'])
        general.pack_start(self.enabled,False,False,0)
        self.maximized = Gtk.CheckButton(label='Hide borders on maximized windows')
        self.maximized.set_active(controller.cfg['hide_maximized'])
        general.pack_start(self.maximized,False,False,0)
        buttons = Gtk.Box(spacing=8)
        for label,fn in [('Apply',self.apply),('Shuffle',lambda *_: controller.shuffle()),('Add PNG',self.import_png)]:
            b=Gtk.Button(label=label); b.connect('clicked',fn); buttons.pack_start(b,False,False,0)
        general.pack_start(buttons,False,False,0)
        self.status = Gtk.Label(xalign=0,wrap=True)
        general.pack_start(self.status,False,False,0)
        for widget,signal in [(self.texture,'changed'),(self.color,'changed'),(self.width,'value-changed'),(self.stitch,'value-changed')]:
            widget.connect(signal,lambda *_: self.update_preview())
        windows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin=16)
        notebook.append_page(windows,Gtk.Label(label='Windows and applications'))
        windows.pack_start(Gtk.Label(label='Pick an open window and assign it a texture.',xalign=0),False,False,0)
        self.window = Gtk.ComboBoxText()
        windows.pack_start(self.window,False,False,0)
        refresh=Gtk.Button(label='Refresh window list'); refresh.connect('clicked',self.refresh_windows)
        windows.pack_start(refresh,False,False,0)
        self.window_texture=self.combo()
        self.window_texture.set_active_id('random')
        windows.pack_start(self.row('Window texture',self.window_texture),False,False,0)
        self.window_color=Gtk.Entry(text='random')
        windows.pack_start(self.row('Window colour',self.window_color),False,False,0)
        self.title_pattern=Gtk.Entry()
        self.title_pattern.set_placeholder_text('For example: *project* (optional)')
        windows.pack_start(self.row('Title pattern for the rule',self.title_pattern),False,False,0)
        for label,fn in [('This window only (until closed)',self.assign_window),('Save rule for application',self.assign_app),('Reset selected window',self.reset_window)]:
            b=Gtk.Button(label=label); b.connect('clicked',fn); windows.pack_start(b,False,False,0)
        windows.pack_start(Gtk.Label(label='Saved rules: the first match wins.',xalign=0),False,False,0)
        self.rules=Gtk.ComboBoxText()
        windows.pack_start(self.rules,False,False,0)
        remove=Gtk.Button(label='Remove selected rule'); remove.connect('clicked',self.remove_rule)
        windows.pack_start(remove,False,False,0)
        self.window_status=Gtk.Label(xalign=0,wrap=True)
        windows.pack_start(self.window_status,False,False,0)
        self.refresh_windows(); self.refresh_rules(); self.update_preview()

    def row(self,label,widget):
        box=Gtk.Box(spacing=16)
        box.pack_start(Gtk.Label(label=label,xalign=0),True,True,0)
        box.pack_end(widget,False,False,0)
        return box

    def combo(self):
        combo=Gtk.ComboBoxText()
        combo.append('random','Random')
        combo.append('off','No border')
        for name in self.controller.registry.ids:
            spec=self.controller.registry.specs.get(name)
            combo.append(name,spec['name'] if spec else name[5:])
        return combo

    def global_style(self):
        return {'texture':self.texture.get_active_id(),'color':self.color.get_text().strip(),
                'width':self.width.get_value_as_int(),'stitch':self.stitch.get_value_as_int()}

    def update_preview(self):
        try:
            style=self.global_style()
            config.validate_style(style,self.controller.registry.ids)
            style=self.controller.registry.resolve(style,'preview',self.controller.cfg['seed'])
            if style['texture']=='off':
                self.preview.clear(); return
            self.preview.set_from_pixbuf(pixbuf(border(self.controller.registry,600,170,style)))
            self.status.set_text('Pattern preview. With random selection each window gets its own border.')
        except (ValueError,KeyError,OSError) as exc:
            self.status.set_text(str(exc))

    def apply(self,*_):
        try:
            self.controller.apply({**self.controller.cfg,**self.global_style(),'enabled':self.enabled.get_active(),
                                   'hide_maximized':self.maximized.get_active(),'inactive_opacity':self.opacity.get_value()})
            self.status.set_text('Settings saved.')
        except (ValueError,OSError) as exc:
            self.status.set_text(str(exc))

    def refresh_windows(self,*_):
        previous=self.window.get_active_id()
        self.window.remove_all()
        self.window_clients={str(c.xid):c for c in self.controller.clients}
        for key,client in self.window_clients.items():
            self.window.append(key,f'{client.wm_class}: {client.title[:65]}')
        if not previous or not self.window.set_active_id(previous):
            self.window.set_active(0)

    def selection(self):
        client=self.window_clients.get(self.window.get_active_id())
        if not client:
            raise ValueError('Select an open window.')
        style={'texture':self.window_texture.get_active_id(),'color':self.window_color.get_text().strip()}
        config.validate_style(style,self.controller.registry.ids)
        return client,style

    def assign_window(self,*_):
        try:
            client,style=self.selection()
            self.controller.overrides[client.xid]=style
            self.controller.dirty=True
            self.window_status.set_text('Applied to the selected window until it is closed.')
        except ValueError as exc:
            self.window_status.set_text(str(exc))

    def assign_app(self,*_):
        try:
            client,style=self.selection()
            if not client.wm_class:
                raise ValueError('The window has no WM_CLASS; use the per-window setting instead.')
            # Escape fnmatch metacharacters so a literal WM_CLASS is safe as a rule.
            literal=''.join({'[':'[[]','*':'[*]','?':'[?]'}.get(c,c) for c in client.wm_class)
            rule={'wm_class':literal,**style}
            title=self.title_pattern.get_text().strip()
            if title:
                rule['title']=title
            cfg=copy.deepcopy(self.controller.cfg)
            cfg['rules']=[r for r in cfg['rules'] if (r.get('wm_class'),r.get('title'))!=(rule['wm_class'],rule.get('title'))]
            cfg['rules'].insert(0,rule)
            self.controller.apply(cfg)
            self.controller.overrides.pop(client.xid,None)
            self.refresh_rules()
            self.window_status.set_text('Rule saved; it will also apply after a restart.')
        except (ValueError,OSError) as exc:
            self.window_status.set_text(str(exc))

    def reset_window(self,*_):
        try:
            client,_style=self.selection()
            self.controller.overrides.pop(client.xid,None)
            self.controller.dirty=True
            self.window_status.set_text('The window now follows application rules or the global settings.')
        except ValueError as exc:
            self.window_status.set_text(str(exc))

    def refresh_rules(self):
        self.rules.remove_all()
        for i,rule in enumerate(self.controller.cfg['rules']):
            self.rules.append(str(i),f"{rule.get('wm_class','*')} / {rule.get('title','*')} → {rule.get('texture','default')}")
        self.rules.set_active(0)

    def remove_rule(self,*_):
        key=self.rules.get_active_id()
        if key is not None:
            cfg=copy.deepcopy(self.controller.cfg)
            cfg['rules'].pop(int(key))
            try:
                self.controller.apply(cfg); self.refresh_rules()
            except (OSError,ValueError) as exc:
                self.window_status.set_text(str(exc))

    def import_png(self,*_):
        dialog=Gtk.FileChooserDialog(title='Add PNG texture',transient_for=self,action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons('Cancel',Gtk.ResponseType.CANCEL,'Add',Gtk.ResponseType.OK)
        file_filter=Gtk.FileFilter(); file_filter.set_name('PNG'); file_filter.add_pattern('*.png'); dialog.add_filter(file_filter)
        try:
            if dialog.run()==Gtk.ResponseType.OK:
                from pathlib import Path
                import tempfile
                source=Path(dialog.get_filename())
                with tempfile.TemporaryDirectory() as temp:
                    staged=Path(temp)/source.name
                    shutil.copyfile(source,staged)
                    check=Registry(Path(temp))
                    if check.errors or not check.custom:
                        raise ValueError('; '.join(check.errors) or 'Invalid texture')
                    dest=config.texture_dir(); dest.mkdir(parents=True,exist_ok=True)
                    target=dest/source.name
                    if target.exists():
                        raise ValueError('A texture with this name already exists. Rename the file.')
                    # Exclusive create prevents accidental replacement of an existing texture.
                    with target.open('xb') as out:
                        out.write(staged.read_bytes())
                self.controller.registry=Registry(config.texture_dir())
                texture='user:'+source.stem
                self.texture.append(texture,source.stem); self.window_texture.append(texture,source.stem)
                self.texture.set_active_id(texture)
                self.status.set_text('Texture added. Click "Apply".')
        except (ValueError,OSError) as exc:
            self.status.set_text(str(exc))
        finally:
            dialog.destroy()
