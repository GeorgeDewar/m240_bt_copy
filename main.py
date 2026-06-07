from regipy.registry import RegistryHive
import argparse
import os
import re
import subprocess


def format_adapter_mac_for_linux(adapter_mac: str) -> str:
    raw = adapter_mac.strip().upper()
    if re.fullmatch(r"[0-9A-F]{12}", raw):
        return ":".join(raw[i:i + 2] for i in range(0, 12, 2))
    if re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", raw):
        return raw
    raise ValueError(
        f"Invalid adapter MAC address '{adapter_mac}'. Expected format like 70:CD:0D:C7:F6:72"
    )

parser = argparse.ArgumentParser(
                    prog='m240_bt_copy',
                    description='Copies Bluetooth keys from a Windows registry hive')
parser.add_argument('--adapter', help='The MAC address of the Bluetooth adapter to copy keys for')
parser.add_argument('--device', help='The MAC address of the Bluetooth device to copy keys for')
parser.add_argument('--target', help='The MAC address of the target Bluetooth device to copy keys to')
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
target_device = device_key.name
if args.target is not None:
    target_device = args.target
target_mac_linux = format_adapter_mac_for_linux(target_device)
if target_mac_linux not in target_devices:
    print(f"Target Bluetooth device with MAC address {target_mac_linux} not found for the specified adapter.")
    print("Available target devices:")
    for device in target_devices:
        print(device)
    exit(1)
print(f"Found target Bluetooth device with MAC address {target_mac_linux}")
