#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
from subprocess import Popen, PIPE

from re import search, match
from yaml import load

config = load(open('.config/displays.yaml', 'r'))
maxdisplays = config['maxdisplays']


def getInfo():
    output = Popen('xrandr', stdout=PIPE).communicate()[0].strip().split('\n')

    connected = set()
    active = set()
    disabled = set()

    for line in output:
        status = search('(?P<name>[\w-]*) (?P<status>\w*)', line)
        info = search('(?P<w>\d+)x(?P<h>\d+)\+(?P<x>\d+)\+(?P<y>\d+) (?P<rotate>inverted|left|right|)', line)
        name = status.group('name')
        if status.group('status') == 'connected':
            connected.add(name)
            if info is not None:
                # Connected and active
                active.add(name)
            else:
                # Connected but not active
                disabled.add(name)

        elif status.group('status') == 'disconnected' and info is not None:
            # Not connected but active
            active.add(name)

    return (connected, active, disabled)


def match_config(c, connected):
    matched_config = dict()
    for key, val in c.items():
        if 'match' in val:
            found = False
            for name in connected:
                if match(val['match'], name):
                    found = True
                    new_config = val.copy()
                    new_config.pop('match')
                    new_config['name'] = name
                    matched_config[key] = new_config
                    print('Matched ', val['match'], name)

            if not found:
                return
        else:
            val['name'] = key
            matched_config[key] = val

    return matched_config


def select(connected):
    print('Connected', connected)
    for c in config['displays']:
        matched_config = match_config(c, connected)
        if not matched_config:
            break

        enabled = set([y['name'] for x, y in matched_config.items()])
        print('Checking config', enabled)
        if connected == enabled:
            return matched_config

    # If no config fully matched
    # Find first config which can be used (don't care if there are
    # unconfigured outputs connected)
    for c in config['displays']:
        matched_config = match_config(c, connected)
        if not matched_config:
            break

        enabled = set([y['name'] for x, y in matched_config.items() if y is not False])
        print('Checking config for partial match', enabled)
        if enabled.issubset(connected):
            return matched_config

    return


def buildOpt(key, val):
    r = ['--{}'.format(key)]
    if type(val) == str:
        r.append(val)
    elif type(val) == int:
        r.append(str(val))
    return r


def build(connected, active, disabled, selected):
    print('Connected', connected)

    name_to_key = dict()
    for k, v in selected.items():
        name_to_key[v['name']] = k

    enable = set([y['name'] for x, y in selected.items() if y is not False])

    # Disable active outputs that we aren't going to use
    disable = active - enable

    print('Disable', disable)

    print('Enable', enable)

    postcommands = []
    commands = []

    # Enable and disable outputs
    current = list(active)
    print('current', current)
    command = ['xrandr']
    while enable or disable:
        # If maxium amount of outputs are active, disable one
        if len(current) >= maxdisplays and disable:
            name = disable.pop()

            command += ['--output', name, '--off']

            # Split into another xrandr call
            if len(current) == maxdisplays:
                commands.append(command)
                command = ['xrandr']

            current.remove(name)
        elif enable:
            name = enable.pop()
            key = name_to_key[name]
            config = selected[key]

            command += ['--output', name]

            if config.get('disable-if-lid-closed', False):
                lid_state_file = open('/proc/acpi/button/lid/LID/state')
                lid_closed = False

                try:
                    lid_state = lid_state_file.read()
                    lid_closed = 'closed' in lid_state
                finally:
                    lid_state_file.close()

                if lid_closed:
                    command += ['--off']
                    continue

                config.pop('disable-if-lid-closed')

            for x, y in config.items():
                if x == 'name':
                    continue

                if type(y) == dict:
                    if 'name' in y:
                        y = selected[y['name']]['name']
                    else:
                        raise 'Bad config value', y

                # If this monitor is positioned relative to another
                # and another monitor isn't activated yet, delay positioning
                if x in ['right-of', 'left-of', 'top-of', 'bottom-of'] and y not in set(current):
                    postcommands += ['--output', name]
                    postcommands += buildOpt(x, y)
                else:
                    command += buildOpt(x, y)

            if len(current) < maxdisplays and name not in current:
                current.append(name)

        else:
            print('Impossible config?')
            return

        print('current', current)

    command += postcommands

    if len(command) > 1:
        commands.append(command)

    return commands


def run(commands):
    for cmd in commands:
        # Execute and wait until completion
        Popen(cmd).communicate()


def main():
    print('# DSPMGR')

    connected, active, disabled = getInfo()

    selected = select(connected)
    if not selected:
        return

    commands = build(connected, active, disabled, selected)
    if not commands:
        return

    print('Commands')
    print(commands)

    run(commands)


if __name__ == '__main__':
    main()
