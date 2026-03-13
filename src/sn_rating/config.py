import logging
from typing import Dict, List, Tuple

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("sn_rating")

SCORE_TO_RATING: List[Tuple[float, str]] = [
    (95, "AAA"),
    (90, "AA+"),
    (85, "AA"),
    (80, "AA-"),
    (75, "A+"),
    (70, "A"),
    (65, "A-"),
    (60, "BBB+"),
    (55, "BBB"),
    (50, "BBB-"),
    (45, "BB+"),
    (40, "BB"),
    (35, "BB-"),
    (30, "B+"),
    (25, "B"),
    (20, "B-"),
    (15, "CCC+"),
    (10, "CCC"),
    (5, "CCC-"),
    (2, "CC"),
    (0, "C"),
]

RATING_SCALE = [
    "AAA", "AA+", "AA", "AA-",
    "A+", "A", "A-",
    "BBB+", "BBB", "BBB-",
    "BB+", "BB", "BB-",
    "B+", "B", "B-",
    "CCC+", "CCC", "CCC-",
    "CC", "C",
]

RATING_WEIGHTS = {
    "quantitative": None,
    "qualitative": None,
}

DISTRESS_BANDS = {
    "interest_coverage": [
        (0.5, -4),
        (0.8, -3),
        (1.0, -2),
    ],
    "dscr": [
        (0.8, -3),
        (0.9, -2),
        (1.0, -1),
    ],
    "altman_z": [
        (1.2, -4),
        (1.5, -3),
        (1.81, -2),
    ],
}
MAX_DISTRESS_NOTCHES = -4

QUAL_SCORE_SCALE: Dict[int, float] = {
    5: 100.0,
    4: 75.0,
    3: 50.0,
    2: 25.0,
    1: 0.0,
}
