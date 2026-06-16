"""Procedural name & data generation utilities."""
import random
import string

# ─── Name pools ──────────────────────────────────────────────────────────────
_FIRST_NAMES = [
    "Aleksander","Nikola","Stefan","Ivan","Dmitri","Viktor","Andrei","Sergei",
    "Pavel","Maxim","Artem","Vladislav","Denis","Kirill","Roman","Evgeny",
    "Omar","Farid","Hassan","Yusuf","Ahmed","Karim","Tariq","Samir","Bilal",
    "Carlos","Miguel","Diego","Luis","Javier","Alejandro","Ricardo","Eduardo",
    "Wei","Jian","Feng","Lei","Hao","Yang","Zhen","Xiao","Ming","Lin",
    "James","Michael","Ryan","Tyler","Brandon","Kyle","Derek","Chris","Jake",
    "Luca","Marco","Federico","Lorenzo","Matteo","Davide","Simone","Andrea",
    "Johan","Lars","Erik","Mikael","Bjorn","Sven","Nils","Oscar","Filip",
    "Jakub","Tomasz","Piotr","Marcin","Karol","Rafal","Michal","Lukasz",
    "Tomas","Martin","Petr","Ondrej","Adam","Jan","David","Lukas","Filip",
    "Antoine","Pierre","Baptiste","Nicolas","Julien","Romain","Florian",
    "Leon","Felix","Moritz","Jonas","Lukas","Tobias","Simon","Julian",
    "Mateus","Gabriel","Thiago","Gustavo","Rafael","Felipe","Bruno","Pedro",
    "Jin","Min","Sung","Hyun","Jae","Seok","Young","Tae","Won","Kyu",
    "Ravi","Arjun","Vikram","Rahul","Priya","Karan","Aditya","Sanjay",
]

_LAST_NAMES = [
    "Ivanov","Petrov","Sidorov","Kozlov","Novikov","Morozov","Volkov","Sokolov",
    "Popov","Lebedev","Smirnov","Kovalev","Orlov","Fedorov","Mikhailov",
    "Silva","Santos","Oliveira","Souza","Lima","Ferreira","Costa","Pereira",
    "Garcia","Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Perez",
    "Wang","Li","Zhang","Liu","Chen","Yang","Huang","Zhao","Wu","Zhou",
    "Smith","Johnson","Williams","Brown","Jones","Miller","Davis","Wilson",
    "Rossi","Ferrari","Ricci","Bruno","Conti","Russo","Esposito","Bianchi",
    "Johansson","Andersen","Nielsen","Hansen","Petersen","Eriksen","Larsen",
    "Nowak","Wojcik","Kowalski","Kaminski","Lewandowski","Zielinski","Szymanski",
    "Dupont","Martin","Bernard","Thomas","Petit","Robert","Richard","Leroy",
    "Muller","Schmidt","Schneider","Fischer","Weber","Wagner","Becker","Schulz",
    "Nakamura","Tanaka","Suzuki","Sato","Watanabe","Ito","Yamamoto","Kobayashi",
    "Park","Kim","Lee","Choi","Cho","Yoon","Lim","Kang","Han","Jung",
    "Okafor","Mensah","Diallo","Traore","Coulibaly","Nkosi","Dlamini","Osei",
    "Ferreira","Carvalho","Gomes","Pinto","Sousa","Alves","Moreira","Rodrigues",
    "Reyes","Morales","Jimenez","Romero","Torres","Ramirez","Flores","Cruz",
]

