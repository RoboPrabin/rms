import subprocess
import ipaddress
import concurrent.futures


def ping_ip(ip):
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "500", str(ip)],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return ip, result.returncode == 0
    except subprocess.TimeoutExpired:
        return ip, False


def scan_network(network="192.168.1.0/24"):
    net = ipaddress.ip_network(network, strict=False)
    total = net.num_addresses
    print(f"Scanning {network} ({total} IPs)...")

    live = []
    free = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(ping_ip, ip): ip for ip in net.hosts()}
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            ip, alive = future.result()
            if alive:
                live.append(str(ip))
            else:
                free.append(str(ip))
            if i % 32 == 0 or i == total:
                print(f"  Progress: {i}/{total - 2}")

    return sorted(live), sorted(free)


if __name__ == "__main__":
    live, free = scan_network("192.168.1.0/24")
    print(f"\nLive IPs ({len(live)}):")
    for ip in live:
        print(f"  {ip}")
    print(f"\nFree IPs ({len(free)}):")
    for ip in free:
        print(f"  {ip}")
