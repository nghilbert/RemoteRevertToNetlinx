import asyncio, asyncssh, sys, getpass
from typing import List, Tuple, Dict

DEVICE_CONFIGS: Dict[str, Dict] = {
    "amx": {
        "username": "amx",
        "encryption_algs": [
            "aes128-cbc",
            "aes192-cbc",
            "aes256-cbc",
            "3des-cbc",
            "blowfish-cbc",
        ],
        "kex_algs": [
            "diffie-hellman-group14-sha1",
            "diffie-hellman-group1-sha1",
        ],
        "commands": ["help"],
    },
    "extron": {"username": "admin", "port": 22023, "commands": ["Help"]},
}


async def execute_commands(
    session: asyncssh.SSHClientConnection, commands: List[str]
) -> None:
    for command in commands:
        print(f"Executing command: {command}")
        try:
            result = await session.run(command, check=True, timeout=10)

            print(f"Output for command '{command}':")
            print(result.stdout)
            if result.stderr:
                print(f"Error (stderr) for command '{command}':")
                print(result.stderr)
        except asyncssh.ProcessError as exc:
            print(f"Error executing command '{command}': {exc}")
        except asyncio.TimeoutError:
            print(f"Command '{command}' timed out.")
        except Exception as exc:
            print(f"Unexpected error occurred while executing '{command}': {exc}")


async def run_client(
    host: str, device_type: str, password_map: Dict[str, str]
) -> asyncssh.SSHCompletedProcess:

    try:
        # Get the device configurations
        config = DEVICE_CONFIGS.get(device_type)
        if not config:
            raise ValueError(f"Unsupported device type: {device_type}")
        password = password_map.get(device_type)

        # Defines arguments for connections
        connect_args = {
            "host": host,
            "username": config["username"],
            "password": password,
            "known_hosts": None,
        }
        if "port" in config:
            connect_args["port"] = config["port"]
        if "encryption_algs" in config:
            connect_args["encryption_algs"] = config["encryption_algs"]
        if "kex_algs" in config:
            connect_args["kex_algs"] = config["kex_algs"]

        # Connect
        async with asyncssh.connect(**connect_args) as conn:
            print(f"Connected to {host} - {device_type}")
            await execute_commands(conn, config.get("commands", []))

    except (OSError, asyncssh.Error) as exc:
        print(f"[{host}] SSH connection failed: {exc}")


# runs multiple SSH clients at once. Takes a List of individual devices represented with Tuples. The Tuple stores the host IP and device_type
async def run_multiple_clients(devices: List[Tuple[str, str]]) -> None:

    # stores passwords securly obtained with getpass from user input
    password_map = {}
    for item in devices.items():
        item.add({"password": getpass.getpass(f"Enter the password for devices: ")})

    # call run_client for each device
    tasks = [
        run_client(host, device_type, password_map) for host, device_type in devices
    ]

    await asyncio.gather(*tasks)


# Declare the host IP and device kind for each device
devices = {
    "nsb-208-touchpad-1.av.ilstu.edu": {"kind": "amx"},
    "192.168.0.1": {
        "kind": "extron",
    },
}
try:
    asyncio.run(run_multiple_clients(devices))
except (OSError, asyncssh.Error) as exc:
    sys.exit("SSH connection failed: " + str(exc))
