# RawRelay / 2600hz

A policy probe for the Bitcoin network. RawRelay queries DNS seeders for live node IPs and pushes raw transactions directly over TCP, bypassing standard relay rules entirely. No node, no private mempool service, no middlemen — a tool for mapping which nodes will accept your specific non-standard transactions.

Named as an homage to [phone phreakers](https://en.wikipedia.org/wiki/Phone_phreaking) — 2600 Hz was the tone used to seize AT&T trunk lines. This tool does the same thing to the Bitcoin network: direct-dials nodes instead of routing through intermediaries.

## What it does

Before this tool, getting a non-standard transaction into miner mempools required either:
- A trusted clique of nodes running custom relay policies, or
- A paid private mempool service (MARA Slipstream, etc.)

RawRelay takes the Bitcoin-native approach: query the public DNS seeders for live node IPs, open direct TCP connections to port 8333, perform a bare `version`/`verack` handshake, and push your raw transaction hex straight to each peer's mempool — no node required on your end.

Originally built as part of a broader "nodeless" and policy-sniffing infrastructure. Re-released during sub-1-sat/vB summer (2024) as a tool for probing mempool policy variations across the network.

## On-chain provenance

The source code of this tool was published on-chain in an oversized OP_RETURN at:

**[`2b27ebd53e6cff168660a4aec74a5a28cd3fa313ef27c82df0194f80c7f3663a`](https://mempool.space/tx/2b27ebd53e6cff168660a4aec74a5a28cd3fa313ef27c82df0194f80c7f3663a)**

Block 905939.

This TX was broadcast using the tool it contains. At 1.02 sat/vB with an oversized OP_RETURN, it would have been dropped by any node running default relay policy at the time. It reached miners because RawRelay bypassed relay entirely, pushing directly to nodes via DNS seeder discovery.

This predates the policy changes that later made large OP_RETURNs and sub-1-sat/vB transactions more widely accepted. The tool remains useful for any transaction the default relay layer rejects — probing the network node by node to find backdoors into mempools that will accept it.

## Requirements

```
pip install dnspython
```

Tkinter is included with standard Python.

## Usage

```
python rawrelay_2600hz.py
```

1. Paste one or more raw transaction hexes (comma or space separated)
2. Click **Query DNS Seeders** to populate the peer list with live nodes
3. Click **Broadcast TX** to push to the network
4. Configure nodes to target, TXs per node, and retries as needed

## License

MIT
