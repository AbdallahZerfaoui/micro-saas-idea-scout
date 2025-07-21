import sys
import json
from src.micro_saas_client import MicroSaasClient, ProxyManager
from src.ai_evaluator import AIEvaluator, EvaluatedIdea


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
    ai_evaluator = AIEvaluator(kw)
    # ideas = client.get_ideas(kw)
    user_limit = input("How many ideas do you want to fetch? ").strip()
    ideas = client.deep_extract_ideas(kw, limit=int(user_limit))
    if ideas:
        print(f"Found ideas for '{kw}':")
        evaluated_ideas = ai_evaluator.evaluate(ideas)
        # print(json.dumps([idea.__dict__ for idea in evaluated_ideas], indent=2))
    else:
        print("No idea found.")


if __name__ == "__main__":
    main()
