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
    # ---- expansion franchises (leagues of 12-20 teams)
    dict(city="Copper Ridge", name="Prospectors", abbr="CPR", c1="#e8964a", c2="#3b2410", glyph="pickaxe",
         shape="hex", arena="The Mineshaft"),
    dict(city="Lakeshore", name="Lumberjacks", abbr="LAK", c1="#e04a3c", c2="#2a1512", glyph="axe", shape="shield",
         arena="Sawmill Gardens"),
    dict(city="Duskfall", name="Owls", abbr="DSK", c1="#b59cff", c2="#221a3d", glyph="owl", shape="circle",
         arena="The Night Nest"),
    dict(city="Steelport", name="Cyclones", abbr="STP", c1="#9fb3c8", c2="#1d2833", glyph="swirl", shape="diamond",
         arena="Gale Force Arena"),
    dict(city="Pinecrest", name="Timber", abbr="PCT", c1="#7bd389", c2="#163322", glyph="tree", shape="hex",
         arena="Evergreen Hall"),
    dict(city="Saltflat", name="Scorpions", abbr="SLT", c1="#ffd166", c2="#3d2a05", glyph="stinger", shape="diamond",
         arena="The Dune"),
    dict(city="Northwind", name="Mammoths", abbr="NWM", c1="#a7e8ff", c2="#143246", glyph="tusk", shape="shield",
         arena="Glacier Garden"),
    dict(city="Bayou City", name="Gators", abbr="BYC", c1="#5ee08a", c2="#0f2e1d", glyph="jaw", shape="circle",
         arena="The Swamp"),
    dict(city="Starfall", name="Meteors", abbr="STF", c1="#ff7ad9", c2="#2e0f2a", glyph="star", shape="hex",
         arena="Impact Center"),
    dict(city="Riverbend", name="Foxes", abbr="RVB", c1="#ff9d3d", c2="#2f1706", glyph="fox", shape="diamond",
         arena="The Den"),
]

CONFERENCES = ["Atlas", "Horizon"]
VALID_TEAM_COUNTS = [10, 12, 14, 16, 18, 20]


def playoff_size(n_teams):
    """4-team field for small leagues, 8-team field from 14 teams up."""
    return 4 if n_teams <= 12 else 8

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

FIRST_NAMES_US = """Aaron Adam Alex Andre Andrew Anthony Austin Bailey Ben Blake Brady Brandon Brendan Brian Brock
Bryce Caleb Cameron Carson Carter Chance Chase Chris Christian Clay Cody Colby Colin Collin Connor Corey Craig Curtis
Dakota Dalton Damon Daniel Darnell Darren Darryl David Dawson DeAndre Dean Derek Derrick Desmond Devante Devin Dominic
Donovan Drew Dustin Dwayne Dylan Easton Eddie Elijah Eric Ethan Evan Garrett Gavin Grady Grant Greg Hayden Hunter
Isaac Jace Jack Jackson Jacob Jake Jalen Jamal Jamar James Jared Jarrett Jason Javon Jaylen Jayson Jeff Jeremy Jerome
Jesse Joel John Jonathan Jordan Joseph Josh Justin Kameron Keegan Keith Kendall Kendrick Kenny Kevin Khalil Kobe
Kyle Kyler Lance Landon Lawrence Logan Lucas Luke Malcolm Marcus Mario Mark Marquis Mason Matt Maurice Max Micah
Michael Miles Mitchell Myles Nathan Nick Noah Nolan Omar Owen Parker Patrick Paul Quinn Ray Reggie Ricky Riley Rob
Rodney Ronnie Russell Ryan Sam Scott Sean Seth Shane Shawn Spencer Stephen Terrance Terrell Terry Thomas Tim Travis
Trent Trevor Tristan Troy Tucker Ty Tyler Tyrone Tyson Wade Walker Wesley Will Wyatt Xavier Zach Zion""".split()

LAST_NAMES_US = """Adams Allen Anderson Armstrong Austin Bailey Baker Banks Barnes Barnett Bell Bennett Berry Bishop
Black Boyd Bradley Brewer Brooks Brown Bryant Burke Burns Bush Butler Byrd Caldwell Campbell Carpenter Carr Carroll
Carter Chambers Chapman Clark Cole Coleman Collins Cook Cooper Cox Craig Crawford Cunningham Curtis Daniels Davidson
Davis Dawson Day Dean Dixon Douglas Duncan Dunn Edwards Elliott Ellis Evans Ferguson Fields Fisher Fleming Fletcher
Ford Foster Fowler Fox Franklin Frazier Fuller Gardner Gibson Gilbert Gordon Graham Grant Gray Green Greene Gregory
Griffin Hale Hall Hamilton Hansen Hardy Harper Harris Hart Harvey Hawkins Hayes Henderson Hicks Hill Holland Holmes
Hopkins Horton Howard Howell Hudson Hughes Hunt Hunter Jackson Jacobs James Jenkins Jennings Johnson Johnston Jones
Jordan Kelley Kelly King Knight Lambert Lane Lawrence Lawson Lewis Little Long Lowe Lucas Lynch Marshall Martin Mason
Matthews Maxwell McCoy McDaniel McKinney Meyer Miles Miller Mills Mitchell Montgomery Moore Morgan Morris Morrison
Murphy Myers Neal Nelson Newman Norris Oliver Owens Palmer Parker Parks Patterson Payne Pearson Perkins Perry Peters
Peterson Phillips Pierce Porter Powell Price Reed Reese Reid Reynolds Rhodes Rice Richards Richardson Riley Roberts
Robertson Robinson Rogers Ross Russell Ryan Sanders Scott Shaw Simmons Sims Smith Snyder Spencer Stanley Steele
Stephens Stevens Stewart Stone Sullivan Sutton Taylor Terry Thomas Thompson Tucker Turner Vaughn Wade Wagner Walker
Wallace Walters Ward Warren Washington Watkins Watson Watts Weaver Webb Welch Wells West Wheeler White Whitfield
Wiggins Williams Williamson Willis Wilson Wood Woods Wright Young""".split()

SCHOOLS = ["Cascade State", "Ridgemont U", "Port Calder", "Halcyon Tech", "Eastvale A&M", "Saint Brennan",
           "Mesa Verde", "Lakeshore", "Northgate", "Redcliff", "Belgrade Academy", "Kaunas Club", "Lagos Elite",
           "Tokyo Prep", "Bayou State", "Granite U", "Pinecrest", "Westmarch", "Ocean City Prep", "Aldergrove",
           "Copper Basin", "Madrid Juniors", "Ironwood College", "Summit Christian", "G-League Ignite East",
           "Bluegrass State", "Delta Tech", "Hill Country U", "Great Lakes", "Palmetto State", "Appalachian A&M",
           "Sierra Pacific", "Prairie View Tech", "Gulf Coast", "Twin Rivers", "Badlands State", "Chesapeake"]

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
