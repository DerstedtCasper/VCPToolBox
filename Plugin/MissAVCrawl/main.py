#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MissAVCrawl Plugin - Main Entry Point
Handles both synchronous and asynchronous commands.
"""

import sys
import json
import traceback
from pathlib import Path

# Ensure local modules can be imported
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import handlers for different command types
from missav_crawl import process_request as handle_sync_request
from missav_crawl_async import handle_async_download

def main():
    """Main function to route commands."""
    try:
        # Read all input from stdin
        input_data = sys.stdin.read().strip()
        if not input_data:
            # A plugin should always receive some input
            result = {
                "status": "error",
                "error": "No input data received by the plugin."
            }
        else:
            # Parse the JSON input
            request_data = json.loads(input_data)
            command = request_data.get('command')

            if not command:
                result = {
                    "status": "error",
                    "error": "Missing 'command' in request data."
                }
            # Route to the appropriate handler based on the command
            elif command == "DownloadVideoAsync":
                # This is an asynchronous command.
                # The handler will print the initial response and start a background thread.
                # The main process will exit after that, so we don't capture a 'result' here.
                handle_async_download(request_data)
                return # Exit immediately after calling the async handler
            else:
                # All other commands are considered synchronous.
                # The handler will do its work and return a result dictionary.
                result = handle_sync_request(request_data)

    except json.JSONDecodeError as e:
        result = {
            "status": "error",
            "error": f"Failed to parse input JSON: {str(e)}"
        }
    except Exception as e:
        result = {
            "status": "error",
            "error": f"An unexpected error occurred in the plugin's main entry point: {str(e)}",
            "traceback": traceback.format_exc()
        }

    # For synchronous commands, print the final result to stdout
    print(json.dumps(result, ensure_ascii=False))
    sys.stdout.flush()

if __name__ == "__main__":
    main()