import subprocess
from datetime import datetime

def run_command(command):
    result = subprocess.run(command, shell=True)
    return result.returncode == 0

try:
    commit_count = int(input("How many commits do you want to create? "))
except ValueError:
    print("Please enter a valid number.")
    exit()

auto_push = input("Automatically push after all commits? (y/n): ").lower()

for i in range(1, commit_count + 1):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    commit_message = (
        f"fix: resolved issue {i}/{commit_count} | {timestamp}"
    )

    success = run_command(
        f'git commit --allow-empty -m "{commit_message}"'
    )

    if success:
        print(f"[+] Commit {i}/{commit_count} created")
    else:
        print(f"[-] Failed to create commit {i}")
        break

print(f"\nFinished. Created {i} commit(s).")

if auto_push == "y":
    print("\nPushing to remote...")
    if run_command("git push"):
        print("[+] Push successful")
    else:
        print("[-] Push failed")