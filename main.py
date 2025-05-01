import asyncio, asyncssh, sys, getpass
from typing import List, Dict

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
    "extron": {"username": "admin", "port": 22023, "commands": ["A"]},
}


async def execute_extron_commands(
    session: asyncssh.SSHClientConnection, commands: List[str]
) -> None:

    # Create an interactive session
    process, chan = await session.create_session(
        asyncssh.SSHClientProcess, term_type="vt100"
    )

    # Execute each command
    for command in commands:
        print(f"Executing extron command: {command}")
        chan.stdin.write(command + "\r")

        # Wait for response and write to output
        await asyncio.sleep(0.5)
        output = await chan.stdout.read(1024)
        # Split the output into lines and skip the echoed command
        lines = output.split("\n")
        output = "\n".join(lines[1:])
        print(f"Extron response: {output.strip()}")


async def execute_commands(
    session: asyncssh.SSHClientConnection, commands: List[str], device_type: str
) -> None:

    # If the device is extron call execute extron commands from an interactie session.
    if device_type == "extron":
        await execute_extron_commands(session, commands)
    else:  # For all other device types, execute each command with session.run().
        for command in commands:
            print(f"Executing command: {command}")
            try:  # Execute command, wait for response, then print response.
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
                print(f"Error executing command '{command}': {exc}")


async def run_client(
    host: str,
    device_type: str,
) -> asyncssh.SSHCompletedProcess:

    try:
        # Get the device configurations
        config = DEVICE_CONFIGS.get(device_type)
        if not config:
            raise ValueError(f"Unsupported device type: {device_type}")

        # Defines arguments for connections
        connect_args = {
            "host": host,
            "username": config["username"],
            "password": config["password"],
            "known_hosts": None,
        }
        if "port" in config:
            connect_args["port"] = config["port"]
        if "encryption_algs" in config:
            connect_args["encryption_algs"] = config["encryption_algs"]
        if "kex_algs" in config:
            connect_args["kex_algs"] = config["kex_algs"]

        # Connect and execute commands
        async with asyncssh.connect(**connect_args) as conn:
            print(f"Connected to {host} - {device_type}")
            await execute_commands(conn, config.get("commands", []), device_type)

    except (OSError, asyncssh.Error) as exc:
        print(f"[{host}] SSH connection failed: {exc}")


# runs multiple SSH clients at once. Takes a List of individual devices represented with Tuples. The Tuple stores the host IP and device_type
async def run_multiple_clients(devices: Dict[str, List[str]]) -> None:
    # Prompt password for each device type
    for device_type in devices:
        password = getpass.getpass(f"Enter the password for '{device_type}': ")
        if device_type in DEVICE_CONFIGS:
            DEVICE_CONFIGS[device_type]["password"] = password
        else:
            print(f"Warning: Unknown device type '{device_type}'")

    # Loop through each IP (hosts) for each device type
    tasks = [
        run_client(host, device_type)
        for (device_type, hosts) in devices.items()
        for host in hosts
    ]

    await asyncio.gather(*tasks)


# Declare the host IP and device kind for each device
devices = {
    "amx": [
        "nsb-208-touchpad-1.av.ilstu.edu",
    ],
    "extron": [
        "192.168.0.1",
    ],
}
try:
    asyncio.run(run_multiple_clients(devices))
except (OSError, asyncssh.Error) as exc:
    sys.exit("SSH connection failed: " + str(exc))
