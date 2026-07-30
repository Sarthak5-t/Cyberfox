from __future__ import annotations

import argparse
import logging
import os
import signal
import sys

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Ares ACP Mesh Node")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=9876, help="WebSocket port")
    parser.add_argument("--node-id", default="", help="Unique node identifier")
    parser.add_argument("--roles", default="", help="Comma-separated roles")
    parser.add_argument("--peers", default="", help="Comma-separated peer URLs")
    parser.add_argument("--auth-secret", default="", help="Mesh auth secret")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    import socket
    node_id = args.node_id or f"mesh-{socket.gethostname()}-{args.port}"
    roles = [r.strip() for r in args.roles.split(",") if r.strip()]
    peers = [p.strip() for p in args.peers.split(",") if p.strip()]

    from plugins.ares.mesh.client import get_mesh_client
    client = get_mesh_client()

    logger.info("Starting ACP Mesh node: %s on ws://%s:%s", node_id, args.host, args.port)
    logger.info("Roles: %s", roles or "(none)")
    if peers:
        logger.info("Peers: %s", peers)

    client.start(
        node_id=node_id,
        roles=roles,
        host=args.host,
        port=args.port,
        peers=peers,
        auth_secret=args.auth_secret,
    )

    def shutdown(sig, frame):
        logger.info("Shutting down mesh node...")
        client.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while client.is_connected:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
