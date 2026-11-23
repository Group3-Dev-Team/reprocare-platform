"""Canonical county labels and read-time compatibility for legacy spellings."""

KENYA_COUNTIES = (
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet",
    "Embu", "Garissa", "Homa Bay", "Isiolo", "Kajiado",
    "Kakamega", "Kericho", "Kiambu", "Kilifi", "Kirinyaga",
    "Kisii", "Kisumu", "Kitui", "Kwale", "Laikipia",
    "Lamu", "Machakos", "Makueni", "Mandera", "Marsabit",
    "Meru", "Migori", "Mombasa", "Murang'a", "Nairobi",
    "Nakuru", "Nandi", "Narok", "Nyamira", "Nyandarua",
    "Nyeri", "Samburu", "Siaya", "Taita-Taveta", "Tana River",
    "Tharaka-Nithi", "Trans Nzoia", "Turkana", "Uasin Gishu",
    "Vihiga", "Wajir", "West Pokot",
)

_COUNTY_NAMES = {name.lower(): name for name in KENYA_COUNTIES}
_COUNTY_ALIASES = {
    "muranga": "murang'a",
    "trans-nzoia": "trans nzoia",
    "nairobi city": "nairobi",
    "taita taveta": "taita-taveta",
    "tharaka nithi": "tharaka-nithi",
    "elgeyo marakwet": "elgeyo-marakwet",
}
_COUNTY_PREFIXES = ("wilaya ya ", "kaunti ya ")
_COUNTY_SUFFIXES = (" county", " city county")


def county_key(value: str | None) -> str:
    """Normalize known imported labels only and preserve unmatched location text."""
    key = " ".join((value or "").strip().lower().split())
    for prefix in _COUNTY_PREFIXES:
        name = key.removeprefix(prefix)
        if name != key and _COUNTY_ALIASES.get(name, name) in _COUNTY_NAMES:
            return _COUNTY_ALIASES.get(name, name)
    for suffix in _COUNTY_SUFFIXES:
        name = key.removesuffix(suffix)
        if name != key and _COUNTY_ALIASES.get(name, name) in _COUNTY_NAMES:
            return _COUNTY_ALIASES.get(name, name)
    return _COUNTY_ALIASES.get(key, key)


def county_filter_labels(value: str) -> tuple[str, ...]:
    key = county_key(value)
    if key not in _COUNTY_NAMES:
        return (key,)
    names = (key, *[alias for alias, target in _COUNTY_ALIASES.items() if target == key])
    return tuple(
        dict.fromkeys(
            [*names, *(prefix + n for prefix in _COUNTY_PREFIXES for n in names), *(n + suffix for suffix in _COUNTY_SUFFIXES for n in names)]
        )
    )
