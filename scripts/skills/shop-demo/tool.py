"""Harmless Skill Shops acceptance package."""
import json

def main():
    return {"skill": "shop-demo", "message": "Skill Shops is working", "version": 1}

if __name__ == "__main__":
    print(json.dumps(main()))
