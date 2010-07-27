#!/usr/bin/env python

# Copyright (c) 2010 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Makes changes to mounted Chromium OS image to allow it to run with VMs

This script changes two files within the Chromium OS image to let the image
work with VMs, particularly QEMU

Currently this script does the following,
1.) Modify the post install script to remove EFI fixup section; the VM's we
support don't have EFI support anyway and this section of the script needs
access to the actual device drives

2.) For QEMU/KVM, we change the xorg.conf to remove mouse support and instead
change it to complete tablet support. This is done to provide better mouse
response in the VM since tablets work of absolute coordinates while the mouse
works of relative. In a screen that doesn't support a mouse grab (e.g., VNC),
relative coordinates can cause the mouse to be flaky

"""

from optparse import OptionParser
import os
import stat
import sys

USAGE = "usage: %prog --mounted_dir=directory --enable_tablet=[true]"

INPUT_SECTION_MARKER = r'Section "InputDevice"'
SECTION_END_MARKER = r'EndSection'

MOUSE_SECTION_IDENTIFIERS = []
MOUSE_SECTION_IDENTIFIERS += ['Identifier "Mouse']
MOUSE_SECTION_IDENTIFIERS += ['Identifier "USBMouse']

REPLACE_USB_MOUSE_PAIR = ('InputDevice "USBMouse" "AlwaysCore"', '')
XORG_CONF_FILENAME = os.path.join('etc', 'X11', 'xorg.conf')


TABLET_DEVICE_CONFIG = """
Section "InputDevice"
  Identifier  "Mouse1"
  Driver      "evdev"
  Option      "Device" "/dev/input/event2"
  Option      "CorePointer" "true"
EndSection
"""


# Modify the xorg.conf file to remove all mouse sections and replace it
# with ours containing the tablet - note: when running under QEMU, you
# *need* to specify the -usbdevice tablet option to get the mouse to work
def FixXorgConf(mount_point):
  xorg_conf_filename = os.path.join(mount_point, XORG_CONF_FILENAME)
  f = open(xorg_conf_filename, 'r')
  xorg_conf = f.read()
  f.close()

  more_sections = 1
  last_found = 0
  while (more_sections):
    # Find the input section.
    m1 = xorg_conf.find(INPUT_SECTION_MARKER, last_found)
    if m1 > -1:
      m2 = xorg_conf.find(SECTION_END_MARKER, m1)
      m2 += len(SECTION_END_MARKER)
      # Make sure the next iteration doesn't rinse/repeat.
      last_found = m2
      # Check if this is a mouse section.
      for ident in MOUSE_SECTION_IDENTIFIERS:
        if xorg_conf.find(ident, m1, m2) != -1:
          xorg_conf = xorg_conf[0:m1] + xorg_conf[m2:]
          last_found -= (m2-m1)
          break
    else:
      more_sections = 0

  xorg_conf = xorg_conf[0:last_found] + TABLET_DEVICE_CONFIG + \
              xorg_conf[last_found:]

  # Replace UsbMouse with Tablet.
  xorg_conf = xorg_conf.replace(REPLACE_USB_MOUSE_PAIR[0],
                                REPLACE_USB_MOUSE_PAIR[1])

  # Write the file back out.
  f = open(xorg_conf_filename, 'w')
  f.write(xorg_conf)
  f.close()

def main():
  parser = OptionParser(USAGE)
  parser.add_option('--mounted_dir', dest='mounted_dir',
                    help='directory where the Chromium OS image is mounted')
  parser.add_option('--enable_tablet', dest='enable_tablet',
                    default="true",
                    help='fixup image for qemu')
  (options, args) = parser.parse_args()

  if not options.mounted_dir:
    parser.error("Please specify the mount point for the Chromium OS image");
  if options.enable_tablet not in ('true', 'false'):
    parser.error("Please specify either true or false for --enable_tablet")

  if (options.enable_tablet == 'true'):
    FixXorgConf(options.mounted_dir)


if __name__ == '__main__':
  main()