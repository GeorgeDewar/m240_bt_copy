from regipy.registry import RegistryHive
import argparse

parser = argparse.ArgumentParser(
                    prog='m240_bt_copy',
                    description='Copies Bluetooth keys from a Windows registry hive')
parser.add_argument('--adapter', help='The MAC address of the Bluetooth adapter to copy keys for')
parser.add_argument('--device', help='The MAC address of the Bluetooth device to copy keys for')
args = parser.parse_args()

reg_path = "/mnt/windows/Windows/System32/config/SYSTEM"
reg = RegistryHive(reg_path)

# Find the Bluetooth adapter
bt = reg.get_key('\ControlSet001\Services\BTHPORT\Parameters\Keys')
if bt.subkey_count == 0:
    print("No Bluetooth adapters found in the registry hive")
    exit(1)
elif args.adapter is not None:
    adapter_key = None
    for subkey in bt.iter_subkeys():
        if subkey.name == args.adapter:
            adapter_key = subkey
            break
    if adapter_key is None:
        print(f"Could not find Bluetooth adapter with MAC address {args.adapter} in the registry hive")
        exit(1)
    print(f"Found Bluetooth adapter with MAC address {args.adapter} in the registry hive. Copying keys...")
elif bt.subkey_count == 1:
    
    adapter_key = bt.iter_subkeys().__next__()
    print(f"Found one Bluetooth adapter in the registry hive: {adapter_key.name}")
else:
    print("Found multiple Bluetooth adapters in the registry hive. Please specify which one to copy keys for using the --adapter argument.")
    print("Available adapters:")
    for subkey in bt.iter_subkeys():
        print(subkey.name)
    exit(1)

# Find the Bluetooth device
if (adapter_key.subkey_count == 0):
    print("No Bluetooth devices found for the specified adapter in the registry hive")
    exit(1)
elif args.device is not None:
    device_key = None
    for subkey in adapter_key.iter_subkeys():
        if subkey.name == args.device:
            device_key = subkey
            break
    if device_key is None:
        print(f"Could not find Bluetooth device with MAC address {args.device} for the specified adapter in the registry hive")
        exit(1)
    print(f"Found Bluetooth device with MAC address {args.device} for the specified adapter in the registry hive.")
elif adapter_key.subkey_count == 1:
    device_key = adapter_key.iter_subkeys().__next__()
    print(f"Found one Bluetooth device for the specified adapter in the registry hive: {device_key.name}")
else:
    print("Found multiple Bluetooth devices for the specified adapter in the registry hive. Please specify which one to copy keys for using the --device argument.")
    print("Available devices:")
    for subkey in adapter_key.iter_subkeys():
        print(subkey.name)
    exit(1)
