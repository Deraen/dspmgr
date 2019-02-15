# dspmgr

Script to automatically switch displaymodes (xrandr, multiple monitors)

## Features

- Keep one display always enabled
  - i3 will close there is no active output
  - generally this might be problem when you dock laptop and disable laptops display and enable two external monitors
- Match displays by regex
  - Refer to matched name from `right-of` etc. options

## Usage

```
dspmgr.py
```

Example for i3 which will also change backgrounds and set i3bar transparency for compton

```
bindsym $mod+Shift+F12 exec --no-startup-id dspmgr.py && rndbg.sh && transset -n i3bar 0.8
```

