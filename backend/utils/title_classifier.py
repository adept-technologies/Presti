import re

# Standalone "AI" word boundary (handles "Head of AI", "VP of AI & Data")
_AI_WORD = re.compile(r"\bai\b", re.IGNORECASE)

# "tech / technology" only when it refers to a genuine technology function.
# The seniority keyword must appear DIRECTLY before "of? tech[nology]",
# which excludes "VP Sales - Heating Technology" (intervening words break it).
_TECH_WORD_ROLE = re.compile(
    r"\btech(?:nology)?\s+(?:officer|lead|director|head|manager|consultant|stack|architect)\b"
    r"|(?:head|director|vp|vice\s+president|chief|lead|svp|evp)\s+(?:of\s+)?tech(?:nology)?\b",
    re.IGNORECASE,
)


def classify_title(title: str) -> str:
    """
    Categorizes job titles into strategic and functional persona buckets.

    Target personas:
    - CEO: Strategic focus on company growth, vision, bottom line.
    - CTO: Strategic + technical detail (architecture, scaling, engineering).
    - CFO: Strategic + financial details (cost efficiency, ROI, OpEx).
    - Manager: Functional and tactical (sprint delivery, team bandwidth).
    - General: Catch-all cohort.
    """
    if not title:
        return "General"

    # Normalise: collapse dots so "C.E.O." → "CEO", lowercase
    title_norm = title.replace(".", "").lower()
    title_lower = title.lower()

    # ------------------------------------------------------------------
    # Pre-checks
    # ------------------------------------------------------------------

    # 1. VP / Senior VP guard — prevents "Vice President of X" from
    #    accidentally matching the CEO "president" keyword.
    is_vp = (
        "vice president" in title_lower
        or title_norm.startswith("vp ")
        or " vp " in title_norm
        or title_norm == "vp"
        or title_norm.startswith("svp")
        or "senior vice president" in title_lower
        or "executive vice president" in title_lower
    )

    # 2. "Product Owner" guard — "owner" appears in many non-CEO titles
    #    (Product Owner, Innovation Owner, Proxy Product Owner, etc.).
    _PRODUCT_OWNER_PREFIXES = (
        "product", "proxy", "innovation", "digital",
        "sw product", "senior sw product", "senior product",
    )
    is_product_owner = (
        "owner" in title_lower
        and any(p in title_lower for p in _PRODUCT_OWNER_PREFIXES)
    )

    # 3. Engineer-who-happens-to-own guard — e.g. "Software Engineer and Owner"
    _ENGINEER_ROLES = ("engineer", "developer", "programmer")
    is_engineer_owner = (
        "owner" in title_lower
        and any(e in title_lower for e in _ENGINEER_ROLES)
    )

    # ------------------------------------------------------------------
    # 1. CEO (Purely Strategic & High-Level)
    # ------------------------------------------------------------------
    if not is_vp and not is_product_owner and not is_engineer_owner and any(x in title_norm for x in [
        "ceo", "chief executive", "founder", "president",
        "co-founder", "cofounder", "owner", "managing director",
    ]):
        return "CEO"

    # ------------------------------------------------------------------
    # 2. CFO (Strategic + Financial/Cost/ROI — check before CTO)
    # ------------------------------------------------------------------
    if any(x in title_lower for x in ["cfo", "chief financial", "treasurer", "controller"]) or \
       ("finance" in title_lower and "manager" not in title_lower):
        return "CFO"

    # ------------------------------------------------------------------
    # 3. CTO (Strategic + Technical/Architecture/Roadmap Detail)
    # ------------------------------------------------------------------
    _CTO_EXPLICIT = [
        "cto", "chief technology", "chief product officer",
        "cpo", "chief architect",
    ]
    # Domain words that, with a seniority title, indicate technical leadership
    _TECH_DOMAIN_WORDS = [
        "engineering", "software", "data", "infrastructure",
        "artificial intelligence", "machine learning",
        "mlops", "devops", "platform", "backend", "frontend", "product",
    ]
    _SENIORITY = ["vp", "vice president", "director", "head", "svp", "evp"]

    is_tech_domain = (
        any(x in title_lower for x in _TECH_DOMAIN_WORDS)
        or bool(_AI_WORD.search(title_lower))          # standalone "AI"
        or bool(_TECH_WORD_ROLE.search(title_lower))   # "head of technology" etc.
    )
    is_senior = any(s in title_lower for s in _SENIORITY)

    if any(x in title_norm for x in _CTO_EXPLICIT) or (is_senior and is_tech_domain):
        return "CTO"

    # ------------------------------------------------------------------
    # 4. CFO secondary (e.g. "Finance Manager")
    # ------------------------------------------------------------------
    if "finance" in title_lower:
        return "CFO"

    # ------------------------------------------------------------------
    # 5. Manager (Tactical & Functional)
    #    Also catches: Product Owners, VPs without a tech domain (sales VP,
    #    operations VP, etc.).
    # ------------------------------------------------------------------
    if is_product_owner:
        return "Manager"

    _MANAGER_KEYWORDS = [
        "manager", "lead", "supervisor", "coordinator",
        "head", "director", "scrum", "project",
        # VP / SVP that didn't match CEO or CTO → sales/ops role
        "vice president", "svp", "evp",
    ]
    # Include bare "owner" only when it's not an engineer-owner combo
    if not is_engineer_owner and "owner" in title_lower:
        return "Manager"

    if any(x in title_lower for x in _MANAGER_KEYWORDS):
        return "Manager"

    return "General"
