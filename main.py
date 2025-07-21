import json
from micro_saas_client import MicroSaasClient


def main():
    """
    Main function to run the micro-saas client demo.
    It initializes the client, checks proxy health, and fetches ideas based on user input.
    """
    client = MicroSaasClient()
    client.healthy_proxy_check()
    kw = input("Keyword? ").strip()
    ideas = client.get_ideas(kw)
    if ideas:
        print(json.dumps(ideas, indent=2))
    else:
        print("No idea found.")


if __name__ == "__main__":
    main()
