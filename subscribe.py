#!/usr/bin/python3 -OO
# -*- coding: utf-8 -*-

import configparser
import os
import redis
import subprocess
import sys
import time


DEFAULT_CFG_PATH = "/etc/signup.cfg"
REDIS_SUB_CH = "gitciuser"
GITOLITE_BIN = "/usr/local/bin/gitolite"
KEYDIR_PATH = "/home/git/.gitolite/keydir"


class SubException(Exception):
    """A basic exception class."""
    pass


def read_config():
    """Read the program configuration from file."""
    config = {}
    config_path = os.environ.get("KEY_SIGNUP_CONFIG", DEFAULT_CFG_PATH)

    if os.path.exists(config_path):
        parser = configparser.ConfigParser()
        parser.read(config_path)

        config = parser["DEFAULT"]
    else:
        print("Warning: config file does not exists, empty config provided")

    return config


def get_db_connection(config):
    """Establish a connection to the database.

    :param config: The configuration parameters.
    :type config: dict
    :return The database connection.
    """
    # TODO: change the host to redis
    redis_host = config.get("REDIS_HOST", "localhost")
    # TODO: change the port to 6379
    redis_port = config.get("REDIS_PORT", 16379)
    redis_pwd = config.get("REDIS_PASSWORD", None)

    try:
        r = redis.StrictRedis(
            host=redis_host, port=redis_port, password=redis_pwd)
        # Dumb check to make sure we have a connection or we have to stop.
        r.info()
    except redis.exceptions.ConnectionError:
        print("Error: unable to establish connection with the database")
        sys.exit(1)

    return r


def handle_message(message, db):
    """Handle the message arrived from the publisher.

    :param message: The message arrived.
    :param db: The database instance.
    """
    user_entry = db.hgetall(message["data"])
    print(user_entry)

    ssh_key = str(user_entry[b"ssh_key"], "utf-8")
    username = str(user_entry[b"username"], "utf-8")

    key_path = os.path.join(KEYDIR_PATH, "{}.pub".format(username))

    print(key_path)

    with open(key_path, mode="w") as pub_key:
        pub_key.write(ssh_key)
        pub_key.flush()

    try:
        subprocess.check_call([GITOLITE_BIN, "setup"])
    except subprocess.CalledProcessError:
        print("Error: error setting up key for {}".format(username))


def main():
    config = read_config()

    db = get_db_connection(config)
    # Create the pub/sub object and subscribe to the messages.
    pub_sub = db.pubsub()
    pub_sub.subscribe(REDIS_SUB_CH)

    while True:
        message = pub_sub.get_message()
        if message and message["type"] == "message":
            print("Got message: {}".format(message))
            handle_message(message, db)
        time.sleep(1)


if __name__ == '__main__':
    sys.exit(main())
