#!/bin/bash
# start_ssh.sh
# A simple entrypoint for the development pod.
# Its only job is to start the SSH server in the foreground to keep the container running,
# allowing the user to connect and perform manual setup tasks.

echo "Development Pod Initializing..."
echo "Starting SSH server on port 22..."
echo "The container will remain active as long as this process is running."
echo "You can now connect via SSH."

# Create the /run/sshd directory if it doesn't exist
mkdir -p /run/sshd

# Execute the SSH daemon in the foreground.
# This is the crucial step that keeps the container alive.
exec /usr/sbin/sshd -D -e
