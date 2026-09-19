import os
import time
import requests

# --- CONFIGURATION ---
DATA_URL = os.getenv("DATA_URL")  # URL containing name::link lines
DISCORD_WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DOWNLOAD_DIR = "./downloads"
MAX_FILE_SIZE_MB = 80
MAX_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

def upload_to_pastebin(text_content):
    """Uploads the execution report to paste.c-net.org and returns the URL."""
    try:
        # paste.c-net.org accepts raw text via POST and returns the full URL in the response text
        response = requests.post("https://paste.c-net.org/", data=text_content.encode('utf-8'))
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        print(f"[-] Failed to upload report to paste.c-net.org: {e}")
    return "Report upload failed."

def download_file(name, link):
    """Downloads a file, capping it at 80MB."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    safe_name = "".join([c if c.isalnum() else "_" for c in name])
    file_path = os.path.join(DOWNLOAD_DIR, f"{safe_name}.file")
    
    start_time = time.time()
    downloaded_bytes = 0
    
    try:
        with requests.get(link, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        downloaded_bytes += len(chunk)
                        if downloaded_bytes > MAX_BYTES:
                            excess = downloaded_bytes - MAX_BYTES
                            f.write(chunk[:-excess])
                            downloaded_bytes = MAX_BYTES
                            break
                        f.write(chunk)
                        
        duration = round(time.time() - start_time, 2)
        size_mb = round(downloaded_bytes / (1024 * 1024), 2)
        return True, f"Success | Size: {size_mb} MB | Time: {duration}s"
    except Exception as e:
        return False, f"Failed | Error: {str(e)}"

def main():
    print("[*] Fetching data source...")
    report_lines = []
    report_lines.append("=== AUTOMATED DOWNLOAD EXECUTION REPORT ===")
    report_lines.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        resp = requests.get(DATA_URL)
        resp.raise_for_status()
        entries = resp.text.strip().splitlines()
    except Exception as e:
        error_msg = f"Critical Error: Failed to fetch data source URL. Details: {e}"
        print(f"[-] {error_msg}")
        return

    success_count = 0
    fail_count = 0

    for idx, line in enumerate(entries, 1):
        if "::" not in line:
            continue
        
        name, link = line.split("::", 1)
        name = name.strip()
        link = link.strip()
        
        # Prints both the item name and the link while running
        print(f"[{idx}/{len(entries)}] Downloading: {name}")
        print(f"    Link: {link}")
        
        status, details = download_file(name, link)
        
        if status:
            success_count += 1
            report_lines.append(f"[SUCCESS] {name} ({link}) -> {details}")
        else:
            fail_count += 1
            report_lines.append(f"[FAILURE] {name} ({link}) -> {details}")
        time.sleep(2)

    # Finalize report summary
    report_lines.insert(2, f"Summary: {success_count} Succeeded, {fail_count} Failed\n" + "-"*40)
    full_report_text = "\n".join(report_lines)

    print("[*] Uploading report to paste.c-net.org...")
    paste_link = upload_to_pastebin(full_report_text)

    print("[*] Sending notification to Discord...")
    payload = {
        "username": "GoFile Max",
        "avatar_url": "https://gofile.io/favicon.ico",
        "content": f"📥 **Download Job Completed!**\n• Success: {success_count}\n• Failed: {fail_count}",
        "embeds": [{
            "title": "📋 Detailed Execution Report",
            "description": f"Click here to view full logs: [View Report]({paste_link})",
            "color": 3066993 if fail_count == 0 else 15158332
        }]
    }
    
    requests.post(DISCORD_WEBHOOK_URL, json=payload)
    print("[+] Done!")

if __name__ == "__main__":
    main()
