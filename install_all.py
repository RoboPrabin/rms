import subprocess
import sys

requirements_file = r"D:\ANJIT\Anjit\PROJECT 2026\rms\requirements.txt"

failed = []

with open(requirements_file, "r", encoding="utf-8") as f:
    packages = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#")
    ]

for package in packages:
    print(f"\nInstalling: {package}")

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", package]
    )

    if result.returncode != 0:
        print(f"FAILED: {package}")
        failed.append(package)

print("\n" + "=" * 50)
print("INSTALLATION COMPLETED")
print("=" * 50)

if failed:
    print("\nFailed packages:")
    for pkg in failed:
        print(pkg)

    with open("failed_packages.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(failed))

    print("\nFailed packages saved to failed_packages.txt")
else:
    print("\nAll packages installed successfully!")