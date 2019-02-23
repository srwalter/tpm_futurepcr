import os
from .util import (
    extend_pcr_with_data,
    find_mountpoint_by_partuuid,
)

def _efivar_read(name, uuid):
    path = "/sys/firmware/efi/efivars/%s-%s" % (name, uuid)
    with open(path, "rb") as fh:
        buf = fh.read()
        return buf[4:]

def loader_get_esp_partuuid():
    buf = _efivar_read("LoaderDevicePartUUID", "4a67b082-0a4c-41cf-b6c7-440b29bb8c4f")
    return buf.decode("utf-16le").rstrip("\0")

def loader_get_current_entry():
    buf = _efivar_read("LoaderEntrySelected", "4a67b082-0a4c-41cf-b6c7-440b29bb8c4f")
    return buf.decode("utf-16le").rstrip("\0")

def _to_efi_path(path):
    # kinda match systemd.git:src/boot/efi/util.c:stra_to_path()
    # (except for the utf16 part, that'll be done on the whole cmdline)
    path = path.replace("/", "\\")
    if not path.startswith("\\"):
        path = "\\" + path
    return path

def loader_parse_config(name, esp=None):
    # match systemd.git:src/boot/efi/boot.c:line_get_key_value()
    esp = esp or "/boot"
    path = os.path.join(esp, "loader/entries/%s.conf" % name)
    config = []
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if (not line) or (line[0] == "#"):
                continue
            try:
                key, val = line.split(None, 1)
            except ValueError:
                continue
            if val[0] == "\"" and val[-1] == "\"":
                val = val[1:-1]
            config.append((key, val))
    return config

def loader_get_cmdline(entry, esp=None):
    # match systemd.git:src/boot/efi/boot.c:config_entry_add_from_file()
    config = loader_parse_config(entry, esp)
    initrd = []
    options = []
    for key, val in config:
        if key == "initrd":
            initrd.append("initrd=" + _to_efi_path(val))
        elif key == "options":
            options.append(val)
    return " ".join([*initrd, *options])

def loader_get_next_cmdline():
    entry = loader_get_current_entry()
    esp = find_mountpoint_by_partuuid(loader_get_esp_partuuid())
    return loader_get_cmdline(entry, esp)

def loader_extend_pcr8(pcr_value, cmdline):
    cmdline = (cmdline + "\0").encode("utf-16le")
    return extend_pcr_with_data(pcr_value, cmdline)
