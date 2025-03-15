import os
import subprocess
import psutil
import time
import yaml
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ServerManager:
    def __init__(self, server_name, server_path, java_path="java", jvm_args="-Xmx2G -Xms1G", mod_loader_jar=None):
        self.server_name = server_name
        self.server_path = server_path
        self.java_path = java_path
        self.jvm_args = jvm_args
        self.mod_loader_jar = mod_loader_jar  # path to the mod loader JAR file
        self.process = None

    def start_server(self):
        try:
            if self.is_server_running():
                logging.info(f"{self.server_name} is already running.")
                return

            # check if the mod loader JAR exists (if specified)
            if self.mod_loader_jar and not os.path.exists(os.path.join(self.server_path, self.mod_loader_jar)):
                logging.error(f"Mod loader JAR ({self.mod_loader_jar}) not found in {self.server_path}. Please install the mod loader.")
                return

            # use the mod loader JAR if specified otherwise use server.jar
            server_jar = self.mod_loader_jar if self.mod_loader_jar else "server.jar"
            server_jar_path = os.path.join(self.server_path, server_jar)

            if not os.path.exists(server_jar_path):
                logging.error(f"{server_jar} not found in {self.server_path}. Please ensure the server JAR is present.")
                return

            logging.info(f"Starting {self.server_name}...")
            command = [self.java_path] + self.jvm_args.split() + ["-jar", server_jar_path]
            logging.info(f"Command: {' '.join(command)}")
            logging.info(f"Working directory: {self.server_path}")
            self.process = subprocess.Popen(
                command,
                cwd=self.server_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True
            )
            logging.info(f"{self.server_name} started. Process PID: {self.process.pid}")

            # log server output in real-time
            def log_output(stream, logger):
                for line in stream:
                    logger(line.strip())

            import threading
            threading.Thread(target=log_output, args=(self.process.stdout, logging.info), daemon=True).start()
            threading.Thread(target=log_output, args=(self.process.stderr, logging.error), daemon=True).start()

        except Exception as e:
            logging.error(f"Error starting server: {e}")

    def stop_server(self):
        try:
            if not self.is_server_running():
                logging.info(f"{self.server_name} is not running.")
                return

            logging.info(f"Stopping {self.server_name}...")
            if self.process:
                try:
                    self.process.stdin.write("stop\n")
                    self.process.stdin.flush()
                except BrokenPipeError:
                    logging.warning(f"{self.server_name} process already terminated.")
                self.process.wait()
                logging.info(f"{self.server_name} stopped.")
            else:
                logging.error(f"Cannot stop {self.server_name}: Process is None.")
        except Exception as e:
            logging.error(f"Error stopping server: {e}")

    def restart_server(self):
        logging.info(f"Restarting {self.server_name}...")
        self.stop_server()
        time.sleep(2)
        self.start_server()

    def is_server_running(self):
        if self.process is None:
            return False
        try:
            return psutil.pid_exists(self.process.pid)
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied:
            logging.error("Permission denied while checking the process.")
            return False

def get_user_input(prompt, default=None):
    """helper function to get user input with a default value"""
    user_input = input(f"{prompt} [{default}]: ").strip()
    return user_input if user_input else default

def load_config():
    # get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "server_config.yaml")

    # default configuration
    default_config = {
        "server_name": "Minecraft Server",
        "server_path": os.path.join(script_dir, "server"),  # relative to the script's location
        "java_path": "java",  # default to system Java
        "jvm_args": "-Xmx2G -Xms1G",  # default JVM arguments
        "mod_loader_jar": None  # no mod loader by default
    }

    try:
        # load the configuration from server_config.yaml
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
        logging.info(f"Loaded config: {config}")
        return config
    except FileNotFoundError:
        # if the config file doesnt exist create it with default values
        logging.warning(f"Config file not found at {config_path}. Creating with default values.")
        try:
            with open(config_path, "w") as file:
                yaml.safe_dump(default_config, file)
            logging.info(f"Configuration saved to {config_path}.")
            return default_config
        except Exception as e:
            logging.error(f"Error saving config: {e}")
            return default_config
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return default_config

def prompt_for_server_folder(config):
    """prompt the user for the server folder location and update the config"""
    server_path = input("Enter the path to your server folder: ").strip()
    if not server_path:
        logging.warning("No server folder path provided. Using default location.")
        server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server")
    else:
        # resolve the server path to an absolute path
        server_path = os.path.abspath(server_path)

    # check if the server folder exists
    if not os.path.exists(server_path):
        logging.warning(f"Server folder not found at {server_path}. Creating it.")
        os.makedirs(server_path)

    config["server_path"] = server_path
    logging.info(f"Server folder set to: {server_path}")

    # save the updated configuration
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_config.yaml")
    try:
        with open(config_path, "w") as file:
            yaml.safe_dump(config, file)
        logging.info(f"Configuration saved to {config_path}.")
    except Exception as e:
        logging.error(f"Error saving config: {e}")

def prompt_for_mods(config):
    """prompt the user if they want to run mods and update the config"""
    use_mods = input("Do you want to run mods on your server? (yes/no) [no]: ").strip().lower()
    if use_mods in ("yes", "y"):
        mod_loader_jar = input("Enter the name of the mod loader JAR file (e.g., forge-1.20.1-47.1.0.jar): ").strip()
        if mod_loader_jar:
            config["mod_loader_jar"] = mod_loader_jar
            logging.info(f"Mod loader JAR set to: {mod_loader_jar}")
        else:
            logging.warning("No mod loader JAR specified. Running vanilla server.")
    else:
        logging.info("Running vanilla server (no mods).")

    # save the updated configuration
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_config.yaml")
    try:
        with open(config_path, "w") as file:
            yaml.safe_dump(config, file)
        logging.info(f"Configuration saved to {config_path}.")
    except Exception as e:
        logging.error(f"Error saving config: {e}")

if __name__ == "__main__":
    config = load_config()
    prompt_for_server_folder(config)  # ask the user for the server folder location
    prompt_for_mods(config)  # ask the user if they want to run mods

    server_manager = ServerManager(
        config.get("server_name", "Minecraft Server"),
        config.get("server_path", "./server"),
        config.get("java_path", "java"),
        config.get("jvm_args", "-Xmx2G -Xms1G"),
        config.get("mod_loader_jar", None)
    )

    server_manager.start_server()
    time.sleep(5)
    server_manager.restart_server()
