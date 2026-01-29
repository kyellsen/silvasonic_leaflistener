import json
import logging
import os
import signal
import sys
import threading
import time

import apprise
import redis
import structlog

# Configure Logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = structlog.get_logger("monitor")

# Config
REDIS_HOST = os.getenv("REDIS_HOST", "silvasonic_redis")
APPRISE_URLS = os.getenv("APPRISE_URLS", "")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 10))

# Service Timeouts (Seconds)
TIMEOUTS = {
    "recorder": 120,
    "controller": 60,
    "processor": 300,  # File processing can block?
    "birdnet": 300,
    "uploader": 3600,
}

shutdown_event = threading.Event()


class Monitor:
    def __init__(self):
        self.apobj = apprise.Apprise()
        if APPRISE_URLS:
            self.apobj.add(APPRISE_URLS)

        self.redis = redis.Redis(host=REDIS_HOST, port=6379, db=0, socket_connect_timeout=5)
        self.service_states = {}  # {service_id: "Running" | "Down"}

    def run(self):
        logger.info("Silvasonic Monitor V2 Starting...")

        # 1. Start Pub/Sub Listener
        pubsub_thread = threading.Thread(target=self.listen_alerts, daemon=True, name="PubSub")
        pubsub_thread.start()

        # 2. Start Watchdog Loop
        self.watchdog_loop()

    def listen_alerts(self):
        r = redis.Redis(host=REDIS_HOST, port=6379, db=0)
        pubsub = r.pubsub()
        pubsub.subscribe("alerts")

        logger.info("Subscribed to 'alerts' channel.")

        while not shutdown_event.is_set():
            try:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
                if message:
                    try:
                        data = json.loads(message["data"])
                        title = data.get("title", "Silvasonic Alert")
                        body = data.get("body", "")
                        tag = data.get("tag", "info")

                        logger.info("received_alert", title=title, tag=tag)

                        # Notify
                        self.apobj.notify(
                            body=body,
                            title=title,
                        )
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        logger.error("alert_process_failed", error=str(e))
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error("pubsub_error", error=str(e))
                time.sleep(5)

    def watchdog_loop(self):
        logger.info("Watchdog loop started.")
        while not shutdown_event.is_set():
            try:
                self.check_heartbeats()
                self.send_self_heartbeat()
            except Exception:
                logger.exception("watchdog_error")

            time.sleep(CHECK_INTERVAL)

    def check_heartbeats(self):
        # Scan keys
        keys = self.redis.keys("status:*")
        now = time.time()

        # Track seen to detect missing
        seen_services = set()

        for k in keys:
            key_str = k.decode()
            try:
                if key_str == "status:monitor":
                    continue  # Skip self

                parts = key_str.split(":")
                # e.g. status:controller, status:recorder:front

                service_type = parts[1]
                instance_id = "_".join(parts[1:])  # controller, recorder_front

                content = self.redis.get(key_str)
                if not content:
                    continue

                # Try to parse
                try:
                    data = json.loads(content)
                    last_ts = float(data.get("timestamp", 0))
                except Exception:
                    # Maybe integer timestamp?
                    last_ts = float(content)

                seen_services.add(instance_id)

                # Check Timeout
                threshold = TIMEOUTS.get(service_type, 120)
                diff = now - last_ts

                is_down = diff > threshold
                prev_status = self.service_states.get(instance_id, "Unknown")

                if is_down and prev_status != "Down":
                    self.notify_state_change(
                        instance_id, "Down", f"Timeout ({int(diff)}s > {threshold}s)"
                    )
                    self.service_states[instance_id] = "Down"

                elif not is_down and prev_status == "Down":
                    self.notify_state_change(instance_id, "Running", "Recovered")
                    self.service_states[instance_id] = "Running"

                elif prev_status == "Unknown":
                    # Initial discovery
                    self.service_states[instance_id] = "Running"

            except Exception as e:
                logger.error(f"Error checking key {key_str}: {e}")

    def notify_state_change(self, service, state, valid):
        logger.info("state_change", service=service, state=state, msg=valid)
        self.apobj.notify(
            title=f"Service {state}: {service}",
            body=f"{service} is now {state}. {valid}",
        )

    def send_self_heartbeat(self):
        try:
            self.redis.set("status:monitor", int(time.time()), ex=30)
        except Exception:
            pass


def main():
    signal.signal(signal.SIGINT, lambda s, f: shutdown_event.set())
    signal.signal(signal.SIGTERM, lambda s, f: shutdown_event.set())

    Monitor().run()


if __name__ == "__main__":
    main()
