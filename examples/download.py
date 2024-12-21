import json
import sys
from base64 import b64decode

import requests


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python download.py [job ID] [destination filepath]")
        return 1

    _, job_id, filepath = sys.argv

    resp = requests.get(f"http://localhost:8000/jobs/{job_id}/result")
    if not resp.ok:
        try:
            err = resp.json()
        except json.JSONDecodeError:
            resp.raise_for_status()
        else:
            print(f"Status code {resp.status_code}. Error: {err}")
            return 1

    with open(filepath, "wb") as f:
        f.write(b64decode(resp.json()["output"]))

    print("File saved.")


if __name__ == "__main__":
    raise SystemExit(main())
