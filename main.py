from regipy.registry import RegistryHive
import argparse
import os
import re
import configparser

def format_adapter_mac_for_linux(adapter_mac: str) -> str:
    raw = adapter_mac.strip().upper()
    if re.fullmatch(r"[0-9A-F]{12}", raw):
        return ":".join(raw[i:i + 2] for i in range(0, 12, 2))
    if re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", raw):
        return raw
    raise ValueError(
        f"Invalid adapter MAC address '{adapter_mac}'. Expected format like 70:CD:0D:C7:F6:72"
    )

def update_key(info_file, key_name, key_value):
    if key_name not in info_file:
        print(f"Info file for target Bluetooth device does not have a {key_name} field")
        exit(1)
    if args.dry_run:
        print(f"Would update {key_name}")
    else:
        info_file[key_name]["Key"] = key_value.hex()

parser = argparse.ArgumentParser(
                    prog='m240_bt_copy',
                    description='Copies Bluetooth keys from a Windows registry hive')
parser.add_argument('--adapter', help='The MAC address of the Bluetooth adapter to copy keys for')
parser.add_argument('--device', help='The MAC address of the Bluetooth device to copy keys for')
parser.add_argument('--target', help='The MAC address of the target Bluetooth device to copy keys to')
parser.add_argument('--dry-run', action='store_true', help='Print the actions that would be taken without actually performing them')
args = parser.parse_args()

print("Loading registry hive...")
reg_path = "/mnt/windows/Windows/System32/config/SYSTEM"
reg = RegistryHive(reg_path)

# Find the Bluetooth adapter
bt = reg.get_key('\ControlSet001\Services\BTHPORT\Parameters\Keys')
if bt.subkey_count == 0:
    print("No Bluetooth adapters found")
    exit(1)
elif args.adapter is not None:
    adapter_key = None
    for subkey in bt.iter_subkeys():
        if subkey.name == args.adapter:
            adapter_key = subkey
            break
    if adapter_key is None:
        print(f"Could not find Bluetooth adapter with MAC address {args.adapter}")
        exit(1)
    print(f"Found Bluetooth adapter with MAC address {args.adapter}")
elif bt.subkey_count == 1:
    
    adapter_key = bt.iter_subkeys().__next__()
    print(f"Found one Bluetooth adapter: {adapter_key.name}")
else:
    print("Found multiple Bluetooth adapters. Please specify which one to copy keys for using the --adapter argument.")
    print("Available adapters:")
    for subkey in bt.iter_subkeys():
        print(subkey.name)
    exit(1)

# Find the Bluetooth device
if (adapter_key.subkey_count == 0):
    print("No Bluetooth devices found for the specified adapter")
    exit(1)
elif args.device is not None:
    device_key = None
    for subkey in adapter_key.iter_subkeys():
        if subkey.name == args.device:
            device_key = subkey
            break
    if device_key is None:
        print(f"Could not find Bluetooth device with MAC address {args.device} for the specified adapter")
        exit(1)
    print(f"Found Bluetooth device with MAC address {args.device} for the specified adapter")
elif adapter_key.subkey_count == 1:
    device_key = adapter_key.iter_subkeys().__next__()
    print(f"Found one Bluetooth device for the specified adapter: {device_key.name}")
else:
    print("Found multiple Bluetooth devices for the specified adapter. Please specify which one to copy keys for using the --device argument.")
    print("Available devices:")
    for subkey in adapter_key.iter_subkeys():
        print(subkey.name)
    exit(1)

# Extract the keys
key_types = ["LTK", "IRK"]
keys = {}
for value in device_key.iter_values():
    if value.name in key_types:
        keys[value.name] = value.value
print("Extracted Bluetooth keys:")
for key_name, key_value in keys.items():
    print(f"{key_name}: {key_value}")

# Find the target adapter
adapter_mac_linux = format_adapter_mac_for_linux(adapter_key.name)
adapter_bt_folder = f"/var/lib/bluetooth/{adapter_mac_linux}"
try:
    target_devices = os.listdir(adapter_bt_folder)
except FileNotFoundError:
    print(f"Bluetooth adapter folder not found: {adapter_bt_folder}")
    exit(1)
except PermissionError:
    print(f"Permission denied when accessing Bluetooth adapter folder: {adapter_bt_folder}")
    print("Please run this script with appropriate permissions (e.g. as root) to access Bluetooth adapter information.")
    print("Try: sudo $(printenv VIRTUAL_ENV)/bin/python3 main.py")
    exit(1)

# Find the target device
source_device = device_key.name
source_mac_linux = format_adapter_mac_for_linux(source_device)
target_device = source_device
if args.target is not None:
    target_device = args.target
target_mac_linux = format_adapter_mac_for_linux(target_device)
if target_mac_linux not in target_devices:
    print(f"Target Bluetooth device with MAC address {target_mac_linux} not found for the specified adapter.")
    print("Available target devices:")
    for device in target_devices:
        print(device)
    exit(1)
info_file = configparser.ConfigParser()
info_file.read(os.path.join(adapter_bt_folder, target_mac_linux, "info"))
if "General" not in info_file or "Name" not in info_file["General"]:
    print(f"Could not read device name from info file for target Bluetooth device with MAC address {target_mac_linux}")
    exit(1)
device_name = info_file["General"]["Name"]
print(f"Found target Bluetooth device {device_name} with MAC address {target_mac_linux}")

# Update the keys in the target device's info file
for key_name, key_value in keys.items():
    if key_name == "IRK":
        update_key(info_file, "IdentityResolvingKey", key_value)
    elif key_name == "LTK":
        update_key(info_file, "PeripheralLongTermKey", key_value)
        update_key(info_file, "SlaveLongTermKey", key_value)
    else:
        print(f"Unknown key type '{key_name}'")
if not args.dry_run:
    print(f"Saving updated info file")
    with open(os.path.join(adapter_bt_folder, target_mac_linux, "info"), "w") as f:
        info_file.write(f)
else:
    print(f"Would save updated info file")

# Rename the folder, if necessary
if target_mac_linux != source_mac_linux:
    source_folder = os.path.join(adapter_bt_folder, source_mac_linux)
    target_folder = os.path.join(adapter_bt_folder, target_mac_linux)
    if os.path.exists(source_folder):
        print(f"Source folder already exists: {source_folder}")
        print("Please remove or rename the existing folder before running this script.")
        exit(1)
    try:
        if not args.dry_run:
            os.rename(target_folder, source_folder)
            print(f"Renamed Bluetooth adapter folder from {target_folder} to {source_folder}")
        else:
            print(f"Would rename Bluetooth adapter folder from {target_folder} to {source_folder}")
    except Exception as e:
        print(f"Failed to rename Bluetooth adapter folder: {e}")
        exit(1)