_NICKNAMES = [
    "Ghost","Shadow","Viper","Storm","Echo","Blade","Phantom","Nexus","Surge",
    "Cipher","Frost","Ember","Void","Apex","Zephyr","Titan","Specter","Nova",
    "Rifts","Kestrel","Raven","Lynx","Falcon","Wolf","Tiger","Dragon","Cobra",
    "Inferno","Blaze","Volt","Neon","Pixel","Grid","Core","Node","Sync",
    "Rush","Flash","Blitz","Havoc","Chaos","Mayhem","Carnage","Fury","Rage",
    "Ace","King","Boss","Chief","Savant","Sage","Oracle","Prophet","Seer",
    "Reaper","Hunter","Slayer","Nemesis","Wraith","Banshee","Specter","Revenant",
    "Zero","One","Alpha","Omega","Delta","Sigma","Lambda","Epsilon","Theta",
    "Crisp","Sharp","Edge","Point","Spike","Dart","Arrow","Bolt","Strike",
    "Lucky","Clutch","Carry","Frag","Aim","Top","Crux","Pivot","Anchor",
    "Byte","Bit","Hex","Null","Stack","Queue","Cache","Loop","Async",
    "Vex","Zap","Slam","Bash","Crunch","Snap","Pop","Lock","Drop",
    "Solo","Duo","Trio","Pack","Crew","Squad","Fleet","Force","Unit",
    "Jade","Ruby","Onyx","Steel","Iron","Bronze","Silver","Gold","Platinum",
    "Static","Dynamic","Kinetic","Elastic","Rigid","Fluid","Dense","Sparse",
]

_NATIONALITIES_BY_REGION = {
    "europe": [
        "Ukrainian","Russian","French","German","Danish","Swedish","Norwegian",
        "Finnish","Polish","Czech","Slovak","Romanian","Serbian","Croatian",
        "Portuguese","Spanish","Italian","Dutch","Belgian","Swiss","Austrian",
        "British","Greek","Hungarian","Bulgarian","Lithuanian","Latvian","Estonian",
    ],
    "asia": [
        "Chinese","South Korean","Japanese","Mongolian","Kazakh","Uzbek",
        "Vietnamese","Thai","Indonesian","Filipino","Malaysian","Singaporean",
        "Indian","Pakistani","Bangladeshi","Sri Lankan","Taiwanese","Hong Kong",
    ],
    "latin_america": [
        "Brazilian","Argentine","Chilean","Colombian","Peruvian","Venezuelan",
        "Uruguayan","Paraguayan","Bolivian","Ecuadorian","Mexican","Costa Rican",
    ],
    "africa_oceania": [
        "South African","Nigerian","Ghanaian","Kenyan","Egyptian","Moroccan",
        "Tunisian","Australian","New Zealander","Filipino","Indonesian","Thai",
    ],
}

_USED_NICKNAMES: set = set()


def random_nickname(region: str | None = None) -> str:
    """Return a unique-ish nickname."""
    available = [n for n in _NICKNAMES if n not in _USED_NICKNAMES]
    if not available:
        # Append a number to make it unique
        base = random.choice(_NICKNAMES)
        nick = f"{base}{random.randint(1, 999)}"
    else:
        nick = random.choice(available)
    _USED_NICKNAMES.add(nick)
    return nick


def random_name(region: str = "europe") -> tuple[str, str]:
    """Return (first_name, last_name)."""
    return random.choice(_FIRST_NAMES), random.choice(_LAST_NAMES)


def random_nationality(region: str = "europe") -> str:
    pool = _NATIONALITIES_BY_REGION.get(region, _NATIONALITIES_BY_REGION["europe"])
    return random.choice(pool)


def random_age(min_age: int = 16, max_age: int = 32) -> int:
    # Weighted towards 18-27
    weights = []
    ages = list(range(min_age, max_age + 1))
    for a in ages:
        if 18 <= a <= 27:
            weights.append(3)
        elif 16 <= a <= 17:
            weights.append(1)
        else:
            weights.append(1.5)
    return random.choices(ages, weights=weights, k=1)[0]


def weighted_randint(low: int, high: int, center: int | None = None, spread: int = 15) -> int:
    """Gaussian-ish integer between low and high, peaked near center."""
    if center is None:
        center = (low + high) // 2
    import math
    val = random.gauss(center, spread)
    return max(low, min(high, int(round(val))))


def generate_id(prefix: str, counter: list) -> str:
    counter[0] += 1
    return f"{prefix}{counter[0]:04d}"


def roll(probability: float) -> bool:
    """Return True with the given probability (0–1)."""
    return random.random() < probability
