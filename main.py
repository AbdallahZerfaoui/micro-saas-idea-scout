import sys
import json
from micro_saas_client import MicroSaasClient, ProxyManager


def main():
    """
    Main function to run the micro-saas client demo.
    It initializes the client, checks proxy health, and fetches ideas based on user input.
    """
    client = MicroSaasClient()
    proxy_manager = ProxyManager()
    if not proxy_manager.healthy_proxy_check():
        print("Exiting...")
        sys.exit(1)
    kw = input("Keyword? ").strip()
    ideas = client.get_ideas(kw)
    # ideas = client.deep_extract_ideas(kw, limit=20)
    if ideas:
        print(f"Found ideas for '{kw}':")
        # print(json.dumps(ideas, indent=2))
    else:
        print("No idea found.")


if __name__ == "__main__":
    main()
