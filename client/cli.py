import argparse
from .client import FastMCPClient


def parse_params(param_list: list[str]) -> dict[str, str]:
    params = {}
    for p in param_list:
        if '=' not in p:
            raise argparse.ArgumentTypeError(f"Invalid parameter '{p}', expected key=value")
        key, value = p.split('=', 1)
        params[key] = value
    return params


def main() -> None:
    parser = argparse.ArgumentParser(description="Command line interface for FastMCP")
    parser.add_argument('--base-url', default='http://localhost:8000', help='FastMCP server base URL')
    parser.add_argument('--list-tools', action='store_true', help='List available tools and exit')
    parser.add_argument('--param', action='append', default=[], help='Query parameter in key=value format (can be used multiple times)')
    parser.add_argument('tool', nargs='?', help='Name of the tool to query')
    args = parser.parse_args()

    client = FastMCPClient(args.base_url)

    if args.list_tools:
        print(client.initialize())
        return

    if not args.tool:
        parser.error('tool is required unless --list-tools is specified')

    params = parse_params(args.param)
    result = client.query(args.tool, params=params or None)
    print(result)


if __name__ == '__main__':
    main()
