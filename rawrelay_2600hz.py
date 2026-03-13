import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import socket
import random
import struct
import hashlib
import time
import dns.resolver
import threading
import re

MAGIC_MAIN = b'\xf9\xbe\xb4\xd9'

peer_status = {}

window = tk.Tk()
window.title("RawRelay - Non-Standard TX Injector - Broadcast 2600")
window.geometry("1000x720")

ipv4_enabled = tk.BooleanVar(value=True)
ipv6_enabled = tk.BooleanVar(value=False)
send_count = tk.IntVar(value=9001)
tx_per_node = tk.IntVar(value=1)
retry_count = tk.IntVar(value=0)

def sha256d(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def make_message(command, payload):
    command = command.encode('ascii') + b'\x00' * (12 - len(command))
    length = struct.pack('<I', len(payload))
    checksum = sha256d(payload)[:4]
    return MAGIC_MAIN + command + length + checksum + payload

def make_version_payload():
    version = 70015
    services = 0
    timestamp = int(time.time())
    addr_services = 0
    addr_ip = b"\x00" * 16
    addr_port = 8333
    nonce = random.getrandbits(64)
    user_agent_bytes = b'\x00'
    start_height = 0
    relay = 0
    payload = struct.pack('<iQQ', version, services, timestamp)
    payload += struct.pack('>Q16sH', addr_services, addr_ip, addr_port)
    payload += struct.pack('>Q16sH', addr_services, addr_ip, addr_port)
    payload += struct.pack('<Q', nonce)
    payload += user_agent_bytes
    payload += struct.pack('<i?', start_height, relay)
    return payload

def send_tx_to_peer(ip, txhex, log_callback):
    try:
        log_callback(f"[*] Connecting to {ip}:8333")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((ip, 8333))
        s.sendall(make_message("version", make_version_payload()))
        time.sleep(0.5)
        s.sendall(make_message("verack", b""))
        time.sleep(0.5)
        tx_payload = bytes.fromhex(txhex)
        s.sendall(make_message("tx", tx_payload))
        s.close()
        peer_status[ip] = '✓'
        log_callback(f"[✓] TX sent to {ip}")
    except Exception as e:
        peer_status[ip] = '✗'
        log_callback(f"[✗] Failed to send to {ip}: {str(e)}")
    update_peer_list()

def query_dns_seeders(log_callback):
    seeders = [
        "seed.bitcoin.sipa.be",
        "dnsseed.bluematt.me",
        "dnsseed.bitcoin.dashjr.org",
        "seed.bitcoinstats.com",
        "seed.bitcoin.jonasschnelli.ch",
        "seed.btc.petertodd.org"
    ]
    record_types = []
    if ipv4_enabled.get():
        record_types.append('A')
    if ipv6_enabled.get():
        record_types.append('AAAA')
    if not record_types:
        ipv4_enabled.set(True)
        record_types.append('A')
    ips = set()
    lock = threading.Lock()
    def query(seeder, rtype):
        try:
            log_callback(f"[*] Querying {seeder} ({rtype})...")
            result = dns.resolver.resolve(seeder, rtype)
            with lock:
                for ipval in result:
                    ip = ipval.to_text()
                    if ip not in peer_status:
                        peer_status[ip] = '○'
                    ips.add(ip)
                    log_callback(f"[+] Found IP: {ip}")
        except Exception as e:
            log_callback(f"[!] Error resolving {seeder}: {str(e)}")
    threads = [threading.Thread(target=query, args=(seeder, rtype)) for seeder in seeders for rtype in record_types]
    for t in threads: t.start()
    for t in threads: t.join()
    update_peer_list()
    return list(ips)

def parse_txs(raw):
    try:
        return re.findall(r'[a-fA-F0-9]{64,}', raw.replace("\n", " ").replace(",", " "))
    except Exception:
        return []

def send_with_retries(ip, txhex, retries, log_callback):
    for attempt in range(retries + 1):
        try:
            send_tx_to_peer(ip, txhex, log_callback)
            break
        except:
            if attempt == retries:
                log_callback(f"[✗] Failed after {retries+1} attempts to {ip}")

def send_to_multiple_peers(raw_input, count, txs_per_peer, log_callback):
    tx_list = parse_txs(raw_input)
    if not tx_list:
        messagebox.showerror("Error", "No valid TXs found.")
        return
    peers = query_dns_seeders(log_callback)
    if not peers:
        log_callback("[!] No peers found.")
        return
    random.shuffle(peers)
    selected = peers[:count]
    for i, ip in enumerate(selected):
        for j in range(min(txs_per_peer, len(tx_list))):
            tx_index = (i * txs_per_peer + j) % len(tx_list)
            txhex = tx_list[tx_index]
            send_with_retries(ip, txhex, retry_count.get(), log_callback)
    log_callback("[*] Broadcast routine complete.")

def handle_submit_tx():
    txhex = tx_input.get("1.0", tk.END).strip()
    if not txhex:
        messagebox.showwarning("Missing TX", "Please enter raw TX hexes.")
        return
    output_box.delete("1.0", tk.END)
    threading.Thread(target=send_to_multiple_peers, args=(txhex, send_count.get(), tx_per_node.get(), log_output)).start()

def handle_query_peers():
    output_box.delete("1.0", tk.END)
    threading.Thread(target=lambda: query_dns_seeders(log_output)).start()

def log_output(message):
    output_box.insert(tk.END, message + "\n")
    output_box.see(tk.END)

def update_peer_list():
    if not hasattr(update_peer_list, "listbox"):
        return
    update_peer_list.listbox.delete(0, tk.END)
    sorted_peers = sorted(peer_status.items(), key=lambda x: (x[1] != '✓', x[1] != '✗', x[1] != '○'))
    for ip, status in sorted_peers:
        update_peer_list.listbox.insert(tk.END, f"{status} {ip}")

notebook = ttk.Notebook(window)
notebook.pack(pady=10, expand=True, fill='both')

main_frame = ttk.Frame(notebook)
peers_frame = ttk.Frame(notebook)
notebook.add(main_frame, text="Main")
notebook.add(peers_frame, text="Peers")

frame = tk.Frame(main_frame)
frame.pack(pady=10)

tx_label = tk.Label(frame, text="Raw TX Hexes (comma or space separated):")
tx_label.grid(row=0, column=0, sticky="w")
tx_input = scrolledtext.ScrolledText(frame, height=8, width=110)
tx_input.grid(row=1, column=0, columnspan=3, padx=5, pady=5)

submit_btn = tk.Button(frame, text="Broadcast TX", command=handle_submit_tx, width=20, bg="green", fg="white")
submit_btn.grid(row=2, column=0, padx=5, pady=5)

query_btn = tk.Button(frame, text="Query DNS Seeders", command=handle_query_peers, width=20)
query_btn.grid(row=2, column=1, padx=5, pady=5)

config_frame = tk.Frame(main_frame)
config_frame.pack(pady=10)

ipv4_checkbox = tk.Checkbutton(config_frame, text="IPv4", variable=ipv4_enabled, command=lambda: ipv4_enabled.set(True) if not ipv4_enabled.get() and not ipv6_enabled.get() else None)
ipv4_checkbox.grid(row=0, column=0, padx=10)

ipv6_checkbox = tk.Checkbutton(config_frame, text="IPv6", variable=ipv6_enabled, command=lambda: ipv6_enabled.set(True) if not ipv6_enabled.get() and not ipv4_enabled.get() else None)
ipv6_checkbox.grid(row=0, column=1, padx=10)

tk.Label(config_frame, text="Nodes to send to:").grid(row=1, column=0, sticky="e", padx=5)
tk.Entry(config_frame, textvariable=send_count, width=6).grid(row=1, column=1, padx=5)

tk.Label(config_frame, text="TXs per node:").grid(row=2, column=0, sticky="e", padx=5)
tk.Entry(config_frame, textvariable=tx_per_node, width=6).grid(row=2, column=1, padx=5)

tk.Label(config_frame, text="Retries:").grid(row=3, column=0, sticky="e", padx=5)
tk.Entry(config_frame, textvariable=retry_count, width=6).grid(row=3, column=1, padx=5)

output_box = scrolledtext.ScrolledText(main_frame, height=25, width=120)
output_box.pack(padx=10, pady=10)

peer_listbox = tk.Listbox(peers_frame, height=30, width=120)
peer_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar = tk.Scrollbar(peers_frame, orient=tk.VERTICAL, command=peer_listbox.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
peer_listbox.config(yscrollcommand=scrollbar.set)
update_peer_list.listbox = peer_listbox

window.mainloop()
