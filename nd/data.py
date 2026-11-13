"""Static data: teams, names, schools, injuries, league constants."""

SALARY_CAP = 108.0      # $M soft cap: above it you can only sign min deals / must match salary in trades
HARD_APRON = 134.0      # $M: no transaction may push payroll above this
MIN_SALARY = 1.1
MAX_SALARY = 42.0
ROSTER_MAX = 15
ROSTER_MIN = 9
TRADE_DEADLINE_DAY = 6  # trades close once 6 regular-season games are played
SEASON_DAYS = 9
START_SEASON = 2027

TEAMS = [
    dict(city="Voltage City", name="Surge", abbr="VOL", c1="#d4ff3a", c2="#1d2a0c", glyph="bolt", shape="hex",
         arena="The Capacitor"),
    dict(city="Ashport", name="Embers", abbr="ASH", c1="#ff5a1f", c2="#ffc23d", glyph="flame", shape="shield",
         arena="Kiln Fieldhouse"),
    dict(city="Glacier Peak", name="Yetis", abbr="GLP", c1="#8be9ff", c2="#1e4fa0", glyph="peak", shape="circle",
         arena="Whiteout Dome"),
    dict(city="Obsidian Bay", name="Krakens", abbr="OBK", c1="#9b5cff", c2="#22d3ee", glyph="trident", shape="diamond",
         arena="The Abyss"),
    dict(city="Sunspire", name="Monarchs", abbr="SUN", c1="#ffcf3d", c2="#7a2610", glyph="crown", shape="shield",
         arena="Solar Court"),
    dict(city="Coldwater", name="Ravens", abbr="CWR", c1="#ff2d55", c2="#1a1d2e", glyph="raven", shape="circle",
         arena="The Rookery"),
    dict(city="Ironvale", name="Golems", abbr="IRV", c1="#ff8a1f", c2="#3d3a36", glyph="anvil", shape="hex",
         arena="Foundry Arena"),
    dict(city="Crescent Harbor", name="Tide", abbr="CRH", c1="#19e3c5", c2="#0b4f6c", glyph="wave", shape="circle",
         arena="Moonwater Pavilion"),
    dict(city="Silverline", name="Comets", abbr="SLC", c1="#c7d2ff", c2="#4f46e5", glyph="comet", shape="diamond",
         arena="Orbit Center"),
    dict(city="Thornfield", name="Vipers", abbr="THV", c1="#3dff8a", c2="#0a3a1f", glyph="fang", shape="shield",
         arena="The Pit"),
]

FIRST_NAMES = """Aaron Abdul Ade Adrian Ahmad Aiden Akira Alonzo Amari Andre Anton Ari Armand Augustin Bakari Bastian
Beau Benedikt Bodhi Bram Brennan Caleb Callum Cam Cassius Cedric Chidi Cole Corbin Cruz Dalen Damari Dante Darius Davi
Dax Deandre Dejan Deshawn Devin Diego Dimitri Dominik Dorian Dre Eamon Eli Elias Emeka Emil Enzo Ezra Felix Finn Gabe
Gideon Goran Hakeem Hassan Hugo Ibrahim Idris Ignacio Imani Isaiah Ivan Jabari Jace Jalen Jamal Jaylen Jericho Joaquin
Jonah Josiah Jovan Julian Kai Kalani Kareem Kasimir Keanu Keon Kenji Khalil Kiran Kobi Lamar Lazar Leandro Lennox Levi
Luca Lukas Malik Marcus Mateo Matthias Milo Moses Musa Nate Nico Nikola Nnamdi Oisin Omari Oren Orlando Oscar Otto Pascal
Quentin Quincy Rafael Rashad Reggie Remy Rio Rohan Ronan Rui Sami Santi Sekou Shai Silas Sol Stellan Tariq Teo Thiago
Tobias Tomas Tre Tyrese Ugo Uriah Vance Viktor Wendell Xavier Yannick Yuki Zaire Zane Zion""".split()

LAST_NAMES = """Abara Achterberg Adebayo-Cole Alcott Amadi Arkwright Ashby Balogun Banerjee Barrowman Batiste Bellweather
Blackwood Bonaventure Brightwater Calloway Castellano Chukwu Coldiron Cormier Crane Dabrowski Dalton Delacroix Demir
Draxler Duquesne Ekwueme Ellery Embree Falcone Fairweather Fenwick Ferreira Fontaine Galloway Gatling Gideon Graves
Halvorsen Hargrove Hawthorne Ilunga Ingram-Lake Iwobi Jankovic Jarreau Kaczmarek Kahale Kessler Kingsley Koval Lachance
Lindqvist Lockhart Lomax Madaki Marchetti Mbeki Merriweather Montrose Nakamura Navarro Nwosu Oakes Okafor-Price Olsen
Onyango Orsini Pacheco Pemberton Petrakis Quaye Radovic Ravensworth Redd Reinholt Rios Rockwell Saint-Clair Salazar Sato
Sexton-Ames Sheffield Silvermoon Sokolov Stroud Sutherland Takahashi Tavares Thibodeaux Thorne Ueda Umeh Valdés Vance
Vasquez Velasco Voss Wainwright Waverly Whitlock Wilder Winslow Wyatt Yamamoto Yeboah Zamora Zelenko Zubiri""".split()

SCHOOLS = ["Cascade State", "Ridgemont U", "Port Calder", "Halcyon Tech", "Eastvale A&M", "Saint Brennan",
           "Mesa Verde", "Lakeshore", "Northgate", "Redcliff", "Belgrade Academy", "Kaunas Club", "Lagos Elite",
           "Tokyo Prep", "Bayou State", "Granite U", "Pinecrest", "Westmarch", "Ocean City Prep", "Aldergrove",
           "Copper Basin", "Madrid Juniors", "Ironwood College", "Summit Christian", "G-League Ignite East"]

INJURIES = [
    # (name, min_games, max_games, weight)
    ("Ankle soreness", 0, 0, 22),
    ("Back spasms", 0, 1, 14),
    ("Ankle sprain", 1, 2, 16),
    ("Hamstring tightness", 1, 2, 12),
    ("Knee contusion", 1, 3, 10),
    ("Concussion protocol", 1, 2, 6),
    ("Groin strain", 2, 4, 7),
    ("Calf strain", 2, 5, 5),
    ("Broken finger", 3, 5, 3),
    ("Sprained MCL", 4, 8, 3),
    ("Fractured wrist", 6, 12, 1.5),
    ("Torn meniscus", 8, 16, 0.8),
]
