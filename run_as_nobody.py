#!/usr/bin/env python3
"""
Helper script to drop privileges and run gunicorn as nobody user
"""
import os
import sys

def drop_privileges():
    """Drop root privileges to nobody:users (99:100)"""
    if os.getuid() != 0:
        # Not root, nothing to do
        return
    
    # Get nobody user info
    nobody_uid = 99
    users_gid = 100
    
    # Fix permissions for data and logs
    os.makedirs('/app/data', exist_ok=True)
    os.makedirs('/app/logs', exist_ok=True)
    os.chown('/app/data', nobody_uid, users_gid)
    os.chown('/app/logs', nobody_uid, users_gid)
    
    # Drop privileges
    os.setgroups([])
    os.setgid(users_gid)
    os.setuid(nobody_uid)
    
    print(f"Dropped privileges to nobody:users (UID: {os.getuid()}, GID: {os.getgid()})")

if __name__ == "__main__":
    # Drop privileges if running as root
    drop_privileges()
    
    # Execute gunicorn with all arguments
    os.execvp(sys.argv[1], sys.argv[1:])