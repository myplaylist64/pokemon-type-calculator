import json
import requests
from colorama import init, Fore, Style

# === Init couleurs ===
init(autoreset=True)

# === Données locales ===
with open("pokemon.json", encoding="utf-8") as f:
    all_pokemon = json.load(f)

# Couleurs par type
TYPE_COLORS = {
    "Électrik": Fore.YELLOW,
    "Plante":   Fore.GREEN,
    "Feu":      Fore.RED,
    "Eau":      Fore.CYAN,
    "Glace":    Fore.LIGHTCYAN_EX,
    "Roche":    Fore.LIGHTBLACK_EX,
    "Sol":      Fore.LIGHTYELLOW_EX,
    "Psy":      Fore.MAGENTA,
    "Ténèbres": Fore.LIGHTBLACK_EX,
    "Spectre":  Fore.LIGHTMAGENTA_EX,
    "Insecte":  Fore.GREEN + Style.DIM,
    "Acier":    Fore.LIGHTWHITE_EX,
    "Fée":      Fore.LIGHTMAGENTA_EX,
    "Dragon":   Fore.BLUE,
    "Combat":   Fore.LIGHTRED_EX,
    "Vol":      Fore.LIGHTBLUE_EX,
    "Poison":   Fore.LIGHTMAGENTA_EX,
    "Normal":   Fore.WHITE,
}

ALL_TYPES_FR = [
    "Normal","Feu","Eau","Électrik","Plante","Glace","Combat","Poison","Sol","Vol",
    "Psy","Insecte","Roche","Spectre","Dragon","Acier","Ténèbres","Fée"
]

TYPES_BY_GEN = {
    1: set(["Normal","Feu","Eau","Électrik","Plante","Glace","Combat","Poison","Sol","Vol","Psy","Insecte","Roche","Spectre","Dragon"]),
    2: set(["Normal","Feu","Eau","Électrik","Plante","Glace","Combat","Poison","Sol","Vol","Psy","Insecte","Roche","Spectre","Dragon","Acier","Ténèbres"]),
    3: None, 4: None, 5: None,
    6: set(ALL_TYPES_FR),
    7: None, 8: None, 9: None
}

def types_allowed_for_gen(gen: int) -> set:
    if gen >= 6:
        return TYPES_BY_GEN[6]
    elif gen >= 2:
        return TYPES_BY_GEN[2]
    else:
        return TYPES_BY_GEN[1]

def color_text(type_name: str) -> str:
    return TYPE_COLORS.get(type_name, Fore.WHITE) + type_name + Style.RESET_ALL

# === Choix génération ===
def ask_generation() -> int:
    while True:
        raw = input("Choisis une génération (1–9) : ").strip()
        if raw.isdigit():
            g = int(raw)
            if 1 <= g <= 9:
                return g
        print("Entrée invalide. Merci de saisir un nombre entre 1 et 9.")

# === Filtrage dataset par génération ===
def filter_pokemon_by_generation(gen: int):
    return [p for p in all_pokemon if int(p.get("generation", 999)) <= gen]

# === Accès données locales ===
def get_local_entry_by_name_fr(name_fr: str, gen: int):
    for p in filter_pokemon_by_generation(gen):
        if p["name"]["fr"].lower() == name_fr.lower():
            return p
    return None

def get_local_entry_by_id(pid: int):
    for p in all_pokemon:
        if int(p["pokedex_id"]) == int(pid):
            return p
    return None

# === Base: résistances locales + ajustements par génération ===
def base_resistances_from_local(pid: int) -> dict:
    entry = get_local_entry_by_id(pid)
    if not entry:
        return {}
    res = {r["name"]: float(r["multiplier"]) for r in entry.get("resistances", [])}
    for t in ALL_TYPES_FR:
        res.setdefault(t, 1.0)
    return res

def adjust_resistances_for_generation(res_map: dict, defender_types: list, gen: int) -> dict:
    res = dict(res_map)

    if gen == 1:
        for t in ("Acier","Ténèbres","Fée"):
            res.pop(t, None)
        if "Psy" in defender_types:
            res["Spectre"] = 0.0

    if 2 <= gen <= 5:
        if "Acier" in defender_types:
            res["Spectre"] = res.get("Spectre", 1.0) * 0.5
            res["Ténèbres"] = res.get("Ténèbres", 1.0) * 0.5

    return res

def filter_defender_types_for_gen(defender_types: list, gen: int) -> list:
    allowed = types_allowed_for_gen(gen)
    return [t for t in defender_types if t in allowed]

# === Option: appel API (fallback) ===
def api_resistances(pid: int) -> dict:
    url = f"https://tyradex.vercel.app/api/v1/pokemon/{pid}"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return {}
        data = r.json()
        rel = data.get("resistances", [])
        d = {x["name"]: float(x["multiplier"]) for x in rel}
        for t in ALL_TYPES_FR:
            d.setdefault(t, 1.0)
        return d
    except Exception:
        return {}

def print_weakness_table(res_map: dict):
    buckets = {4:[], 2:[], 1:[], 0.5:[], 0.25:[], 0:[]}
    for t, mult in res_map.items():
        if mult >= 3.99: k = 4
        elif 1.99 <= mult < 3.99: k = 2
        elif 0.99 <= mult < 1.99: k = 1
        elif 0.49 <= mult < 0.99: k = 0.5
        elif 0.24 <= mult < 0.49: k = 0.25
        else: k = 0
        buckets[k].append(color_text(t))
    print()
    for k in (4,2,1,0.5,0.25,0):
        if buckets[k]:
            print(f" - x{k} : {', '.join(sorted(buckets[k]))}")

def main():
    print("Tape '00' pour quitter. Commande: /gen (changer génération)")
    gen = ask_generation()

    while True:
        nom = input("\nNom FR d’un Pokémon (ou commande) : ").strip()
        if nom == "00":
            print("Au revoir !")
            break

        if nom == "/gen":
            gen = ask_generation()
            continue

        entry = get_local_entry_by_name_fr(nom, gen)
        if not entry:
            print("Pokémon non trouvé dans la génération courante.")
            continue

        pid = int(entry["pokedex_id"])
        defender_types = [t["name"] for t in entry.get("types", [])]
        defender_types = filter_defender_types_for_gen(defender_types, gen)

        base = base_resistances_from_local(pid)
        if not base:
            base = api_resistances(pid)
        res_map = adjust_resistances_for_generation(base, defender_types, gen)

        print(f"\nFaiblesses de {entry['name']['fr']} (Gen {gen}) — Types: {', '.join(defender_types) if defender_types else 'Inconnus'}")
        print_weakness_table(res_map)

if __name__ == "__main__":
    main()
