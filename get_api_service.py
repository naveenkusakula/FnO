from typing import Dict, Optional
from datetime import datetime

import requests
from config import Config


class GetApiService:

    def __init__(self, config: Config, auth_token: str):
        self.config = config
        self.auth_token = auth_token

    def get_positions(self) -> Optional[Dict]:
        payload = (
            f'jData={{\n\t"uid": "{self.config.CLIENT_ID}",\n\t"actid": "{self.config.CLIENT_ID}"\n}}'
            f"&jKey={self.auth_token}"
        )
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "insomnia/11.0.1",
        }

        try:
            response = requests.request(
                "POST", self.config.POSITIONS_URL, data=payload, headers=headers
            )
            if response.status_code == 200:
                return response.json()
            print(f"Error fetching positions: {response.status_code}, {response.text}")
            return None
        except Exception as e:
            print(f"Exception while fetching positions: {e}")
            return None

    def get_options(
        self, strike: float, expiry: str = None, option_type: str = "C"
    ) -> Optional[Dict]:
        """
        strike: numeric strike (26000)
        expiry: string like "28-Oct-2025" or "28-OCT-25" or None (will try config)
        option_type: "C" or "P"
        """
        # determine underlying symbol from config or default
        underlying = (
            getattr(self.config, "UNDERLYING", None)
            or getattr(self.config, "UNDERLYING_SYMBOL", None)
            or "NIFTY"
        )

        # get expiry from arg or config
        expiry_input = (
            expiry
            or getattr(self.config, "OPTIONS_EXPIRY", None)
            or getattr(self.config, "EXPIRY_DATE", None)
            or ""
        )

        # try to normalize expiry to DDMMMYY uppercase, e.g. 28OCT25
        expiry_fmt = ""
        if expiry_input:
            try:
                # try common format dd-MMM-YYYY or dd-MMM-YY (case-insensitive)
                try:
                    dt = datetime.strptime(expiry_input, "%d-%b-%Y")
                except Exception:
                    dt = datetime.strptime(expiry_input, "%d-%b-%y")
                expiry_fmt = dt.strftime("%d%b%y").upper()
            except Exception:
                # fallback: remove non-alphanum and uppercase (best-effort)
                expiry_fmt = "".join(ch for ch in expiry_input if ch.isalnum()).upper()

        # build tsym like NIFTY28OCT25C26000
        # strike as integer without decimals
        try:
            strike_int = int(float(strike))
        except Exception:
            strike_int = strike
        tsym = f"{underlying}{expiry_fmt}{str(option_type).upper()}{strike_int}"

        payload = (
            f'jData={{\n\t"uid": "{self.config.CLIENT_ID}",\n\t"actid": "{self.config.CLIENT_ID}",'
            f'\n\t"tsym": "{tsym}",'
            f'\n\t"strprc": "{float(strike):.2f}",'
            f'\n\t"exch": "NFO",'
            f'\n\t"cnt": "4"\n}}'
            f"&jKey={self.auth_token}"
        )
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "insomnia/11.0.1",
        }

        try:
            response = requests.request(
                "POST", self.config.OPTIONS_URL, data=payload, headers=headers
            )
            if response.status_code == 200:
                return response.json()
            print(f"Error fetching options: {response.status_code}, {response.text}")
            return None
        except Exception as e:
            print(f"Exception while fetching options: {e}")
            return None


if __name__ == "__main__":
    import argparse
    import json
    import os

    # simple CLI to call get_options
    parser = argparse.ArgumentParser(
        prog="get_api_service", description="Get API service commands"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_get = subparsers.add_parser("get_options", help="Fetch option data for a strike")
    p_get.add_argument(
        "--strike", "-s", required=True, type=float, help="Strike price (e.g. 26000)"
    )
    p_get.add_argument(
        "--expiry",
        "-e",
        default=None,
        help="Expiry string (e.g. '28-Oct-2025'). If omitted, Config value is used.",
    )
    p_get.add_argument(
        "--type",
        "-t",
        choices=["C", "P", "c", "p"],
        default="C",
        help="Option type: C or P",
    )

    args = parser.parse_args()

    # instantiate config and service; auth token is read from env API_AUTH_TOKEN
    cfg = Config()
    auth = os.environ.get("API_AUTH_TOKEN", "")
    svc = GetApiService(cfg, auth_token=auth)

    if args.command == "get_options":
        opt_type = args.type.upper()
        resp = svc.get_options(
            strike=args.strike, expiry=args.expiry, option_type=opt_type
        )
        # print nicely
        print(json.dumps(resp, indent=2))
